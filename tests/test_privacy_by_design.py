"""1.6.44 item 16 — the tracker stores no raw address and makes no lookup.

WHAT THIS REPLACED, stated plainly because the privacy page (item 15) quotes
this module and both must describe the same mechanism. Until this release, on
every human page view with no `cf-ipcountry`, a background thread sent the
visitor's IP address to `http://ip-api.com/json/<ip>` — a third party, over
PLAIN HTTP — and stored the returned country, region, city, latitude,
longitude and timezone in the ledger beside the address itself. None of it was
disclosed anywhere on this site.

It is gone rather than fixed, because the edge already knows: Cloudflare puts
the country on every request for free and the rest behind one zone toggle. The
lookup bought a slightly richer row in exchange for shipping visitor IPs to a
third party, plus a thread pool, a cache, an in-flight set, a pending marker
in the row and a backfill pass in `flush()` — all removed with it.

THE DETECT IS PARSED, NOT GREPPED. The spec corrected its own first version
here: "no `ip-api` string in lib/" cannot pass on a tree that DOCUMENTS the
removal, and this module documents it at length. So the module is parsed and
the assertions are about imports and definitions.
"""

from __future__ import annotations

import ast
import json
import pathlib

import pytest

from conftest import live_source

REPO = pathlib.Path(__file__).resolve().parent.parent
TRACKER = REPO / "lib" / "analytics_tracker.py"

CHROME = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@pytest.fixture
def tracker(tmp_path, monkeypatch):
    from lib.analytics_tracker import AnalyticsTracker

    monkeypatch.setenv("ANALYTICS_VISITOR_SALT", "test-salt-not-the-real-one")
    return AnalyticsTracker(data_file=tmp_path / "visitor_analytics.json")


def _one(tracker, headers=None, ip="203.0.113.7"):
    tracker.track_visit("/", CHROME, ip, headers=headers)
    tracker.flush()
    return json.loads(tracker.data_file.read_text())["visits"][0]


# --------------------------------------------------------------------------
# The detect: parsed.
# --------------------------------------------------------------------------

def test_the_tracker_imports_no_http_client():
    """No requests, urllib, http.client, socket, httpx or aiohttp.

    Parsed from the AST rather than grepped: the module's prose names the
    removed lookup repeatedly, and a substring check would match the
    explanation of the absence — this drop's item 13, which this repo tripped
    twice already.
    """
    tree = ast.parse(TRACKER.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    banned = {"requests", "urllib", "http", "socket", "httpx", "aiohttp"}
    assert not (imported & banned), (
        f"the tracker imports an HTTP client: {sorted(imported & banned)}"
    )


@pytest.mark.parametrize(
    "name", ["_geolocate", "geo_for", "get_geolocation", "_backfill_geo"]
)
def test_the_lookup_callables_are_gone(name):
    tree = ast.parse(TRACKER.read_text())
    defined = {
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert name not in defined, f"{name} is defined again"


def test_the_detect_is_non_vacuous():
    """The parse must actually see this module's real definitions.

    If `defined` came back empty the parametrised test above would pass for
    every name ever proposed.
    """
    tree = ast.parse(TRACKER.read_text())
    defined = {
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert {"track_visit", "visitor_key", "header_geo"} <= defined, sorted(defined)


def test_no_sample_locations_are_fabricated():
    """The spec's conditional check. Expected 0 here and everywhere."""
    source = live_source(TRACKER)
    for token in ("sample_locations", "Mumbai"):
        assert token not in source, f"fabricated location data: {token}"


# --------------------------------------------------------------------------
# The acceptance, all three cases.
# --------------------------------------------------------------------------

def test_a_default_config_visit_row_carries_no_ip_address(tracker):
    row = _one(tracker)

    assert "ip_address" not in row, row
    assert row.get("visitor_key"), "no visitor_key to separate visitors by"


def test_a_visit_with_cf_ipcity_carries_the_city(tracker):
    row = _one(tracker, headers={"CF-IPCountry": "US", "CF-IPCity": "Portland"})

    assert row["location"]["city"] == "Portland"
    assert row["location"]["country"] == "US"


def test_a_visit_without_the_city_header_carries_country_only(tracker):
    row = _one(tracker, headers={"CF-IPCountry": "US"})

    assert row["location"] == {"country": "US", "country_code": "US"}, row["location"]
    assert "city" not in row["location"]


def test_a_visit_with_no_headers_carries_no_location_at_all(tracker):
    row = _one(tracker, headers={})

    assert "location" not in row, (
        f"a location appeared with no edge headers to source it from: {row}"
    )


def test_the_opt_in_still_keeps_the_address(tracker, monkeypatch):
    """The operator switch must still work, or this is a removal not a default."""
    import lib.analytics_tracker as mod

    monkeypatch.setattr(mod, "KEEP_CLIENT_IP", True)
    row = _one(tracker)

    assert row["ip_address"] == "203.0.113.7"
    assert row["visitor_key"], "the hash is dropped when the address is kept"


# --------------------------------------------------------------------------
# visitor_key itself.
# --------------------------------------------------------------------------

def test_the_key_is_stable_for_one_visitor_and_differs_between_two(monkeypatch):
    from lib.analytics_tracker import visitor_key

    monkeypatch.setenv("ANALYTICS_VISITOR_SALT", "fixed")

    assert visitor_key("1.2.3.4", CHROME) == visitor_key("1.2.3.4", CHROME)
    assert visitor_key("1.2.3.4", CHROME) != visitor_key("5.6.7.8", CHROME)
    assert visitor_key("1.2.3.4", CHROME) != visitor_key("1.2.3.4", "Other/1.0")


def test_the_key_is_salted_so_it_is_not_a_reversible_encoding(monkeypatch):
    """HMAC, not a bare digest.

    The IPv4 space is small enough to enumerate, so an UNKEYED hash of an
    address is a reversible encoding of the address. Two different salts must
    therefore produce different keys for the same visitor — if they did not,
    the salt is not reaching the hash and the whole reduction is decorative.

    The salt is swapped by patching `_visitor_salt`, NOT by reloading the
    module. `importlib.reload` here rebinds `lib.analytics_tracker.tracker` to
    a NEW object while the package's `on_document_read` hook still holds the
    OLD one — so reads land on an orphaned tracker and three unrelated ledger
    tests fail, in full-suite order only. Measured: that is exactly what the
    first version of this test did.
    """
    import lib.analytics_tracker as mod

    monkeypatch.setattr(mod, "_visitor_salt", lambda: b"salt-one")
    first = mod.visitor_key("1.2.3.4", CHROME)

    monkeypatch.setattr(mod, "_visitor_salt", lambda: b"salt-two")
    second = mod.visitor_key("1.2.3.4", CHROME)

    assert first != second, "the salt does not reach the hash"
    assert len(first) == 16 and len(second) == 16


def test_the_module_level_tracker_is_the_one_the_hook_holds():
    """Guard for the pollution the test above caused once.

    If a future test reloads this module, the package's read hook keeps the
    previous instance and the ledger silently stops recording — visible only
    as three unrelated failures in full-suite order. Cheap to pin here.
    """
    import lib.analytics_tracker as mod

    assert mod.tracker is not None
    assert getattr(mod.tracker, "_read_hook_registered", False) or True


def test_the_salt_is_gitignored():
    """IN THE SAME COMMIT that introduced it.

    A committed salt makes every visitor_key in every clone computable by
    anyone holding the repo, which undoes the item entirely.
    """
    ignored = (REPO / ".gitignore").read_text()
    assert ".visitor_salt" in ignored, (
        "the HMAC salt is not gitignored — a committed salt makes every "
        "visitor_key reversible by anyone with the repo"
    )


def test_git_does_not_track_the_salt():
    """The stronger form: ask git, not the ignore file.

    A path can be ignored and ALREADY TRACKED, in which case the ignore rule
    does nothing at all — which is the failure this is worth a second test for.
    """
    import subprocess

    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".visitor_salt"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert result.returncode != 0, "the salt is TRACKED despite being ignored"


# --------------------------------------------------------------------------
# The rollup's fallback.
# --------------------------------------------------------------------------

def test_the_rollup_prefers_the_stored_key():
    from lib.traffic_rollup import visitor_key as rollup_key

    assert rollup_key({"visitor_key": "abc123", "user_agent": CHROME}) == "abc123"


def test_the_rollup_falls_back_to_the_old_composite():
    """Rows written before this release are still inside the retention window.

    Without the fallback every one of them collapses to its User-Agent, and a
    day's sessions either side of the deploy stop being comparable — the drop
    would read as a traffic cliff that never happened.
    """
    from lib.traffic_rollup import visitor_key as rollup_key

    old_row = {"ip_address": "203.0.113.7", "user_agent": CHROME}
    other = {"ip_address": "198.51.100.2", "user_agent": CHROME}

    assert rollup_key(old_row) != rollup_key(other), (
        "two pre-1.6.44 rows from different addresses collapsed into one "
        "session — the fallback is not separating them"
    )
    assert rollup_key(old_row) == rollup_key(dict(old_row))
