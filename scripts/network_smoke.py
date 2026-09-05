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
import ssl
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TIMEOUT = 30
try:
    from lib.constants import PROBE_UA_SUFFIX as _PROBE
except Exception:  # running outside a repo checkout — keep the token intact
    _PROBE = "2plot-internal/probe"
# The default UA names the BROWSER lane first (template 1.6.40; muischeduler's
# finding on its item-12 port, and independently this repo's on its own): at
# dash-improve-my-llms >= 2.8 a UA with no browser engine token is classified
# crawler-lane, so a bare internal token made every default-UA check read the
# prerendered crawler document — a manifest-link or og:image check goes red the
# moment a floor moves, in CD's verify job. The internal token stays IN the
# string, after the engine token: INTERNAL_UA_TOKEN is a substring match, so
# the far side's internal-traffic exclusion still holds. CRAWLER_UA is the
# other lane and is deliberately untouched.
#
# This repo fixed the symptom first, per-check, on `installable_as_an_app`
# (the check that noticed: the crawler document carries no `<link
# rel="manifest">`, correctly, because a crawler cannot install an app). The
# template's shape is better and replaces it — the DEFAULT was the wrong lane,
# so fixing one caller left every other default-UA check one browser-document
# assertion away from the same red.
#
# 1.6.44 item 4 moves these to the `/probe` SPELLING. The outbound half was
# already here (1.6.40) — what was missing is the distinction the fleet reads
# in its logs: `2plot-internal/1.0` is this app calling a peer, and
# `2plot-internal/probe` is machinery checking a host. Same token, so the far
# side's suppression is unchanged; different word, so the log says which.
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
    + _PROBE + " network-smoke"
)
UA = BROWSER_UA
CRAWLER_UA = (
    "Mozilla/5.0 (compatible; Googlebot/2.1) " + _PROBE + " network-smoke"
)

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

# Owner-only surfaces that must 404 their llms.txt to an anonymous reader:
# every registered /admin/ page's machine twin, plus one canary. Pinned
# against the page registry by tests/test_nav_contract.py so a page added,
# renamed or deleted moves this tuple in the SAME change — /admin/traffic
# arrived in the 1.6.34 ledger round and this tuple did not notice, so the
# live battery was not checking the newest owner surface at all.
HIDDEN_DOC_PATHS = (
    "/admin/control-board/llms.txt",
    "/admin/traffic/llms.txt",
    # THE CANARY, and deliberately not registry-derived: `/admin` is not a
    # page, so nothing would ever add it. It catches a 404 that stops being
    # a real refusal — if the package ever served a directory-ish path, this
    # is the check that says so before a real admin twin leaks.
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
OG_IMAGE_WIDTH = 1200
OG_IMAGE_HEIGHT = 630

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


class SmokeSkip(Exception):
    """A check that cannot apply here — recorded as `skip`, NEVER as `pass`.

    The distinction is the whole item (1.6.44 item 5, note 88): a check that
    silently passes when its precondition is absent swept nothing, and reads
    identically to one that swept the corpus and found it clean. This battery
    had exactly that shape — `api_rows_present` answered a 404 with
    `expect(True, "")`, printing `[pass]` for a host with no /api at all.
    """


class _Headers(dict):
    """Lower-cased response headers that also remember REPEATED names.

    Both `dict(resp.headers)` and `{k: v for k, v in resp.headers.items()}`
    keep only the LAST value per name, and dash-improve-my-llms emits several
    `Link` headers — so the discovery relations were unreadable through the
    plain dict this battery used. Every existing caller wants the dict, so the
    dict is what this still is; `get_all()` is the repaired accessor.

    `get_all()` is NECESSARY AND NOT SUFFICIENT: a folded value is equally
    legal, and over HTTP/2 both discovery relations can arrive comma-joined in
    ONE `link` header. A caller counting relations must PARSE the values it
    gets back rather than count the list.
    """

    def __init__(self, pairs):
        self._all: dict = {}
        for key, value in pairs:
            self._all.setdefault(key.lower(), []).append(value)
        super().__init__({k: v[-1] for k, v in self._all.items()})

    def get_all(self, name: str) -> list:
        return list(self._all.get(name.lower(), []))


class SmokeFailure(Exception):
    pass


def _ssl_context() -> ssl.SSLContext:
    """Verify certificates via certifi when available.

    macOS Python ships without OS trust-store integration, so bare urllib
    fails every https fetch with CERTIFICATE_VERIFY_FAILED. In THIS script
    that misreads as the host being down — `fetch` re-raises after its
    retries and the battery reports a healthy satellite as unreachable.
    scripts/smoke_live.py has carried this since template 1.6.16 (spec
    SYNC-1.6.10-1.6.16 item 7); this file was missed, and a seat on macOS
    could not tell a TLS-trust gap from an outage. Verification stays ON
    either way; certifi only supplies the CA bundle.
    """
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


SSL_CONTEXT = _ssl_context()


def fetch_raw(url: str, ua: str = UA, method: str = "GET",
              body: bytes | None = None, headers: dict | None = None,
              timeout: int = TIMEOUT, retries: int = 3):
    """(status, headers, BYTES) — HTTP errors are results, not exceptions;
    network errors raise AFTER retries.

    Bytes rather than text, because one caller needs them: the social card is a
    PNG and its real dimensions live in the IHDR chunk at bytes 16..24. A
    decode with `errors="replace"` substitutes U+FFFD for every invalid byte
    and is one-way, so the header would be gone before it could be read.

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
            with urllib.request.urlopen(
                    req, timeout=timeout, context=SSL_CONTEXT) as r:
                return (r.status, _Headers(r.headers.items()), r.read())
        except urllib.error.HTTPError as e:
            return (e.code, _Headers(e.headers.items()), e.read())
        except Exception as exc:  # timeout, reset, truncated read, …
            last_exc = exc
    raise last_exc


def fetch(url: str, ua: str = UA, method: str = "GET",
          body: bytes | None = None, headers: dict | None = None,
          timeout: int = TIMEOUT, retries: int = 3):
    """(status, headers, text) — `fetch_raw` with the body decoded.

    A thin delegate ON PURPOSE. The in-process test patches ONE transport, and
    if these were two independent implementations the card check would keep
    reaching the real CDN from a unit test while everything else was stubbed.
    """
    status, hdrs, raw = fetch_raw(url, ua, method, body, headers, timeout, retries)
    return status, hdrs, raw.decode("utf-8", "replace")


def record(name: str, verdict: str, detail: str = "") -> None:
    _RESULTS.append((name, verdict, detail))
    print(f"[{verdict:>4}] {name}" + (f" — {detail}" if detail else ""), flush=True)
    if verdict == WARN and os.getenv("GITHUB_ACTIONS"):
        print(f"::warning title=network-smoke {name}::{detail}", flush=True)


def check(name: str, fn) -> None:
    try:
        fn()
        record(name, PASS)
    except SmokeSkip as exc:
        record(name, SKIP, str(exc))
    except SmokeFailure as exc:
        record(name, FAIL, str(exc))
    except Exception as exc:  # network/parse error → still a failure
        record(name, FAIL, f"{type(exc).__name__}: {exc}")


def expect(cond: bool, msg: str) -> None:
    if not cond:
        raise SmokeFailure(msg)


def skip(msg: str) -> None:
    """This check does not apply to this host. Never a pass."""
    raise SmokeSkip(msg)


# ------------------------------------------------------------- the battery --


def declared_python_minor():
    """The fleet Python this checkout declares: the Dockerfile's FROM minor.

    None when there is nothing to hold the host against — no Dockerfile
    beside this script (the script run outside a checkout) — or when the
    seat itself is off-contract: SMOKE_PYTHON_DECLARED=ignore is set by
    ci.yml's matrix boot step, whose gunicorn deliberately runs the LEG's
    interpreter (3.13/3.10), and tests/test_network_smoke.py's in-process
    seat sets it for the same reason. The seats that leave it armed are
    exactly the ones whose interpreter is a deploy artifact: the docker
    container in CI, and production in CD.
    """
    if os.environ.get("SMOKE_PYTHON_DECLARED") == "ignore":
        return None
    dockerfile = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "Dockerfile")
    try:
        with open(dockerfile, encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"FROM\s+python:(\d+\.\d+)", line)
                if m:
                    return m.group(1)
    except OSError:
        return None
    return None


def satellite_checks(base: str) -> None:
    get = lambda path, **kw: fetch(base + path, **kw)  # noqa: E731

    def healthz_ok():
        status, _, text = get("/healthz")
        expect(status == 200, f"/healthz {status}")
        expect(json.loads(text).get("ok") is True, f"unexpected body {text[:120]!r}")

    def python_matches_declared():
        # WHICH interpreter serves, versus the one this repo declares. A fork
        # could carry one Python in the Dockerfile and serve another for
        # months because nothing on the wire could contradict either —
        # /healthz's `python` field is the observability, and this check is
        # the teeth: the served minor must equal the Dockerfile's FROM minor.
        # A MISSING field is a FAIL, never a skip (spec 1.6.28): emojimart's
        # image moved to 3.14 by dependabot alone, so the cheap half of the
        # detect passed while the expensive half failed invisibly.
        status, _, text = get("/healthz")
        expect(status == 200, f"/healthz {status}")
        served = json.loads(text).get("python") or ""
        expect(bool(served), "/healthz carries no `python` field — the "
               "serving interpreter is invisible (pre-1.6.27 build?)")
        declared = declared_python_minor()
        if declared is None:
            return
        served_minor = ".".join(served.split(".")[:2])
        expect(served_minor == declared,
               f"host serves Python {served}, repo declares {declared} — "
               "a stale image, or a platform runtime nobody aligned")

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

        expect("/assets/" not in images[0],
               "the app is serving its own card — a cold container blanks the "
               "preview, and the platform caches the miss")

        # The file has to exist AND be the shape the tags promise. Read the
        # BYTES, not the decoded text: PNG stores its dimensions in the IHDR
        # chunk at bytes 16..24, which a lossy decode destroys.
        #
        # This is the check that catches a re-upload at a different size —
        # every offline test stays green while the platform reserves the box
        # the tags declare and crops the image into it. It is how the previous
        # card (1280x515, 2.49:1, and the 2plot wordmark rather than a per-site
        # card at all) went unnoticed.
        img_status, img_headers, raw = fetch_raw(OG_IMAGE_URL)
        expect(img_status == 200, f"the og:image URL returns {img_status}")
        expect(img_headers.get("content-type", "").startswith("image/"),
               f"og:image serves {img_headers.get('content-type')!r}")
        # 24 bytes is exactly the signature plus the IHDR width/height, which
        # is all this reads — `>` rather than `>=` would reject a perfectly
        # readable header for being minimal.
        expect(raw[1:4] == b"PNG" and len(raw) >= 24,
               "og:image is not a PNG (or is truncated)")
        actual_w = int.from_bytes(raw[16:20], "big")
        actual_h = int.from_bytes(raw[20:24], "big")
        expect((actual_w, actual_h) == (OG_IMAGE_WIDTH, OG_IMAGE_HEIGHT),
               f"the CDN file is {actual_w}x{actual_h}, the tags declare "
               f"{OG_IMAGE_WIDTH}x{OG_IMAGE_HEIGHT}")

    def head_get_parity_three_uas():
        """HEAD answers wherever GET does, in every lane (1.6.44 item 5).

        `/healthz` alone with one UA is NOT the test, and this repo's own kit
        says why: the prerender middleware answers a crawler-UA `HEAD /`
        before routing, so that one path returns 200 on a host whose every
        other route 405s. Probe paths that are NOT `/`, with all three UAs,
        and count the pairs so a loop that stops looping fails instead of
        passing quietly.
        """
        paths = ("/healthz", "/llms.txt", "/robots.txt", "/sitemap.xml", "/")
        agents = (("browser", BROWSER_UA), ("crawler", CRAWLER_UA),
                  ("engine", "curl/8 " + _PROBE))
        mismatches = []
        pairs = 0
        for path in paths:
            for lane, ua in agents:
                get_status, _, _ = get(path, ua=ua)
                head_status, _, _ = get(path, ua=ua, method="HEAD")
                pairs += 1
                if head_status != get_status:
                    mismatches.append(
                        f"{lane} {path}: HEAD {head_status} vs GET {get_status}"
                        + (" (no HEAD rule for this GET route)"
                           if head_status == 405 else ""))
        expect(pairs == len(paths) * len(agents),
               f"compared {pairs} pairs, expected {len(paths) * len(agents)}")
        expect(not mismatches, "; ".join(mismatches))

    def discovery_link_headers_per_lane():
        """Both lanes advertise the same discovery relations.

        Read EVERY `Link` value, not `headers['link']`: repeated headers keep
        only the last through a plain dict — which is what this battery used
        until 1.6.44 — and a folded comma-joined value is equally legal. So
        parse the relations out of everything that came back rather than
        counting the list.
        """
        wanted = {"alternate", "describedby"}
        for lane, ua in (("browser", BROWSER_UA), ("crawler", CRAWLER_UA)):
            status, headers, _ = get("/", ua=ua)
            expect(status == 200, f"{lane} GET / {status}")
            values = headers.get_all("link")
            rels = set(re.findall(r'rel="?([a-zA-Z-]+)"?', ", ".join(values)))
            expect(wanted <= rels,
                   f"{lane} lane advertises {sorted(rels) or 'no Link header'}"
                   f" — missing {sorted(wanted - rels)}")
            expect(all("/llms.txt" in v for v in values),
                   f"{lane} lane's Link headers do not point at /llms.txt: "
                   f"{values}")

    def ai_bot_posture():
        """The SERVED robots.txt against the one this app GENERATES.

        1.6.44 item 19, from the 2plot.dev proxy canary. An edge can inject,
        rewrite or replace robots.txt in perfectly valid syntax, with no tell
        beyond a comment marker — a grep for `User-agent:` sails straight
        past it. To learn what the APP declares you must generate it in
        process or read the config; to learn what the WORLD is told you fetch
        it; and WHEN THEY DIFFER, THE DIFFERENCE IS THE FINDING. Same family
        as "verify the artifact the claim is about, and say which one".

        SKIPPED where the app cannot be generated beside this script (a copy
        of the battery run against another host) — a comparison with only
        one side is not a comparison.
        """
        status, _, served = get("/robots.txt")
        expect(status == 200, f"/robots.txt {status}")

        try:
            from lib.robots_expected import expected_directives
            generated = expected_directives()
        except Exception as exc:
            skip(f"cannot generate this app's robots.txt here ({type(exc).__name__})")

        if not generated:
            skip("the app generated no directives to compare against")

        def directives(text):
            out = []
            for line in text.splitlines():
                line = line.split("#", 1)[0].strip()
                if line and ":" in line:
                    name, _, value = line.partition(":")
                    out.append((name.strip().lower(), value.strip()))
            return out

        served_directives = directives(served)
        expect(served_directives,
               "the served robots.txt carries no directives at all")

        # BOTH directions. An edge that REMOVES a directive is as much a
        # rewrite as one that adds a stanza — dropping this host's `Allow:`
        # rules for the AI search agents would be invisible to an
        # added-only comparison, and it is the change most likely to be
        # made on your behalf by a "security" default.
        #
        # MULTISETS, not membership (corrected here, leaflet 1.6.44). This
        # robots.txt carries ~16 directives of which many are the IDENTICAL
        # pair ("allow", "/") — one per AI-agent stanza. With `d not in
        # generated` over a LIST, removing ONE agent's `Allow: /` leaves the
        # other copies matching and the diff comes back empty: the exact
        # edit this row exists to catch is the one it could not see. Measured
        # on this host — the removed-directive test passed as `pass` until
        # this changed. Counter subtraction compares how MANY of each.
        from collections import Counter

        served_counts = Counter(served_directives)
        generated_counts = Counter(generated)
        injected = sorted((served_counts - generated_counts).elements())
        missing = sorted((generated_counts - served_counts).elements())
        markers = [ln.strip() for ln in served.splitlines()
                   if ln.strip().startswith("#")
                   and ("BEGIN" in ln or "Managed" in ln or "END" in ln)]
        expect(not injected and not missing and not markers,
               "the served robots.txt is not the one this app wrote"
               + (f" — {len(injected)} directive(s) the app did not "
                  f"generate, first: {injected[0]}" if injected else "")
               + (f" — {len(missing)} directive(s) the app wrote that are "
                  f"NOT served, first: {missing[0]}" if missing else "")
               + (f" — edge marker: {markers[0]!r}" if markers else ""))

    def directory_counts_are_derived():
        """The Network section lists exactly the peers the module names.

        Counts come from `lib/network_directory`, never a literal: a hard
        number in a battery stops testing the moment the fleet grows, and
        passes while doing it.
        """
        try:
            from lib.constants import BASE_URL
            from lib.network_directory import peers_for
        except Exception:
            skip("no checkout beside this script — the directory is unreadable")
        expected = {p["url"].rstrip("/") for p in peers_for(BASE_URL)}
        expect(len(expected) > 0,
               "peers_for() names no peers — nothing to hold the wire to")
        _status, _, text = get("/llms.txt")
        section = text.split("## Network", 1)[-1]
        missing = sorted(u for u in expected if u.rstrip("/") not in section)
        expect(not missing,
               f"{len(missing)} of {len(expected)} peers absent from the "
               f"/llms.txt Network section: {missing[:3]}")

    def api_llms_rows_present():
        """Note 79/80: /api can ship EMPTY at 200 — with a canonical, an h1
        and a heading — by FOUR different mechanisms (a missing
        metadata.json, a gitignored one, a package that ships none, or a
        directive whose output never reaches the machine lane). All four
        look identical from outside and none of them fail a status check.
        The invariant that catches every one is ROWS, on the machine lane
        where the content is text: the document must carry more table pipes
        than it has headings, and name a real component."""
        try:
            from lib.constants import API_PACKAGES
        except Exception:
            skip("no checkout beside this script — API_PACKAGES unreadable")
        if not API_PACKAGES:
            skip("API_PACKAGES is empty on this host — nothing to index")

        status, _, doc = get("/api/llms.txt", ua=CRAWLER_UA)
        if status == 404:
            # NEVER `expect(True, "")`, which is what stood here until 1.6.44
            # and printed `[pass]` for a host serving no /api at all. This host
            # DECLARES packages, so a 404 is a real failure; a host declaring
            # none skipped above and never reaches this line.
            expect(False, f"/api/llms.txt 404 while API_PACKAGES declares "
                          f"{list(API_PACKAGES)}")
        expect(status == 200, f"/api/llms.txt {status}")
        rows = doc.count("|")
        headings = doc.count("### ")
        expect(headings > 0, "/api/llms.txt has no component sections")
        expect(rows > headings * 4, (
            f"/api/llms.txt has {headings} component headings but only {rows} "
            "table cells — the page is heading-shaped and row-empty"
        ))

    def installable_as_an_app():
        """The manifest, and whether a browser could offer to install this.

        It shipped with empty `name`/`short_name` and icon paths pointing at
        the site root, where nothing is served — so the install prompt was
        never possible, and nothing anywhere said so.

        Reads the BROWSER document — which is now simply the default UA
        (1.6.40); a manifest link is a property of that document and of no
        other. See the BROWSER_UA comment above for why the default moved.
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
        ("python_matches_declared", python_matches_declared),
        ("llms_txt_identity", llms_txt_identity),
        ("llms_txt_names_the_hub", llms_txt_names_the_hub),
        ("page_llms_nav", page_llms_nav),
        ("hidden_pages_404", hidden_pages_404),
        ("robots_artifact_fingerprint", robots_artifact_fingerprint),
        ("sitemap_absolute_and_on_this_host", sitemap_absolute_and_on_this_host),
        ("crawler_gets_prose", crawler_gets_prose),
        ("agents_and_browsers_get_different_types",
         agents_and_browsers_get_different_types),
        ("social_card_real_pixels", social_card_is_shareable),
        ("installable_as_an_app", installable_as_an_app),
        ("head_get_parity_three_uas", head_get_parity_three_uas),
        ("api_llms_rows_present", api_llms_rows_present),
        ("discovery_link_headers_per_lane", discovery_link_headers_per_lane),
        ("directory_counts_are_derived", directory_counts_are_derived),
        ("ai_bot_posture", ai_bot_posture),
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
