"""1.6.44 item 9 — DIVERGENCES carries its guard entries where they get read.

A guard entry documents something this repo MATCHES or deliberately does NOT
carry. Nothing in a diff distinguishes a deliberate absence from an accident,
so a sync "restores" it — and the people who would have known better are the
fan-out and the next sync author, who read this FILE. A test docstring is
invisible to both.

The section is therefore structural, not decorative, and these assertions hold
its shape.
"""

from __future__ import annotations

import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
TEXT = (REPO / "DIVERGENCES.md").read_text()

SECTION = "## Recorded conventions (not divergences)"


def test_the_subsection_exists():
    assert SECTION in TEXT


def test_the_guard_entries_live_under_it():
    """The acceptance: our own guard entries MOVED, not merely added."""
    start = TEXT.index(SECTION)
    end = TEXT.index("## This repo's divergences")
    section = TEXT[start:end]

    bullets = re.findall(r"^- \*\*(.+?)\*\*", section, re.M | re.S)
    assert len(bullets) >= 4, (
        f"only {len(bullets)} guard entries — the section is decorative"
    )

    joined = section.lower()
    for expected in ("user-agent list", "loading", "skip", "stdlib"):
        assert expected in joined, f"{expected!r} is not recorded as a guard"


def test_guard_entries_are_not_duplicated_in_the_numbered_divergences():
    """A guard recorded twice drifts, and the copy nobody edits is the one a
    sync reads."""
    start = TEXT.index("## This repo's divergences")
    numbered = TEXT[start:TEXT.index("## Byte-owned paths")]

    assert "Neither is a prop of dash 4.4.1" not in numbered, (
        "the 6f prohibition is recorded in both the guard section and a "
        "numbered divergence"
    )


def test_the_numbered_divergences_are_sequential():
    """Ordering, because entries were appended mid-file during this pass and
    a file that reads 1,2,...,12,17,18,13,... is one nobody trusts."""
    numbers = [int(n) for n in re.findall(r"^### (\d+)\.", TEXT, re.M)]

    assert numbers, "no numbered divergences found — this test swept nothing"
    assert numbers == sorted(numbers), f"out of order: {numbers}"
    assert numbers == list(range(1, len(numbers) + 1)), f"gaps: {numbers}"


@pytest.mark.parametrize("heading", [
    "## Recorded conventions (not divergences)",
    "## This repo's divergences",
    "## Byte-owned paths",
    "## Declared posture",
])
def test_the_files_top_level_shape_is_intact(heading):
    assert TEXT.count(heading) == 1, f"{heading!r} appears != once"
