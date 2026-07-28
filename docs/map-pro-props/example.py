"""
Map pro props — limited working example.

A New Orleans riverfront map. Sliders clamp the user's allowed zoom range, the
SegmentedControl swaps maxBounds on/off (pan past the edges and you'll bounce
back), and six switches at the bottom toggle the interaction handlers
(dragging, scrollWheelZoom, doubleClickZoom, boxZoom, pinchZoom, keyboard)
at runtime — exactly the surface dash-leaflet 1.x exposed.
"""

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, callback
from dl2_locations import NEW_ORLEANS
from dl2_shared import code_panel, header, info_panel

# A ~17 x 20 km box centred on the city — the same real-world size in every
# demo that clamps or drapes something, wherever that demo is set.
HARBOR_BOUNDS = NEW_ORLEANS.bounds(8.35, 9.83)

CODE = """dl2.Map(
    center=[29.9511, -90.0715],
    zoom=12,
    minZoom=10,                                # can't zoom out past 10
    maxZoom=18,                                # can't zoom in past 18
    maxBounds=[[29.876, -90.174], [30.026, -89.969]],  # pan-clamped to the riverfront
    zoomControl=True,                          # +/- buttons (constructor-only)
    keyboard=True,                             # arrow keys (mutable)
    dragging=True,                             # pointer drag-pan (mutable)
    scrollWheelZoom=True,                      # mouse-wheel zoom (mutable)
    doubleClickZoom=True,                      # dbl-click zoom (mutable)
    boxZoom=True,                              # shift-drag box-zoom (mutable)
    pinchZoom=True,                            # touch pinch-zoom (mutable; v2 name for touchZoom)
    children=[dl2.TileLayer()],
)"""

component = dmc.Stack(
    [
        header(
            "Map pro props",
            "minZoom / maxZoom / maxBounds / zoomControl / keyboard — try the "
            "sliders to clamp the viewport; pan past the dashed box edges to feel "
            "the bounce; flip the keyboard switch and the arrow keys stop working.",
            badge="dl2.Map",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dl2.Map(
                            id="mpp-map",
                            center=NEW_ORLEANS.center,
                            zoom=12,
                            minZoom=10,
                            maxZoom=18,
                            maxBounds=HARBOR_BOUNDS,
                            zoomControl=True,
                            keyboard=True,
                            dragging=True,
                            scrollWheelZoom=True,
                            doubleClickZoom=True,
                            boxZoom=True,
                            pinchZoom=True,
                            style={"height": "55vh"},
                            children=[dl2.TileLayer()],
                        ),
                        shadow="sm",
                        radius="md",
                        withBorder=True,
                        style={"overflow": "hidden", "height": "55vh"},
                    ),
                    span=8,
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            info_panel(
                                "Zoom range",
                                dmc.RangeSlider(
                                    id="mpp-zoom-range",
                                    min=0,
                                    max=22,
                                    step=1,
                                    value=[10, 18],
                                    marks=[
                                        {"value": 0, "label": "0"},
                                        {"value": 22, "label": "22"},
                                    ],
                                ),
                            ),
                            info_panel(
                                "maxBounds (clamp panning)",
                                dmc.SegmentedControl(
                                    id="mpp-bounds",
                                    data=[
                                        {"label": "Harbor box", "value": "harbor"},
                                        {"label": "Unclamped", "value": "off"},
                                    ],
                                    value="harbor",
                                    fullWidth=True,
                                ),
                            ),
                            info_panel(
                                "Interaction handlers",
                                dmc.Stack(
                                    [
                                        dmc.Switch(id="mpp-dragging", checked=True, label="dragging"),
                                        dmc.Switch(id="mpp-scrollwheel", checked=True, label="scrollWheelZoom"),
                                        dmc.Switch(id="mpp-dblclick", checked=True, label="doubleClickZoom"),
                                        dmc.Switch(id="mpp-boxzoom", checked=True, label="boxZoom"),
                                        dmc.Switch(id="mpp-pinchzoom", checked=True, label="pinchZoom"),
                                        dmc.Switch(id="mpp-keyboard", checked=True, label="keyboard"),
                                    ],
                                    gap=4,
                                ),
                            ),
                            info_panel(
                                "Current viewport (read back from Map.viewport)",
                                dmc.Code(id="mpp-viewport-readout", block=True),
                            ),
                        ],
                        gap="md",
                    ),
                    span=4,
                ),
            ],
            gutter="md",
        ),
        code_panel("Map with the new pro props", CODE),
    ],
    gap="md",
)


@callback(Output("mpp-map", "minZoom"), Output("mpp-map", "maxZoom"), Input("mpp-zoom-range", "value"))
def update_zoom_range(rng):
    if not rng:
        return 10, 18
    return int(rng[0]), int(rng[1])


@callback(Output("mpp-map", "maxBounds"), Input("mpp-bounds", "value"))
def update_bounds(mode):
    return HARBOR_BOUNDS if mode == "harbor" else None


@callback(Output("mpp-map", "keyboard"), Input("mpp-keyboard", "checked"))
def update_keyboard(checked):
    return bool(checked)


@callback(Output("mpp-map", "dragging"), Input("mpp-dragging", "checked"))
def update_dragging(checked):
    return bool(checked)


@callback(Output("mpp-map", "scrollWheelZoom"), Input("mpp-scrollwheel", "checked"))
def update_scrollwheel(checked):
    return bool(checked)


@callback(Output("mpp-map", "doubleClickZoom"), Input("mpp-dblclick", "checked"))
def update_dblclick(checked):
    return bool(checked)


@callback(Output("mpp-map", "boxZoom"), Input("mpp-boxzoom", "checked"))
def update_boxzoom(checked):
    return bool(checked)


@callback(Output("mpp-map", "pinchZoom"), Input("mpp-pinchzoom", "checked"))
def update_pinchzoom(checked):
    return bool(checked)


@callback(Output("mpp-viewport-readout", "children"), Input("mpp-map", "viewport"))
def viewport_readout(vp):
    if not vp:
        return "(no viewport yet)"
    c = vp.get("center", [0, 0])
    return (
        f"center: [{c[0]:.4f}, {c[1]:.4f}]\n"
        f"zoom:   {vp.get('zoom')}\n"
        f"bounds: {vp.get('bounds')}"
    )
