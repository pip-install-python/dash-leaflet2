"""
TileLayer pro props — limited working example.

Demonstrates the new dl2.TileLayer surface (minZoom, bounds, errorTileUrl, zIndex,
subdomains, detectRetina, tms). Two stacked tile layers are mounted into one map:
a base OSM layer with subdomains + detectRetina, and an overlay layer constrained
to a bounding box around Rockport TX with a transparent errorTileUrl. Toggling the
zIndex slider reorders them; toggling 'detectRetina' swaps the hi-DPI tile request.
"""

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, callback, html
from dl2_shared import code_panel, header, info_panel

# 1x1 transparent PNG — replaces 404 tiles outside the bounds.
BLANK_TILE = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkAAIAAAUAAdM6"
    "wQAAAABJRU5ErkJggg=="
)

# Rough box around Rockport, TX.
RCK_BOUNDS = [[27.93, -97.20], [28.12, -96.95]]

CODE = """dl2.Map(center=[28.02, -97.05], zoom=10, children=[
    dl2.TileLayer(
        id="base-tile",
        # Subdomains substituted into {s} — distribute requests across a, b, c.
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        subdomains=["a", "b", "c"],
        detectRetina=True,        # 2x tiles on hi-DPI screens
        minZoom=2,                # don't request tiles below world-view
        maxZoom=18,
        zIndex=1,
    ),
    dl2.TileLayer(
        id="overlay-tile",
        url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}.png",
        subdomains=["a", "b", "c", "d"],
        bounds=[[27.93, -97.20], [28.12, -96.95]],   # only paint tiles inside this box
        errorTileUrl=BLANK_TILE,                      # 1x1 transparent png for 404s
        opacity=0.85,
        zIndex=10,                                    # paint above OSM (negative = below)
    ),
])"""


component = dmc.Stack(
    [
        header(
            "TileLayer pro props",
            "Two stacked tile layers — an OSM base (subdomains a/b/c, detectRetina) "
            "and a CARTO labels-only overlay clipped to Rockport, TX via bounds. "
            "Move the overlay opacity slider to fade the labels in/out. "
            "Flip the zIndex segmented control to put the labels below or above the "
            "OSM base. Outside the bounds box, only the OSM base shows.",
            badge="dl2.TileLayer",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dl2.Map(
                            id="tlpro-map",
                            center=[28.02, -97.05],
                            zoom=10,
                            minZoom=2,
                            maxZoom=18,
                            style={"height": "55vh"},
                            children=[
                                dl2.TileLayer(
                                    id="tlpro-base",
                                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                                    subdomains=["a", "b", "c"],
                                    detectRetina=True,
                                    minZoom=2,
                                    maxZoom=19,
                                    zIndex=1,
                                ),
                                dl2.TileLayer(
                                    id="tlpro-overlay",
                                    url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}.png",
                                    subdomains=["a", "b", "c", "d"],
                                    bounds=RCK_BOUNDS,
                                    errorTileUrl=BLANK_TILE,
                                    opacity=0.85,
                                    zIndex=10,
                                ),
                            ],
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
                                "Overlay opacity",
                                dmc.Slider(
                                    id="tlpro-opacity",
                                    min=0,
                                    max=1,
                                    step=0.05,
                                    value=0.85,
                                    label=None,
                                ),
                            ),
                            info_panel(
                                "Overlay zIndex",
                                dmc.SegmentedControl(
                                    id="tlpro-zindex",
                                    data=[
                                        {"label": "Behind OSM", "value": "-1"},
                                        {"label": "Above OSM", "value": "10"},
                                    ],
                                    value="10",
                                    fullWidth=True,
                                ),
                            ),
                            info_panel(
                                "Base layer",
                                html.Div(
                                    [
                                        dmc.Badge(
                                            "detectRetina ON",
                                            color="blue",
                                            variant="light",
                                            mb=4,
                                        ),
                                        dmc.Text(
                                            "Subdomains a/b/c spread requests across "
                                            "three OSM hosts.",
                                            size="xs",
                                            c="dimmed",
                                        ),
                                    ]
                                ),
                            ),
                            info_panel(
                                "Overlay bounds",
                                dmc.Code(
                                    f"{RCK_BOUNDS}",
                                    block=False,
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
        code_panel("Stacked TileLayers with the new props", CODE),
    ],
    gap="md",
)


@callback(Output("tlpro-overlay", "opacity"), Input("tlpro-opacity", "value"))
def update_opacity(v):
    return float(v or 0)


@callback(Output("tlpro-overlay", "zIndex"), Input("tlpro-zindex", "value"))
def update_zindex(v):
    return int(v) if v is not None else 10


