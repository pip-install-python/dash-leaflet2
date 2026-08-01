"""Site identity: one brand, every surface, verbatim.

The network standard says a site states what it is in the same words
everywhere an agent or a reader can reach. The failure this pins is silent,
which is why it needs tests rather than a code review: nothing errors when a
surface falls back to a default.

dash-improve-my-llms 2.3.4's `resolve_site_title` is what makes the fix
possible: it takes the home page's registered `name` first, `app.title`
second, and *skips* generic candidates ("Home", "Index", "Dash") rather than
publishing them. This site is one candidate away from that failure — its home
page is registered under the nav label "Home", which is on the generic list —
so the explicit `register_page_metadata(path="/", name=SITE_BRAND)` call in
run.py is load-bearing, not decorative.
"""

from __future__ import annotations

from conftest import BROWSER_ACCEPT, REPO_ROOT, SAMPLE_PAGE
from lib.constants import SITE_BRAND, SITE_DESCRIPTION

# Spelled out rather than imported, so that renaming the constant cannot
# silently rename the site. Changing the brand should require changing this
# line, deliberately.
EXPECTED_BRAND = "dash-leaflet2 — Leaflet 2 maps for Dash"


def test_brand_constant_is_the_agreed_identity():
    assert SITE_BRAND == EXPECTED_BRAND


def test_app_title_is_the_brand(app):
    """`Dash(title=...)` — the <title> and `resolve_site_title`'s fallback."""
    assert app.title == EXPECTED_BRAND


def test_home_prose_opens_with_the_brand():
    """The home markdown's own H1, below the frontmatter."""
    body = (REPO_ROOT / "docs" / "home" / "home.md").read_text()
    headings = [ln for ln in body.splitlines() if ln.startswith("# ")]
    assert headings, "docs/home/home.md has no H1"
    assert headings[0] == f"# {EXPECTED_BRAND}"


def test_llms_index_h1_is_the_brand(client):
    """The single most-read line of this site, and the one nobody looks at."""
    response = client.get("/llms.txt")
    assert response.ok
    assert response.text.splitlines()[0] == f"# {EXPECTED_BRAND}"


def test_llms_index_tagline_is_the_description(client):
    body = client.get("/llms.txt").text
    assert f"> {SITE_DESCRIPTION}" in body


def test_the_viewer_brand_chip_is_not_a_framework_default(client):
    """The chip that reads a bare "Dash" on a pre-2.3.4 artifact.

    It is rendered from the same `resolve_site_title` call as the H1, so
    asserting the brand is present catches both a stale package and a
    regressed constant.
    """
    import html as html_module

    page = client.get(f"{SAMPLE_PAGE}/llms.txt", accept=BROWSER_ACCEPT).text
    assert html_module.escape(EXPECTED_BRAND) in page or EXPECTED_BRAND in page, (
        "the viewer banner does not name this site"
    )


def test_a_control_board_toggle_cannot_rename_the_site():
    """The regression `lib.page_visibility.published_name` exists to stop.

    `apply_llms_state` re-registers a page's metadata every time a verdict
    changes, from the name the markdown loader recorded — "Home" for this
    site's root. Without the substitution, one flip of the home page's
    llms.txt switch would overwrite SITE_BRAND at runtime and the /llms.txt H1
    would quietly become "Home", with nothing logged.
    """
    from lib.page_visibility import published_name

    assert published_name("/", "Home") == EXPECTED_BRAND
    assert published_name(SAMPLE_PAGE, "Pointer Events") == "Pointer Events"


def test_the_home_page_name_really_is_generic():
    """The premise of the test above, pinned.

    If the home page were ever renamed to something specific, the substitution
    would be redundant rather than load-bearing — and this test failing is how
    you would find out, instead of discovering that two mechanisms now fight
    over the same string.
    """
    from dash_improve_my_llms.handlers import _GENERIC_SITE_TITLES

    import frontmatter

    meta, _ = frontmatter.parse((REPO_ROOT / "docs" / "home" / "home.md").read_text())
    assert meta["name"].strip().lower() in _GENERIC_SITE_TITLES


def test_no_surface_falls_back_to_a_generic_title():
    """The values `resolve_site_title` is designed to skip.

    If the brand were ever set to one of these, the package would silently
    fall through to the next candidate and this repo would have no idea which
    string it was publishing.
    """
    from dash_improve_my_llms.handlers import _GENERIC_SITE_TITLES

    assert SITE_BRAND.strip().lower() not in _GENERIC_SITE_TITLES


def test_the_package_name_is_in_the_description_not_the_brand():
    """Naming rules from the standard, both directions.

    The brand says what the site *is*; the byline belongs in the description.
    A brand of "Pip Install Python" would make every satellite in the network
    share one name. (`dash-leaflet2` is this project's actual name, so it
    legitimately appears in both.)
    """
    assert "dash-leaflet2" in SITE_DESCRIPTION
    assert "Pip Install Python" in SITE_DESCRIPTION
    assert "Pip Install Python" not in SITE_BRAND


def test_readme_agrees_with_the_brand():
    """A README that names the site differently is the next drift."""
    readme = (REPO_ROOT / "README.md").read_text()
    assert EXPECTED_BRAND in readme, "README.md does not state the site brand"


def test_llms_package_floor_is_the_network_standard():
    """Identity resolution lives in the package; the floor is what delivers it."""
    import dash_improve_my_llms as pkg

    parts = tuple(int(p) for p in pkg.__version__.split(".")[:3] if p.isdigit())
    assert parts >= (2, 3, 4), (
        f"dash-improve-my-llms {pkg.__version__} predates resolve_site_title; "
        "the viewer chip and the /llms.txt H1 would fall back to app.title"
    )


def test_the_home_markdown_is_no_longer_a_scaffold():
    """`This page demonstrates Home.` was the generated stub's prose."""
    body = (REPO_ROOT / "docs" / "home" / "home.md").read_text()
    assert "This page demonstrates Home." not in body
