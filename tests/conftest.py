"""Shared fixtures — boot the real app once, then interrogate it.

The suite deliberately exercises `run.py` itself rather than a stripped-down
app assembled for testing. Nearly everything worth catching here lives in the
wiring: registration order, which middleware runs first, whether a page's
prose survived to the response. A test app that re-implements that wiring
tests the re-implementation.

Backend selection follows `DASH_BACKEND`, so the same suite runs against
Flask, FastAPI and Quart in CI. `client` normalises the three test clients
behind `.get(path, user_agent=...) -> Response`.

SECRETLESS, AND ORDER MATTERS. The suite runs against the app exactly as CI's
zero-secret container does: no Clerk keys (auth falls open, non-public tiers
still deny), no `CROSS_APP_WEBHOOK_SECRET` (the hub client reports itself
disabled, the traffic reporter never starts a thread, and nothing is ever
POSTed to the hub), and the analytics ledger in a temp dir. The zero-secret
boot is itself the first invariant — every fail-closed assertion in
tests/test_access.py depends on it.

The env block below therefore has to run BEFORE anything imports `run.py`,
because run.py calls `load_dotenv()` at import time and a developer's local
`.env` would otherwise flip the app into a configured posture. `load_dotenv()`
never overrides an existing key, so pinning each secret to `""` here (falsy to
every `os.getenv(...) or None` reader in `lib/`) neutralises the file without
deleting it. In CI there is no `.env` at all and this is belt-and-braces. Same
pattern as 2plotai, pip-docs+ and dash-documentation-boilerplate.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import pytest

from lib.constants import BASE_URL

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# --- 1. Neutralise every secret (must precede any import of run.py) ---------
SECRET_ENV_KEYS = (
    "CLERK_SECRET_KEY", "CLERK_PUBLISHABLE_KEY", "CLERK_SIGN_IN_URL",
    "CLERK_SIGN_UP_URL", "CLERK_FRONTEND_API", "CLERK_WEBHOOK_SECRET",
    "CLERK_IS_SATELLITE", "CLERK_SATELLITE_DOMAIN", "SESSION_SECRET",
    "FLASK_SECRET_KEY", "CROSS_APP_WEBHOOK_SECRET", "NETWORK_BULLETIN_URL",
    "ADMIN_EMAILS", "MUI_PRO_API_KEY", "DATABASE_URL", "AD_DATABASE_URL",
)
for _key in SECRET_ENV_KEYS:
    os.environ[_key] = ""

# --- 1b. Pin the gate's env knobs to the shipped-dark posture ---------------
# These are not secrets, but they change what every page IS, so a developer
# who exported PAGE_DEFAULT_TIER=auth to try the gate locally would otherwise
# see two dozen unrelated tests fail on a sign-in card. Blank means "unset" to
# `lib.page_tiers._default_tier`, i.e. public — the posture the pilot deploys
# with, and the one tests/test_access.py's inertness assertions describe.
for _key in ("PAGE_DEFAULT_TIER", "PAGE_DEFAULT_VISIBILITY", "LLMS_PUBLIC_DEFAULT",
             "LLMS_SMALL_TIER", "LLMS_FULL_TIER"):
    os.environ[_key] = ""

# --- 2. Keep app state out of the repo --------------------------------------
# Without this the suite appends its own hits to the checked-out
# visitor_analytics.json, which then shows up in `git status` and, worse, in
# the next hourly rollup a developer's local run happens to send.
_TMP_STATE = tempfile.mkdtemp(prefix="leaflet-tests-")
os.environ["TRAFFIC_ANALYTICS_FILE"] = os.path.join(_TMP_STATE, "visitor_analytics.json")
os.environ["PAGE_VISIBILITY_FILE"] = os.path.join(_TMP_STATE, "page_visibility.json")
# Behind Cloudflare in production; in tests an outbound ip-api.com lookup per
# hit would make the suite depend on a third party being up.
os.environ["ANALYTICS_GEO_LOOKUP"] = "0"
# The base-URL guard and the reporter both key off these; keep them inert.
os.environ.setdefault("APP_ENV", "test")

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
CRAWLER_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

# What a real browser sends. `/<page>/llms.txt` negotiates on this header —
# not on the User-Agent — so it is what separates "a person opened the URL"
# from "an agent fetched it".
BROWSER_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"

# The body dash-improve-my-llms serves when a page has no prose registered.
# Its presence on any page is the failure this whole network cares most about.
STUB_MARKER = "This page contains interactive content that requires JavaScript"

# A real documentation page, used wherever a test needs one that is not the
# home page. Mirrors scripts/network_smoke.SAMPLE_PAGE.
SAMPLE_PAGE = "/pointer-events"


def backend() -> str:
    """Whichever backend the app will actually boot on.

    Not `os.environ["DASH_BACKEND"]` directly: run.py calls `load_dotenv()`,
    so a local .env can select a backend the bare environment knows nothing
    about. Reading the env here instead would hand out a Werkzeug test client
    for a FastAPI app, and every test would fail on the client rather than on
    the code.
    """
    from lib.backend import resolve_backend

    return resolve_backend()


@pytest.fixture(scope="session")
def app_module():
    """Import run.py as a module, from the repo root.

    run.py opens 'templates/index.html' by relative path and pages/markdown.py
    globs 'docs/**/*.md', so the process CWD has to be the repo root regardless
    of where pytest was invoked from.
    """
    os.chdir(REPO_ROOT)
    spec = importlib.util.spec_from_file_location("runmod", REPO_ROOT / "run.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["runmod"] = module
    try:
        spec.loader.exec_module(module)
    except SystemExit:  # pragma: no cover - run.py doesn't call sys.exit today
        pass
    return module


@pytest.fixture(scope="session")
def app(app_module):
    return app_module.app


def live_source(path) -> str:
    """A module's CODE, with every comment and docstring removed.

    Item 13's rule, as machinery. A detect that greps source matches the
    COMMENT explaining why the thing is absent, and stripping comments still
    leaves the DOCSTRING doing the same job — which is exactly how
    `test_the_module_carries_no_user_agent_list` went red at 1.6.44 item 8:
    a function docstring quoting `'claudebot'` to explain a measurement read
    as a resurrected User-Agent table. `ast.unparse` drops comments outright,
    and docstrings are stripped explicitly here.

    Use this for any assertion of the form "this string must not appear in
    this module", because the better the code is documented, the more
    reliably a raw grep reports the defect the documentation denies.
    """
    import ast
    from pathlib import Path

    tree = ast.parse(Path(path).read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


class Response:
    __slots__ = ("status", "text", "headers", "raw_headers")

    def __init__(self, status: int, text: str, headers=None) -> None:
        self.status = status
        self.text = text
        # The RAW (name, value) pairs, repeats intact (1.6.44 item 5). Both
        # `dict(resp.headers)` and a dict comprehension keep only the LAST
        # value per name, and dash-improve-my-llms emits several `Link`
        # headers — so a discovery-relation assertion made through `.headers`
        # below is reading one of them and calling it all of them.
        self.raw_headers = list(
            (headers or {}).items() if hasattr(headers, "items") else (headers or [])
        )
        # Headers matter from 2.2.0 on: `/<page>/llms.txt` content-negotiates,
        # so the *type* of the response is part of the contract and `Vary` is
        # what stops a CDN serving cached HTML to the next agent.
        #
        # Keys are lowercased because the three backends disagree on casing —
        # Werkzeug hands back `Content-Type`, httpx `content-type`. A plain
        # `headers.get("Content-Type")` therefore passes on Flask and fails on
        # FastAPI and Quart, which reads like a backend bug and isn't one.
        self.headers = {k.lower(): v for k, v in self.raw_headers}

    @property
    def ok(self) -> bool:
        return self.status == 200

    def header(self, name: str, default: str = "") -> str:
        return self.headers.get(name.lower(), default)

    def header_all(self, name: str) -> list:
        """EVERY value sent under this name, repeats intact.

        `header()` answers with the last one, which is what a dict can hold.
        Discovery relations arrive as several `Link` headers, so a caller
        counting them must come through here — and must still PARSE what it
        gets, because a comma-folded single header is equally legal.
        """
        want = name.lower()
        return [v for k, v in self.raw_headers if k.lower() == want]

    @property
    def content_type(self) -> str:
        return self.header("Content-Type")

    def __repr__(self) -> str:  # pragma: no cover - assertion output only
        return f"<Response {self.status} {self.content_type} {len(self.text)}b>"


class Client:
    """One synchronous `.get()` across all three backends.

    Quart's test client is async all the way down — both the request and
    `get_data()` return coroutines — so it gets driven from a loop owned by
    the fixture rather than being awaited by every test.
    """

    def __init__(self, raw, kind: str, loop=None) -> None:
        self._raw = raw
        self._kind = kind
        self._loop = loop

    def get(self, path: str, user_agent: str = BROWSER_UA, accept: str = None) -> Response:
        headers = {"User-Agent": user_agent}
        if accept is not None:
            headers["Accept"] = accept

        if self._kind == "werkzeug":
            r = self._raw.get(path, headers=headers)
            # `r.headers` is a Werkzeug Headers: iterating it yields every
            # repeat, where dict(...) would collapse them.
            return Response(r.status_code, r.get_data().decode("utf-8", "replace"),
                            list(r.headers))
            # errors="replace", not `as_text=True`: the latter decodes strictly
            # and raises UnicodeDecodeError on any binary response, so a test
            # that merely checks a favicon or a manifest icon RESOLVES would
            # blow up on the PNG's first byte. httpx (the FastAPI branch) is
            # already lenient; this matches it.

        if self._kind == "quart":
            async def fetch():
                r = await self._raw.get(path, headers=headers)
                return r.status_code, await r.get_data(as_text=True), list(r.headers)

            return Response(*self._loop.run_until_complete(fetch()))

        r = self._raw.get(path, headers=headers)
        return Response(r.status_code, r.text, list(r.headers.multi_items()))

    def head(self, path: str, user_agent: str = BROWSER_UA) -> Response:
        """The same request as `.get()`, by the other method (1.6.44 item 2).

        HEAD is the method the fleet's ASGI hosts were silently 405ing on
        EVERY route — `/healthz`, `/robots.txt`, `/sitemap.xml` included —
        because FastAPI's `APIRoute` takes `methods` literally where Werkzeug
        and `starlette.routing.Route` both derive HEAD from GET. A parity
        assertion needs to issue the real method: there is no way to observe
        that defect through `.get()`.

        A HEAD response has no body by definition, so the text is "" on every
        backend and only the status and headers carry information.
        """
        headers = {"User-Agent": user_agent}

        if self._kind == "werkzeug":
            r = self._raw.head(path, headers=headers)
            return Response(r.status_code, "", list(r.headers))

        if self._kind == "quart":
            async def fetch():
                r = await self._raw.head(path, headers=headers)
                return r.status_code, "", list(r.headers)

            return Response(*self._loop.run_until_complete(fetch()))

        r = self._raw.head(path, headers=headers)
        return Response(r.status_code, "", list(r.headers.multi_items()))


@pytest.fixture(scope="session")
def client(app):
    """A test client for whichever backend is under test.

    FastAPI/Quart need the ASGI lifespan to have run: Dash registers its page
    catch-all from the startup event, so a client used outside the lifespan
    context 404s every non-root URL for reasons that have nothing to do with
    the code under test.
    """
    kind = backend()
    if kind == "flask":
        yield Client(app.server.test_client(), "werkzeug")
    elif kind == "quart":
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            yield Client(app.server.test_client(), "quart", loop=loop)
        finally:
            loop.close()
    elif kind == "fastapi":
        from starlette.testclient import TestClient

        with TestClient(app.server) as raw:
            yield Client(raw, "httpx")
    else:  # pragma: no cover - resolve_backend() rejects anything else
        raise RuntimeError(f"unsupported DASH_BACKEND={kind!r}")


@pytest.fixture(scope="session")
def tmp_state_dir():
    """Where the app's ledger and claim files live for this run."""
    return _TMP_STATE


@pytest.fixture(scope="session")
def pages(app_module):
    """Every registered page as (path, name, entry), sorted by path."""
    import dash

    return sorted(
        ((entry["path"], entry.get("name", ""), entry) for entry in dash.page_registry.values()),
        key=lambda item: item[0],
    )


@pytest.fixture(scope="session")
def page_paths(pages):
    return [path for path, _name, _entry in pages]


# The base URL the battery is pointed at in-process. The real script takes
# `--base-url`; the harness substitutes this host's own, so a check that
# hardcoded another host would fail here rather than silently pass.
BASE = BASE_URL


# ---------------------------------------------------------------------------
# The network battery, wired to the in-process app.
#
# Lifted out of tests/test_network_smoke.py at 1.6.44 item 19: two files now
# drive this harness (the battery's own tests and the robots-posture tests),
# and a second copy would drift from this one — which is how a harness starts
# passing a check the real script would fail.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def battery():
    spec = importlib.util.spec_from_file_location(
        "network_smoke", REPO_ROOT / "scripts" / "network_smoke.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["network_smoke"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def wired(battery, client, monkeypatch):
    """Point the battery's `fetch` at the test client.

    The signature is `fetch(url, ua=..., method=..., body=..., headers=...)`
    and it returns `(status, lowercased_headers, text)`. Only GET is used by
    the satellite battery, so a non-GET here is a bug in the script rather
    than something to emulate.
    """
    seen_agents = []

    def _png_header(width: int, height: int) -> bytes:
        """The 24 bytes the card check actually reads.

        PNG signature (8) + length/type of the IHDR chunk (8) + width and
        height as big-endian uint32 (8). The battery reads bytes 16..24 and
        nothing else, so a synthetic header is a faithful stand-in for a real
        image — and it keeps the suite off the network.
        """
        return (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR"
                + width.to_bytes(4, "big") + height.to_bytes(4, "big"))

    def fetch_raw(url, ua=battery.UA, method="GET", body=None, headers=None,
                  timeout=None, retries=1):
        # HEAD joined GET at 1.6.44 item 5 (`head_get_parity_three_uas`).
        # Anything else is still a bug in the script rather than something to
        # emulate — and the assert says which method, so a future POST does
        # not read as a mysterious stub failure.
        assert method in ("GET", "HEAD"), (
            f"the satellite battery issued a {method}"
        )
        seen_agents.append(ua)
        accept = (headers or {}).get("Accept")

        # Off-host URLs — today just the CDN-hosted social card — resolve to a
        # stub at the DECLARED size, so the check passes here and still has to
        # be earned against the real CDN after a deploy. Reaching the real CDN
        # from a unit test would make the suite depend on another service.
        if not url.startswith(BASE) and "://" in url:
            return (200, {"content-type": "image/png"},
                    _png_header(battery.OG_IMAGE_WIDTH, battery.OG_IMAGE_HEIGHT))

        path = url[len(BASE):] if url.startswith(BASE) else url
        if method == "HEAD":
            response = client.head(path or "/", user_agent=ua)
        else:
            response = client.get(path or "/", user_agent=ua, accept=accept)
        # `battery._Headers`, NOT a plain dict (1.6.44 item 5). The battery's
        # discovery check calls `.get_all("link")`, and a dict keeps only the
        # last of the several `Link` headers the package emits — so a plain
        # dict here would make that check assert about one relation while
        # believing it had read them all. `raw_headers` carries the repeats.
        return (response.status, battery._Headers(response.raw_headers),
                response.text.encode())

    # `fetch_raw`, NOT `fetch`. The card check reads PNG bytes, and `fetch` is
    # a thin decoding delegate — patching it would leave `fetch_raw` reaching
    # the real CDN from a unit test, and patching only `fetch` in a repo where
    # they were separate implementations is how the boilerplate's copy of this
    # test silently kept hitting the network.
    monkeypatch.setattr(battery, "fetch_raw", fetch_raw)
    monkeypatch.setattr(battery, "_RESULTS", [])
    # This seat's interpreter is the DEVELOPER's, never a deploy artifact —
    # the in-process app answers /healthz with whatever Python is running
    # pytest, while the Dockerfile declares the fleet's. Comparing them here
    # would fail on every machine that is not coincidentally on the fleet
    # minor, and would be measuring the seat rather than the deploy. The
    # seats that leave `python_matches_declared` armed are the ones whose
    # interpreter IS the artifact: the docker container in CI (which asserts
    # the image's own Python) and production in CD. The `python` FIELD's
    # presence is still pinned here, and by tests/test_healthz_identity.py.
    monkeypatch.setattr(battery, "declared_python_minor", lambda: None)
    battery.seen_agents = seen_agents
    return battery
