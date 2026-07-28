"""
TextMarker — editable, draggable, styleable map captions (limited working example).

The map hosts one selected `dl2.TextMarker` you can drag, double-click to edit, and
restyle with the on-canvas resize / rotate handles + the contextual toolbar — OR drive
every prop from the right column. A second caption has `scaleWithZoom=True` so it keeps a
fixed ground footprint as you zoom. The `EditControl`'s `text` tool (Route B) is wired in
too: pick the **T** tool, click the map, and type — the caption round-trips through the
same `geojson` channel as every drawn shape, as a `kind:"text"` Point.
"""

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, callback, clientside_callback
from dl2_tiles import SATELLITE, register_theme_swap
from dl2_locations import SAN_FRANCISCO
from dl2_shared import code_panel, header, info_panel

# Basemap pair for this page. dl2_tiles owns the light/dark wiring so
# every example themes the same way — see register_theme_swap below.
TILES = SATELLITE
TILE_URL = TILES.url("light")
ATTR = TILES.attribution()

CENTER = SAN_FRANCISCO.at(1.4, -1.3)  # Fisherman's Wharf

ANCHORS = [
    "top-left", "top", "top-right",
    "left", "center", "right",
    "bottom-left", "bottom", "bottom-right",
]

CODE = """import dash_leaflet2 as dl2

dl2.Map(center=[37.808, -122.409], zoom=14, children=[
    dl2.TileLayer(),

    # A caption you place like a Marker: drag to move, double-click to edit,
    # and (when selected) resize / rotate with the on-canvas handles.
    dl2.TextMarker(
        id="cap",
        text="Fisherman's Wharf",
        position=[37.808, -122.409],
        color="#0b3d66", fontSize=26, fontWeight=700,
        backgroundColor="rgba(255,255,255,0.6)",
        selected=True,            # shows the handles + style toolbar
    ),

    # scaleWithZoom keeps a fixed GROUND size (grows on screen as you zoom in).
    dl2.TextMarker(text="PIER 39", position=[37.8087, -122.4098],
                   color="#c92a2a", fontSize=16, scaleWithZoom=True),

    # Route B — the EditControl 'text' tool: click the T, click the map, type.
    # Captions serialize as kind:"text" Point features in EditControl.geojson.
    dl2.EditControl(id="edit", draw={"text": True}),
])

# read it back
@callback(Output("out", "children"), Input("cap", "position"),
          Input("cap", "text"), Input("cap", "n_edits"))
def show(pos, text, n_edits): ...
"""


def _map():
    return dl2.Map(
        id="tm-map",
        center=CENTER,
        zoom=14,
        style={"height": "62vh"},
        children=[
            dl2.TileLayer(id="tm-tile", url=TILE_URL, attribution=ATTR),
            dl2.TextMarker(
                id="tm-cap",
                text="Fisherman's Wharf",
                position=CENTER,
                color="#0b3d66",
                fontSize=26,
                fontWeight=700,
                backgroundColor="rgba(255,255,255,0.6)",
                anchor="center",
                selected=True,
            ),
            dl2.TextMarker(
                id="tm-geo",
                text="PIER 39",
                position=[37.8087, -122.4098],
                color="#c92a2a",
                fontSize=16,
                fontWeight=700,
                scaleWithZoom=True,
            ),
            dl2.EditControl(
                id="tm-edit",
                position="topright",
                # Only expose the text tool here to keep the demo focused.
                draw={
                    "marker": False, "polyline": False, "polygon": False,
                    "rectangle": False, "circle": False, "circlemarker": False,
                    "text": True,
                },
            ),
        ],
    )


component = dmc.Stack(
    [
        header(
            "TextMarker — editable map captions",
            "Place styled text on the map like a Marker. Drag to move, double-click to "
            "edit, resize/rotate with the on-canvas handles, and restyle from the glass "
            "toolbar — or drive every prop from the right. Position, text, rotation, font "
            "size, and color all round-trip back to Dash.",
            badge="dl2.TextMarker · EditControl text tool",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        _map(),
                        shadow="sm",
                        radius="md",
                        withBorder=True,
                        style={"overflow": "hidden", "height": "62vh"},
                    ),
                    span=8,
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            info_panel(
                                "Caption text",
                                dmc.TextInput(id="tm-text", value="Fisherman's Wharf"),
                            ),
                            info_panel(
                                "Typography",
                                dmc.Stack(
                                    [
                                        dmc.ColorInput(id="tm-color", value="#0b3d66", format="hex"),
                                        dmc.Text("Font size", size="xs", c="dimmed"),
                                        dmc.Slider(id="tm-size", min=10, max=64, value=26),
                                        dmc.Text("Rotation", size="xs", c="dimmed"),
                                        dmc.Slider(
                                            id="tm-rot", min=-180, max=180, value=0,
                                            marks=[{"value": 0, "label": "0°"}],
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                            info_panel(
                                "Anchor",
                                dmc.SegmentedControl(
                                    id="tm-anchor",
                                    data=[{"label": a, "value": a} for a in ANCHORS],
                                    value="center",
                                    orientation="vertical",
                                    fullWidth=True,
                                    size="xs",
                                ),
                            ),
                            info_panel(
                                "Geographic sizing",
                                dmc.Switch(
                                    id="tm-scale",
                                    label="scaleWithZoom (fixed ground size)",
                                    checked=False,
                                ),
                            ),
                            info_panel(
                                "Live readback",
                                dmc.Code(id="tm-out", block=True, children="…"),
                            ),
                        ],
                        gap="md",
                    ),
                    span=4,
                ),
            ],
            gutter="md",
        ),
        code_panel("A caption that places, styles, and round-trips like a Marker", CODE),
    ],
    gap="md",
)


# ---- controls -> component (one-way drivers; the on-map UI is the other path) ----------
@callback(Output("tm-cap", "text"), Input("tm-text", "value"))
def _text(v):
    return v or ""


@callback(Output("tm-cap", "color"), Input("tm-color", "value"))
def _color(v):
    return v or "#0b3d66"


@callback(Output("tm-cap", "fontSize"), Input("tm-size", "value"))
def _size(v):
    return int(v or 26)


@callback(Output("tm-cap", "rotation"), Input("tm-rot", "value"))
def _rot(v):
    return int(v or 0)


@callback(Output("tm-cap", "anchor"), Input("tm-anchor", "value"))
def _anchor(v):
    return v or "center"


@callback(Output("tm-cap", "scaleWithZoom"), Input("tm-scale", "checked"))
def _scale(checked):
    return bool(checked)


# ---- component -> readback panel -------------------------------------------------------
@callback(
    Output("tm-out", "children"),
    Input("tm-cap", "position"),
    Input("tm-cap", "text"),
    Input("tm-cap", "rotation"),
    Input("tm-cap", "fontSize"),
    Input("tm-cap", "n_edits"),
    Input("tm-cap", "n_drags"),
    Input("tm-edit", "geojson"),
)
def _readback(pos, text, rot, size, n_edits, n_drags, geo):
    n_captions = sum(
        1
        for f in (geo or {}).get("features", [])
        if (f.get("properties") or {}).get("kind") == "text"
    )
    return (
        f"position : {pos}\n"
        f"text     : {text!r}\n"
        f"rotation : {rot}\n"
        f"fontSize : {size}\n"
        f"n_edits  : {n_edits or 0}\n"
        f"n_drags  : {n_drags or 0}\n"
        f"edit-tool captions: {n_captions}"
    )


# ---- light/dark tile swap (standard pattern) ------------------------------------------
register_theme_swap("tm-tile", TILES)
