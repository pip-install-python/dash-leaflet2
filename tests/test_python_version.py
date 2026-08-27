"""One fleet Python — image, CI site lane and render.yaml must agree.

Found by the ops seat reading the tree, not a report (2026-08-25): the
template's Dockerfile said `python:3.11.8-slim` — a PATCH pin, so the image
never received a 3.11.x security release — while its CI matrix said 3.12 and
render.yaml said 3.12.0. Three declared Pythons, the docker boot/battery
testing an interpreter the matrix never ran, and nothing on the wire able to
contradict any of them. These pins hold every encoding to ONE minor, sourced
from the Dockerfile's FROM tag; /healthz's `python` field plus the
`python_matches_declared` battery check (scripts/network_smoke.py) hold the
serving host to the same one.

What is deliberately NOT here: no comparison of the RUNNING interpreter to
the fleet minor — the suite legitimately runs on the window legs, where that
assertion would be false by design. Image-vs-declaration is the battery's
job, against a host.

TWO PYTHONS LIVE IN THIS ci.yml, and this file pins exactly one of them
(spec 1.6.28's site-vs-package split). THE SITE LANE — `pytest`,
`docs-compat`, `lint`, the wheel job's release check, `pip-audit`, and
cd.yml's verify job — installs requirements.txt and boots the docs app, and
is held to the image's minor. THE PACKAGE LANE — `Package · Python`, whose
matrix is ["3.9" … "3.13"] — tests the dash_leaflet2 wheel's own
`requires-python: >=3.9` claim against a bare `pip install dash`. That
window is the package's business: pinning it to a container base would
break the wheel's contract the moment the image moved. The greps below are
scoped so the two can never be conflated — see
`test_the_package_lane_is_out_of_scope_and_stays_wide`, which fails if the
package matrix ever collapses onto the fleet minor.
"""
from __future__ import annotations

import re

from conftest import REPO_ROOT


def _fleet_minor() -> str:
    """The single source: the Dockerfile's FROM tag."""
    for line in (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines():
        m = re.match(r"FROM\s+python:(\S+)", line)
        if m:
            return m.group(1)
    raise AssertionError("Dockerfile has no `FROM python:` line")


def _uncommented(path) -> list[str]:
    return [
        ln for ln in (REPO_ROOT / path).read_text(encoding="utf-8").splitlines()
        if not ln.lstrip().startswith("#")
    ]


def _render_runtime() -> str:
    for ln in _uncommented("render.yaml"):
        m = re.match(r"\s*runtime:\s*(\S+)", ln)
        if m:
            return m.group(1)
    raise AssertionError("render.yaml declares no `runtime:`")


def test_dockerfile_tag_is_minor_only():
    """The patch pin IS the security bug: `3.11.8-slim` never receives a
    3.11.x fix release. The minor tag tracks them through Docker Hub."""
    tag = _fleet_minor()
    assert re.fullmatch(r"\d+\.\d+-slim", tag), (
        f"Dockerfile FROM tag is {tag!r} — must be a MINOR tag "
        "(python:X.Y-slim), never a patch pin"
    )


def test_render_yaml_agrees_with_the_image():
    """BRANCHES on the service runtime (spec 1.6.28, filed independently by
    three forks in the batch-2/3 round).

    THIS repo is the `docker` branch: render.yaml line 19 is
    `runtime: docker`, so NOTHING reads PYTHON_VERSION — the image is the
    interpreter. The key must be ABSENT. A value there would read like the
    platform's setting and could never be true: the item's own defect class
    (a declaration nothing holds to reality) arriving through the fix.

    The `python` branch is kept live below rather than deleted as dead code.
    If this service is ever migrated to Render's native runtime, the test
    flips branches by itself instead of silently passing on a stale
    assumption — and a fork reading this file gets the reference
    implementation for both, per the spec.
    """
    minor = _fleet_minor().removesuffix("-slim")
    runtime = _render_runtime()
    lines = _uncommented("render.yaml")
    value = None
    for i, ln in enumerate(lines):
        if re.match(r"\s*- key: PYTHON_VERSION$", ln):
            m = re.search(r'value:\s*"([^"]+)"', lines[i + 1])
            value = m and m.group(1)
            break
    if runtime == "docker":
        assert value is None, (
            f"render.yaml declares PYTHON_VERSION {value!r} on a docker "
            "runtime — nothing reads it there; a string that looks like "
            "the platform's setting and can never be true is the drift "
            "class this file exists to kill. Delete the key."
        )
        return
    assert runtime == "python", (
        f"render.yaml runtime is {runtime!r} — this test knows `python` "
        "and `docker`; extend the branch deliberately"
    )
    assert value, "render.yaml declares no PYTHON_VERSION"
    assert re.fullmatch(r"\d+\.\d+\.\d+", value), (
        f"PYTHON_VERSION {value!r} — Render requires full X.Y.Z"
    )
    assert value.startswith(minor + "."), (
        f"render.yaml PYTHON_VERSION {value} vs image python:{minor}-slim — "
        "the native-runtime lane and the image lane disagree"
    )


def test_ci_site_lane_matrix_mains_agree_with_the_image():
    """The SITE lane's two matrices — `pytest` and `docs-compat` — both
    declare a single-element main axis, and both must be the fleet minor.

    The package matrix is excluded BY SHAPE, not by a job-name list: it
    declares five elements, so the single-element pattern cannot match it.
    That is deliberate — a name list would rot the moment a job is renamed,
    while the shape distinction is the real one (a site lane pins ONE
    Python; a package lane declares a support window)."""
    minor = _fleet_minor().removesuffix("-slim")
    ci = _uncommented(".github/workflows/ci.yml")

    mains = [m.group(1) for ln in ci
             if (m := re.match(r'\s*python:\s*\["([\d.]+)"\]\s*$', ln))]
    assert mains, "no single-element python matrix found in ci.yml"
    assert set(mains) == {minor}, (
        f"ci.yml site-lane matrix mains {mains} vs image python:{minor}-slim"
    )


def test_ci_and_cd_singleton_jobs_agree_with_the_image():
    """`lint`, the wheel job's release check and `pip-audit` in ci.yml, and
    cd.yml's verify job, pin a literal python-version. Every one is site
    lane. The matrix jobs' `${{ matrix.python }}` is deliberately not a
    literal and is covered by the matrix test above."""
    minor = _fleet_minor().removesuffix("-slim")
    for workflow in (".github/workflows/ci.yml", ".github/workflows/cd.yml"):
        literals = [m.group(1) for ln in _uncommented(workflow)
                    if (m := re.match(r'\s*python-version:\s*"([\d.]+)"', ln))]
        assert literals, f"{workflow} pins no literal python-version"
        assert set(literals) == {minor}, (
            f"{workflow} singleton jobs pin {literals}, image is "
            f"python:{minor}-slim"
        )


def test_site_matrix_legs_are_the_floor_and_the_adjacent_minor():
    """DIVERGENCE from the template's three-wide window, deliberately.

    The template's legs are X.Y-1 and X.Y-2 — a rolling window around the
    fleet Python. This site's legs are its FLOOR and the rung directly
    below the fleet Python, because this fork HAS a hard floor the template
    does not: `python-frontmatter` 1.3 imports `typing.TypeGuard` (3.10+),
    and the vendored `dash-clerk-auth` 1.0.5 declares `requires-python
    >=3.10`. requirements.txt is what the floor leg proves still resolves,
    and a rolling window would stop testing it the moment the fleet Python
    moved twice — which is exactly when a floor quietly breaks.

    So the assertion is not "within three of the fleet minor" but the two
    things this fork actually means: one leg IS the declared floor, and one
    leg is directly below the fleet Python. Both are still checked, so the
    window can neither collapse to one nor drift silently."""
    major, y = (int(p) for p in _fleet_minor().removesuffix("-slim").split("."))
    ci = _uncommented(".github/workflows/ci.yml")
    legs = [m.group(1) for ln in ci
            if (m := re.match(r'\s*- python:\s*"([\d.]+)"', ln))]
    assert legs, "the site matrix has no include legs — the window collapsed"

    floor = _declared_floor()
    assert floor in legs, (
        f"site matrix legs {legs} do not include the declared floor {floor} "
        "— requirements.txt's floor stopped being exercised"
    )
    adjacent = f"{major}.{y - 1}"
    assert adjacent in legs, (
        f"site matrix legs {legs} lack {adjacent}, the rung directly below "
        f"the fleet Python {major}.{y}"
    )


def _declared_floor() -> str:
    """This site's Python floor, from the one place that states it.

    Sourced, never repeated: the floor is a real dependency fact
    (`python-frontmatter` 1.3's `typing.TypeGuard`, dash-clerk-auth 1.0.5's
    `requires-python >=3.10`), and a literal here would be exactly the extra
    encoding this file exists to prevent."""
    from lib.constants import DOCS_PYTHON_FLOOR

    return DOCS_PYTHON_FLOOR


def test_the_package_lane_is_out_of_scope_and_stays_wide():
    """The guard on the guard (spec 1.6.28's site-vs-package split).

    If someone ever "fixes" the package matrix to match the fleet Python,
    every pin above would still pass while the wheel's `requires-python
    >=3.9` claim silently stopped being tested. This fails instead."""
    ci = _uncommented(".github/workflows/ci.yml")
    wide = [ln for ln in ci
            if re.match(r'\s*python:\s*\["3\.9",', ln)]
    assert wide, (
        "the Package matrix no longer starts at 3.9 — the wheel declares "
        "requires-python >=3.9 in pyproject.toml, and that claim is only "
        "true if CI tests it. This is the PACKAGE lane; it is deliberately "
        "wider than the site lane and must not be pinned to the image."
    )
