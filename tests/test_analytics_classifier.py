"""ONE classifier — the tracker delegates to dash_improve_my_llms.classify().

Until 1.6.34 lib/analytics_tracker.py carried its own User-Agent lists: it
filed ClaudeBot (Anthropic's TRAINING crawler) under "search", still named
the retired `anthropic-ai` / `claude-web` tokens, and counted every UA-less
or library client (httpx, Go-http-client, node-fetch) as a human. Every
host in the fleet reported those numbers to the hub. These pins hold the
delegation in place — each UA string is one taken from the wire on
2026-08-29 — and the last test greps the module so a list cannot come
back quietly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import live_source

from lib.analytics_tracker import AnalyticsTracker
from lib.constants import INTERNAL_UA_TOKEN

CLAUDEBOT = ("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; "
             "ClaudeBot/1.0; +claudebot@anthropic.com)")
GPTBOT = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)"
GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
HTTPX = "python-httpx/0.27.0"
CHROME = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


@pytest.fixture
def tracker(tmp_path, monkeypatch):
    monkeypatch.setenv("ANALYTICS_GEO_LOOKUP", "0")
    return AnalyticsTracker(tmp_path / "ledger.json")


def _rows(tracker):
    tracker.flush()
    path = Path(tracker.data_file)
    if not path.exists():        # nothing written → the file is never created
        return []
    return json.loads(path.read_text())["visits"]


def _one(tracker, ua):
    tracker.track_visit("/", ua, "203.0.113.9")
    rows = _rows(tracker)
    assert len(rows) == 1, rows
    return rows[0]


@pytest.mark.parametrize("ua, bot_type, vendor_key", [
    (CLAUDEBOT, "training", "claudebot"),
    (GPTBOT, "training", "gptbot"),
    (GOOGLEBOT, "traditional", "googlebot"),
    (HTTPX, "unknown", None),
    ("", "unknown", None),
    (None, "unknown", None),
])
def test_crawler_lane_rows(tracker, ua, bot_type, vendor_key):
    assert tracker.is_bot(ua) is True
    assert tracker.detect_bot_type(ua) == bot_type
    row = _one(tracker, ua)
    assert row["device_type"] == "bot"
    assert row["bot_type"] == bot_type
    assert row["vendor_key"] == vendor_key
    assert row["lane"] == "crawler"
    assert row["verified"] in ("verified", "unverified", "n/a")


def test_claudebot_is_training_and_unverifiable(tracker):
    """The finding that produced this file: ClaudeBot was 'search' for a
    year. And Anthropic publishes no IP ranges, so `verified` is n/a — a
    property of the vendor, never a defect on this host."""
    row = _one(tracker, CLAUDEBOT)
    assert row["bot_type"] == "training"
    assert row["vendor_class"] == "training"
    assert row["verified"] == "n/a"


def test_a_browser_row_carries_no_vendor_keys(tracker):
    """Human rows carry no vendor identity — and, since 1.6.44 item 16, no
    raw address either.

    THE KEY SET MOVED, DELIBERATELY. This assertion previously allowed
    `ip_address` and that was the point of the item: the tracker no longer
    stores it. `visitor_key` — a keyed one-way hash — takes its place, so a
    visitor can still be told from another without being stored. The spec
    named this exact failure in advance: the row-key set is a fork-owned seam
    and its failing IS the item landing.

    Still an upper bound rather than equality: a host with
    ANALYTICS_KEEP_CLIENT_IP=1 legitimately adds `ip_address` back, and a
    Cloudflare zone with the location transform on adds `location`.
    """
    assert tracker.is_bot(CHROME) is False
    row = _one(tracker, CHROME)
    assert row["device_type"] == "desktop"
    assert set(row) <= {"timestamp", "path", "device_type", "user_agent",
                        "visitor_key", "ip_address", "location"}, row

    # The two halves of the item, asserted rather than implied.
    assert "ip_address" not in row, (
        "the raw client address is back in a default-config row"
    )
    assert row.get("visitor_key"), (
        "no visitor_key — sessions collapse to the User-Agent"
    )
    assert "_geo_pending" not in row, "the removed lookup's marker is back"


def test_internal_traffic_is_still_dropped_before_classification(tracker):
    tracker.track_visit("/", f"Mozilla/5.0 {INTERNAL_UA_TOKEN}-sweep", "203.0.113.9")
    assert _rows(tracker) == []


def test_the_module_carries_no_user_agent_list():
    """The grep. A token the registry lacks is a pushback to the package,
    never a list here (.claude/CLAUDE.md trap)."""
    path = Path(__file__).resolve().parent.parent / "lib" / "analytics_tracker.py"
    src = path.read_text()
    # PARSED, not stripped (1.6.44 item 13). This filtered comments and the
    # MODULE docstring, which was enough until a FUNCTION docstring quoted a
    # measured `classify()` result to explain where vendor_class comes from —
    # and the guard read that quotation as a resurrected UA table (item 8,
    # measured: it went red on "'claudebot'" appearing in prose). A comment
    # strip cannot see a docstring; `ast` removes both.
    code = live_source(path)
    survivors = [t for t in ("'anthropic-ai'", "'claude-web'", "'perplexitybot'",
                             "'gptbot'", "'claudebot'", "'googlebot'", "'bingbot'",
                             "'headlesschrome'", "'phantomjs'", "'pingdom'")
                 if t in code]
    assert survivors == [], f"a hand-written UA list is back: {survivors}"
    assert "from dash_improve_my_llms import classify" in src
