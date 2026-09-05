"""1.6.44 item 17 — trap 3(a) becomes a script, so nobody re-derives it live.

The trap is THIS FORK'S OWN measurement (2026-08-31): which branch Render
builds can be established on a GREEN push, by timing, without waiting for a red
one. What it lacked was a concrete form — and a method that has to be
reconstructed mid-promote, at speed, is a method that will be reconstructed
wrong. `scripts/promote_sampler.py` is that form.

The three things a hand-written watcher gets wrong, all pinned below:

1. ONE loop, ONE timeline — two separate reconstructions invite exactly the
   arithmetic error the measurement exists to avoid;
2. time against the PROMOTE STEP's `completed_at`, never the deploy JOB's: the
   job CONTAINS the build-match wait, so it completes when the wait SEES the
   swap and therefore tracks the swap, not the promote;
3. `unreadable` is a state DISTINCT from `old`. The container restart lands
   exactly where the bracket needs its sample, so an un-retried loop is
   systematically blind at the only moment that matters — and folding
   unreadable into old invents a bracket nobody observed.
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import promote_sampler as sampler  # noqa: E402

KIT = re.sub(r"\s+", " ", (REPO / ".claude" / "CLAUDE.md").read_text()).lower()


# --------------------------------------------------------------------------
# The detect: three phrases, whitespace FLATTENED.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("phrase", ["eight samples at 45", "completed_at",
                                    "unreadable"])
def test_the_trap_carries_the_concrete_form(phrase):
    """Flattened, because these phrases WRAP in the kit's 72-column prose and
    a literal grep would miss every one of them (item 13)."""
    assert phrase in KIT, f"the amended trap does not carry {phrase!r}"


def test_the_trap_was_amended_in_place_not_appended():
    """The item says amend, not append.

    An appended second trap leaves the original standing without the concrete
    form, and a reader who finds the first one stops there.
    """
    assert KIT.count("which branch render actually builds") == 1, (
        "there are two branch-timing traps now — one of them is a duplicate"
    )
    original = KIT.index("which branch render actually builds")
    amended = KIT.index("eight samples at 45")
    assert amended > original, "the concrete form is not inside the trap"
    assert amended - original < 3000, (
        "the concrete form is too far from the trap it belongs to — it was "
        "appended elsewhere rather than amended in"
    )


# --------------------------------------------------------------------------
# The sampler's own contract.
# --------------------------------------------------------------------------

def test_unreadable_is_a_state_of_its_own():
    assert sampler.classify(None, "abc123def456") == sampler.UNREADABLE
    assert sampler.UNREADABLE != sampler.OLD, (
        "unreadable collapsed into old — the bracket becomes one nobody saw"
    )


def test_a_matching_build_is_new_and_a_different_one_is_old():
    assert sampler.classify("abc123def456789", "abc123def456") == sampler.NEW
    assert sampler.classify("999999999999", "abc123def456") == sampler.OLD


def test_it_probes_with_the_fleet_probe_ua():
    """A sampler that pollutes the ledger it is timing is its own bug."""
    from lib.constants import INTERNAL_UA_TOKEN

    assert INTERNAL_UA_TOKEN in sampler.PROBE_UA
    assert sampler.PROBE_UA.startswith("curl/8"), (
        "the probe leads with the internal token, so it classifies "
        "crawler-lane instead of exercising the lane it means to"
    )


def test_it_points_at_this_host():
    assert "leaflet.2plot.dev" in sampler.DEFAULT_URL, sampler.DEFAULT_URL


def test_it_uses_a_certifi_ssl_context():
    """The kit's own trap: an ad-hoc probe against a production host needs the
    certifi context or it dies on CERTIFICATE_VERIFY_FAILED."""
    source = (REPO / "scripts" / "promote_sampler.py").read_text()
    assert "certifi" in source
    assert "SSL_CONTEXT" in source


def test_each_sample_is_retried():
    """The restart lands exactly where the bracket needs its sample."""
    assert sampler.ATTEMPTS >= 3, sampler.ATTEMPTS


# --------------------------------------------------------------------------
# The refusal — the part that makes a printed bracket mean something.
# --------------------------------------------------------------------------

def _run(states, capsys, monkeypatch):
    """Drive main() over a canned sequence of wire states."""
    builds = iter(states)
    monkeypatch.setattr(sampler, "read_build", lambda url: next(builds))
    monkeypatch.setattr(sampler.time, "sleep", lambda _s: None)
    code = sampler.main(
        ["promote_sampler.py", "--sha", "abc123def456", "--samples",
         str(len(states)), "--interval", "0"]
    )
    return code, capsys.readouterr().out


def test_it_refuses_a_bracket_it_did_not_observe(capsys, monkeypatch):
    """A single NEW sample cannot say what it FOLLOWED.

    This is the refusal the item asks for: without an OLD sample before the
    first NEW, the run has measured a build that was already live and can
    report nothing about when it landed.
    """
    code, out = _run(["abc123def456789"] * 3, capsys, monkeypatch)

    assert code == 1
    assert "cannot say what" in out, out


def test_it_refuses_when_the_swap_never_landed(capsys, monkeypatch):
    code, out = _run(["999999999999"] * 3, capsys, monkeypatch)

    assert code == 1
    assert "did not land inside the window" in out, out


def test_it_reports_a_bracket_it_did_observe(capsys, monkeypatch):
    """The positive case, so the two refusals above are not the only outcome —
    a sampler that refused everything would satisfy them both."""
    code, out = _run(
        ["999999999999", "999999999999", None, "abc123def456789"],
        capsys, monkeypatch,
    )

    assert code == 0, out
    assert "last OLD" in out and "first NEW" in out
    assert "unreadable" in out, (
        "the unreadable sample inside the bracket was not reported — that "
        "sample is the container restart, the most informative one"
    )
    assert "completed_at" in out, (
        "the output does not say to time against the promote STEP"
    )
