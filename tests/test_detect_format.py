"""1.6.44 item 13 — a detect parses, or it strips comments AND STRINGS.

THE SPEC'S FILE TARGET DOES NOT EXIST HERE. Item 13 names `sync/README.md`;
this fork has no `sync/` directory (the template is the only host that keeps
the spec archive). The RULE still applies — this repo writes detects in every
test file — so it lands in `.claude/CLAUDE.md`, which is where this fork keeps
its authoring rules, and the machinery lands in `conftest.live_source()`.

The rule was earned twice during this drop, on this tree:

* item 6's a11y detects hunted `trigger="hover"`, `loading=` and `Pillow` and
  matched the comments explaining that those must never appear;
* item 8 tripped the pre-existing UA-list guard, which ALREADY stripped
  comments and the module docstring — a FUNCTION docstring quoting a measured
  `classify()` result read as a resurrected vendor table.

The second is the interesting one: it shows that "strip comments" is not a
weaker version of the right answer, it is a different answer that fails.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from conftest import live_source

REPO = pathlib.Path(__file__).resolve().parent.parent
KIT = (REPO / ".claude" / "CLAUDE.md").read_text()
FLAT_KIT = re.sub(r"\s+", " ", KIT).lower()


# --------------------------------------------------------------------------
# The rule is written down, and names strings.
# --------------------------------------------------------------------------

def test_the_rule_names_strings_not_only_comments():
    """The detect for this item: the rule must name STRINGS."""
    assert "strip comments and strings" in FLAT_KIT, (
        "the kit's detect rule does not mention strings"
    )
    assert "docstring" in FLAT_KIT
    assert "ast.parse" in FLAT_KIT or "ast.unparse" in FLAT_KIT


def test_the_rule_names_the_formatting_failure_modes():
    for phrase in ("flatten", "case-insensitiv"):
        assert phrase in FLAT_KIT, f"the kit does not mention {phrase!r}"


@pytest.mark.parametrize("phrase", [
    "measured on a green push",
    "corpus is non-empty",
    "verify the artifact the claim is about",
])
def test_the_sync_1_6_43_item_3_detects_are_green(phrase):
    """The acceptance, read CASE-INSENSITIVELY and on flattened whitespace.

    Both readings, because the template's own version of this detect grepped
    the phrase in the CAPITALS a spec uses for emphasis while the trap ships in
    sentence case — so it returned 0 on the tree that authored it.
    """
    assert phrase in FLAT_KIT, f"trap phrase absent (flattened): {phrase!r}"
    assert re.search(re.escape(phrase), KIT, re.I), (
        f"trap phrase absent (raw, case-insensitive): {phrase!r}"
    )


# --------------------------------------------------------------------------
# The machinery, and the control that shows why a comment strip is not enough.
# --------------------------------------------------------------------------

SAMPLE = '''\
"""Module docstring mentioning FORBIDDEN_TOKEN to explain its absence."""


def f():
    """Function docstring also mentioning FORBIDDEN_TOKEN."""
    # A comment mentioning FORBIDDEN_TOKEN.
    return 1
'''


def _comment_strip(text: str) -> str:
    """The naive approach: drop comment lines and the MODULE docstring.

    This is not a strawman — it is what this repo's UA-list guard actually did
    until item 8, and it is the obvious thing to write.
    """
    code = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    return re.sub(r'^"""[\s\S]*?"""', "", code, count=1)


def test_a_comment_strip_still_sees_the_token(tmp_path):
    """THE CONTROL. Without this, the test below proves only that some
    function returns a string without the token in it."""
    assert "FORBIDDEN_TOKEN" in _comment_strip(SAMPLE), (
        "the naive strip no longer leaks the token — re-derive this item"
    )


def test_live_source_does_not(tmp_path):
    path = tmp_path / "sample.py"
    path.write_text(SAMPLE)

    assert "FORBIDDEN_TOKEN" not in live_source(path), (
        "live_source leaked a token from a comment or docstring"
    )


def test_live_source_still_sees_real_code(tmp_path):
    """The other direction: a stripper that returns nothing would pass every
    absence assertion ever written."""
    path = tmp_path / "sample.py"
    path.write_text(SAMPLE + "\nREAL_CODE_TOKEN = 'FORBIDDEN_TOKEN'\n")

    source = live_source(path)
    assert "REAL_CODE_TOKEN" in source
    assert "FORBIDDEN_TOKEN" in source, (
        "a token in a real assignment was stripped — live_source is removing "
        "code, not just prose"
    )


def test_the_guards_that_use_it_actually_use_it():
    """Both callers, so the helper cannot become decorative."""
    for name in ("test_analytics_classifier.py", "test_a11y_agentic.py",
                 "test_vendor_class.py"):
        text = (REPO / "tests" / name).read_text()
        assert "live_source" in text or "ast" in text, (
            f"{name} makes absence assertions without parsing"
        )
