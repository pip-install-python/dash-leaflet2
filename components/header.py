"""Header for the dash-leaflet2 documentation site.

Branding: satellite emoji + green "dash-leaflet2" title. Preserves the
`color-scheme-toggle` ActionIcon id from the boilerplate so the appshell's
clientside callbacks (theme storage + Mantine forceColorScheme) keep working,
AND the showcase pages' tile-URL light/dark callbacks (which target the same
id with a Switch on the original app.py) — see `assets/leaflet2_maps.js`.
"""
import dash_mantine_components as dmc
from dash import Input, Output, clientside_callback
from dash_iconify import DashIconify

from components.backend_badge import create_backend_badge
from lib.backend import get_backend_info
from lib.constants import LEAFLET_VERSION


def create_link(icon, href):
    return dmc.Anchor(
        dmc.ActionIcon(
            DashIconify(icon=icon, width=22),
            variant="subtle",
            size="lg",
            color="gray",
        ),
        href=href,
        target="_blank",
    )


def create_search(data):
    return dmc.Select(
        id="select-component",
        placeholder="Search pages...",
        searchable=True,
        clearable=True,
        w=240,
        size="sm",
        nothingFoundMessage="No pages found",
        leftSection=DashIconify(icon="tabler:search", width=18),
        data=[
            {"label": entry["name"], "value": entry["path"]}
            for entry in data
            if entry.get("name") not in (None, "Home", "Not found 404")
            and entry.get("path") not in ("/404", "/not-found")
        ],
        visibleFrom="sm",
        comboboxProps={"zIndex": 2000},
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
                        ),
                        dmc.Burger(
                            id="desktop-navbar-toggle",
                            opened=True,
                            size="sm",
                            visibleFrom="md",
                            color="var(--mantine-color-green-6)",
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
                                            dmc.Text(
                                                "dash-leaflet2",
                                                size="lg",
                                                fw=700,
                                                c="green",
                                                id="dash-docs-title",
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
                        ),
                    ],
                    gap="md",
                ),
                dmc.Group(
                    [
                        dmc.Box(create_backend_badge(), visibleFrom="sm"),
                        dmc.Box(_openapi_link(), visibleFrom="md"),
                        create_search(data),
                        create_link(
                            "radix-icons:github-logo",
                            "https://github.com/pip-install-python/dash-leaflet2",
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
                        ),
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

# Mobile drawer open
clientside_callback(
    """function(n_clicks) { return true }""",
    Output("components-navbar-drawer", "opened"),
    Input("drawer-hamburger-button", "n_clicks"),
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
