"""
Edit Control — native v2 drawing/editing toolbar with full dash-leaflet-style API parity.

Mirrors dash-leaflet's EditControl prop shape (`draw`, `edit`, `drawToolbar`, `editToolbar`,
`action`) so callbacks compose the same way: bump n_clicks to dispatch from Python; read
`action` to react to any change. The contextual sub-toolbar (Finish / Delete last point /
Cancel during draw; Save / Cancel during edit; Clear all during remove) appears alongside
the icon strip while a tool/mode is active. The Edit section appears only when shapes exist.
"""

import json

import dash
import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, ctx
from dl2_tiles import TRANSIT, register_theme_swap
from dl2_locations import TORONTO
from dl2_shared import code_panel, header, info_panel

# Basemap pair for this page — dl2_tiles owns the light/dark wiring.
TILES = TRANSIT

TILE_URL = TILES.url("light")
ATTR = TILES.attribution()

CODE = '''dl2.Map(children=[
    dl2.TileLayer(),
    dl2.EditControl(id="ec",
                    draw={"rectangle": False},        # disable specific tools
                    shapeOptions={"color": "#2f9e44"})
])

# Python -> control: bump n_clicks each time, like dash-leaflet
@callback(Output("ec", "drawToolbar"), Input("draw-poly-btn", "n_clicks"))
def draw_polygon(n):
    return {"mode": "polygon", "n_clicks": n}

@callback(Output("ec", "editToolbar"), Input("clear-btn", "n_clicks"))
def clear_all(n):
    return {"mode": "remove", "action": "clear all", "n_clicks": n}

# Single Input for "anything changed"
@callback(Output("out", "children"), Input("ec", "action"))
def react(a):
    return f"{a}"'''


def _btn(label, _id, color="gray"):
    return dmc.Button(label, id=_id, size="xs", variant="light", color=color)


component = dmc.Stack(
    [
        header(
            "Draw & Edit",
            "Native v2 EditControl with dash-leaflet's prop API. Contextual sub-toolbar "
            "(Finish / Delete last point / Cancel) appears while a tool is active; the Edit "
            "section + its Save/Cancel/Clear-all controls appear only when shapes exist.",
            badge="dl2.EditControl",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dl2.Map(
                            id="ec-map",
                            center=TORONTO.center,
                            zoom=12,
                            style={"height": "62vh"},
                            children=[
                                dl2.TileLayer(
                                    id="ec-tile", **TILES.kwargs("light")
                                ),
                                dl2.EditControl(
                                    id="ec",
                                    position="topleft",
                                    shapeOptions={
                                        "color": "#2f9e44",
                                        "weight": 3,
                                        "fillOpacity": 0.2,
                                    },
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
                                "Counter / last action",
                                dmc.Code(
                                    id="ec-status",
                                    block=True,
                                    style={
                                        "minHeight": "80px",
                                        "whiteSpace": "pre-wrap",
                                    },
                                ),
                            ),
                            info_panel(
                                "action (single Input for 'anything changed')",
                                dmc.Code(id="ec-action", block=True),
                            ),
                            info_panel(
                                "Python → control",
                                dmc.Stack(
                                    [
                                        dmc.Text(
                                            "Start a draw tool from Python:",
                                            size="sm",
                                            c="dimmed",
                                        ),
                                        dmc.Group(
                                            [
                                                _btn(
                                                    "Marker", "ec-draw-marker", "green"
                                                ),
                                                _btn(
                                                    "Polyline",
                                                    "ec-draw-polyline",
                                                    "green",
                                                ),
                                                _btn(
                                                    "Polygon",
                                                    "ec-draw-polygon",
                                                    "green",
                                                ),
                                                _btn(
                                                    "Rectangle",
                                                    "ec-draw-rectangle",
                                                    "green",
                                                ),
                                            ]
                                        ),
                                        dmc.Text(
                                            "Dispatch an action on the active tool:",
                                            size="sm",
                                            c="dimmed",
                                            mt="xs",
                                        ),
                                        dmc.Group(
                                            [
                                                _btn(
                                                    "Finish", "ec-act-finish", "green"
                                                ),
                                                _btn(
                                                    "Delete last point",
                                                    "ec-act-del",
                                                    "yellow",
                                                ),
                                                _btn("Cancel", "ec-act-cancel", "gray"),
                                            ]
                                        ),
                                        dmc.Text(
                                            "Edit / Remove:",
                                            size="sm",
                                            c="dimmed",
                                            mt="xs",
                                        ),
                                        dmc.Group(
                                            [
                                                _btn(
                                                    "Enter edit mode", "ec-edit", "blue"
                                                ),
                                                _btn("Clear all", "ec-clear", "red"),
                                            ]
                                        ),
                                        dmc.Divider(my="xs"),
                                        dmc.Group(
                                            [
                                                dmc.Switch(
                                                    id="ec-disable-rect",
                                                    checked=False,
                                                    size="sm",
                                                    label="Disable rectangle tool (draw= prop)",
                                                ),
                                            ]
                                        ),
                                        # See /edit-control-measurement for the measurementSystem prop, a
                                        # popover-driven color picker, click-to-recolor in edit mode, and
                                        # per-shape area / radius tooltips (showMeasurementTooltips=True).
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
        info_panel(
            "GeoJSON FeatureCollection",
            dmc.Code(
                id="ec-geojson",
                block=True,
                style={
                    "maxHeight": "260px",
                    "overflow": "auto",
                    "fontSize": "11px",
                    "whiteSpace": "pre",
                },
            ),
        ),
        code_panel("dl2.EditControl pattern (dash-leaflet API parity)", CODE),
    ],
    gap="md",
)


# --- Readouts ----------------------------------------------------------------
@callback(
    Output("ec-status", "children"),
    Output("ec-geojson", "children"),
    Output("ec-action", "children"),
    Input("ec", "geojson"),
    Input("ec", "n_drawn"),
    Input("ec", "lastAction"),
    Input("ec", "action"),
)
def show_state(geo, n, last, action):
    if not geo:
        return "Pick a tool (top-left) or use the Python buttons →", "—", "—"
    feats = (geo or {}).get("features", [])
    status = f"n_drawn: {n or 0}\nfeatures: {len(feats)}\nlastAction: {last}"
    return status, json.dumps(geo, indent=2), json.dumps(action or {}, indent=1)


# --- Python -> control: drawToolbar ------------------------------------------
@callback(
    Output("ec", "drawToolbar"),
    Input("ec-draw-marker", "n_clicks"),
    Input("ec-draw-polyline", "n_clicks"),
    Input("ec-draw-polygon", "n_clicks"),
    Input("ec-draw-rectangle", "n_clicks"),
    Input("ec-act-finish", "n_clicks"),
    Input("ec-act-del", "n_clicks"),
    Input("ec-act-cancel", "n_clicks"),
    prevent_initial_call=True,
)
def drive_draw(m, l, p, r, fin, dl, cn):
    t = ctx.triggered_id
    n = sum(x or 0 for x in (m, l, p, r, fin, dl, cn))  # always-increasing tick
    if t == "ec-draw-marker":
        return {"mode": "marker", "n_clicks": n}
    if t == "ec-draw-polyline":
        return {"mode": "polyline", "n_clicks": n}
    if t == "ec-draw-polygon":
        return {"mode": "polygon", "n_clicks": n}
    if t == "ec-draw-rectangle":
        return {"mode": "rectangle", "n_clicks": n}
    if t == "ec-act-finish":
        return {"action": "finish", "n_clicks": n}
    if t == "ec-act-del":
        return {"action": "delete last point", "n_clicks": n}
    if t == "ec-act-cancel":
        return {"action": "cancel", "n_clicks": n}
    return dash.no_update


# --- Python -> control: editToolbar ------------------------------------------
@callback(
    Output("ec", "editToolbar"),
    Input("ec-edit", "n_clicks"),
    Input("ec-clear", "n_clicks"),
    prevent_initial_call=True,
)
def drive_edit(e, c):
    t = ctx.triggered_id
    n = (e or 0) + (c or 0)
    if t == "ec-edit":
        return {"mode": "edit", "n_clicks": n}
    if t == "ec-clear":
        return {"mode": "remove", "action": "clear all", "n_clicks": n}
    return dash.no_update


# --- draw= prop gating: disable rectangle tool when the switch is on ---------
@callback(Output("ec", "draw"), Input("ec-disable-rect", "checked"))
def gate(disabled):
    return {"rectangle": not bool(disabled)}


# Light/dark basemap, driven off the color-scheme store.
register_theme_swap("ec-tile", TILES)
