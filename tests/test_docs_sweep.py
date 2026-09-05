"""1.6.44 item 7 — CI actually reads docs/, and the heading it must not double.

THE GAP, measured on this tree rather than inherited. The lint job runs

    flake8 lib components pages tests scripts run.py usage.py

`docs/` is not on that list, and `.flake8` excludes `docs/*/` outright. So
nothing in CI has ever read the 28 Python files under `docs/` — every one of
which is imported by a documentation page at boot, which means a syntax error
in any of them takes a page down at import, not at render.

The measurement, with a deliberately broken `def broken(:` in `docs/`:

    flake8 docs/                     -> exit 0, ZERO output
    python -m py_compile <same file> -> exit 1, SyntaxError

The linter is not passing that file. It is not reading it. That is note 88's
rule in its sharpest form: a sweep that found nothing and a sweep that swept
nothing produce the same green, and only one of them is evidence — so the CI
step counts what it swept and fails on an empty corpus.
"""

from __future__ import annotations

import compileall
import pathlib
import re

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
CI = (REPO / ".github" / "workflows" / "ci.yml").read_text()

DOC_PY = sorted(DOCS.rglob("*.py"))


def test_the_docs_corpus_is_not_empty():
    """Asserted FIRST and separately, because every other assertion in this
    file is a negative over this corpus."""
    assert len(DOC_PY) >= 10, (
        f"only {len(DOC_PY)} python files under docs/ — either the corpus "
        "moved or this sweep is about to go green over nothing"
    )


def test_every_docs_python_file_compiles():
    """The in-process twin of the CI step."""
    failures = []
    for path in DOC_PY:
        if not compileall.compile_file(str(path), quiet=2, force=True):
            failures.append(str(path.relative_to(REPO)))
    assert not failures, f"docs/ files that do not compile: {failures}"


def test_flake8_does_not_cover_docs_which_is_why_this_exists():
    """Pin the REASON, so nobody deletes the sweep as redundant.

    If `.flake8` ever stops excluding `docs/*/` AND the lint job starts
    passing `docs`, this test goes red and the sweep can be reconsidered
    deliberately instead of quietly.
    """
    flake8_cfg = (REPO / ".flake8").read_text()
    excluded = "docs/*/" in flake8_cfg

    lint_step = re.search(r"run:\s*flake8\s+([^\n]+)", CI)
    assert lint_step, "could not find the flake8 invocation in ci.yml"
    linted = lint_step.group(1).split()

    assert excluded or "docs" not in linted, (
        "docs/ is now both linted and un-excluded — the py_compile sweep may "
        "be redundant; decide deliberately rather than leaving both"
    )


def test_ci_registers_the_sweep_by_name():
    """The detect names the step, so the step must carry the name."""
    workflow = yaml.safe_load(CI)
    names = [
        step.get("name", "")
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
    ]
    assert "py_compile sweep of docs/" in names, (
        f"the sweep step is not registered by name; steps: {names}"
    )


def test_the_sweep_step_fails_on_an_empty_corpus():
    """The step must not report a green sweep of nothing.

    Asserted on the step's own script rather than by running CI: the guard is
    the whole point of the item, and a step that lost it would still pass
    every other assertion here.
    """
    workflow = yaml.safe_load(CI)
    step = next(
        s for job in workflow["jobs"].values()
        for s in job.get("steps", [])
        if s.get("name") == "py_compile sweep of docs/"
    )
    script = step["run"]

    assert "-eq 0" in script and "exit 1" in script, (
        "the sweep does not fail on an empty corpus:\n" + script
    )
    assert "wc -l" in script, "the sweep does not count what it swept"


# --------------------------------------------------------------------------
# The rider: one page, one top heading.
# --------------------------------------------------------------------------

def _titles(node, found=None):
    """Every dmc.Title `order` in a rendered component tree."""
    found = [] if found is None else found
    order = getattr(node, "order", None)
    if order is not None and type(node).__name__ == "Title":
        found.append(order)
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            _titles(child, found)
    elif children is not None:
        _titles(children, found)
    return found


def test_markdown_pages_own_the_top_heading():
    """`pages/markdown.py` renders the page title as `Title(order=2)`.

    A docs example that emits its own `Title(order=1)` therefore renders a
    heading ABOVE the page's own title — two competing top headings, which is
    both a visual defect and a document-outline one for anything reading the
    structure.

    Asserted STRUCTURALLY, and scoped: a page that does NOT render through
    markdown.py is entitled to its own order=1, so this only holds the
    example components that do.
    """
    markdown_src = (REPO / "pages" / "markdown.py").read_text()
    assert "order=2" in markdown_src, (
        "pages/markdown.py no longer renders the page title at order=2 — "
        "re-derive what a docs example may emit before trusting this test"
    )

    offenders = []
    checked = 0
    for example in sorted(DOCS.glob("*/example.py")):
        import importlib.util

        slug = example.parent.name
        spec = importlib.util.spec_from_file_location(
            f"_docs_{slug.replace('-', '_')}", example
        )
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception:
            continue  # an example needing a live map/optional dep is not this test's business
        component = getattr(module, "component", None)
        if component is None:
            continue
        checked += 1
        if 1 in _titles(component):
            offenders.append(slug)

    assert checked > 0, (
        "no example components could be loaded — this assertion swept nothing"
    )
    assert not offenders, (
        f"{offenders} emit Title(order=1) under markdown.py's order=2 — "
        "the page renders two competing top headings"
    )


@pytest.mark.parametrize("path", [p for p in DOC_PY if p.name == "example.py"][:1])
def test_the_title_walker_actually_finds_titles(path):
    """CONTROL for the walker: a negative from a function that finds nothing
    is worthless. Build a tree that DOES contain an order=1 and see it."""
    import dash_mantine_components as dmc

    tree = dmc.Stack([dmc.Title("x", order=1), dmc.Text("y")])
    assert 1 in _titles(tree), "the walker cannot see an order=1 it was given"

    clean = dmc.Stack([dmc.Title("x", order=3)])
    assert 1 not in _titles(clean)
