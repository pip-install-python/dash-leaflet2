"""1.6.44 item 10 — the kit carries the acceptance-output rule.

An acceptance is a claim about a tree AT A VERSION, and a report that omits
the version is a claim nobody can reproduce. The rule matters more on this
fork than on a pinned host: our requirements line is a `>=2.8.0` FLOOR, so
"what the file says" and "what the venv resolved" are different questions.
"""

from __future__ import annotations

import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
KIT = (REPO / ".claude" / "CLAUDE.md").read_text()


def _flat(text: str) -> str:
    """Whitespace-flattened, so a phrase that WRAPS across a line still
    matches (the template's own item-13 finding: two of five detects were
    formatting-bound)."""
    return re.sub(r"\s+", " ", text).lower()


FLAT = _flat(KIT)


@pytest.mark.parametrize("phrase", [
    "print the resolved version beside the result",
    "mod.__file__",
    "never by reading",
    "actionlint",
    "shellcheck",
])
def test_the_rule_names_its_parts(phrase):
    assert phrase.lower() in FLAT, f"the kit does not carry {phrase!r}"


def test_the_rule_says_import_rather_than_read_the_requirements():
    """The specific instruction, not just the topic.

    "print the version" is satisfiable by reading requirements.txt, which
    states an intent — and on a `>=` floor the intent and the fact routinely
    differ. The kit has to say which one counts.
    """
    assert "requirements.txt" in FLAT
    assert "importing" in FLAT


def test_the_rule_covers_tools_whose_local_run_differs_from_ci():
    assert "when the check you ran differs from the check ci runs" in FLAT


def test_the_kit_names_this_forks_own_unrunnable_leg():
    """Item 10's rule applied to itself: this seat cannot run the quart leg,
    and a kit that states the general rule without naming the local instance
    leaves every report free to omit it."""
    assert "quart" in FLAT


def test_the_resolved_version_is_actually_resolvable_this_way():
    """The mechanism the rule prescribes must work in this tree."""
    import dash_improve_my_llms as pkg

    assert pkg.__file__.endswith("__init__.py")
    assert "site-packages" in pkg.__file__ or ".venv" in pkg.__file__
    assert re.match(r"^\d+\.\d+", pkg.__version__), pkg.__version__
