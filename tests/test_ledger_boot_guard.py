"""1.6.44 item 22 — the ledger says at boot whether it will survive the deploy.

With `TRAFFIC_ANALYTICS_FILE` unset, `analytics_path()` falls back to
`visitor_analytics.json` in the app directory — which a Docker deploy replaces
wholesale. Every visit and every read row is then discarded on each deploy
while nothing anywhere says so. This host has had exactly that shape of defect
before, with the control-board store.

MIRRORS the `[visibility]` warning in lib/page_visibility.py, deliberately: an
operator greps one deploy log for "WARNING" and should find both persistence
problems in the same shape, not one warning and one silence.

WHY A SUBPROCESS AND NOT `caplog`. The drop says to assert this via caplog. It
cannot be: the guard is a `print` at IMPORT time, before any logging
configuration a host might apply — which is the point, since the line has to
reach the deploy log unconditionally. caplog captures the logging module and
would see nothing, and a test built that way would fail against correct code
and be "fixed" by turning the print into a logger call that a real deploy log
might never show. Booting a fresh interpreter is also the real boot path.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent

BOOT = "import lib.analytics_tracker"


def _boot(env_overrides: dict) -> str:
    """Boot a fresh interpreter and return everything it printed."""
    env = dict(os.environ)
    env.pop("TRAFFIC_ANALYTICS_FILE", None)
    env.update({k: v for k, v in env_overrides.items() if v is not None})
    env["PYTHONPATH"] = str(REPO)

    result = subprocess.run(
        [sys.executable, "-c", BOOT],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return result.stdout + result.stderr


def test_unset_warns_at_boot():
    output = _boot({})

    assert "[analytics] WARNING" in output, (
        "no boot warning with TRAFFIC_ANALYTICS_FILE unset — a deploy that "
        "silently discards the ledger looks identical to one that does not"
    )
    assert "TRAFFIC_ANALYTICS_FILE" in output
    assert "will NOT survive a redeploy" in output


def test_set_is_silent(tmp_path):
    """The other direction. A guard that always warns is noise an operator
    learns to skip, which is the same as no guard."""
    output = _boot({"TRAFFIC_ANALYTICS_FILE": str(tmp_path / "ledger.json")})

    assert "[analytics] WARNING" not in output, (
        f"warned despite the variable being set:\n{output}"
    )


def test_a_declared_var_pointing_at_an_unmounted_disk_still_warns():
    """The env being right is only HALF the persistence story.

    An app can mkdir /var/data on the container filesystem and look fine until
    the next deploy wipes it — indistinguishable from the unset case without
    this check.
    """
    output = _boot({"TRAFFIC_ANALYTICS_FILE": "/var/data/visitor_analytics.json"})

    if os.path.ismount("/var/data"):   # pragma: no cover — not on this seat
        pytest.skip("/var/data is a real mount here")

    assert "not a mounted disk" in output, output


def test_it_mirrors_the_visibility_warning_shape():
    """Same shape, same grep — asserted STRUCTURALLY, not by co-firing.

    The first version of this booted `lib.analytics_tracker` and expected the
    `[visibility]` warning alongside it. It does not fire from that import —
    it lives in `lib.page_visibility` and runs on run.py's boot — so the test
    failed against correct code. The property that actually matters is that
    the two guards READ the same, which is a property of the source.
    """
    import re

    analytics = (REPO / "lib" / "analytics_tracker.py").read_text()
    visibility = (REPO / "lib" / "page_visibility.py").read_text()

    for source, prefix, var in (
        (analytics, "[analytics] WARNING", "TRAFFIC_ANALYTICS_FILE"),
        (visibility, "[visibility] WARNING", "PAGE_VISIBILITY_FILE"),
    ):
        assert prefix in source, f"{prefix} is missing"
        assert f"{var} unset" in source, f"{var} unset is not the wording"
        assert "not a mounted disk" in source, (
            f"{prefix} has no unmounted-disk branch — the env being right is "
            "only half the persistence story"
        )

    # Both must be a bare print, so the line reaches a deploy log whatever a
    # host has done to logging configuration.
    for source, prefix in ((analytics, "[analytics]"), (visibility, "[visibility]")):
        window = source[source.index(prefix) - 200:source.index(prefix)]
        assert re.search(r"print\($", window.strip()) or "print(" in window, (
            f"{prefix} is not emitted by a bare print()"
        )


# --------------------------------------------------------------------------
# The pairing with item 20.
# --------------------------------------------------------------------------

def test_the_boot_guard_and_the_healthz_block_agree(tmp_path, monkeypatch):
    """PAIRS WITH ITEM 20: the guard says it ONCE, the block says it
    CONTINUOUSLY. Assert they AGREE rather than pinning either value.

    Two diagnostics that disagree about the same fact are worse than one —
    whichever an operator happens to read, they cannot trust it.
    """
    import lib.health as health

    # A path OUTSIDE the repo: persistent, and the boot guard stays silent.
    outside = tmp_path / "var" / "data" / "visitor_analytics.json"
    outside.parent.mkdir(parents=True)
    monkeypatch.setattr("lib.analytics_tracker.analytics_path", lambda: outside)

    block = health._ledger_block()
    quiet = "[analytics] WARNING" not in _boot(
        {"TRAFFIC_ANALYTICS_FILE": str(outside)}
    )

    assert block["persistent"] is True
    assert quiet is True, (
        "healthz reports the ledger persistent while the boot guard warns — "
        "the two diagnostics disagree"
    )


def test_they_agree_in_the_unset_case(monkeypatch):
    """The other half of the pairing."""
    import lib.health as health

    inside = REPO / "visitor_analytics.json"
    monkeypatch.setattr("lib.analytics_tracker.analytics_path", lambda: inside)

    block = health._ledger_block()
    warned = "[analytics] WARNING" in _boot({})

    assert block["persistent"] is False
    assert warned is True, (
        "healthz reports the ledger NON-persistent while the boot guard is "
        "silent — an operator reading only the log would never know"
    )


def test_the_healthz_block_is_still_readable_after_all_this(client):
    """Cheap end-to-end guard: the guard runs at import, and an import-time
    print that raised would take the whole app down rather than the ledger."""
    payload = json.loads(client.get("/healthz").text)

    assert payload["ok"] is True
    assert "ledger" in payload
