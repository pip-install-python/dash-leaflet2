"""1.6.44 item 21 — `reads` are pruned by date, never by count.

`_prune` applied the count cap to BOTH tables. For `visits` that is right: the
visit table is unbounded in the bad case — a scraper hammering one path writes
a row per request — and the cap is what stops one afternoon filling the disk.

For `reads` it is wrong, and wrong in the direction that destroys the data the
table exists for. A crawler sweep legitimately produces tens of thousands of
read rows in a day, so a count cap silently discards rows that are INSIDE the
retention window: it throws away the busiest days first. A count cap answers
"how big is the file"; the retention window answers "what are we allowed to
keep". Only the second is a policy.

THE CHOICE LIVES AT THE CALL SITE, so it is source-pinned by AST as well as
exercised. A behavioural test cannot see a `cap=True` restored above it — the
row counts would be identical for every corpus smaller than the cap, which is
every corpus a test suite builds by default.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

import lib.analytics_tracker as tracker_mod

REPO = pathlib.Path(__file__).resolve().parent.parent
TRACKER = REPO / "lib" / "analytics_tracker.py"


def _rows(n, ts):
    return [{"ts": ts, "path": "/llms.txt", "kind": "read"} for _ in range(n)]


@pytest.fixture
def big_corpus():
    """20,001 in-window read rows plus one outside it.

    The size is the point: one more than MAX_VISITS, so the cap — if it
    applied — would drop exactly one in-window row and nothing else. A smaller
    corpus cannot tell the two rules apart.
    """
    from datetime import datetime, timedelta

    now = datetime.now()
    inside = (now - timedelta(days=1)).timestamp()
    outside = (now - timedelta(days=tracker_mod.RETENTION_DAYS + 5)).timestamp()

    return _rows(tracker_mod.MAX_VISITS + 1, inside) + _rows(1, outside)


# --------------------------------------------------------------------------
# The acceptance.
# --------------------------------------------------------------------------

def test_the_corpus_is_the_size_the_acceptance_names(big_corpus):
    """Note 88 on the fixture itself: at MAX_VISITS or below, the two rules
    agree and every assertion here is vacuous."""
    assert tracker_mod.MAX_VISITS == 20000, tracker_mod.MAX_VISITS
    assert len(big_corpus) == 20002


def test_reads_keep_every_in_window_row_and_lose_the_dated_one(big_corpus):
    kept = tracker_mod._prune(
        big_corpus, stamp=tracker_mod._read_stamp, cap=False
    )

    assert len(kept) == 20001, (
        f"expected 20,001 in-window read rows to survive, got {len(kept)} — "
        "the count cap is still being applied to reads"
    )


def test_the_same_corpus_WITH_the_cap_loses_an_in_window_row(big_corpus):
    """PROVE THE TEST RED ON THE PRE-ITEM BEHAVIOUR before believing it.

    This is the old code path, run deliberately. If it did NOT lose a row, the
    test above would be passing for a reason that has nothing to do with the
    fix — and this file would be green over a corpus that cannot tell the
    rules apart.
    """
    capped = tracker_mod._prune(
        big_corpus, stamp=tracker_mod._read_stamp, cap=True
    )

    assert len(capped) == 20000, (
        f"the pre-item behaviour kept {len(capped)} rows — it did not lose an "
        "in-window row, so the acceptance above proves nothing"
    )
    assert len(capped) < 20001


def test_visits_keep_the_count_cap():
    """The other table's rule is unchanged, and that is deliberate.

    Built with VISIT-shaped rows: `_visit_stamp` reads an ISO `timestamp`
    while `_read_stamp` reads a float `ts`. Handing the read fixture to the
    visits path made every row fail the cutoff and drop — a test that "passed"
    the wrong way round, and would have reported the cap working while
    measuring nothing but a shape mismatch.
    """
    from datetime import datetime, timedelta

    inside = (datetime.now() - timedelta(days=1)).isoformat()
    outside = (datetime.now()
               - timedelta(days=tracker_mod.RETENTION_DAYS + 5)).isoformat()
    corpus = (
        [{"timestamp": inside, "path": "/"} for _ in range(tracker_mod.MAX_VISITS + 1)]
        + [{"timestamp": outside, "path": "/"}]
    )

    kept = tracker_mod._prune(corpus)

    assert len(kept) == tracker_mod.MAX_VISITS, (
        f"visits kept {len(kept)} rows — the cap that stops one scraping "
        "afternoon filling the disk is gone"
    )


def test_the_retention_window_still_applies_to_reads(big_corpus):
    """`cap=False` must not become "keep everything"."""
    kept = tracker_mod._prune(
        big_corpus, stamp=tracker_mod._read_stamp, cap=False
    )

    assert len(kept) == len(big_corpus) - 1, (
        "the out-of-window row survived — reads are no longer pruned at all"
    )


# --------------------------------------------------------------------------
# Source-pinned: the choice at the call site.
# --------------------------------------------------------------------------

def test_the_reads_call_site_passes_cap_false():
    """AST, not a grep, and not a behavioural check.

    The rule per table is chosen AT THE CALL. A `cap=True` restored above this
    line would be invisible to any suite whose corpus is smaller than 20,000
    rows — which is every suite that does not build one on purpose.
    """
    tree = ast.parse(TRACKER.read_text())
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name) and node.func.id == "_prune"
    ]
    assert len(calls) == 2, f"expected two _prune call sites, found {len(calls)}"

    by_kwargs = []
    for call in calls:
        kwargs = {kw.arg: kw.value for kw in call.keywords}
        cap = kwargs.get("cap")
        by_kwargs.append((
            "reads" if "stamp" in kwargs else "visits",
            None if cap is None else getattr(cap, "value", "?"),
        ))

    assert ("reads", False) in by_kwargs, (
        f"the reads call site does not pass cap=False: {by_kwargs}"
    )
    assert ("visits", None) in by_kwargs, (
        f"the visits call site should take the default cap: {by_kwargs}"
    )


def test_the_default_is_conservative():
    """A caller that does not think about it gets the capped behaviour."""
    import inspect

    default = inspect.signature(tracker_mod._prune).parameters["cap"].default
    assert default is True, default


# --------------------------------------------------------------------------
# End to end, through the writer.
# --------------------------------------------------------------------------

def test_a_written_ledger_keeps_more_reads_than_the_cap(tmp_path, monkeypatch):
    """The rule as it actually reaches disk, not just as `_prune` computes it."""
    import json
    from datetime import datetime, timedelta

    from lib.analytics_tracker import AnalyticsTracker

    monkeypatch.setenv("ANALYTICS_VISITOR_SALT", "test-salt")
    ledger = tmp_path / "visitor_analytics.json"
    inside = (datetime.now() - timedelta(days=1)).timestamp()
    ledger.write_text(json.dumps({
        "visits": [],
        "reads": _rows(tracker_mod.MAX_VISITS + 1, inside),
    }))

    tracker = AnalyticsTracker(data_file=ledger)
    tracker.track_visit("/", "Mozilla/5.0 test", "203.0.113.7")
    tracker.flush()

    reads = json.loads(ledger.read_text())["reads"]
    assert len(reads) == tracker_mod.MAX_VISITS + 1, (
        f"the writer kept {len(reads)} read rows — the cap is being applied "
        "somewhere other than _prune"
    )
