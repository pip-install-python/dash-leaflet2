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
from dl2_shared import code_panel, header, info_panel

CODE_LG = """dl2.Map(children=[
    dl2.TileLayer(),
    dl2.LayerGroup(children=[
        dl2.Marker(position=[28.02, -97.05]),
        dl2.Marker(position=[28.04, -97.02]),
        dl2.Marker(position=[28.00, -97.08]),
    ]) if show_markers else None,
])"""

CODE_FG = """dl2.Map(children=[
    dl2.TileLayer(),
    dl2.FeatureGroup(id="fg", children=[
        dl2.Polygon(positions=[...]),
        dl2.Polyline(positions=[...]),
        dl2.Circle(center=[...], radius=400),
        dl2.Marker(position=[...]),
    ]),
])

@callback(Output("fg-readout","children"), Input("fg","geojson"))
def show(geojson): ..."""


component = dmc.Stack(
    [
        header(
            "LayerGroup & FeatureGroup",
            "LayerGroup bundles N layers so one switch hides them all. "
            "FeatureGroup adds aggregate event + GeoJSON output — click any child and "
            "n_clicks bumps; add/remove children and n_layers bumps too.",
            badge="dl2.LayerGroup / FeatureGroup",
        ),

        dmc.Title("1. LayerGroup", order=3, mt="md"),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dl2.Map(
                            id="lg-map",
                            center=[28.02, -97.05],
                            zoom=12,
                            style={"height": "45vh"},
                            children=[
                                dl2.TileLayer(),
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
        code_panel("LayerGroup", CODE_LG),

        dmc.Title("2. FeatureGroup", order=3, mt="md"),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dl2.Map(
                            id="fg-map",
                            center=[28.02, -97.05],
                            zoom=12,
                            style={"height": "45vh"},
                            children=[
                                dl2.TileLayer(),
                                dl2.FeatureGroup(
                                    id="fg",
                                    children=[
                                        dl2.Polygon(
                                            positions=[
                                                [28.04, -97.10],
                                                [28.06, -97.04],
                                                [28.04, -96.99],
                                                [28.02, -97.05],
                                            ],
                                            color="#228be6",
                                            fillOpacity=0.35,
                                        ),
                                        dl2.Polyline(
                                            positions=[
                                                [27.99, -97.10],
                                                [27.99, -97.04],
                                                [27.99, -96.98],
                                            ],
                                            color="#fa5252",
                                            weight=3,
                                        ),
                                        dl2.Circle(
                                            center=[28.03, -97.02],
                                            radius=600,
                                            color="#40c057",
                                            fillOpacity=0.25,
                                        ),
                                        dl2.Marker(position=[28.01, -97.06]),
                                    ],
                                ),
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
        code_panel("FeatureGroup", CODE_FG),
    ],
    gap="md",
)


@callback(Output("lg-container", "children"), Input("lg-toggle", "checked"))
def render_group(show):
    if not show:
        return []
    return dl2.LayerGroup(
        children=[
            dl2.Marker(position=[28.02, -97.05]),
            dl2.Marker(position=[28.04, -97.02]),
            dl2.Marker(position=[28.00, -97.08]),
        ]
    )


@callback(Output("fg-clicks", "children"), Input("fg", "n_clicks"))
def show_clicks(n):
    return str(n or 0)


@callback(Output("fg-geojson-readout", "children"), Input("fg", "geojson"))
def show_geojson(gj):
    if not gj:
        return "(no children yet)"
    return json.dumps(gj, indent=2)[:2000]
