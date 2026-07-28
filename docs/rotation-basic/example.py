"""
Basic Map Rotation — `bearing` on dl2.Map + dl2.KeyboardControl

The minimum-viable mirror of dash-leaflet's `rotation_basic.py`, adapted to
the dash-leaflet2 primitives we just added:

  * `dl2.Map(bearing=...)`        — CSS-rotated map pane
  * `dl2.KeyboardControl()`       — arrow keys rotate, Cmd/Ctrl+Arrow pans
  * `dl2.Marker(rotateWithMap=False)` — icon stays in a fixed SCREEN
    orientation (upright) while the map rotates around it. The opposite mode,
    `rotateWithMap=True`, is what flight-sim / walking-sim use for sprites
    that should rotate together with the world.

CAVEAT (documented in dl2.Map's docstring too): this is CSS rotation, not
coordinate-correct rotation. Tiles, markers, polygons render in the right
place visually; click-to-latlng resolution at non-zero bearing is OFF by
the rotation amount because Leaflet's hit-testing doesn't know we rotated.
For a basic showcase + flight/walking sims (camera-follow), this is fine.
"""

import dash
import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, clientside_callback, ctx, dcc, html
from dash_iconify import DashIconify
from dl2_shared import code_panel, header, info_panel

CARTO_LIGHT = "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
CARTO_DARK = "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
ATTR = (
    '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> '
    '&copy; <a href="https://carto.com/attributions">CARTO</a>'
)

CODE = """dl2.Map(
    id="rb-map",
    center=[51.505, -0.09],
    zoom=13,
    bearing=0,           # NEW: CSS-rotated map pane
    children=[
        dl2.TileLayer(url=CARTO_LIGHT),
        # KeyboardControl: arrows rotate the map, Cmd/Ctrl+Arrow pans.
        dl2.KeyboardControl(id="rb-kbd", bearingStep=5, panStep=80),
        # rotateWithMap=False keeps the icon at a fixed SCREEN orientation
        # (the home icon stays upright even when the map underneath spins).
        dl2.Marker(position=[51.505, -0.09], iconify="mdi:home",
                   rotateWithMap=False),
    ],
)

# Slider -> map.bearing (live)
@callback(Output("rb-map", "bearing"), Input("rb-slider", "value"))
def set_bearing(deg): return deg

# Map -> Python: viewport.bearing changes when KeyboardControl rotates
@callback(Output("rb-slider", "value"),
          Input("rb-map", "viewport"),
          prevent_initial_call=True)
def echo_bearing(vp): return (vp or {}).get("bearing", 0)"""


component = dmc.Stack(
    [
        header(
            "Basic Rotation",
            "Drag the slider, press the preset compass buttons, or use the arrow "
            "keys to rotate the map (hold Cmd / Ctrl + arrow to pan instead). "
            "The center pin has rotateWithMap=False so it stays UPRIGHT on screen "
            "while the map underneath rotates around it.",
            badge="dl2.Map(bearing=) + KeyboardControl",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dl2.Map(
                            id="rb-map",
                            center=[51.505, -0.09],
                            zoom=13,
                            bearing=0,
                            style={"height": "62vh"},
                            children=[
                                dl2.TileLayer(
                                    id="rb-tile", url=CARTO_LIGHT, attribution=ATTR
                                ),
                                dl2.KeyboardControl(
                                    id="rb-kbd", bearingStep=5, panStep=80
                                ),
                                dl2.Marker(
                                    position=[51.505, -0.09],
                                    iconify="mdi:home",
                                    iconSize=36,
                                    iconColor="var(--mantine-color-green-6)",
                                    # iconAnchor at center (default for iconify is
                                    # bottom-center; we override here so the icon's
                                    # visual center IS the geographic point — the icon
                                    # then rotates in place around its own center).
                                    iconAnchor=[18, 18],
                                    rotateWithMap=False,
                                    children=dl2.Tooltip(
                                        "London — center pin (rotateWithMap=False, stays upright)",
                                    ),
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
                                "Bearing",
                                dmc.Stack(
                                    [
                                        dmc.Group(
                                            [
                                                dmc.Badge(
                                                    id="rb-bearing-badge",
                                                    color="green",
                                                    variant="light",
                                                    size="lg",
                                                    children="0°",
                                                ),
                                                DashIconify(
                                                    id="rb-compass-icon",
                                                    icon="mdi:compass-outline",
                                                    width=28,
                                                    color="var(--mantine-color-green-6)",
                                                ),
                                            ],
                                            gap="sm",
                                        ),
                                        dmc.Slider(
                                            id="rb-slider",
                                            min=0,
                                            max=359,
                                            step=1,
                                            value=0,
                                            marks=[
                                                {"value": 0, "label": "N"},
                                                {"value": 90, "label": "E"},
                                                {"value": 180, "label": "S"},
                                                {"value": 270, "label": "W"},
                                            ],
                                        ),
                                        dmc.Group(
                                            [
                                                dmc.Button(
                                                    "N",
                                                    id="rb-btn-N",
                                                    size="xs",
                                                    variant="light",
                                                ),
                                                dmc.Button(
                                                    "E",
                                                    id="rb-btn-E",
                                                    size="xs",
                                                    variant="light",
                                                ),
                                                dmc.Button(
                                                    "S",
                                                    id="rb-btn-S",
                                                    size="xs",
                                                    variant="light",
                                                ),
                                                dmc.Button(
                                                    "W",
                                                    id="rb-btn-W",
                                                    size="xs",
                                                    variant="light",
                                                ),
                                                dmc.Button(
                                                    "Reset",
                                                    id="rb-btn-reset",
                                                    size="xs",
                                                    variant="light",
                                                    color="gray",
                                                ),
                                            ],
                                            gap="xs",
                                            grow=True,
                                        ),
                                    ],
                                    gap="sm",
                                ),
                            ),
                            info_panel(
                                "KeyboardControl readout",
                                dmc.Stack(
                                    [
                                        dmc.Group(
                                            [
                                                dmc.Text(
                                                    "Rotations:", size="sm", c="dimmed"
                                                ),
                                                dmc.Badge(
                                                    id="rb-n-rot",
                                                    color="gray",
                                                    variant="light",
                                                    children="0",
                                                ),
                                                dmc.Text(
                                                    "Pans:", size="sm", c="dimmed"
                                                ),
                                                dmc.Badge(
                                                    id="rb-n-pan",
                                                    color="gray",
                                                    variant="light",
                                                    children="0",
                                                ),
                                            ],
                                            gap="xs",
                                        ),
                                        dmc.Code(
                                            id="rb-lastkey",
                                            block=True,
                                            style={
                                                "minHeight": "60px",
                                                "fontSize": "11px",
                                            },
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                            info_panel(
                                "Viewport (map → Python)",
                                dmc.Code(
                                    id="rb-viewport",
                                    block=True,
                                    style={"fontSize": "11px", "minHeight": "80px"},
                                ),
                            ),
                        ],
                        gap="md",
                    ),
                    span=4,
                ),
            ]
        ),
        code_panel("Pattern", CODE),
    ],
    gap="md",
)


# Slider -> map bearing
@callback(Output("rb-map", "bearing"), Input("rb-slider", "value"))
def slider_to_bearing(deg):
    return deg


# Preset buttons -> slider (which then drives bearing).
@callback(
    Output("rb-slider", "value"),
    Input("rb-btn-N", "n_clicks"),
    Input("rb-btn-E", "n_clicks"),
    Input("rb-btn-S", "n_clicks"),
    Input("rb-btn-W", "n_clicks"),
    Input("rb-btn-reset", "n_clicks"),
    prevent_initial_call=True,
)
def preset_to_slider(*_):
    presets = {
        "rb-btn-N": 0,
        "rb-btn-E": 90,
        "rb-btn-S": 180,
        "rb-btn-W": 270,
        "rb-btn-reset": 0,
    }
    return presets.get(ctx.triggered_id, dash.no_update)


# Map bearing (driven by KeyboardControl) -> slider (so the slider tracks
# arrow-key rotation in real time).
@callback(
    Output("rb-slider", "value", allow_duplicate=True),
    Input("rb-map", "viewport"),
    prevent_initial_call=True,
)
def viewport_to_slider(vp):
    return round((vp or {}).get("bearing") or 0)


# Bearing badge + compass-icon visual rotation.
@callback(
    Output("rb-bearing-badge", "children"),
    Output("rb-compass-icon", "style"),
    Input("rb-slider", "value"),
)
def readouts(deg):
    deg = deg or 0
    return f"{deg}°", {
        "transform": f"rotate({deg}deg)",
        "transition": "transform 0.15s",
    }


# Viewport JSON readout.
@callback(Output("rb-viewport", "children"), Input("rb-map", "viewport"))
def viewport_text(vp):
    if not vp:
        return "—"
    return (
        "center: [{lat}, {lng}]\nzoom: {z}\nbearing: {b}°\nbounds: "
        "N {n}  S {s}  E {e}  W {w}"
    ).format(
        lat=vp["center"][0],
        lng=vp["center"][1],
        z=vp["zoom"],
        b=round(vp.get("bearing") or 0),
        n=vp["bounds"]["north"],
        s=vp["bounds"]["south"],
        e=vp["bounds"]["east"],
        w=vp["bounds"]["west"],
    )


# KeyboardControl readout.
@callback(
    Output("rb-n-rot", "children"),
    Output("rb-n-pan", "children"),
    Output("rb-lastkey", "children"),
    Input("rb-kbd", "n_rotations"),
    Input("rb-kbd", "n_pans"),
    Input("rb-kbd", "lastKey"),
)
def kbd_readout(n_rot, n_pan, last_key):
    import json as _json

    return (
        str(n_rot or 0),
        str(n_pan or 0),
        _json.dumps(last_key, indent=1) if last_key else "—",
    )


# Theme sync — mirrors the other showcase pages.
clientside_callback(
    "(checked) => (checked ? '%s' : '%s')" % (CARTO_LIGHT, CARTO_DARK),
    Output("rb-tile", "url"),
    Input("color-scheme-toggle", "checked"),
)
