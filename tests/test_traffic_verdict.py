"""1.6.44 item 3 — the reads table says WHAT HAPPENED, not just that it was asked.

A read is not a serve. `dash-improve-my-llms` emits one ledger event per corpus
document it handles, and the `verdict` field says whether the fetch got what it
asked for: `served`, or one of `denied` / `blocked` / `rate_limited` / `priced`
/ `gated`. Before this item `/admin/traffic` grouped rows by path alone and
showed a hit count, so a denied fetch and a served fetch of the same path were
one indistinguishable number — enforcement rendered as traffic.

The acceptance is end-to-end on purpose. A fixture proves the table can render
a column; only a real fetch proves the ledger actually carries a non-served
verdict on this host, through this app's own gate wiring. Measured in-process
before the test was written:

    /admin/traffic/llms.txt        -> 404, ledger verdict=denied
    /admin/control-board/llms.txt  -> 404, ledger verdict=denied
    /llms.txt                      -> 200, ledger verdict=served

Both halves matter. A suite with only the denied row cannot tell "the gate
works" from "every read is denied"; a suite with only the served row is the
pre-item board.
"""

from __future__ import annotations

import importlib
import json
from datetime import date, datetime

import pytest

from conftest import CRAWLER_UA
from dash_improve_my_llms._ledger import EVENT_FIELDS

TODAY = date.today()


def _page():
    import pages.traffic as traffic
    return importlib.reload(traffic)


def _read(verdict, path="/llms.txt", vendor_key="gptbot"):
    ev = {k: None for k in EVENT_FIELDS}
    ev.update(
        ts=datetime(TODAY.year, TODAY.month, TODAY.day, 12).timestamp(),
        path=path, method="GET", tier="page", lane="crawler",
        bot_type="training", vendor_key=vendor_key, verified="unverified",
        verdict=verdict, status=200, bytes=500, ua="ua", kind="read",
    )
    ev.pop("client_ip", None)
    return ev


# --------------------------------------------------------------------------
# The live half: a real fetch of a real mark_hidden path.
# --------------------------------------------------------------------------

def test_a_hidden_path_fetched_by_a_crawler_records_a_non_served_verdict(
    app_module, client, tmp_path, monkeypatch
):
    """The acceptance, on the wire this app actually serves.

    `/admin/traffic` and `/admin/control-board` are both `mark_hidden`, so
    their machine surfaces must not hand a crawler the document — and the
    ledger must RECORD that rather than staying silent, or the board has
    nothing to label.
    """
    from lib.analytics_tracker import tracker

    ledger = tmp_path / "visitor_analytics.json"
    monkeypatch.setenv("TRAFFIC_ANALYTICS_FILE", str(ledger))
    monkeypatch.setattr(tracker, "_data_file", ledger, raising=False)

    hidden = client.get("/admin/traffic/llms.txt", user_agent=CRAWLER_UA)
    public = client.get("/llms.txt", user_agent=CRAWLER_UA)
    tracker.flush()

    assert hidden.status == 404, "a mark_hidden page served its machine document"
    assert public.status == 200, "the public corpus stopped answering a crawler"

    rows = json.loads(ledger.read_text()).get("reads", [])
    by_path = {r.get("path"): r.get("verdict") for r in rows}

    assert by_path.get("/admin/traffic/llms.txt") == "denied", (
        f"the hidden fetch was not recorded as denied: {by_path}"
    )
    assert by_path.get("/llms.txt") == "served", (
        "the CONTROL is missing — without a served row beside the denied one "
        f"this assertion cannot tell a working gate from a dead corpus: {by_path}"
    )


# --------------------------------------------------------------------------
# The rendering half.
# --------------------------------------------------------------------------

def test_the_reads_table_renders_the_verdict_word(app_module):
    """Grouped by (path, verdict), and the word itself is in the DOM.

    Asserted on the WORD, never on a colour: a badge that carried only a tone
    would put the entire meaning in a channel a screen reader does not get.
    """
    traffic = _page()
    rendered = str(traffic.top_paths_block([_read("denied"), _read("served")]))

    assert "denied" in rendered, "the verdict column does not render the verdict"
    assert "served" in rendered
    assert "verdict" in rendered, "the column header is missing"


def test_the_same_path_splits_by_verdict_instead_of_folding(app_module):
    """The defect this item names, pinned directly.

    Two fetches of ONE path with different verdicts must be two rows. Grouped
    by path alone they are a single '2' and the board reports a denial as
    traffic.
    """
    traffic = _page()
    reads = [_read("denied"), _read("denied"), _read("served")]

    [(key, verified, paths)] = traffic.top_paths(reads)
    cells = {(p, v): n for p, v, n in paths}

    assert cells == {("/llms.txt", "denied"): 2, ("/llms.txt", "served"): 1}, (
        f"rows folded across verdicts: {cells}"
    )


def test_serve_counts_keeps_denied_reads_out_of_serves(app_module):
    """`(served, not_served)` — and the mutation that makes it non-vacuous."""
    traffic = _page()

    served, withheld = traffic.serve_counts(
        [_read("served"), _read("denied"), _read("blocked"), _read("rate_limited")]
    )
    assert (served, withheld) == (1, 3), (
        f"expected 1 served / 3 withheld, got {served}/{withheld}"
    )

    # Non-vacuity: an all-served day must NOT report withheld rows, or the
    # split above could be passing by counting something unrelated.
    assert traffic.serve_counts([_read("served")] * 4) == (4, 0)
    assert traffic.serve_counts([]) == (0, 0)


@pytest.mark.parametrize(
    "verdict", ["served", "priced", "gated", "denied", "blocked", "rate_limited"]
)
def test_every_ledger_verdict_gets_a_labelled_badge(app_module, verdict):
    """All six of the package's verdicts render as the word.

    Parametrised over the full set rather than the two the fixtures use, so a
    verdict this host has not seen yet cannot render as an empty cell the
    first time enforcement fires.
    """
    traffic = _page()
    assert verdict in str(traffic._verdict_cell(verdict))


def test_an_absent_verdict_renders_a_placeholder_not_a_blank(app_module):
    """A pre-1.6.34 ledger row has no verdict at all. It must still occupy a
    labelled cell rather than silently reading as served."""
    traffic = _page()
    row = _read("served")
    row["verdict"] = None

    [(_, _, paths)] = traffic.top_paths([row])
    assert paths == [("/llms.txt", "—", 1)], paths

    served, withheld = traffic.serve_counts([row])
    assert (served, withheld) == (0, 1), (
        "a row with no verdict was counted as served — absence is not a serve"
    )
