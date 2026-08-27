#!/usr/bin/env python3
"""Post-deploy checks against a *live* satellite.

    python scripts/smoke_live.py https://leaflet.2plot.dev

Everything here fails silently in production if it isn't checked. A wrong
canonical host doesn't error, it deindexes; a stub body doesn't error, it
serves crawlers nothing; a dead peer link doesn't error, it just teaches an
agent that this network's directory isn't worth following.

Run in CD after every deploy, and by hand against any satellite you're
upgrading. Exit code is the number of failed checks, capped at 125.

Only the standard library, so it runs anywhere without an install step.
"""

from __future__ import annotations

import os
import re
import sys
import ssl
import html as html_lib
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Every UA below carries the network's internal-traffic token (the analytics
# point of truth — https://2plot.ai/docs/satellite-analytics, "Internal
# traffic"). A post-deploy battery runs on every push and sweeps every peer in
# the directory; without the token it registers as a burst of visitors, and
# the crawler-shaped probes register as crawler interest. The Googlebot and
# Chrome tokens are still there, so the target exercises exactly the path
# being tested — it just knows the caller is machinery.
try:
    from lib.constants import INTERNAL_UA as _INTERNAL_UA
except Exception:  # pragma: no cover — running outside a repo checkout
    _INTERNAL_UA = "2plot-internal/1.0 (+https://2plot.ai/docs/satellite-analytics)"

CRAWLER_UA = (
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html) "
    + _INTERNAL_UA
)
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 " + _INTERNAL_UA
)
# `/<page>/llms.txt` negotiates on Accept, not on the User-Agent.
BROWSER_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
STUB_MARKER = "This page contains interactive content that requires JavaScript"
# Rendered chrome, not the bare class name — a Markdown page may legitimately
# discuss `dv-banner` (this network has one that does); it can never contain
# the element.
CHROME = re.compile(r'<[a-z]+ class="dv-banner')
TIMEOUT = 30
# Attempts per URL for NETWORK-level errors only — see `fetch`.
#
# Env-overridable since the 1.6.28 contract (spec SYNC-1.6.22-1.6.29 item 6):
# these were hardcoded here, which is how muischeduler ran a 1.2.4-vintage
# copy against a free-tier host with no way to widen the window from CD.
# Generous by default on purpose — a free-tier cold start routinely takes
# 60-90s, and the only cost of a wide window is paid when the host is
# actually down, because a warm host passes the first probe.
RETRIES = max(1, int(os.getenv("SMOKE_FETCH_RETRIES") or 3))
WAKE_ATTEMPTS = max(1, int(os.getenv("SMOKE_WAKE_ATTEMPTS") or 24))
WAKE_INTERVAL_S = max(0.0, float(os.getenv("SMOKE_WAKE_INTERVAL_S") or 10))


def _ssl_context() -> ssl.SSLContext:
    """Verify certificates via certifi when available.

    macOS Python ships without OS trust-store integration, so bare urllib
    fails every https fetch with CERTIFICATE_VERIFY_FAILED — which reads as
    "the whole site is down" (every check 0s). Same fix as audit_links.py.
    Verification stays ON either way; certifi only supplies the CA bundle.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


SSL_CONTEXT = _ssl_context()

failures: List[str] = []
warnings: List[str] = []
checks_run = 0


def fetch(
    url: str,
    user_agent: str = BROWSER_UA,
    accept: Optional[str] = None,
    retries: Optional[int] = None,
    timeout: float = TIMEOUT,
) -> Tuple[int, str, Dict[str, str]]:
    """Returns (status, body, headers).

    Headers are part of the contract from 2.2.0 on: `/<page>/llms.txt`
    content-negotiates, so which *type* came back is the thing being checked,
    and `Vary` is what stops a CDN handing cached HTML to the next agent.

    NETWORK-LEVEL failures are retried; HTTP statuses are not. The distinction
    matters because this script makes ~17 requests in a burst against a host on
    Render's free tier, which sleeps after ~15 minutes idle — so one cold start
    or one dropped connection used to surface as `FAIL canonical on /<page>`,
    a check that had never actually run. A misdiagnosed failure is worse than a
    slow one: it sends you looking at canonical tags that were correct all
    along. A real 404 or 500 still fails on the first response, immediately.
    """
    headers = {"User-Agent": user_agent}
    if accept is not None:
        headers["Accept"] = accept
    request = urllib.request.Request(url, headers=headers)
    last: Exception | None = None
    attempts = RETRIES if retries is None else max(1, retries)
    for attempt in range(attempts):
        if attempt:
            time.sleep(2 * attempt)
        try:
            with urllib.request.urlopen(
                request, timeout=timeout, context=SSL_CONTEXT
            ) as response:
                body = response.read().decode("utf-8", "replace")
                return response.status, body, dict(response.headers)
        except urllib.error.HTTPError as exc:
            # The STATUS is the answer; the body is a bonus. Reading it can
            # itself raise — a peer that 502s mid-body raises IncompleteRead
            # here — and an exception escaping `fetch` takes the whole script
            # down. That turns one sick peer into a dead CD run, which is
            # exactly what the fatal/warn split in `check()` exists to prevent.
            try:
                body = exc.read().decode("utf-8", "replace")
            except Exception:  # noqa: BLE001 - truncated or already-closed body
                body = ""
            return exc.code, body, dict(exc.headers or {})
        except Exception as exc:  # noqa: BLE001 - DNS, TLS, timeouts all land here
            last = exc
    return 0, f"{type(last).__name__}: {last}", {}


def header(headers: Dict[str, str], name: str) -> str:
    """Case-insensitive header lookup — proxies rewrite the casing."""
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def check(name: str, passed: bool, detail: str = "", fatal: bool = True) -> None:
    """Record one check. ``fatal=False`` warns instead of failing the deploy.

    The distinction is a policy, not a convenience: **a check about THIS host
    is fatal; a check about somebody else's host is a warning.**

    Peer reachability is the only thing in this script that fails on someone
    else's infrastructure, and gating a deploy on it is shared fate — one peer
    with an expired certificate turns every satellite in the network red, none
    of them can ship, and the people who see it learn that red CD means
    nothing. The information is still worth having (a directory of dead links
    degrades silently and nothing else reports it), so it is surfaced as a
    warning and, under Actions, as an annotation on the run summary.
    """
    global checks_run
    checks_run += 1
    if passed:
        print(f"  ok    {name}")
    elif fatal:
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))
        failures.append(name)
    else:
        print(f"  warn  {name}" + (f" — {detail}" if detail else ""))
        warnings.append(f"{name}" + (f" — {detail}" if detail else ""))
        if os.getenv("GITHUB_ACTIONS"):
            print(f"::warning title=peer unreachable::{name} — {detail}")


def wake(base: str) -> bool:
    """Poll `/healthz` until the host actually answers.

    A sleeping free-tier host greets its first visitor with the platform's
    loading page or a hang, and the first visitor after a deploy is this
    battery — so without this loop the opening checks fail on a perfectly
    healthy site, and the CD log blames whichever check happened to run
    first. Requiring `ok: true` rather than any 200 keeps the loading page
    (and a CDN error page, which is also a 200) from counting as awake.

    Each probe is single-shot with a short timeout: the loop IS the retry
    ladder here, and per-probe printing is what makes a slow start readable
    in the CD log rather than a silent multi-minute stall.
    """
    url = f"{base}/healthz"
    for attempt in range(1, WAKE_ATTEMPTS + 1):
        try:
            status, body, _ = fetch(url, retries=1, timeout=10)
        except TypeError:
            # A legacy `fetch` stub — the pre-1.6.2x `(url, user_agent,
            # accept)` signature — from a test that monkeypatches fetch
            # without patching wake. The real fetch cannot raise TypeError
            # (its signature takes these kwargs and everything inside its
            # attempt loop is caught), so this branch can only be a stub's
            # signature binding. Probe bare rather than take a whole suite
            # down: the 1.6.28 fan-out went red on 7 of 12 forks exactly
            # here (spec SYNC-1.6.22-1.6.29 item 6).
            status, body, _ = fetch(url)
        if status == 200 and re.search(r'"ok"\s*:\s*true', body):
            print(f"  wake  attempt {attempt}/{WAKE_ATTEMPTS}: up")
            return True
        detail = f"HTTP {status}" if status else body[:80]
        print(f"  wake  attempt {attempt}/{WAKE_ATTEMPTS}: {detail}", flush=True)
        if attempt < WAKE_ATTEMPTS:
            time.sleep(WAKE_INTERVAL_S)
    return False


def main(base: str) -> int:
    base = base.rstrip("/")
    host = urlparse(base).netloc
    print(f"Smoke-testing {base}\n")

    # --- 0. Wake the host before asserting anything about it ---------------
    print("Wake-up")
    if not wake(base):
        # ONE clear failure, not a cascade: sixty per-check failures against
        # a host that never answered all say the same thing and bury it.
        check(
            "host answered /healthz",
            False,
            f"never woke after {WAKE_ATTEMPTS} probes ~{WAKE_INTERVAL_S:g}s "
            "apart — nothing else was tested",
        )
        print(f"\n0/{checks_run} checks passed")
        print("\nFailed:")
        for name in failures:
            print(f"  - {name}")
        return min(len(failures), 125)

    # --- 1. The site is up, and llms.txt is the index it should be ---------
    print("Core surfaces")
    status, home, _ = fetch(f"{base}/")
    check("home page responds 200", status == 200, f"got {status}")

    status, llms, llms_headers = fetch(f"{base}/llms.txt")
    check("/llms.txt responds 200", status == 200, f"got {status}")
    check("/llms.txt lists pages", "## Pages" in llms or "# " in llms)
    check("/llms.txt publishes the network directory", "## Network" in llms)

    status, robots, _ = fetch(f"{base}/robots.txt")
    check("/robots.txt responds 200", status == 200, f"got {status}")
    check(
        "/robots.txt points at this host's sitemap",
        f"Sitemap: {base}/sitemap.xml" in robots,
        "sitemap line missing or pointing elsewhere",
    )
    # The artifact fingerprint. pip metadata is invisible from outside, so
    # these robots.txt stanzas are how a live host is proven to run the
    # intended dash-improve-my-llms: 2.3.2 introduced the OAI-SearchBot /
    # ChatGPT-User / PerplexityBot allowlist, 2.3.3 added Claude-User and
    # Claude-SearchBot.
    #
    # PER-SITE: most satellites also expect `ClaudeBot -> Disallow: /`, the
    # 2.3.3 training-crawler split. This host runs `block_ai_training=False`
    # ON PURPOSE (run.py's RobotsConfig — for MIT-licensed component docs,
    # being in the training corpus is how a model recommends the library), and
    # under that config the package emits no ClaudeBot stanza at all. The
    # absence is asserted below so a silent flip of that flag is still caught.
    robots_lines = robots.splitlines()

    def robots_rule(agent: str) -> str:
        marker = f"User-agent: {agent}"
        if marker not in robots_lines:
            return "(missing)"
        idx = robots_lines.index(marker)
        following = robots_lines[idx + 1: idx + 2]
        return following[0] if following else "(missing)"

    for agent, expected, since in (
        ("OAI-SearchBot", "Allow: /", "2.3.2"),
        ("ChatGPT-User", "Allow: /", "2.3.2"),
        ("PerplexityBot", "Allow: /", "2.3.2"),
        ("Claude-User", "Allow: /", "2.3.3"),
        ("Claude-SearchBot", "Allow: /", "2.3.3"),
    ):
        got = robots_rule(agent)
        check(
            f"/robots.txt {agent} -> {expected.split(':')[0]} ({since} artifact fingerprint)",
            got == expected,
            f"got {got}: this host runs a pre-{since} artifact",
        )

    check(
        "/robots.txt keeps this site's deliberate open-training posture",
        "User-agent: ClaudeBot" not in robots_lines,
        "a ClaudeBot stanza appeared — block_ai_training flipped to True?",
    )

    status, sitemap, _ = fetch(f"{base}/sitemap.xml")
    check("/sitemap.xml responds 200", status == 200, f"got {status}")
    page_urls = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    check("/sitemap.xml lists pages", bool(page_urls), "no <loc> entries")
    foreign = [u for u in page_urls if urlparse(u).netloc != host]
    check("/sitemap.xml stays on this host", not foreign, f"foreign URLs: {foreign[:3]}")

    status, health, _ = fetch(f"{base}/healthz")
    check("/healthz responds 200", status == 200, f"got {status}")

    # --- 2. Canonical host — the failure that deindexes a satellite --------
    print("\nCanonical tags")
    for url in [f"{base}/"] + page_urls[:8]:
        _status, html, _ = fetch(url, CRAWLER_UA)
        found = re.findall(r'rel="canonical"\s+href="([^"]*)"', html)
        check(
            f"canonical on {urlparse(url).path or '/'}",
            len(found) == 1 and urlparse(found[0]).netloc == host,
            f"got {found}",
        )

    # --- 3. No page serves the JavaScript stub ----------------------------
    print("\nCrawler bodies")
    for url in [f"{base}/"] + page_urls[:8]:
        _status, html, _ = fetch(url, CRAWLER_UA)
        check(
            f"real content on {urlparse(url).path or '/'}",
            STUB_MARKER not in html,
            "served the JavaScript stub",
        )

    # --- 3c. Crawler/browser identity parity ------------------------------
    # Every SEO defect measured across the fleet in 2026-08 was one bug in
    # different clothes: the head a crawler received had drifted from the head
    # a browser received — 4-7 icon links vs zero, "site | page" vs a bare
    # page name, og:image vs nothing. Content may differ between the two
    # documents (that is what the prerender is for); IDENTITY may not. This
    # block is the single assertion that would have caught all of it.
    print("\nCrawler/browser identity parity")

    def identity(doc: str) -> Dict[str, object]:
        # Icons compare as the SET of declared sizes, not a raw link count:
        # Dash auto-injects one extra favicon link (with a cache-busting
        # query) into the browser head, so counts differ by one forever while
        # the actual identity — which sizes a consumer can pick from — is
        # what the two heads must agree on.
        icon_links = re.findall(
            r'<link[^>]+rel="(?:icon|apple-touch-icon)"[^>]*>', doc)
        # Unescape before comparing: one side may write an apostrophe as
        # &#x27; and the other verbatim — same identity, different escaping.
        unescape = html_lib.unescape
        return {
            "icon sizes": sorted(
                {z for link in icon_links
                 for z in re.findall(r'sizes="([^"]+)"', link)}
            ),
            "title": unescape(
                (re.findall(r"<title>(.*?)</title>", doc, re.S) or [""])[0].strip()
            ),
            "og:image": sorted({
                unescape(u) for u in re.findall(
                    r'property="og:image"[^>]+content="([^"]*)"', doc)
            }),
            "twitter:card": sorted({
                unescape(v) for v in re.findall(
                    r'name="twitter:card"[^>]+content="([^"]*)"', doc)
            }),
        }

    for url in [f"{base}/"] + page_urls[:3]:
        path = urlparse(url).path or "/"
        _status, crawler_html, _ = fetch(url, CRAWLER_UA)
        _status, browser_html, _ = fetch(url, BROWSER_UA)
        seen_c, seen_b = identity(crawler_html), identity(browser_html)
        for field in ("icon sizes", "title", "og:image", "twitter:card"):
            check(
                f"{path}: crawler and browser agree on {field}",
                seen_c[field] == seen_b[field] and seen_c[field] not in (0, "", []),
                f"crawler={seen_c[field]!r} browser={seen_b[field]!r}",
            )
        check(
            f"{path}: crawlers get an icon >=192px",
            'sizes="192x192"' in crawler_html or 'sizes="512x512"' in crawler_html,
            "no >=192px icon link in the crawler head — Google's preferred size",
        )

    # --- 4. Content negotiation on llms.txt -------------------------------
    # Production is where this can break in ways development cannot show: a
    # CDN sitting in front of the app is free to ignore `Vary` and serve one
    # cached variant to everyone. Chrome leaking into the Markdown makes every
    # agent in the network pay tokens for decoration and appears in no
    # dashboard; the Markdown leaking into a browser just looks unfinished.
    print("\nContent negotiation")
    check(
        "/llms.txt serves Markdown to a plain request",
        not CHROME.search(llms) and "<!DOCTYPE html>" not in llms,
        "the viewer chrome reached an agent",
    )

    page_doc = next(
        (f"{u.rstrip('/')}/llms.txt" for u in page_urls if urlparse(u).path not in ("", "/")),
        f"{base}/llms.txt",
    )

    status, doc, doc_headers = fetch(page_doc)
    check(f"{urlparse(page_doc).path} responds 200", status == 200, f"got {status}")
    check(
        "agents get text/markdown",
        "text/markdown" in header(doc_headers, "Content-Type"),
        header(doc_headers, "Content-Type") or "no Content-Type",
    )
    check(
        "agents get no viewer chrome",
        not CHROME.search(doc) and "<!DOCTYPE html>" not in doc,
        "the viewer chrome reached an agent",
    )
    check(
        "page document is not a dead end",
        f"{base}/llms.txt" in doc,
        "no route back to the site index",
    )

    status, view, view_headers = fetch(page_doc, accept=BROWSER_ACCEPT)
    check(
        "browsers get text/html",
        "text/html" in header(view_headers, "Content-Type"),
        header(view_headers, "Content-Type") or "no Content-Type",
    )
    check("the viewer renders the network wordmark", "mk-wordmark" in view)
    check(
        "the viewer is noindex",
        bool(re.search(r'<meta[^>]+name="robots"[^>]+noindex', view)),
        "the rendered view would compete with the page it documents",
    )

    # Both variants, because a cache keys on the request that populated it.
    for label, headers in (("markdown", doc_headers), ("html", view_headers)):
        check(
            f"Vary: Accept on the {label} variant",
            "accept" in header(headers, "Vary").lower(),
            f"Vary: {header(headers, 'Vary') or '(absent)'} — a shared cache "
            "may serve this variant to everyone",
        )

    # --- 5. Every peer in the directory resolves --------------------------
    # A directory of dead links degrades quietly, and nothing else will tell
    # you — so this is still worth checking on every deploy. But it is the ONE
    # section that tests hosts this deployment does not control, so it warns
    # rather than fails. See `check()` for why. That the directory is
    # *published at all* is this host's job, so that check stays fatal.
    print("\nNetwork directory")
    # `[` `]` `(` are excluded, not just whitespace: the 2.2.0 nav block writes
    # links as `[https://host/llms.txt](https://host/llms.txt)`, and a class
    # that stops only at `)` swallows the label and the opening paren into one
    # malformed URL — which then 404s and fails a perfectly good deploy.
    peer_docs = sorted(set(re.findall(r"https://[^\s()\[\]\"'<>]+/llms\.txt", llms)))
    check("directory lists peer llms.txt URLs", bool(peer_docs), "none found")
    for url in peer_docs:
        if url.startswith(base):
            continue
        status, body, headers = fetch(url)
        # A 200 is not enough. A Dash app answers its catch-all with the SPA
        # shell for *any* unmatched path, so a host that does not serve
        # llms.txt at all still returns 200 text/html — and a status-only
        # check passes on every one of them. Verified on 2plot.dev, where
        # /api/this-endpoint-cannot-exist also returns 200 text/html.
        is_html = "text/html" in header(headers, "Content-Type").lower() or (
            body.lstrip()[:15].lower().startswith("<!doctype html")
        )
        if status != 200:
            check(f"peer reachable: {url}", False, f"got {status}", fatal=False)
        else:
            check(
                f"peer serves a document: {url}",
                not is_html,
                "200, but HTML — that host's catch-all, not an llms.txt",
                fatal=False,
            )

    passed = checks_run - len(failures) - len(warnings)
    summary = f"\n{passed}/{checks_run} checks passed"
    if warnings:
        summary += f", {len(warnings)} warnings (peers — not this deployment)"
    print(summary)

    if warnings:
        print("\nWarned:")
        for name in warnings:
            print(f"  - {name}")

    if failures:
        print("\nFailed:")
        for name in failures:
            print(f"  - {name}")
        return min(len(failures), 125)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
