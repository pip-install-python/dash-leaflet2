"""Sidebar navigation for the dash-leaflet2 documentation site.

The boilerplate's flat `page_order` list is swapped for category-grouped
sections so the navbar matches the original dash-leaflet2 NAV map (Start here,
v2 capabilities, Layers, Markers, Controls, Rotation & Sims, Dash integration).
Each docs/*/<slug>.md's `category` frontmatter feeds the grouping.
"""
from __future__ import annotations

from collections import OrderedDict

import dash_mantine_components as dmc
from dash import ALL, Input, Output, callback, ctx, html
from dash_iconify import DashIconify

CATEGORY_ORDER = [
    "Start here",
    "v2 capabilities",
    "Layers",
    "Markers",
    "Controls (compiled dl2.*)",
    "Rotation & Sims",
    "Dash integration",
]

EXCLUDED_LINKS: set[str] = {
    "/404",
    "/not-found",
    # Admin surfaces are not documentation, so they never join the categorised
    # docs sections. `/admin/control-board` gets its own section instead, which
    # is hidden by default and revealed server-side to allowlisted accounts —
    # see `create_admin_section` below.
    "/admin/control-board",
}

# The control board's nav entry. Rendered into both the desktop navbar and the
# mobile drawer, so its id is pattern-matched: two components may not share a
# plain string id, and the reveal callback has to reach both.
ADMIN_NAV_ID = "admin-nav-section"
_HIDDEN = {"display": "none"}


def create_nav_link(icon: str, text: str, href: str, external: bool = False):
    return dmc.Anchor(
        dmc.Group(
            [
                DashIconify(icon=icon or "tabler:file-text", width=18),
                dmc.Text(text, size="sm", fw=500),
            ],
            gap="sm",
        ),
        href=href,
        target="_blank" if external else None,
        className="navbar-link",
        underline=False,
    )


def create_nav_section(title: str, links: list):
    return dmc.Stack(
        [
            dmc.Text(
                title,
                size="xs",
                fw=700,
                tt="uppercase",
                c="dimmed",
                mb="xs",
            ),
            dmc.Stack(links, gap="xs"),
        ],
        gap="sm",
    )


def create_admin_section(loc: str):
    """The owner-only Control Board link, hidden until the server says otherwise.

    Hidden by DEFAULT, and revealed by `_reveal_admin_nav` below rather than by
    anything the browser knows. The distinction matters: `clerk-auth-store`
    lives in the page and a determined visitor can put whatever they like in
    it, so the decision is made server-side against the real session.

    Even so, this link is cosmetic. `/admin/control-board` gates itself twice —
    `pages/control_board.layout()` re-checks on every render, and the mutating
    callback re-checks before it will change anything — and it fails CLOSED
    when Clerk is unavailable. Revealing this link grants nothing; hiding it
    stops the board being advertised to readers it would only reject.
    """
    return html.Div(
        id={"type": ADMIN_NAV_ID, "loc": loc},
        style=_HIDDEN,
        children=dmc.Stack(
            [
                dmc.Divider(mt="md", mb="sm"),
                create_nav_section(
                    "Admin",
                    [
                        create_nav_link(
                            "tabler:adjustments-cog",
                            "Control Board",
                            "/admin/control-board",
                        )
                    ],
                ),
            ],
            gap="xs",
        ),
    )


@callback(
    Output({"type": ADMIN_NAV_ID, "loc": ALL}, "style"),
    Input("url", "pathname"),
    # The app sets `prevent_initial_callbacks=True` globally, so without this
    # the section would stay hidden until the visitor navigated somewhere —
    # including for the owner, on the page they signed in to.
    prevent_initial_call=False,
)
def _reveal_admin_nav(_pathname):
    """Show the Admin section only to accounts the control board would admit.

    Deliberately the SAME predicate the page itself uses (`is_admin_user`, or
    `admin_access_open` when Clerk is off) rather than a bare comparison
    against the owner's address. A nav that used a narrower rule would hide the
    board from an ADMIN_EMAILS account that can still open it by URL — a link
    that lies about access is worse than no link.

    With ADMIN_EMAILS unset, `is_admin_user` reduces to the owner's address
    alone, which is exactly the owner-only behaviour wanted here.

    `url.pathname` is the trigger rather than `clerk-auth-store` because the
    store only exists when Clerk is running; a callback with a missing Input
    never fires, which would silently disable this everywhere Clerk is off.
    Satellite sign-in round-trips through Clerk's hosted pages and returns as a
    full page load, so this re-evaluates at exactly the right moment anyway.
    """
    from lib.auth import admin_access_open, clerk_enabled, is_admin_user

    visible = is_admin_user() if clerk_enabled() else admin_access_open()
    style = {} if visible else _HIDDEN
    return [style] * len(ctx.outputs_list)


def _categorize(data) -> "OrderedDict[str, list]":
    """Bucket page registry entries by their `category` field, preserving the
    intentional CATEGORY_ORDER and folding unknown categories into 'Other'."""
    buckets: OrderedDict[str, list] = OrderedDict((c, []) for c in CATEGORY_ORDER)
    other: list = []
    for entry in data:
        path = entry.get("path")
        if not path or path in EXCLUDED_LINKS:
            continue
        link = create_nav_link(
            entry.get("icon") or "tabler:file-text",
            entry.get("name", path),
            path,
        )
        category = entry.get("category")
        if category in buckets:
            buckets[category].append(link)
        else:
            other.append(link)
    if other:
        buckets["Other"] = other
    return OrderedDict((k, v) for k, v in buckets.items() if v)


def create_content(data, loc: str = "navbar"):
    buckets = _categorize(data)
    sections = []
    for i, (title, links) in enumerate(buckets.items()):
        if i > 0:
            sections.append(dmc.Divider(mt="md", mb="sm"))
        sections.append(create_nav_section(title, links))

    sections.append(dmc.Divider(mt="md", mb="sm"))
    sections.append(
        create_nav_section(
            "Resources",
            [
                create_nav_link(
                    "tabler:brand-github",
                    "GitHub",
                    "https://github.com/pip-install-python/dash-leaflet2",
                    external=True,
                ),
                create_nav_link(
                    "simple-icons:leaflet",
                    "Leaflet 2 (upstream)",
                    "https://leafletjs.com/",
                    external=True,
                ),
                create_nav_link(
                    "ic:baseline-design-services",
                    "DMC",
                    "https://www.dash-mantine-components.com/",
                    external=True,
                ),
                create_nav_link(
                    "fluent-mdl2:forum",
                    "Dash Community",
                    "https://community.plotly.com/",
                    external=True,
                ),
            ],
        )
    )

    sections.append(create_admin_section(loc))

    return dmc.ScrollArea(
        offsetScrollbars=True,
        type="scroll",
        style={"height": "100%"},
        children=dmc.Stack(sections, gap="xs", p="md"),
    )


def create_navbar(data):
    return dmc.AppShellNavbar(
        children=create_content(data, loc="navbar"),
        style={"borderRight": "1px solid var(--mantine-color-gray-3)"},
    )


def create_navbar_drawer(data):
    return dmc.Drawer(
        id="components-navbar-drawer",
        overlayProps={"opacity": 0.55, "blur": 3},
        zIndex=1500,
        offset=8,
        radius="md",
        withCloseButton=True,
        size="280px",
        children=create_content(data, loc="drawer"),
        trapFocus=False,
        position="left",
    )
