"""The network's internal-traffic contract — the analytics point of truth.

The rule (https://2plot.ai/docs/satellite-analytics, "Internal traffic"): a
request whose User-Agent contains `2plot-internal` is 2plot machinery talking
to itself — the hub's hourly health sweep, CI smoke batteries, the 4x-daily
heartbeat, cross-app calls — and is counted NOWHERE. Dropped at write time,
before bot classification. `/healthz` is never a visit either.

Both halves are tested here, because a contract kept on only one side is not
kept at all:

*inbound*   token-carrying requests never reach the ledger, and therefore
            never reach `human_hits` / `bot_hits` in the rollup this app POSTs
            to 2plot.ai;
*outbound*  every call this host makes to another network host sends
            `INTERNAL_UA`, so the far side can apply the same rule. That half
            was missing: the ad client fetched a campaign from 2plot.dev on
            every single docs page view, arriving as `python-requests/2.x`,
            and the hub counted this satellite's readers as its own bots.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from conftest import BROWSER_UA, CRAWLER_UA, SAMPLE_PAGE
from lib import satellite_analytics
from lib.constants import INTERNAL_UA, INTERNAL_UA_TOKEN, internal_ua

# A real page. `should_skip` drops infrastructure paths (`/llms.txt`,
# `/robots.txt`, `/healthz`, `/api/`, ...), so an assertion made against one of
# those would pass no matter what the tracker did.
PAGE = SAMPLE_PAGE


def _ledger_visits() -> list[dict]:
    """Every hit on disk."""
    try:
        with open(satellite_analytics.LEDGER) as fh:
            return [json.loads(ln) for ln in fh if ln.strip()]
    except FileNotFoundError:
        return []


def _rollup() -> dict:
    """Today's rollup as the hub would receive it, or an all-zero stand-in."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return satellite_analytics.rollup(today) or {"human_hits": 0, "bot_hits": 0}


def _distinct_ua(label: str, base: str = BROWSER_UA) -> str:
    """A UA that is unique per call site.

    `track()` dedupes the same (visitor, path) inside DEDUPE_S, and the visitor
    key is `ip | md5(user-agent)[:8]` — so two hits from the test client with
    the same UA collapse into one and a delta assertion silently measures
    nothing. Varying the UA gives each assertion its own visitor.
    """
    return f"{base} {label}"


# --------------------------------------------------------------- the token --


def test_token_is_the_network_wide_string():
    """The contract only works if every host agrees on the byte sequence."""
    assert INTERNAL_UA_TOKEN == "2plot-internal"
    assert INTERNAL_UA_TOKEN in INTERNAL_UA
    assert INTERNAL_UA.startswith(INTERNAL_UA_TOKEN)


def test_caller_suffix_never_breaks_the_token():
    ua = internal_ua("ad-client")
    assert INTERNAL_UA_TOKEN in ua
    assert ua.endswith("ad-client")
    assert internal_ua() == INTERNAL_UA
    assert internal_ua("  ") == INTERNAL_UA


# ------------------------------------------------------------------ inbound --


def test_the_tests_can_see_the_ledger_at_all(client, tmp_state_dir):
    """Guard for every delta assertion below.

    If the ledger path were wrong (or the suite were writing into the repo's
    own satellite_traffic.jsonl), every "count did not change" test would pass
    vacuously. Prove a write lands first — and that tracking is enabled at all,
    which for this app means SATELLITE_ANALYTICS_DRY_RUN rather than a secret.
    """
    assert satellite_analytics.enabled(), (
        "tracking is dormant — every exclusion test below would pass vacuously"
    )
    assert str(satellite_analytics.LEDGER).startswith(tmp_state_dir), (
        satellite_analytics.LEDGER
    )
    before = len(_ledger_visits())
    client.get(PAGE, user_agent=_distinct_ua("ledger-guard"))
    assert len(_ledger_visits()) == before + 1


def test_internal_ua_is_counted_nowhere(client):
    before = len(_ledger_visits())
    client.get(PAGE, user_agent=internal_ua("network-smoke"))
    client.get("/", user_agent=INTERNAL_UA)
    assert len(_ledger_visits()) == before


def test_a_crawler_shaped_probe_carrying_the_token_stays_internal(client):
    """The battery's crawler probe exercises the bot path deliberately.

    It must still not be counted. This is precisely why the drop happens
    before `is_bot` — classification would file it under `bot`.
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
    client.get("/healthz", user_agent=_distinct_ua("healthz-browser"))
    assert len(_ledger_visits()) == before


def test_the_pageview_beacon_also_drops_internal_traffic(client):
    """The SPA beacon is a second write path into the same ledger.

    `/api/pageview` is how every client-side route change is counted, so a
    drop applied only to the request middleware would leak everything after
    the entry page. Both go through `track()`, and this is what pins that.
    """
    assert satellite_analytics.is_internal(internal_ua("network-smoke"))
    assert satellite_analytics.is_internal(f"{CRAWLER_UA} {INTERNAL_UA}")
    assert not satellite_analytics.is_internal(BROWSER_UA)
    assert not satellite_analytics.is_internal(None)


# ----------------------------------------------- the reported numbers -------
#
# The exclusion that actually matters. Everything above is about the ledger;
# this is about what 2plot.ai charts.


def test_internal_traffic_is_absent_from_human_hits_and_bot_hits(client):
    before = _rollup()

    # Four calls that are all machinery, in the two shapes the network sends:
    # a plain internal UA, and a crawler-shaped probe carrying the token.
    for n in range(2):
        client.get(PAGE, user_agent=internal_ua(f"network-smoke-{n}"))
        client.get(PAGE, user_agent=f"{CRAWLER_UA} {INTERNAL_UA} {n}")

    after = _rollup()
    assert after["human_hits"] == before["human_hits"], (
        "internal traffic reached human_hits — the hub would chart the health "
        "sweep as readers of these docs"
    )
    assert after["bot_hits"] == before["bot_hits"], (
        "internal traffic reached bot_hits — the hub would chart CI as crawler "
        "interest"
    )


def test_the_tracker_sits_outside_the_handler_chain(app):
    """The structural fix behind `test_real_traffic_is_still_counted`.

    On Flask, `before_request` handlers stop running the moment one returns a
    response — and `add_llms_routes` installs `_bot_middleware`, which returns
    prerendered HTML for every crawler. While the tracker was a
    `before_request`, not one crawler request ever reached it, and this
    satellite reported `bot_hits: 0` to 2plot.ai every day it was live.

    Registration order cannot fix that: Flask wants the tracker registered
    FIRST, Starlette's `add_middleware` wants it LAST, and one call site
    cannot be both. So the WSGI app is wrapped instead. That is what this
    pins — the behavioural test catches the symptom, this names the cause.
    """
    if backend_name() != "flask":
        pytest.skip("WSGI wrapping is a Flask-backend concern")

    handlers = [
        f"{fn.__module__}.{fn.__qualname__}"
        for fn in app.server.before_request_funcs.get(None, [])
    ]
    assert not any("_satellite_track" in name for name in handlers), (
        "the tracker is back to being a before_request handler — the llms bot "
        f"middleware will short-circuit every crawler past it. Handlers: {handlers}"
    )
    assert "_wsgi_tracker" in repr(app.server.wsgi_app) or callable(app.server.wsgi_app)


def backend_name() -> str:
    from conftest import backend

    return backend()


def test_real_traffic_is_still_counted(client):
    """The exclusions must not have lobotomised the tracker.

    A rule that drops everything also satisfies every assertion above, so the
    positive case is load-bearing: one browser hit is one human, one Googlebot
    hit is one bot.
    """
    before = _rollup()
    client.get(PAGE, user_agent=_distinct_ua("real-human"))
    client.get(PAGE, user_agent=_distinct_ua("real-bot", CRAWLER_UA))
    after = _rollup()

    assert after["human_hits"] == before["human_hits"] + 1
    assert after["bot_hits"] == before["bot_hits"] + 1


# ----------------------------------------------------------------- outbound --


class _Captured(Exception):
    """Abort the request once the headers have been seen."""


def _capture_headers(monkeypatch, module, attr):
    """Record the headers of the next outbound call, then abort it."""
    seen = {}

    def fake(*args, **kwargs):
        seen.update(kwargs.get("headers") or {})
        raise _Captured

    monkeypatch.setattr(module, attr, fake)
    return seen


def test_the_traffic_rollup_post_sends_the_token(monkeypatch):
    """The signed hourly rollup to 2plot.ai."""
    import requests

    monkeypatch.setenv("CROSS_APP_WEBHOOK_SECRET", "test-secret")
    seen = _capture_headers(monkeypatch, requests, "post")
    with pytest.raises(_Captured):
        satellite_analytics.post_signed(
            "/api/satellite/traffic", {"app": "leaflet", "date": "2026-07-31"}
        )
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
