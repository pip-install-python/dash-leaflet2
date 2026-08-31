"""
LayerGroup & FeatureGroup — limited working example.

Top map: a LayerGroup containing three markers — toggle them all on/off with one
switch (the group itself is conditionally rendered, so all children come and go
together).

Bottom map: a FeatureGroup wrapping three vector layers + a marker. Click any
of them and FeatureGroup's `n_clicks` bumps; the readout shows the combined
GeoJSON it emits.
"""

import json

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, callback, html
from dl2_tiles import ESRI_CANVAS, register_theme_swap
from dl2_locations import PHILADELPHIA
from dl2_shared import info_panel

# Basemap pair for this page — dl2_tiles owns the light/dark wiring.
TILES = ESRI_CANVAS




component = dmc.Stack(
    [

        dmc.Title("1. LayerGroup", order=3, mt="md"),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dl2.Map(
                            id="lg-map",
                            center=PHILADELPHIA.center,
                            zoom=12,
                            style={"height": "45vh"},
                            children=[
                                dl2.TileLayer(id="lg-tile", **TILES.kwargs("light")),
                                html.Div(id="lg-container"),
                            ],
                        ),
                        shadow="sm",
                        radius="md",
                        withBorder=True,
                        style={"overflow": "hidden", "height": "45vh"},
                    ),
                    span=8,
                ),
                dmc.GridCol(
                    info_panel(
                        "Toggle the whole group",
                        dmc.Switch(
                            id="lg-toggle",
                            checked=True,
                            label="Show three markers (all in one LayerGroup)",
                        ),
                    ),
                    span=4,
                ),
            ],
            gutter="md",
        ),

        dmc.Title("2. FeatureGroup", order=3, mt="md"),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dl2.Map(
                            id="fg-map",
                            center=PHILADELPHIA.center,
                            zoom=12,
                            style={"height": "45vh"},
                            children=[
                                dl2.TileLayer(),
                                # region featuregroup
                                dl2.FeatureGroup(
                                    id="fg",
                                    children=[
                                        dl2.Polygon(
                                            # (north_km, east_km) from the
                                            # city centre — the shape keeps its
                                            # real-world size at any latitude.
                                            positions=PHILADELPHIA.ring([
                                                (2.2, -4.9),
                                                (4.5, 1.0),
                                                (2.2, 5.9),
                                                (0.0, 0.0),
                                            ]),
                                            color="#228be6",
                                            fillOpacity=0.35,
                                        ),
                                        dl2.Polyline(
                                            positions=PHILADELPHIA.ring([
                                                (-3.3, -4.9),
                                                (-3.3, 1.0),
                                                (-3.3, 6.9),
                                            ]),
                                            color="#fa5252",
                                            weight=3,
                                        ),
                                        dl2.Circle(
                                            center=PHILADELPHIA.at(1.1, 2.9),
                                            radius=600,
                                            color="#40c057",
                                            fillOpacity=0.25,
                                        ),
                                        dl2.Marker(position=PHILADELPHIA.at(-1.1, -1.0)),
                                    ],
                                ),
                                # endregion
                            ],
                        ),
                        shadow="sm",
                        radius="md",
                        withBorder=True,
                        style={"overflow": "hidden", "height": "45vh"},
                    ),
                    span=8,
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            info_panel(
                                "Group n_clicks",
                                dmc.Badge(id="fg-clicks", color="blue", variant="light", children="0"),
                            ),
                            info_panel(
                                "Combined geojson (vector children)",
                                dmc.Code(
                                    id="fg-geojson-readout",
                                    block=True,
                                    children="(click a shape)",
                                    style={"maxHeight": "20vh", "overflow": "auto"},
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
    ],
    gap="md",
)


@callback(Output("lg-container", "children"), Input("lg-toggle", "checked"))
def render_group(show):
    if not show:
        return []
    # region layergroup
    return dl2.LayerGroup(
        children=[
            dl2.Marker(position=PHILADELPHIA.center),
            dl2.Marker(position=PHILADELPHIA.at(2.2, 2.9)),
            dl2.Marker(position=PHILADELPHIA.at(-2.2, -2.9)),
        ]
    )
    # endregion


@callback(Output("fg-clicks", "children"), Input("fg", "n_clicks"))
def show_clicks(n):
    return str(n or 0)


@callback(Output("fg-geojson-readout", "children"), Input("fg", "geojson"))
def show_geojson(gj):
    if not gj:
        return "(no children yet)"
    return json.dumps(gj, indent=2)[:2000]


# Light/dark basemap, driven off the color-scheme store.
register_theme_swap("lg-tile", TILES)
