"""1.6.44 item 12 — a CD lane that CALLS ci.yml must not also let ci.yml run itself.

When `cd.yml` does `uses: ./.github/workflows/ci.yml` AND `ci.yml` also
triggers on `push: branches: [main]`, one push produces TWO full matrices. Both
resolve to the same commit, both go green, and the only symptom is the runner
bill and a workflow list nobody can read.

THIS REPO DOES NOT HAVE THE DEFECT — measured, not assumed:

    ci.yml triggers: {pull_request, workflow_dispatch, workflow_call}
    cd.yml triggers: {push: {branches: [main]}, workflow_dispatch}
    cd.yml line 55: uses: ./.github/workflows/ci.yml

`ci.yml` has no `push` trigger at all, so the matrix runs exactly once per push
— inside the CD run, as `ci / *` jobs. This file exists to keep it that way,
which is the only useful form of the item on a tree that is already correct.

THE PARSING GOTCHA IS THE POINT OF HALF THIS FILE. YAML 1.1 resolves an
unquoted `on:` key to the BOOLEAN `True`, so `workflow["on"]` raises KeyError
on every workflow file ever written. Measured here:

    top-level keys = ['name', True, 'permissions', 'concurrency', 'env', 'jobs']

A test that catches that KeyError and moves on asserts NOTHING while looking
thorough — so `_triggers()` below raises if it cannot find the key under either
spelling, and a dedicated test pins the gotcha itself.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = REPO / ".github" / "workflows"


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text())


def _triggers(workflow: dict) -> dict:
    """The `on:` block, under whichever key YAML gave it.

    NEVER a silent fallback. If neither spelling is present the workflow is
    not what this test thinks it is, and saying so beats returning `{}` and
    passing every assertion downstream.
    """
    for key in ("on", True):
        if key in workflow:
            value = workflow[key]
            if isinstance(value, dict):
                return value
            if isinstance(value, list):
                return {k: None for k in value}
            return {str(value): None}
    raise AssertionError(
        f"no `on:` block found under either 'on' or True; keys={list(workflow)}"
    )


def test_the_yaml_gotcha_is_real_and_handled():
    """Pin the mechanism, so nobody 'simplifies' `_triggers` back to ['on'].

    If PyYAML ever stops doing this, the helper still works and this test goes
    red with an explanation rather than the helper failing mysteriously later.
    """
    raw = yaml.safe_load((WORKFLOWS / "ci.yml").read_text())

    assert "on" not in raw, (
        "PyYAML no longer folds `on:` to True — `_triggers` can be simplified, "
        "but do it deliberately"
    )
    assert True in raw, f"neither spelling present: {list(raw)}"
    assert isinstance(_triggers(raw), dict)


def test_cd_calls_ci_as_a_reusable_workflow():
    """The precondition. Without this the rest of the file is about nothing."""
    text = (WORKFLOWS / "cd.yml").read_text()
    assert "uses: ./.github/workflows/ci.yml" in text, (
        "cd.yml no longer calls ci.yml — this item does not apply and this "
        "file should be reconsidered rather than left passing"
    )


def test_ci_does_not_also_trigger_itself_on_a_push_to_main():
    """The item. One push, one matrix."""
    triggers = _triggers(_load("ci.yml"))

    assert "push" not in triggers, (
        "ci.yml triggers on push AND is called by cd.yml — every push to main "
        f"runs the matrix twice on the same sha. Triggers: {sorted(triggers)}"
    )


def test_ci_is_still_callable_and_still_runs_on_pull_requests():
    """The other direction: 'no push trigger' must not have been achieved by
    removing the triggers that make CI useful."""
    triggers = _triggers(_load("ci.yml"))

    assert "workflow_call" in triggers, (
        "ci.yml is not callable — cd.yml's `uses:` cannot work"
    )
    assert "pull_request" in triggers, (
        "ci.yml no longer runs on pull requests, so nothing checks a PR"
    )


def test_cd_is_the_one_that_owns_the_push():
    triggers = _triggers(_load("cd.yml"))

    assert "push" in triggers, "nothing runs on a push to main any more"
    branches = (triggers["push"] or {}).get("branches")
    assert branches == ["main"], branches


@pytest.mark.parametrize("name", ["ci.yml", "cd.yml", "release.yml"])
def test_every_workflow_parses_and_declares_triggers(name):
    """Sweep guard: a workflow that stopped parsing would otherwise be
    invisible to every assertion above."""
    workflow = _load(name)
    assert isinstance(workflow, dict), name
    assert _triggers(workflow), f"{name} declares no triggers"
    assert workflow.get("jobs"), f"{name} declares no jobs"
