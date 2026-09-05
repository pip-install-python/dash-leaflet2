"""1.6.44 item 14 — the traps-currency counter, and why it matches loosely.

A fork's traps section drifts behind the template's SILENTLY: the kit is
contract-class, so no sync copies it, and until this script nothing printed the
gap. emojimart carried 7 entries against 22 and its HEAD trap still held the
diagnosis 1.6.32 had corrected — a fork acting on a fact the fleet retired
months ago.

THE FORK ADAPTATION IS THE POINT OF SHIPPING IT HERE. The template's copy
resolves its reference kit as `REPO_ROOT/.claude/CLAUDE.md`, which on the
template IS the reference. Run unchanged in a fork, that compares this repo's
kit against ITSELF and reports a perfect score forever — worse than not having
the script, because it manufactures the reassurance the item exists to deny.

Measured on this tree when the script first ran here: **fork 21 / template 28**,
nine named. Four were real absences, three belonged to later items in this same
stack, and TWO WERE FALSE POSITIVES — traps this fork carries, split across two
bullets, so no single bullet cleared the 0.6 overlap. That limit is recorded in
the kit rather than tuned away: the threshold is deliberately generous because
a strict check trains forks to paste over their own adaptations.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import kit_traps  # noqa: E402

TEMPLATE = kit_traps.resolve_template()


def test_this_forks_traps_section_parses():
    entries = kit_traps.trap_entries((REPO / ".claude" / "CLAUDE.md").read_text())
    assert len(entries) >= 20, (
        f"only {len(entries)} trap entries parsed — either the section shrank "
        "or the parser stopped seeing it, and both make every count below a lie"
    )


def test_the_reference_kit_is_never_this_repos_own():
    """The fork adaptation, asserted directly.

    If `resolve_template()` ever returns our own kit, the comparison becomes
    self-referential and reports 100% forever.
    """
    own = (REPO / ".claude" / "CLAUDE.md").resolve()
    if TEMPLATE is not None:
        assert TEMPLATE.resolve() != own, (
            "kit_traps is comparing this repo's kit against itself"
        )


def test_it_reports_the_pair_and_names_what_is_missing():
    """The detect: `fork N / template M`, plus names."""
    if TEMPLATE is None:
        pytest.skip("no template kit beside this checkout")

    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "kit_traps.py")],
        capture_output=True, text=True, cwd=REPO,
    )
    out = result.stdout

    assert "fork " in out and "/ template " in out, out
    fork_n = int(out.split("fork ")[1].split(" /")[0])
    template_n = int(out.split("/ template ")[1].split()[0])
    assert fork_n >= 20 and template_n >= 20, out
    if result.returncode:
        assert "MISSING:" in out, "non-zero exit but nothing named"


def test_matching_is_by_token_overlap_not_exact_text():
    """A fork is EXPECTED to merge a trap into its own wording.

    A reworded entry carrying the same content must still count, or the check
    trains forks to paste over their adaptations — the opposite of the item.
    """
    template_entry = (
        "Always GET, never HEAD — on the ASGI backends HEAD is answered by "
        "nothing at all, because FastAPI's APIRoute takes methods literally."
    )
    reworded = (
        "Always GET and never HEAD — on our ASGI backends HEAD is answered by "
        "nothing at all, since FastAPI's APIRoute takes its methods literally "
        "here too, measured on this host 2026-09-05."
    )
    assert kit_traps._present(template_entry, [reworded]), (
        "a merged, host-annotated rewording read as absence"
    )


def test_the_matcher_only_reads_the_first_sentence_and_that_is_a_limit():
    """A SECOND measured limit of the shared tool, recorded not patched.

    `_tokens()` splits on the first `.` or `:` and scores only that clause. A
    fork that rewords a trap to open with a short colon-terminated summary is
    therefore scored on a handful of words and reads as missing, however
    faithfully the rest of the entry carries the trap.

    Found by this test file's own first fixture. NOT fixed here on purpose:
    the script's counts are compared across the fleet, so a fork that quietly
    changes the algorithm makes its number incomparable with everyone else's.
    The limit belongs in a pushback to the template seat, and meanwhile in the
    kit beside the split-across-bullets one.
    """
    template_entry = (
        "Always GET, never HEAD — on the ASGI backends HEAD is answered by "
        "nothing at all, because FastAPI's APIRoute takes methods literally."
    )
    early_colon = (
        "Always GET and never HEAD: on our ASGI backends nothing at all "
        "answers HEAD, since FastAPI's APIRoute takes its methods literally."
    )
    assert not kit_traps._present(template_entry, [early_colon]), (
        "the first-sentence limit is gone — the tool improved upstream, so "
        "drop this test and the kit note with it"
    )


def test_an_unrelated_entry_does_not_count_as_present():
    """The other direction: loose must not mean useless."""
    template_entry = (
        "Always GET, never HEAD — on the ASGI backends HEAD is answered by "
        "nothing at all."
    )
    unrelated = "Never round-trip JSON through zsh echo; it eats the newlines."
    assert not kit_traps._present(template_entry, [unrelated])


def test_the_known_false_positive_is_recorded_in_the_kit():
    """The measured limit, written down rather than tuned away.

    The threshold cannot see a template trap a fork carries SPLIT ACROSS two
    bullets. That happened twice here, so the kit says to read the pair as a
    prompt to look rather than as a verdict.
    """
    import re

    kit = re.sub(r"\s+", " ", (REPO / ".claude" / "CLAUDE.md").read_text()).lower()
    assert "split across two" in kit, (
        "the counter's known limit is not recorded, so the next reader will "
        "treat a false positive as a missing trap and duplicate it"
    )


def test_this_fork_is_not_far_behind():
    """The acceptance, as a number rather than a feeling.

    Not "equal": two of the template's traps belong to items 18 and 19, which
    are later in this same stack, and a test demanding parity mid-stack would
    fail for the wrong reason.
    """
    if TEMPLATE is None:
        pytest.skip("no template kit beside this checkout")

    fork_n, template_n, missing = kit_traps.compare(
        (REPO / ".claude" / "CLAUDE.md").read_text(), TEMPLATE.read_text()
    )
    assert fork_n >= template_n - 3, (
        f"fork {fork_n} / template {template_n}; missing "
        f"{[kit_traps.key(m) for m in missing]}"
    )
