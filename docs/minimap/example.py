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
from dl2_locations import PITTSBURGH
from dl2_shared import code_panel, header, info_panel

CARTO_LIGHT = "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
CARTO_DARK = "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
ATTR = (
    '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> '
    '&copy; <a href="https://carto.com/attributions">CARTO</a>'
)

CODE = """dl2.Map(children=[
    dl2.TileLayer(url=CARTO_LIGHT),
    dl2.MiniMap(
        id="mini",
        position="bottomright",
        url=CARTO_LIGHT,
        width=160,
        height=160,
        zoomLevelOffset=-5,
        toggleDisplay=True,
    ),
])

# The corner toggle is two-way: clicks round-trip; Python can drive it too.
@callback(Output("mini", "minimized"),
          Input("mini-collapse", "n_clicks"),
          State("mini", "minimized"),
          prevent_initial_call=True)
def collapse(_, current):
    return not bool(current)"""


component = dmc.Stack(
    [
        header(
            "MiniMap",
            "An overview map pinned to a corner of the main map. The minimap tracks the main "
            "view's center and zoom (with a configurable offset) and draws a rectangle showing "
            "the main viewport. Click the corner toggle to collapse / expand — same "
            "`leaflet-control-minimap-toggle-display-<position>` class as the leaflet-minimap "
            "plugin, native to Leaflet 2.",
            badge="dl2.MiniMap",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
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
                                    url=CARTO_LIGHT,
                                    width=160,
                                    height=160,
                                    zoomLevelOffset=-5,
                                    toggleDisplay=True,
                                ),
                            ],
                        ),
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
        code_panel("dl2.MiniMap — placement + two-way toggle", CODE),
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
clientside_callback(
    "(checked) => (checked ? '%s' : '%s')" % (CARTO_LIGHT, CARTO_DARK),
    Output("mini-tile", "url"),
    Input("color-scheme-toggle", "checked"),
)

clientside_callback(
    "(checked) => (checked ? '%s' : '%s')" % (CARTO_LIGHT, CARTO_DARK),
    Output("mini", "url"),
    Input("color-scheme-toggle", "checked"),
)
