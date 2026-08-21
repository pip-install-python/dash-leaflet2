"""The control-board store must reconcile across gunicorn workers.

The Dockerfile runs this app with more than one worker process
(``--workers ${WEB_CONCURRENCY:-2}``). A board toggle mutates
``_overrides`` only in the worker that served the POST and persists to
``PAGE_VISIBILITY_FILE``; every other worker holds its import-time copy
unless it re-reads the file. Before the reload landed, an anonymous
refresh of a page the board had just made public was a coin flip decided
by which worker answered — the pilot's live defect of 2026-08-21.

These tests play the *other* worker: they write the store file behind
the module's back and check the read path notices. They also pin the
convention the rest of this suite relies on — injecting straight into
``_overrides`` without touching the file must never be clobbered.
"""

import json
import os
import time

import pytest

from lib import page_visibility


@pytest.fixture
def clean_store():
    """Snapshot module state; leave no store file behind for later tests."""
    saved_overrides = {
        path: dict(entry) for path, entry in page_visibility._overrides.items()
    }
    saved_stamp = page_visibility._store_mtime_ns
    yield
    page_visibility._STORE_PATH.unlink(missing_ok=True)
    page_visibility._overrides.clear()
    page_visibility._overrides.update(saved_overrides)
    page_visibility._store_mtime_ns = saved_stamp
    page_visibility._next_stat_at = 0.0


def _foreign_write(payload: dict) -> None:
    """A write by 'another worker': same file, not through this module."""
    path = page_visibility._STORE_PATH
    path.write_text(json.dumps(payload))
    stamp = time.time_ns()
    os.utime(path, ns=(stamp, stamp))  # guarantee the mtime actually moves


def test_a_foreign_workers_toggle_is_picked_up(clean_store):
    """The whole defect: another worker made a page public; we must see it."""
    _foreign_write({"/reload-canary": {"visibility": "public"}})
    page_visibility._next_stat_at = 0.0  # skip the 1s stat throttle

    assert page_visibility.tier_override("/reload-canary") == "public"
    assert page_visibility.get_settings("/reload-canary")["visibility"] == "public"


def test_a_second_foreign_write_supersedes_the_first(clean_store):
    """Reload keys on mtime, so consecutive toggles each land."""
    _foreign_write({"/reload-canary": {"visibility": "public"}})
    page_visibility._next_stat_at = 0.0
    assert page_visibility.tier_override("/reload-canary") == "public"

    _foreign_write({"/reload-canary": {"visibility": "auth", "llms_public": False}})
    page_visibility._next_stat_at = 0.0
    assert page_visibility.tier_override("/reload-canary") == "auth"
    assert page_visibility.llms_public_override("/reload-canary") is False


def test_direct_injection_survives_when_the_file_never_moves(clean_store):
    """The suite-wide convention: tests write ``_overrides`` directly.

    With no store file on disk (stat fails) the reload must be a no-op,
    or every existing access test would have its fixtures wiped mid-run.
    """
    page_visibility._STORE_PATH.unlink(missing_ok=True)
    page_visibility._overrides["/injected"] = {"visibility": "hidden"}
    page_visibility._next_stat_at = 0.0

    assert page_visibility.tier_override("/injected") == "hidden"


def test_own_persist_does_not_bounce_back(clean_store):
    """The writing worker records its own stamp — no self-reload churn.

    After ``set_visibility`` persists, injecting an extra entry directly
    must survive a reload check: the file's mtime equals the recorded
    stamp, so nothing is re-read and the injection stays.
    """
    page_visibility.set_visibility("/reload-canary", "public")
    page_visibility._overrides["/injected"] = {"visibility": "hidden"}
    page_visibility._next_stat_at = 0.0

    assert page_visibility.tier_override("/injected") == "hidden"
    assert page_visibility.tier_override("/reload-canary") == "public"
