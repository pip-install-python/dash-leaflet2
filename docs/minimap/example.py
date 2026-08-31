"""
MiniMap — small overview map pinned to a corner of the main map.

Demonstrates `dl2.MiniMap`, the native Leaflet 2 replacement for the leaflet-minimap
plugin (Leaflet-1-only). The corner toggle uses the standard class
`leaflet-control-minimap-toggle-display leaflet-control-minimap-toggle-display-<position>`
so existing CSS targeting those hooks keeps working. Two-way `minimized` prop —
the user's click round-trips to Python, and a Python callback can collapse/expand the
minimap from a button.
"""

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, clientside_callback
from dash_iconify import DashIconify
from dl2_tiles import ESRI_STREET, POSITRON, register_theme_swap
from dl2_locations import PITTSBURGH
from dl2_shared import info_panel

# TWO different basemaps on purpose. A minimap that renders the same tiles as
# the map above it is just a smaller copy; giving the overview its own, more
# generalised cartography is what makes it useful — you read context from the
# inset and detail from the main map. Both pairs theme independently.
MAIN_TILES = ESRI_STREET      # detailed street cartography
MINI_TILES = POSITRON         # generalised, low-contrast overview

CARTO_LIGHT = MAIN_TILES.url("light")
ATTR = MAIN_TILES.attribution()
MINI_LIGHT = MINI_TILES.url("light")



component = dmc.Stack(
    [
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        # region map
                        dl2.Map(
                            id="mini-map",
                            center=PITTSBURGH.center,
                            zoom=12,
                            style={"height": "62vh"},
                            children=[
                                dl2.TileLayer(
                                    id="mini-tile", url=CARTO_LIGHT, attribution=ATTR
                                ),
                                dl2.Marker(
                                    position=PITTSBURGH.center,
                                    iconify="mdi:lighthouse-on",
                                    iconColor="#e8590c",
                                    iconSize=32,
                                    children=dl2.Tooltip(children="Center marker"),
                                ),
                                dl2.MiniMap(
                                    id="mini",
                                    position="bottomright",
                                    url=MINI_LIGHT,
                                    width=160,
                                    height=160,
                                    zoomLevelOffset=-5,
                                    toggleDisplay=True,
                                ),
                            ],
                        ),
                        # endregion
                        shadow="sm",
                        radius="md",
                        withBorder=True,
                        style={"overflow": "hidden"},
                    ),
                    span=8,
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            info_panel(
                                "State",
                                dmc.Stack(
                                    [
                                        dmc.Group(
                                            [
                                                dmc.Text(
                                                    "minimized:", size="sm", c="dimmed"
                                                ),
                                                dmc.Badge(
                                                    id="mini-state",
                                                    color="gray",
                                                    variant="light",
                                                    children="false",
                                                ),
                                            ],
                                            gap="xs",
                                        ),
                                        dmc.Text(
                                            "Drag the main map — the rectangle on the minimap tracks the "
                                            "main viewport bounds.",
                                            size="sm",
                                            c="dimmed",
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                            info_panel(
                                "Python → control",
                                dmc.Stack(
                                    [
                                        dmc.Text(
                                            "Drive the corner toggle from Python:",
                                            size="sm",
                                            c="dimmed",
                                        ),
                                        dmc.Button(
                                            "Toggle minimap",
                                            id="mini-collapse",
                                            size="xs",
                                            variant="light",
                                            color="green",
                                            leftSection=DashIconify(
                                                icon="mdi:arrow-collapse", width=14
                                            ),
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                            info_panel(
                                "Reposition",
                                dmc.Stack(
                                    [
                                        dmc.Text(
                                            "Move the minimap to any corner:",
                                            size="sm",
                                            c="dimmed",
                                        ),
                                        dmc.SegmentedControl(
                                            id="mini-position",
                                            data=[
                                                {"value": "topleft", "label": "TL"},
                                                {"value": "topright", "label": "TR"},
                                                {"value": "bottomleft", "label": "BL"},
                                                {"value": "bottomright", "label": "BR"},
                                            ],
                                            value="bottomright",
                                            size="xs",
                                            fullWidth=True,
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                        ],
                        gap="md",
                    ),
                    span=4,
                ),
            ]
        ),
    ],
    gap="md",
)


# Two-way: minimap → Python (state readout).
@callback(
    Output("mini-state", "children"),
    Output("mini-state", "color"),
    Input("mini", "minimized"),
)
def show_state(m):
    return ("true" if m else "false"), ("orange" if m else "gray")


# Python → minimap: toggle the corner button.
@callback(
    Output("mini", "minimized"),
    Input("mini-collapse", "n_clicks"),
    State("mini", "minimized"),
    prevent_initial_call=True,
)
def toggle_from_python(_, current):
    return not bool(current)


# Python → minimap: move it to a different corner via the SegmentedControl.
@callback(
    Output("mini", "position"),
    Input("mini-position", "value"),
)
def reposition(p):
    return p or "bottomright"


# Light/dark sync — same pattern every showcase page uses. Mirror the app
# color-scheme toggle to BOTH the main tile layer URL and the minimap's URL so
# the inner map theme stays in sync with the outer one.
register_theme_swap("mini-tile", MAIN_TILES)

register_theme_swap("mini", MINI_TILES)
