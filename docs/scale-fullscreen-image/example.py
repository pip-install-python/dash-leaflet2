"""
ScaleControl, FullScreenControl, ImageOverlay — limited working example.

A single map with the scale bar bottom-left, the fullscreen button top-left, and
a sample raster (NASA Blue Marble) ImageOverlay draped over a Rockport, TX
bounding box. Right column tweaks each piece live.
"""

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, callback
from dl2_shared import code_panel, header, info_panel

OVERLAY_BOUNDS = [[27.95, -97.15], [28.10, -96.95]]
# Public sample image used by Leaflet docs.
SAMPLE_IMAGE = "https://leafletjs.com/examples/crs-simple/uqm_map_full.png"
SAMPLE_IMAGE_2 = "https://maps.lib.utexas.edu/maps/historical/texas_southern_1895.jpg"

ANCHORS = [
    "top-left", "top", "top-right",
    "left", "center", "right",
    "bottom-left", "bottom", "bottom-right",
]

CODE = """dl2.Map(center=[28.02, -97.05], zoom=12, children=[
    dl2.TileLayer(),
    dl2.ScaleControl(position="bottomleft", metric=True, imperial=True),
    dl2.FullScreenControl(position="topleft"),

    # Editable: click to select, drag to move, corner dot resizes (about `anchor`),
    # top dot rotates. bounds / rotation / selected round-trip back to Dash.
    dl2.ImageOverlay(
        id="img",
        url="https://leafletjs.com/examples/crs-simple/uqm_map_full.png",
        bounds=[[27.95, -97.15], [28.10, -96.95]],
        opacity=0.85,
        editable=True, selected=True, anchor="center", rotation=0,
    ),
])

@callback(Output("out", "children"),
          Input("img", "bounds"), Input("img", "rotation"))
def show(bounds, rotation): ..."""

component = dmc.Stack(
    [
        header(
            "Scale, FullScreen, ImageOverlay",
            "Scale bar bottom-left (metric + imperial), fullscreen button top-left, and an "
            "EDITABLE ImageOverlay: click it to select, then drag to move, drag the corner "
            "dot (the anchor marker) to resize, and the top dot to rotate — bounds + rotation "
            "round-trip back to Dash. The anchor dot follows the chosen anchor.",
            badge="dl2.{Scale,FullScreen}Control · editable dl2.ImageOverlay",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dl2.Map(
                            id="sfi-map",
                            center=[28.02, -97.05],
                            zoom=11,
                            style={"height": "60vh"},
                            children=[
                                dl2.TileLayer(),
                                dl2.ScaleControl(
                                    id="sfi-scale",
                                    position="bottomleft",
                                    metric=True,
                                    imperial=True,
                                ),
                                dl2.FullScreenControl(
                                    id="sfi-fs",
                                    position="topleft",
                                    title="Enter full screen",
                                    titleCancel="Leave full screen",
                                ),
                                dl2.ImageOverlay(
                                    id="sfi-image",
                                    url=SAMPLE_IMAGE,
                                    bounds=OVERLAY_BOUNDS,
                                    opacity=0.85,
                                    editable=True,
                                    selected=True,
                                    anchor="center",
                                    rotation=0,
                                ),
                            ],
                        ),
                        shadow="sm",
                        radius="md",
                        withBorder=True,
                        style={"overflow": "hidden", "height": "60vh"},
                    ),
                    span=8,
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            info_panel(
                                "Scale bar",
                                dmc.Stack(
                                    [
                                        dmc.SegmentedControl(
                                            id="sfi-scale-pos",
                                            data=[
                                                {"label": "BL", "value": "bottomleft"},
                                                {"label": "BR", "value": "bottomright"},
                                                {"label": "TL", "value": "topleft"},
                                                {"label": "TR", "value": "topright"},
                                            ],
                                            value="bottomleft",
                                            fullWidth=True,
                                        ),
                                        dmc.Switch(id="sfi-scale-metric", checked=True, label="metric"),
                                        dmc.Switch(id="sfi-scale-imperial", checked=True, label="imperial"),
                                    ],
                                    gap="xs",
                                ),
                            ),
                            info_panel(
                                "Fullscreen",
                                dmc.Stack(
                                    [
                                        dmc.Badge(id="sfi-fs-state", color="gray", variant="light", children="windowed"),
                                        dmc.Text(id="sfi-fs-clicks", size="xs", c="dimmed"),
                                    ],
                                    gap="xs",
                                ),
                            ),
                            info_panel(
                                "ImageOverlay opacity",
                                dmc.Slider(
                                    id="sfi-image-opacity",
                                    min=0,
                                    max=1,
                                    step=0.05,
                                    value=0.6,
                                ),
                            ),
                            info_panel(
                                "ImageOverlay source",
                                dmc.SegmentedControl(
                                    id="sfi-image-url",
                                    data=[
                                        {"label": "UQM sample", "value": SAMPLE_IMAGE},
                                        {"label": "1895 TX scan", "value": SAMPLE_IMAGE_2},
                                    ],
                                    value=SAMPLE_IMAGE,
                                    fullWidth=True,
                                ),
                            ),
                            info_panel(
                                "Transform (anchor pivot)",
                                dmc.Stack(
                                    [
                                        dmc.SegmentedControl(
                                            id="sfi-anchor",
                                            data=[{"label": a, "value": a} for a in ANCHORS],
                                            value="center",
                                            orientation="vertical",
                                            fullWidth=True,
                                            size="xs",
                                        ),
                                        dmc.Text("Rotation", size="xs", c="dimmed"),
                                        dmc.Slider(
                                            id="sfi-rot", min=-180, max=180, value=0,
                                            marks=[{"value": 0, "label": "0°"}],
                                        ),
                                        dmc.Code(id="sfi-image-out", block=True, children="…"),
                                    ],
                                    gap="xs",
                                ),
                            ),
                        ],
                        gap="md",
                    ),
                    span=4,
                ),
            ],
            gutter="md",
        ),
        code_panel("Three new pieces in one map", CODE),
    ],
    gap="md",
)


@callback(Output("sfi-scale", "position"), Input("sfi-scale-pos", "value"))
def scale_pos(v):
    return v or "bottomleft"


@callback(Output("sfi-scale", "metric"), Input("sfi-scale-metric", "checked"))
def scale_metric(checked):
    return bool(checked)


@callback(Output("sfi-scale", "imperial"), Input("sfi-scale-imperial", "checked"))
def scale_imperial(checked):
    return bool(checked)


@callback(Output("sfi-fs-state", "children"), Output("sfi-fs-state", "color"), Input("sfi-fs", "fullscreen"))
def fs_state(is_full):
    if is_full:
        return "fullscreen", "blue"
    return "windowed", "gray"


@callback(Output("sfi-fs-clicks", "children"), Input("sfi-fs", "n_clicks"))
def fs_clicks(n):
    return f"button clicks: {n or 0}"


@callback(Output("sfi-image", "opacity"), Input("sfi-image-opacity", "value"))
def image_opacity(v):
    return float(v or 0)


@callback(Output("sfi-image", "url"), Input("sfi-image-url", "value"))
def image_url(v):
    return v or SAMPLE_IMAGE


@callback(Output("sfi-image", "anchor"), Input("sfi-anchor", "value"))
def image_anchor(v):
    return v or "center"


@callback(Output("sfi-image", "rotation"), Input("sfi-rot", "value"))
def image_rotation(v):
    return int(v or 0)


@callback(
    Output("sfi-image-out", "children"),
    Input("sfi-image", "bounds"),
    Input("sfi-image", "rotation"),
    Input("sfi-image", "n_transforms"),
)
def image_readback(bounds, rotation, n):
    b = bounds or OVERLAY_BOUNDS
    return (
        f"rotation: {rotation or 0}°\n"
        f"bounds  : [[{b[0][0]:.4f}, {b[0][1]:.4f}],\n"
        f"           [{b[1][0]:.4f}, {b[1][1]:.4f}]]\n"
        f"n_transforms: {n or 0}"
    )
