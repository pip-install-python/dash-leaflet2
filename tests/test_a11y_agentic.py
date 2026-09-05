"""1.6.44 item 6 — the a11y / agentic block.

Seven sub-items. Four are fixed in code and pinned here; two are RECORDED in
DIVERGENCES rather than fixed, which the item's own wording allows; one — the
`loading`/`decoding` attributes — cannot ship at all and is pinned as a
prohibition so a future sync cannot reintroduce it.

(a) the app menu opened on hover only, so it was unreachable by keyboard;
(b) prose links relied on colour alone (WCAG 1.4.1);
(c) icon controls were 34px against a 44px touch minimum;
(d) RECORDED — the mobile console error, which the template did not reproduce
    and which was originally reported ON THIS HOST;
(e) RECORDED — assets ship unminified, deliberately;
(f) width/height on content images, and NEVER loading/decoding;
(g) /assets/ had no cache lifetime — measured `no-cache` on our own wire.
"""

from __future__ import annotations

import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
MAIN_CSS = (REPO / "assets" / "main.css").read_text()


def live_source(path: pathlib.Path) -> str:
    """The module's CODE, with comments and docstrings removed.

    Item 13's rule applied to item 6's own detects, and it caught these tests
    on the first run: every assertion below hunts for a string that the code
    near it EXPLAINS THE ABSENCE OF, so a raw `in source` check matches the
    comment saying "we must never pass loading=" and reports the defect the
    comment documents the absence of. `ast.unparse` of the parsed tree drops
    comments entirely and docstrings are stripped explicitly.
    """
    import ast

    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


# --------------------------------------------------------------------------
# (a) the menu is operable without a pointer
# --------------------------------------------------------------------------

def test_the_app_menu_does_not_open_on_hover_alone():
    """`trigger="hover"` makes a menu pointer-only.

    Keyboard focus and a touch tap both reach the target and neither opens a
    hover-only menu, so every app in `other_apps_for()` was unreachable to a
    keyboard or screen-reader user. The TARGET was already a real Button —
    the element was never the defect, which is why a review looking at the
    markup would have passed it.
    """
    source = live_source(REPO / "components" / "header.py")

    assert "'hover'" not in source, (
        "the app menu is hover-only again — it cannot be opened by keyboard"
    )
    assert "'click-hover'" in source


def test_the_menu_target_is_a_real_button():
    """Non-vacuity for the above: a hover menu on a non-focusable target is a
    different (worse) defect, and the fix above assumes this one is a Button."""
    import components.header as header

    assert "dmc.Button" in (REPO / "components" / "header.py").read_text()
    assert hasattr(header, "create_header")


# --------------------------------------------------------------------------
# (b) prose links do not rely on colour alone
# --------------------------------------------------------------------------

def test_prose_links_are_underlined():
    assert "#main-content p a" in MAIN_CSS
    block = MAIN_CSS[MAIN_CSS.index("#main-content p a"):]
    assert "text-decoration: underline" in block[:400]


def test_the_underline_rule_is_scoped_to_the_page_body():
    """The spec's warning: an unscoped rule repaints the chrome.

    This site's chrome is made of anchors — the wordmark, the app menu, every
    footer icon, all 27 navbar rows. A bare `a { text-decoration: underline }`
    would underline all of them.
    """
    # Parse rule blocks, and object only to an UNSCOPED selector that sets
    # text-decoration. A bare `a { transition: ... }` has always been here and
    # repaints nothing; the crude "no bare `a` selector" form flagged it and
    # would have sent someone to delete a correct rule.
    offenders = []
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", MAIN_CSS):
        if "text-decoration" not in body:
            continue
        for selector in selectors.split(","):
            selector = selector.strip().split("/*")[-1].strip()
            if not selector or selector.startswith("@"):
                continue
            if selector.endswith("a") and "#main-content" not in selector:
                offenders.append(selector)
    assert not offenders, (
        f"unscoped anchor underline rules would repaint the chrome: {offenders}"
    )

    for selector in ("#main-content p a", "#main-content li a",
                     "#main-content td a", "#main-content blockquote a"):
        assert selector in MAIN_CSS, f"missing {selector}"


def test_icon_and_card_links_are_exempted():
    """An underline under an image is a stray rule, not an affordance."""
    assert "#main-content a:has(> img)" in MAIN_CSS


# --------------------------------------------------------------------------
# (c) touch targets
# --------------------------------------------------------------------------

def test_header_and_footer_icons_meet_44px_at_phone_width():
    """A Mantine ActionIcon size="lg" is 34px. This site's header and footer
    are made of them."""
    assert "min-width: 44px" in MAIN_CSS and "min-height: 44px" in MAIN_CSS

    idx = MAIN_CSS.index("min-width: 44px")
    window = MAIN_CSS[max(0, idx - 700):idx]
    assert "max-width: 750px" in window, (
        "the 44px floor is not inside a phone-width media query — it would "
        "also inflate the desktop chrome"
    )
    assert "mantine-ActionIcon-root" in window


def test_the_icon_controls_really_are_action_icons_at_size_lg():
    """Non-vacuity: if the header stopped using ActionIcon size="lg", the CSS
    above would be aimed at nothing and would still pass."""
    header = (REPO / "components" / "header.py").read_text()
    footer = (REPO / "components" / "footer.py").read_text()

    assert header.count("dmc.ActionIcon") >= 3, header.count("dmc.ActionIcon")
    assert 'size="lg"' in header and 'size="lg"' in footer


# --------------------------------------------------------------------------
# (f) width/height yes, loading/decoding never
# --------------------------------------------------------------------------

def test_dash_still_raises_on_loading_and_decoding():
    """THE PROHIBITION, measured against the pinned Dash rather than quoted.

    Neither attribute is a prop of dash 4.4.1's html.Img, and Dash raises on
    an unknown one — so adding them is a collection error on every page that
    renders an image, not a degraded hint. If this test ever goes red, Dash
    LEARNED the props and item 6f can be completed rather than capped.
    """
    from dash import html

    for prop in ("loading", "decoding"):
        with pytest.raises(TypeError) as exc:
            html.Img(src="x", **{prop: "lazy"})
        assert prop in str(exc.value)


def test_the_image_renderer_ships_neither_attribute():
    source = live_source(REPO / "lib" / "directives" / "headings.py")

    for banned in ("loading=", "decoding="):
        assert banned not in source, (
            f"the image renderer passes {banned} — Dash raises on it, so this "
            "is a collection error on every page with an image"
        )
    # ...while the attributes it SHOULD pass are there. Asserted on the dict
    # the renderer splats, because that is how they are actually passed —
    # `width=` never appears literally, which is how the first version of this
    # assertion managed to fail against correct code.
    assert "'width'" in source and "'height'" in source
    assert "_intrinsic_size" in source


def test_a_local_image_gets_its_intrinsic_size():
    """Read off the file header, stdlib only.

    The template's own finding on this sub-item: its first version used
    Pillow, which this repo installs only in two BUILD-TIME scripts and not in
    requirements.txt — so the feature was inert in production and on every CI
    leg while looking correct in review.
    """
    from lib.directives.headings import _intrinsic_size

    width, height = _intrinsic_size("/assets/favicon/android-chrome-192x192.png")
    assert (width, height) == (192, 192), (width, height)


def test_a_remote_image_gets_no_box():
    """No box beats a wrong box, and a render must never reach the network."""
    from lib.directives.headings import _intrinsic_size

    assert _intrinsic_size("https://img.shields.io/badge/a-b.svg") == (None, None)


def test_pillow_is_not_required_for_any_of_this():
    """Pin the template's finding directly: the size readers must not import
    an optional build-time dependency."""
    source = live_source(REPO / "lib" / "directives" / "headings.py")
    assert "PIL" not in source and "Pillow" not in source


# --------------------------------------------------------------------------
# (g) the asset cache lifetime, on every lane this repo serves
# --------------------------------------------------------------------------

def test_assets_get_a_lifetime_and_documents_do_not():
    from lib.static_cache import cache_control_for

    assert cache_control_for("/assets/main.css")
    assert "max-age=" in cache_control_for("/assets/style.css")

    for document in ("/", "/llms.txt", "/healthz", "/api", "/admin/traffic",
                     "/_dash-component-suites/x.js"):
        assert cache_control_for(document) is None, (
            f"{document} was given a cache lifetime — it is an answer about "
            "right now, and an hour of a stale one is an unreproducible bug"
        )


def test_the_asset_header_reaches_the_wire_on_this_lane(client):
    """Asserted on the SERVED response, not on the policy function.

    The policy returning the right string proves nothing about whether any
    lane applies it — which is precisely how this could ship half-wired.
    """
    response = client.get("/assets/main.css")
    if response.status != 200:
        pytest.skip(f"/assets/main.css is {response.status} under the test client")

    assert "max-age=" in response.header("Cache-Control"), (
        f"served Cache-Control was {response.header('Cache-Control')!r}"
    )


def test_all_three_lanes_read_the_same_policy_module():
    """One module, three callers — so the lanes cannot drift.

    This repo serves three backends where the template serves two, so a port
    that stopped at Flask + ASGI would leave Quart on `no-cache` while the
    others served an hour, and nothing on the wire would reveal it because a
    host runs one lane at a time.
    """
    run_py = (REPO / "run.py").read_text()
    asgi = (REPO / "lib" / "asgi_middleware.py").read_text()

    assert run_py.count("from lib.static_cache import cache_control_for") == 2, (
        "expected the Flask AND Quart hooks to read the policy module"
    )
    assert "cache_control_for" in asgi
    assert "StaticCacheMiddleware" in asgi


# --------------------------------------------------------------------------
# (d) and (e) — recorded, not fixed. Pin the RECORD.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("marker", [
    "loading",           # 6f's prohibition
    "not minified",      # 6e
    "console",           # 6d
])
def test_the_recorded_decisions_are_written_down(marker):
    """A recorded decision that is not in DIVERGENCES is indistinguishable
    from drift, and the next sync will "fix" it."""
    text = (REPO / "DIVERGENCES.md").read_text().lower()
    assert marker in text, f"{marker!r} is not recorded in DIVERGENCES.md"
