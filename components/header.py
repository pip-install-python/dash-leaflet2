"""Header for the dash-leaflet2 documentation site.

Branding: satellite emoji + green "dash-leaflet2" title. Preserves the
`color-scheme-toggle` ActionIcon id from the boilerplate so the appshell's
clientside callbacks (theme storage + Mantine forceColorScheme) keep working,
AND the showcase pages' tile-URL light/dark callbacks (which target the same
id with a Switch on the original app.py) — see `assets/leaflet2_maps.js`.

The Clerk avatar lives here too. `lib/auth.py` registers Clerk with
`headless=True`, which means the package injects NO UI of its own — so without
`create_clerk_menu()` below there is simply no way to sign in, even though Clerk
itself initialises correctly.
"""
import dash_mantine_components as dmc
from dash import Input, Output, State, clientside_callback
from dash_iconify import DashIconify

from components.backend_badge import create_backend_badge
from components.navbar import search_data
from lib.auth import clerk_enabled
from lib.backend import get_backend_info
from lib.constants import API_PACKAGES, BASE_URL, GITHUB_URL, LEAFLET_VERSION


def create_clerk_avatar():
    """Clerk avatar / sign-in control, sat beside the colour-scheme toggle.

    Returns None when Clerk is not configured, so local development and any
    deploy without the keys renders the header exactly as before rather than
    erroring on a missing component.

    The package renders `#clerk-login-button` inside this widget. Since
    dash-clerk-auth 0.9.2 the package's own handler is already satellite-safe
    (it navigates to the primary rather than opening `openSignIn()`, a modal
    that POSTs to the satellite FAPI and 403s), so this button needs nothing
    from us. `lib.auth._install_satellite_signin_delegation` still intercepts
    the id in the capture phase — not for this button, but for the sign-in card
    in `lib.page_visibility`, which Dash renders after the package has already
    bound its listeners.
    """
    if not clerk_enabled():
        return None
    from dash_clerk_auth import create_clerk_menu

    return create_clerk_menu(show_dropdown=True, dropdown_align="right")


def create_link(icon, href, label):
    """External icon link. ``label`` is REQUIRED: an icon-only link has no
    accessible name — screen readers announce "link" and AI agents can't
    tell what it does (the Lighthouse/Agentic-Browsing failure measured on
    this host, 2026-08-21)."""
    return dmc.Anchor(
        dmc.ActionIcon(
            DashIconify(icon=icon, width=22),
            variant="subtle",
            size="lg",
            color="gray",
            **{"aria-label": label},
        ),
        href=href,
        target="_blank",
        **{"aria-label": label},
    )


def create_other_apps_menu():
    """*Other Apps* — the network, from ONE registry (template 1.6.38).

    A hover menu in the top bar (the 2plot.dev shape the owner named as the
    reference), populated from lib.network_directory: the PRIMARY
    applications only, this app omitted, labelled by domain. The sidebar
    carries no network section any more — this is the only place the network
    is listed, so it cannot be listed twice.
    """
    from lib.network_directory import other_apps_for

    return dmc.Menu(
        [
            dmc.MenuTarget(
                dmc.Button(
                    "Other Apps",
                    variant="subtle",
                    color="gray",
                    size="sm",
                    leftSection=DashIconify(icon="svg-spinners:blocks-scale", width=18),
                    visibleFrom="md",
                    id="other-apps-menu-target",
                )
            ),
            dmc.MenuDropdown(
                [
                    dmc.MenuItem(
                        entry["label"],
                        leftSection=DashIconify(icon=entry["icon"], width=16),
                        href=entry["url"],
                        target="_blank",
                    )
                    for entry in other_apps_for(BASE_URL)
                ],
                id="other-apps-menu",
                # Solid, themed panel (1.6.39): the seat found the dropdown
                # near-transparent with washed-out items in dark mode.
                styles={"dropdown": {
                    "backgroundColor": "var(--mantine-color-body)",
                    "border": "1px solid var(--mantine-color-default-border)",
                    "boxShadow": "var(--mantine-shadow-md)",
                }},
            ),
        ],
        trigger="hover",
        openDelay=100,
        closeDelay=200,
    )


def _package_version():
    """The documented component package's version, or None."""
    if not API_PACKAGES:
        return None
    try:
        from importlib.metadata import version

        return version(API_PACKAGES[0].replace("_", "-"))
    except Exception:
        try:
            import importlib

            return getattr(importlib.import_module(API_PACKAGES[0]), "__version__", None)
        except Exception:
            return None


def create_version_badge():
    """`v<version>` of the documented package, when the fork declares one.

    Distinct from the wordmark's `Leaflet <LEAFLET_VERSION>` line below: that
    names the UPSTREAM library this wraps, this names the wheel a reader
    would `pip install`. Both are true and they are not the same number.
    """
    v = _package_version()
    if not v:
        return None
    return dmc.Badge(
        f"v{v}",
        variant="light",
        color="gray",
        radius="sm",
        styles={"root": {"textTransform": "none", "fontWeight": 600}},
        **{"aria-label": f"{API_PACKAGES[0]} version {v}"},
    )


def create_search(data):
    """Searchable dropdown for page navigation — the sidebar's pages and
    nothing else (never /admin/*, never hidden-tier; components/navbar
    decides)."""
    return dmc.Select(
        id="select-component",
        placeholder="Search pages...",
        searchable=True,
        clearable=True,
        w=240,
        size="sm",
        nothingFoundMessage="No pages found",
        leftSection=DashIconify(icon="tabler:search", width=18),
        data=search_data(data),
        visibleFrom="sm",
        comboboxProps={"zIndex": 2000},
        **{"aria-label": "Search pages"},
        styles={"input": {"borderColor": "var(--mantine-color-gray-4)"}},
    )


def _openapi_link():
    """Swagger UI link, FastAPI backend only."""
    info = get_backend_info()
    if info.name != "fastapi":
        return None
    return dmc.Tooltip(
        label="OpenAPI docs (Swagger UI) — FastAPI backend",
        position="bottom",
        withArrow=True,
        children=dmc.Anchor(
            dmc.Badge(
                "OpenAPI",
                leftSection=DashIconify(icon="logos:swagger", width=14),
                variant="light",
                color="cyan",
                radius="sm",
                styles={"root": {"textTransform": "none", "fontWeight": 600}},
            ),
            href="/docs",
            target="_blank",
            underline=False,
        ),
    )


def create_header(data):
    return dmc.AppShellHeader(
        dmc.Group(
            [
                dmc.Group(
                    [
                        dmc.ActionIcon(
                            DashIconify(icon="radix-icons:hamburger-menu", width=22),
                            id="drawer-hamburger-button",
                            variant="subtle",
                            size="lg",
                            color="gray",
                            hiddenFrom="md",
                            **{"aria-label": "Open navigation menu"},
                        ),
                        dmc.Burger(
                            id="desktop-navbar-toggle",
                            opened=True,
                            size="sm",
                            visibleFrom="md",
                            color="var(--mantine-color-green-6)",
                            # The a11y audit named this exact id: a Burger is a
                            # button with no text, so without a label screen
                            # readers announce "button" and nothing else.
                            **{"aria-label": "Toggle the documentation sidebar"},
                        ),
                        dmc.Anchor(
                            dmc.Group(
                                [
                                    DashIconify(
                                        icon="emojione:satellite",
                                        width=28,
                                    ),
                                    dmc.Stack(
                                        [
                                            # The wordmark is 13 characters at
                                            # size lg/700, which is wide enough
                                            # on a phone to push the right-hand
                                            # group (GitHub, theme, the 44px
                                            # avatar) into a second row. Below
                                            # xs it gives way to the map glyph.
                                            #
                                            # visibleFrom is CSS, not a
                                            # conditional render, and it has to
                                            # stay that way: this id is read by
                                            # assets/text_animation.js and is
                                            # the dummy Output of the
                                            # colour-scheme bridge callback
                                            # below. Dropping the node would
                                            # break the CARTO tile swap on
                                            # phones and leave that callback
                                            # pointing at nothing.
                                            dmc.Text(
                                                "dash-leaflet2",
                                                size="lg",
                                                fw=700,
                                                c="green",
                                                id="dash-docs-title",
                                                visibleFrom="xs",
                                            ),
                                            dmc.Text(
                                                "🗺️",
                                                size="lg",
                                                hiddenFrom="xs",
                                                # Decorative: the Anchor's
                                                # aria-label carries the name,
                                                # so this is not announced as
                                                # "world map".
                                                **{"aria-hidden": "true"},
                                            ),
                                            dmc.Text(
                                                f"Leaflet {LEAFLET_VERSION}",
                                                size="xs",
                                                c="dimmed",
                                                visibleFrom="md",
                                                style={"marginTop": -4},
                                            ),
                                        ],
                                        gap=0,
                                    ),
                                ],
                                gap="sm",
                                wrap="nowrap",
                            ),
                            href="/",
                            underline=False,
                            # Without this the link's accessible name changes
                            # with the viewport: `display: none` text is not
                            # exposed, so below xs the name would collapse to
                            # the emoji alone.
                            **{"aria-label": "dash-leaflet2 — home"},
                        ),
                    ],
                    gap="md",
                ),
                dmc.Group(
                    [
                        dmc.Box(create_backend_badge(), visibleFrom="sm"),
                        dmc.Box(_openapi_link(), visibleFrom="md"),
                        dmc.Box(create_version_badge(), visibleFrom="sm"),
                        create_search(data),
                        create_other_apps_menu(),
                        create_link(
                            "radix-icons:github-logo",
                            GITHUB_URL,
                            "View the source on GitHub",
                        ),
                        dmc.ActionIcon(
                            [
                                DashIconify(
                                    icon="radix-icons:sun",
                                    width=22,
                                    id="light-theme-icon",
                                ),
                                DashIconify(
                                    icon="radix-icons:moon",
                                    width=22,
                                    id="dark-theme-icon",
                                ),
                            ],
                            variant="subtle",
                            color="yellow",
                            id="color-scheme-toggle",
                            size="lg",
                            **{"aria-label": "Toggle light / dark color scheme"},
                        ),
                        # Sign in / avatar. None when Clerk is unconfigured —
                        # DMC skips None children, so the header is unchanged.
                        create_clerk_avatar(),
                    ],
                    gap="sm",
                ),
            ],
            justify="space-between",
            h=70,
            px="xl",
        ),
    )


# Search select → URL navigation
clientside_callback(
    """
    function(value) {
        if (value) { return value }
    }
    """,
    Output("url", "href"),
    Input("select-component", "value"),
)

# Mobile drawer search → navigate (the header Select is hidden on phones;
# the drawer's sticky search is the phone's jump-to-page entry point).
clientside_callback(
    """
    function(value) {
        if (value) {
            return value
        }
        return window.dash_clientside.no_update
    }
    """,
    Output("url", "href", allow_duplicate=True),
    Input("mobile-select-component", "value"),
    prevent_initial_call=True,
)

# The full-height drawer's overlay no longer covers the header, so the
# hamburger stays reachable while it is open — a second tap must close it.
clientside_callback(
    """function(n_clicks, opened) { return !opened }""",
    Output("components-navbar-drawer", "opened"),
    Input("drawer-hamburger-button", "n_clicks"),
    State("components-navbar-drawer", "opened"),
    prevent_initial_call=True,
)

# Bridge: the showcase JS (assets/leaflet2_maps.js) watches
# <html data-mantine-color-scheme> to swap CARTO light_all/dark_all tiles.
# The boilerplate's appshell sets MantineProvider.forceColorScheme but
# does NOT mirror the value onto <html data-mantine-color-scheme>, which is
# what Mantine itself uses to derive CSS variables — and what our JS reads.
# Mirror it here.
clientside_callback(
    """
    function(scheme) {
        const v = scheme || 'light';
        document.documentElement.setAttribute('data-mantine-color-scheme', v);
        return window.dash_clientside.no_update;
    }
    """,
    Output("dash-docs-title", "id"),
    Input("color-scheme-storage", "data"),
)
