"""The network's internal-traffic contract — the analytics point of truth.

The rule (https://2plot.ai/docs/satellite-analytics, "Internal traffic"): a
request whose User-Agent contains `2plot-internal` is 2plot machinery talking
to itself — the hub's hourly health sweep, CI smoke batteries, the 4x-daily
heartbeat, cross-app calls — and is counted NOWHERE. Dropped at write time,
before device detection and before bot classification. `/healthz` is never a
visit either.

Both halves are tested here, because a contract kept on only one side is not
kept at all:

*inbound*   token-carrying requests never reach the ledger, and therefore
            never reach `human_hits` / `bot_hits` in the hourly rollup this
            app POSTs to 2plot.ai;
*outbound*  every call this host makes to another network host sends
            `INTERNAL_UA`, so the far side can apply the same rule. That half
            was missing: the ad client fetched a campaign from 2plot.dev on
            every single docs page view, arriving as `python-requests/2.x`,
            and the hub counted this satellite's readers as its own bots.
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from conftest import BROWSER_UA, CRAWLER_UA, SAMPLE_PAGE
from lib.analytics_tracker import analytics_path, tracker
from lib.constants import INTERNAL_UA, INTERNAL_UA_TOKEN, internal_ua

# A real page. `lib/traffic_rollup` drops infrastructure paths (`/llms.txt`,
# `/robots.txt`, `/healthz`, ...) at read time, so a rollup assertion made
# against one of those would pass no matter what the tracker did.
PAGE = SAMPLE_PAGE


def _ledger_visits():
    """Every hit on disk, flushing the write buffer first."""
    tracker.flush()
    try:
        with open(analytics_path()) as f:
            return json.load(f).get("visits", [])
    except FileNotFoundError:
        return []


def _rollup():
    """Today's rollup as the hub would receive it, or an all-zero stand-in."""
    from lib.traffic_rollup import daily_rollup

    tracker.flush()
    return daily_rollup("leaflet", datetime.now().date()) or {
        "human_hits": 0, "bot_hits": 0,
    }


# --------------------------------------------------------------- the token --


def test_token_is_the_network_wide_string():
    """The contract only works if every host agrees on the byte sequence."""
    assert INTERNAL_UA_TOKEN == "2plot-internal"
    assert INTERNAL_UA_TOKEN in INTERNAL_UA
    assert INTERNAL_UA.startswith(INTERNAL_UA_TOKEN)


def test_caller_suffix_never_breaks_the_token():
    ua = internal_ua("traffic-reporter")
    assert INTERNAL_UA_TOKEN in ua
    assert ua.endswith("traffic-reporter")
    assert internal_ua() == INTERNAL_UA
    assert internal_ua("  ") == INTERNAL_UA


# ------------------------------------------------------------------ inbound --


def test_the_tests_can_see_the_ledger_at_all(client, tmp_state_dir):
    """Guard for every delta assertion below.

    If the ledger path were wrong (or the suite were writing into the repo's
    own visitor_analytics.json), every "count did not change" test would pass
    vacuously. Prove a write lands first.
    """
    assert str(analytics_path()).startswith(tmp_state_dir), analytics_path()
    before = len(_ledger_visits())
    client.get(PAGE, user_agent=BROWSER_UA)
    assert len(_ledger_visits()) == before + 1


def test_internal_ua_is_counted_nowhere(client):
    before = len(_ledger_visits())
    client.get(PAGE, user_agent=internal_ua("network-smoke"))
    client.get("/", user_agent=INTERNAL_UA)
    assert len(_ledger_visits()) == before


def test_a_crawler_shaped_probe_carrying_the_token_stays_internal(client):
    """The battery's crawler probe exercises the bot path deliberately.

    It must still not be counted. This is precisely why the drop happens
    before `detect_device_type` — classification would file it under `bot`.
    """
    before = len(_ledger_visits())
    client.get(PAGE, user_agent=f"{CRAWLER_UA} {INTERNAL_UA}")
    assert len(_ledger_visits()) == before


def test_the_token_is_matched_case_insensitively(client):
    before = len(_ledger_visits())
    client.get(PAGE, user_agent="2PLOT-INTERNAL/1.0 Health-Sweep")
    assert len(_ledger_visits()) == before


def test_healthz_is_never_a_visit(client):
    before = len(_ledger_visits())
    client.get("/healthz", user_agent="Render/1.0 health-check")
    client.get("/healthz", user_agent=BROWSER_UA)
    assert len(_ledger_visits()) == before


# ----------------------------------------------- the reported numbers -------
#
# The exclusion that actually matters. Everything above is about the ledger;
# this is about what 2plot.ai charts.


def test_internal_traffic_is_absent_from_human_hits_and_bot_hits(client):
    before = _rollup()

    # Four calls that are all machinery, in the two shapes the network sends:
    # a plain internal UA, and a crawler-shaped probe carrying the token.
    for _ in range(2):
        client.get(PAGE, user_agent=internal_ua("network-smoke"))
        client.get(PAGE, user_agent=f"{CRAWLER_UA} {INTERNAL_UA}")

    after = _rollup()
    assert after["human_hits"] == before["human_hits"], (
        "internal traffic reached human_hits — the hub would chart the health "
        "sweep as readers of these docs"
    )
    assert after["bot_hits"] == before["bot_hits"], (
        "internal traffic reached bot_hits — the hub would chart CI as crawler "
        "interest"
    )


def test_real_traffic_is_still_counted(client):
    """The exclusions must not have lobotomised the tracker.

    A rule that drops everything also satisfies every assertion above, so the
    positive case is load-bearing: one browser hit is one human, one Googlebot
    hit is one bot.
    """
    before = _rollup()
    client.get(PAGE, user_agent=BROWSER_UA)
    client.get(PAGE, user_agent=CRAWLER_UA)
    after = _rollup()

    assert after["human_hits"] == before["human_hits"] + 1
    assert after["bot_hits"] == before["bot_hits"] + 1


# ------------------------------------------------------- the READ table -----
#
# "Counted nowhere" includes the `reads` table (1.6.43 item 1). Everything
# above this point tests `visits`, which `track_visit` has guarded since the
# internal-traffic contract existed. `record_read` — the `on_document_read`
# hook the 2.8.0 floor added — never learned the rule, so until this round the
# hub's health sweep, every satellite's link audit and every post-deploy
# battery landed in `reads` and were the busiest "vendor" on the board.


def _ledger_reads():
    tracker.flush()
    try:
        with open(analytics_path()) as f:
            return json.load(f).get("reads", [])
    except FileNotFoundError:
        return []


def test_the_drop_keys_on_the_field_the_package_actually_sends():
    """This item's own failure mode, guarded.

    The drop reads `event["ua"]`. `EVENT_FIELDS` has `ua`, NOT `user_agent` —
    a drop keyed on the wrong name is a silent no-op that passes every
    "no rows" assertion below by dropping nothing and being asked nothing.
    Checked against the RESOLVED package rather than a literal, so a rename
    between versions fails here rather than in production.
    """
    import importlib.metadata as md

    from dash_improve_my_llms import _ledger

    from pathlib import Path

    assert "ua" in _ledger.EVENT_FIELDS, (
        f"the package resolved here ({md.version('dash-improve-my-llms')}) has "
        f"no `ua` field: {_ledger.EVENT_FIELDS}"
    )
    tracker_src = (Path(__file__).resolve().parent.parent
                   / "lib" / "analytics_tracker.py").read_text()
    body = tracker_src.split("def record_read")[1].split("def _enqueue")[0]
    assert 'event.get("ua")' in body, "record_read does not key the drop on `ua`"
    assert "INTERNAL_UA_TOKEN" in body, "record_read never checks the token"


def test_an_internal_probe_writes_no_read_row(client, capsys):
    """One probe carrying the token -> ZERO read rows, count PRINTED.

    A bare "no rows" is the negative this round learned not to trust, so the
    count goes next to the result and the positive control below proves the
    pin cannot pass by dropping everything.
    """
    before = len(_ledger_reads())
    client.get("/llms.txt", user_agent=internal_ua("network-smoke"))
    client.get("/llms.txt", user_agent=f"{CRAWLER_UA} {INTERNAL_UA}")
    after = len(_ledger_reads())
    with capsys.disabled():
        print(f"\n    internal probes: reads {before} -> {after} (delta 0 expected)")
    assert after == before, (
        f"internal traffic reached the read table: {after - before} row(s)"
    )


def test_a_real_crawler_probe_writes_exactly_one_read_row(client, capsys):
    """The positive control, in the same file as the negative.

    A `record_read` that returned unconditionally would satisfy the test
    above; this is what stops that passing.
    """
    before = len(_ledger_reads())
    client.get("/llms.txt", user_agent=CRAWLER_UA)
    after = len(_ledger_reads())
    with capsys.disabled():
        print(f"    crawler probe  : reads {before} -> {after} (delta 1 expected)")
    assert after == before + 1, (
        f"expected exactly one read row, got {after - before}"
    )


def test_the_zero_above_is_the_drop_working_not_the_probe_being_silent(
    client, monkeypatch, capsys
):
    """MUTATION CHECK, and the reason this file has one.

    `delta 0` proves the drop only if the package WOULD have emitted a row
    for that request. If an internal UA happened not to reach the crawler
    lane, the assertion above would pass while `record_read` did nothing —
    the vacuous negative this round has now produced three times.

    So: neutralise the token, send the identical probe, and require the row
    to appear. If it does, the zero above was the drop.
    """
    from lib import constants

    monkeypatch.setattr(constants, "INTERNAL_UA_TOKEN", "\x00-never-matches")
    before = len(_ledger_reads())
    client.get("/llms.txt", user_agent=internal_ua("network-smoke"))
    after = len(_ledger_reads())
    with capsys.disabled():
        print(f"    token neutralised: reads {before} -> {after} (delta 1 expected)")
    assert after == before + 1, (
        "with the token neutralised the identical probe STILL wrote no row — "
        "so the zero in the test above says nothing about the drop"
    )


def test_internal_reads_never_reach_the_rollups_vendor_block(client):
    """The number the hub actually charts.

    `vendors[]` and `reads` in the daily rollup are built from this table, so
    a token-carrying probe must not appear as a vendor row either.
    """
    from lib.traffic_rollup import daily_rollup, load_reads

    # Scoped to the rows THIS test causes. The mutation check above
    # deliberately writes one internal row (with the token neutralised) to
    # prove the drop is load-bearing, so a whole-table assertion here would
    # fail on another test's intentional fixture rather than on a defect.
    before = len(_ledger_reads())
    for _ in range(3):
        client.get("/llms.txt", user_agent=internal_ua("link-audit"))
    tracker.flush()
    new_rows = load_reads(str(analytics_path()))[before:]
    internal = [r for r in new_rows
                if INTERNAL_UA_TOKEN in (r.get("ua") or "").lower()]
    assert internal == [], f"{len(internal)} internal row(s) in the read table"
    assert new_rows == [], f"3 internal probes wrote {len(new_rows)} row(s)"

    payload = daily_rollup("leaflet", datetime.now().date()) or {}
    for v in payload.get("vendors", []):
        assert INTERNAL_UA_TOKEN not in str(v.get("key") or "").lower()


# ----------------------------------------------------------------- outbound --


class _Captured(Exception):
    """Abort the request once the headers have been seen."""


def _capture_headers(monkeypatch, module, attr="post"):
    """Record the headers of the next outbound call, then abort it."""
    seen = {}

    def fake(*args, **kwargs):
        seen.update(kwargs.get("headers") or {})
        raise _Captured

    monkeypatch.setattr(module, attr, fake)
    return seen


def test_the_traffic_rollup_post_sends_the_token(monkeypatch):
    import requests

    from lib import satellite_reporter

    seen = _capture_headers(monkeypatch, requests, "post")
    ok, _detail = satellite_reporter.post_rollup(
        {"app": "leaflet", "date": "2026-07-31"}, secret="test-secret"
    )
    assert ok is False  # the fake raised; we only wanted the headers
    assert INTERNAL_UA_TOKEN in seen.get("User-Agent", "")


def test_the_ad_fetch_sends_the_token(monkeypatch):
    """One call per docs page view — the loudest of the two."""
    from lib import ad_client

    seen = _capture_headers(monkeypatch, ad_client._session, "get")
    monkeypatch.setattr(ad_client, "_last_failure", 0.0)
    assert ad_client.fetch_ad(SAMPLE_PAGE) is None
    assert INTERNAL_UA_TOKEN in seen.get("User-Agent", "")


def test_the_ad_fetch_still_fails_soft(monkeypatch):
    """The header must not have cost the module its fail-silent contract.

    `fetch_ad` swallowing everything is what keeps an ad-server outage from
    breaking a page view; a `from lib.constants import ...` placed outside the
    try block would have moved an ImportError out of that guarantee.
    """
    from lib import ad_client

    monkeypatch.setattr(ad_client, "_last_failure", 0.0)
    monkeypatch.setattr(
        ad_client._session, "get",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ad server down")),
    )
    assert ad_client.fetch_ad(SAMPLE_PAGE) is None


@pytest.mark.parametrize("script", ["smoke_live", "network_smoke"])
def test_every_battery_script_sends_the_token(script):
    """A post-deploy battery sweeps every peer; it must not register anywhere."""
    import importlib.util

    from conftest import REPO_ROOT

    spec = importlib.util.spec_from_file_location(
        f"_ua_{script}", REPO_ROOT / "scripts" / f"{script}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    agents = [
        value
        for name, value in vars(module).items()
        if (name == "UA" or name.endswith("_UA")) and isinstance(value, str)
    ]
    assert agents, f"scripts/{script}.py declares no User-Agent constant"
    missing = [ua for ua in agents if INTERNAL_UA_TOKEN not in ua]
    assert missing == [], f"scripts/{script}.py sends untokened UAs: {missing}"
