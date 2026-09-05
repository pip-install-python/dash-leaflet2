"""1.6.44 item 8 — prefer the package's vendor_class, derive only when absent.

The rule this repo already lives by, extended to one more field: there is ONE
classifier, and a fork that computes an answer the package also computes will
disagree with it the moment the registry learns something the fork's table does
not have. `lib/analytics_tracker.py` carried a User-Agent list for a year and
filed ClaudeBot — Anthropic's TRAINING crawler — under "search"; the fix was to
delegate, not to correct the table.

So `vendor_class` is TAKEN from the event where present and DERIVED FROM THE
PACKAGE'S OWN REGISTRY where absent. Never from a local map.

THE TEST SHAPE MATTERS MORE THAN USUAL HERE, and the spec says why: "prefer"
that never derives and "derive" that never prefers both pass a one-sided test.
Both directions are pinned, and the prefer direction uses a CONFLICTING
fixture — a package value the registry would contradict — because a fixture
where the two agree cannot tell which one was used.
"""

from __future__ import annotations

import pathlib

import pytest

import lib.analytics_tracker as tracker_mod

REPO = pathlib.Path(__file__).resolve().parent.parent

CLAUDEBOT_UA = (
    "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; "
    "ClaudeBot/1.0; +claudebot@anthropic.com)"
)


def test_the_registry_and_a_conflicting_value_really_differ():
    """Non-vacuity for the fixture below.

    If the registry happened to answer "sentinel" the conflict test would pass
    while proving nothing about which source won.
    """
    assert tracker_mod._vendor_class_from_registry("claudebot") == "training"


def test_a_package_provided_class_passes_through_untouched(monkeypatch):
    """PREFER. The package's answer wins even when the registry disagrees.

    The conflict is deliberate and impossible in the wild — that is the point.
    A fixture where package and registry agree cannot distinguish "took the
    package's value" from "recomputed and got lucky".
    """
    monkeypatch.setattr(
        tracker_mod, "classify",
        lambda ua, ip=None: {
            "lane": "crawler",
            "bot_type": "training",
            "vendor_key": "claudebot",       # registry says "training"
            "vendor_class": "sentinel-from-package",
            "verified": "verified",
        },
    )
    result = tracker_mod._classify(CLAUDEBOT_UA)

    assert result["vendor_class"] == "sentinel-from-package", (
        "the fork overwrote the package's vendor_class with its own answer"
    )


def test_an_absent_class_is_derived_from_the_registry(monkeypatch):
    """DERIVE. The other direction, so a "prefer" that never derives fails."""
    monkeypatch.setattr(
        tracker_mod, "classify",
        lambda ua, ip=None: {
            "lane": "crawler",
            "bot_type": "training",
            "vendor_key": "claudebot",
            "vendor_class": None,
            "verified": "n/a",
        },
    )
    result = tracker_mod._classify(CLAUDEBOT_UA)

    assert result["vendor_class"] == "training", (
        "an event carrying a vendor and no class reached the ledger unlabelled"
    )


def test_no_vendor_means_no_class_and_no_crash(monkeypatch):
    monkeypatch.setattr(
        tracker_mod, "classify",
        lambda ua, ip=None: {"lane": "browser", "vendor_key": None,
                             "vendor_class": None},
    )
    assert tracker_mod._classify("Mozilla/5.0")["vendor_class"] is None


def test_an_unknown_vendor_derives_nothing_rather_than_guessing():
    assert tracker_mod._vendor_class_from_registry("not-a-real-vendor") is None
    assert tracker_mod._vendor_class_from_registry(None) is None
    assert tracker_mod._vendor_class_from_registry("") is None


def test_the_real_classifier_still_labels_claudebot_as_training():
    """End to end on the RESOLVED package, no monkeypatching.

    The two directions above are both stubbed by construction; this is the one
    that would notice if `classify` stopped being called at all.
    """
    result = tracker_mod._classify(CLAUDEBOT_UA)

    assert result["vendor_key"] == "claudebot"
    assert result["vendor_class"] == "training", result
    assert result["lane"] == "crawler"


def test_the_class_is_never_read_from_a_local_map():
    """The rule, pinned in source: no hand-written vendor->class table.

    Parsed rather than grepped (item 13) — the module's prose explains at
    length why such a table must not exist, and a raw substring check matches
    the explanation.
    """
    import ast

    tree = ast.parse((REPO / "lib" / "analytics_tracker.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:] or [ast.Pass()]
    source = ast.unparse(tree)

    for token in ("training", "search", "traditional"):
        assert f"'{token}'" not in source, (
            f"a literal {token!r} appears in the tracker's CODE — the class "
            "must come from the package's registry, never a local table"
        )


@pytest.mark.parametrize("name", ["get_vendor"])
def test_the_derivation_uses_the_packages_own_registry(name):
    """Same registry `classify()` reads — not a second opinion."""
    import ast

    source = ast.unparse(
        ast.parse((REPO / "lib" / "analytics_tracker.py").read_text())
    )
    assert name in source
    assert "dash_improve_my_llms.vendors" in source
