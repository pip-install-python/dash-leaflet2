#!/usr/bin/env python3
"""Smoke battery for a 2plot satellite — CI container and production alike.

One script, two seats, the SAME named checks either way, so a failure in CI
and a failure against production read identically:

    CI container   python scripts/network_smoke.py --base-url http://localhost:8050
    Production     python scripts/network_smoke.py --base-url https://leaflet.2plot.dev

Stdlib-only on purpose: CI runs it from the host against the booted container
with a bare `python3`, before anything is pip-installed.

Copied from dash-documentation-boilerplate (the network template); only the
block marked "per-site" below differs. If a check outside that block is wrong,
it is wrong on twenty hosts — fix it there and re-sync.

What a satellite is to the network is what the battery proves: that it states
its identity, that its agent-facing document surfaces are real, that it runs
the intended dash-improve-my-llms artifact, and that no owner-only surface
leaks. A satellite holds no key material, so unlike the hub's copy of this
script there is no agent-key API to fail closed — the corresponding check
here is that this host's llms.txt points *back* at the hub that does.

Every UA this script sends carries the internal-traffic token (the analytics
point of truth — https://2plot.ai/docs/satellite-analytics, "Internal
traffic"): a battery must never register as a visitor or a "bot" in any
network ledger. Even the deliberately crawler-shaped probe appends the token
— the target still exercises its bot path, but its analytics know the caller
is machinery.

Exit code: 1 if any check fails, else 0.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TIMEOUT = 30
try:
    from lib.constants import INTERNAL_UA as _INTERNAL_UA
except Exception:  # running outside a repo checkout — keep the token intact
    _INTERNAL_UA = "2plot-internal/1.0 (+https://2plot.ai/docs/satellite-analytics)"
UA = _INTERNAL_UA + " network-smoke"
CRAWLER_UA = "Mozilla/5.0 (compatible; Googlebot/2.1) " + _INTERNAL_UA

# The body dash-improve-my-llms serves when a page has no prose registered.
# Matched in full, deliberately: this app's own <noscript> block legitimately
# says "requires JavaScript", and a substring check on that phrase reports a
# perfectly healthy host as broken.
STUB_MARKER = "This page contains interactive content that requires JavaScript"

# ---------------------------------------------------------------- per-site --
# The values a fork changes. Everything below this block is the network
# standard and is copied verbatim.

# This app's one identity (lib/constants.SITE_BRAND). tests/test_site_identity
# asserts every local surface carries it; this pins the DEPLOYED artifact to
# it, which is the half no unit test can reach.
SITE_H1 = "# dash-leaflet2 — Leaflet 2 maps for Dash"

# The container port. Matches the Dockerfile's EXPOSE / PORT and run.py.
DEFAULT_BASE_URL = "http://localhost:8050"

# A real documentation page, used to prove `/<page>/llms.txt` works at all.
# `/pointer-events` is a core Leaflet 2 page and is not going anywhere.
SAMPLE_PAGE = "/pointer-events"

# Owner-only surfaces that must 404 their llms.txt to an anonymous reader.
# `/admin/control-board` is this app's one hidden page (run.py calls
# `mark_hidden` on it); `/admin` is the canary for the next one added.
HIDDEN_DOC_PATHS = (
    "/admin/control-board/llms.txt",
    "/admin/llms.txt",
)

# The hub one level up the chain. A satellite's llms.txt must name it — that
# is what lets an agent walk from any leaf to the network root.
HUB_URL = "https://2plot.dev"

# The social card. Dash emits `og:image` on every page and leaves it EMPTY
# when it can find no image, which renders a blank preview on every platform
# and is invisible from inside the app — nobody sees their own unfurls. The
# URL is served from the 2plot CDN so a sleeping free-tier container never
# costs a preview. Keep in step with lib/constants.OG_IMAGE_URL.
OG_IMAGE_URL = "https://cdn.2plot.ai/github_assets/leaflet.2plot.dev.png"

# --- robots.txt fingerprint, and this site's DELIBERATE divergence -----------
# pip metadata is invisible from outside a running host, so the robots.txt
# crawler split is how a live host is proven to run the intended package.
#
# Most satellites run `block_ai_training=True`, whose 2.3.3 fingerprint is
# `ClaudeBot -> Disallow: /`. THIS SITE RUNS `block_ai_training=False` ON
# PURPOSE (see run.py's RobotsConfig): for MIT-licensed component
# documentation, being in the training corpus is how a model recommends this
# library to somebody who never visits the site. Under that config the package
# emits no ClaudeBot stanza at all — training crawlers fall under `*`.
#
# So the fingerprint checked here is the AI-search allowlist, which 2.3.2
# (OAI-SearchBot) and 2.3.3 (Claude-User, Claude-SearchBot) introduced and
# which both configs emit — plus an explicit assertion that ClaudeBot carries
# no Disallow, which is what turns the divergence from drift into a decision.
ROBOTS_ALLOWED = (
    ("OAI-SearchBot", "2.3.2"),
    ("Claude-User", "2.3.3"),
    ("Claude-SearchBot", "2.3.3"),
    ("ChatGPT-User", "2.3.2"),
    ("PerplexityBot", "2.3.2"),
)
BLOCK_AI_TRAINING = False

# ---------------------------------------------------------------------------

PASS, FAIL, WARN, SKIP = "pass", "FAIL", "warn", "skip"
_RESULTS: list[tuple[str, str, str]] = []  # (name, verdict, detail)


class SmokeFailure(Exception):
    pass


def fetch(url: str, ua: str = UA, method: str = "GET",
          body: bytes | None = None, headers: dict | None = None,
          timeout: int = TIMEOUT, retries: int = 3):
    """(status, headers, text) — HTTP errors are results, not exceptions;
    network errors raise AFTER retries.

    Response headers come back lower-cased: gunicorn sends `content-type`,
    proxies often re-case it — callers must not care.
    """
    last_exc: Exception | None = None
    for attempt in range(retries):
        if attempt:
            time.sleep(2 * attempt)
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header("User-Agent", ua)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return (r.status, {k.lower(): v for k, v in r.headers.items()},
                        r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            return (e.code, {k.lower(): v for k, v in e.headers.items()},
                    e.read().decode("utf-8", "replace"))
        except Exception as exc:  # timeout, reset, truncated read, …
            last_exc = exc
    raise last_exc


def record(name: str, verdict: str, detail: str = "") -> None:
    _RESULTS.append((name, verdict, detail))
    print(f"[{verdict:>4}] {name}" + (f" — {detail}" if detail else ""), flush=True)
    if verdict == WARN and os.getenv("GITHUB_ACTIONS"):
        print(f"::warning title=network-smoke {name}::{detail}", flush=True)


def check(name: str, fn) -> None:
    try:
        fn()
        record(name, PASS)
    except SmokeFailure as exc:
        record(name, FAIL, str(exc))
    except Exception as exc:  # network/parse error → still a failure
        record(name, FAIL, f"{type(exc).__name__}: {exc}")


def expect(cond: bool, msg: str) -> None:
    if not cond:
        raise SmokeFailure(msg)


# ------------------------------------------------------------- the battery --

def satellite_checks(base: str) -> None:
    get = lambda path, **kw: fetch(base + path, **kw)  # noqa: E731

    def healthz_ok():
        status, _, text = get("/healthz")
        expect(status == 200, f"/healthz {status}")
        expect(json.loads(text).get("ok") is True, f"unexpected body {text[:120]!r}")

    def llms_txt_identity():
        # The check this whole standard exists for. The H1 is what an agent
        # fetching /llms.txt cold reads as the name of this site, and a
        # pre-2.3.4 artifact publishes `app.title` (or a bare "Dash") there
        # with nothing else looking wrong.
        status, headers, text = get("/llms.txt")
        expect(status == 200, f"/llms.txt {status}")
        ct = headers.get("content-type", "")
        expect(ct.startswith("text/markdown"), f"content-type {ct!r}")
        first = text.splitlines()[0] if text else ""
        expect(first == SITE_H1, f"H1 {first!r} — identity regression?")
        expect("## Pages" in text, "page index section missing")
        expect("## Network" in text, "cross-host directory missing")

    def llms_txt_names_the_hub():
        _status, _, text = get("/llms.txt")
        expect(HUB_URL in text, f"the directory does not name {HUB_URL}")

    def page_llms_nav():
        status, _, text = get(f"{SAMPLE_PAGE}/llms.txt")
        expect(status == 200, f"{SAMPLE_PAGE}/llms.txt {status}")
        expect("/llms.txt" in text, "llms_nav header missing — page doc is a dead end")

    def hidden_pages_404():
        for path in HIDDEN_DOC_PATHS:
            status, _, _ = get(path)
            expect(status == 404, f"{path} {status} (owner surface leaked)")

    def robots_artifact_fingerprint():
        status, _, text = get("/robots.txt")
        expect(status == 200, f"/robots.txt {status}")
        lines = [ln.strip() for ln in text.splitlines()]

        def rule(agent):
            marker = f"User-agent: {agent}"
            expect(marker in lines, f"{marker} stanza missing")
            return lines[lines.index(marker) + 1]

        for agent, since in ROBOTS_ALLOWED:
            got = rule(agent)
            expect(got == "Allow: /",
                   f"{agent} -> {got!r}, expected 'Allow: /': pre-{since} artifact")

        # The divergence, pinned. If someone flips `block_ai_training` in
        # run.py without meaning to, this is the check that says so.
        if not BLOCK_AI_TRAINING:
            expect("User-agent: ClaudeBot" not in lines,
                   "a ClaudeBot stanza appeared — block_ai_training flipped to "
                   "True? This site allows AI training on purpose (run.py)")
        else:  # pragma: no cover - the other posture, kept so a flip is one line
            expect(rule("ClaudeBot") == "Disallow: /",
                   "ClaudeBot is not blocked despite block_ai_training=True")

        expect(any(ln.startswith("Sitemap:") for ln in lines), "Sitemap line missing")

    def sitemap_absolute_and_on_this_host():
        status, _, text = get("/sitemap.xml")
        expect(status == 200, f"/sitemap.xml {status}")
        expect("<loc>https://" in text or "<loc>http://" in text,
               "no absolute <loc> URLs")
        for path in HIDDEN_DOC_PATHS:
            leaked = path.rsplit("/llms.txt", 1)[0]
            expect(leaked not in text, f"hidden path {leaked} leaked into sitemap")

    def crawler_gets_prose():
        # The prerender. A crawler that receives the JavaScript stub indexes
        # nothing, and the page looks perfect in a browser the whole time.
        status, _, text = get("/", ua=CRAWLER_UA)
        expect(status == 200, f"/ {status}")
        expect("<title>" in text, "crawler HTML has no <title>")
        expect(STUB_MARKER not in text,
               "the home page served the JavaScript stub to a crawler")
        expect('rel="canonical"' in text, "no canonical tag for a crawler")

    def agents_and_browsers_get_different_types():
        # One URL, two audiences, and a `Vary` that stops a CDN mixing them.
        status, md_headers, md = get(f"{SAMPLE_PAGE}/llms.txt")
        expect(status == 200, f"{SAMPLE_PAGE}/llms.txt {status}")
        expect(md_headers.get("content-type", "").startswith("text/markdown"),
               f"agents got {md_headers.get('content-type')!r}")
        expect("<!DOCTYPE html>" not in md, "viewer chrome reached an agent")

        _status, html_headers, html = get(
            f"{SAMPLE_PAGE}/llms.txt",
            headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
        expect("text/html" in html_headers.get("content-type", ""),
               f"browsers got {html_headers.get('content-type')!r}")
        expect("mk-wordmark" in html, "the network wordmark is missing")

        for label, headers in (("markdown", md_headers), ("html", html_headers)):
            expect("accept" in headers.get("vary", "").lower(),
                   f"no Vary: Accept on the {label} variant — a shared cache "
                   "may serve it to everyone")

    def social_card_is_shareable():
        """The link preview, which nobody on the team ever sees.

        Checked against the deployed host because every part of it can break
        without the app noticing: an empty `og:image` (Dash's default when it
        finds no image) renders a blank card, and a CDN asset that starts
        404ing takes every preview with it while the site itself looks fine.
        """
        status, _, html = get("/")
        expect(status == 200, f"/ {status}")

        images = re.findall(
            r'<meta[^>]+property="og:image"[^>]*content="([^"]*)"', html)
        expect(bool(images), "no og:image tag at all")
        expect(all(src.strip() for src in images),
               "og:image is EMPTY — the link preview renders a blank card")
        expect(len(images) == 1, f"{len(images)} og:image tags — scrapers pick one")
        expect(images[0] == OG_IMAGE_URL, f"og:image is {images[0]!r}")

        twitter = re.findall(
            r'<meta[^>]+(?:property|name)="twitter:image"[^>]*content="([^"]*)"', html)
        expect(bool(twitter) and all(t.strip() for t in twitter),
               "twitter:image is missing or empty")

        # The image has to actually exist. A 404 here is the whole card.
        img_status, img_headers, _ = fetch(OG_IMAGE_URL)
        expect(img_status == 200, f"the og:image URL returns {img_status}")
        expect(img_headers.get("content-type", "").startswith("image/"),
               f"og:image serves {img_headers.get('content-type')!r}")

    def installable_as_an_app():
        """The manifest, and whether a browser could offer to install this.

        It shipped with empty `name`/`short_name` and icon paths pointing at
        the site root, where nothing is served — so the install prompt was
        never possible, and nothing anywhere said so.
        """
        _status, _, html = get("/")
        match = re.search(r'<link[^>]+rel="manifest"[^>]+href="([^"]+)"', html)
        expect(bool(match), "no manifest link — the app cannot be installed")

        status, _, body = get(match.group(1))
        expect(status == 200, f"the manifest returns {status}")
        manifest = json.loads(body)
        expect(bool(manifest.get("name", "").strip()), "manifest name is empty")
        expect(bool(manifest.get("short_name", "").strip()), "short_name is empty")
        expect(bool(manifest.get("start_url")), "no start_url")

        icons = manifest.get("icons") or []
        expect(bool(icons), "the manifest declares no icons")
        for icon in icons:
            icon_status, _, _ = get(icon["src"])
            expect(icon_status == 200,
                   f"manifest icon {icon['src']} returns {icon_status}")

    for name, fn in (
        ("healthz_ok", healthz_ok),
        ("llms_txt_identity", llms_txt_identity),
        ("llms_txt_names_the_hub", llms_txt_names_the_hub),
        ("page_llms_nav", page_llms_nav),
        ("hidden_pages_404", hidden_pages_404),
        ("robots_artifact_fingerprint", robots_artifact_fingerprint),
        ("sitemap_absolute_and_on_this_host", sitemap_absolute_and_on_this_host),
        ("crawler_gets_prose", crawler_gets_prose),
        ("agents_and_browsers_get_different_types",
         agents_and_browsers_get_different_types),
        ("social_card_is_shareable", social_card_is_shareable),
        ("installable_as_an_app", installable_as_an_app),
    ):
        check(name, fn)


# ------------------------------------------------------------------- main --

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                    help="the satellite under test (default: the CI container)")
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    print(f"network-smoke → {base}\n")
    satellite_checks(base)

    counts = {v: sum(1 for _, verdict, _ in _RESULTS if verdict == v)
              for v in (PASS, FAIL, WARN, SKIP)}
    print(f"\n{counts[PASS]} passed, {counts[FAIL]} failed, "
          f"{counts[WARN]} warnings, {counts[SKIP]} skipped")
    return 1 if counts[FAIL] else 0


if __name__ == "__main__":
    sys.exit(main())
