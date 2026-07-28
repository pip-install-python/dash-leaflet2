"""Vector Layers — Polygon / Polyline / Circle / CircleMarker."""

import dash_mantine_components as dmc
from dash import Input, Output, callback, dcc
from dl2_shared import code_panel, header, info_panel, map_div

JS = """new leaflet.Polygon([[28.05,-97.10],[28.06,-97.02],[28.01,-97.00]],
    {color: "#2f9e44", fillOpacity: 0.25}).addTo(map);
new leaflet.Polyline([[28.03,-97.09],[28.04,-97.02]], {weight: 4}).addTo(map);
new leaflet.Circle([28.0,-97.04], {radius: 1500}).addTo(map);       // metres
new leaflet.CircleMarker([28.015,-97.07], {radius: 10}).addTo(map); // pixels

layer.on("click", () => set_props("vec-store", {data: {shape: "polygon"}}));"""

component = dmc.Stack(
    [
        header(
            "Vector Layers",
            "The vector primitives a real dashboard needs — Polygon, Polyline, Circle "
            "(geo-radius) and CircleMarker (pixel-radius) — each with tooltips and "
            "click handlers that round-trip into Python.",
        ),
        dmc.Grid(
            [
                dmc.GridCol(map_div("vector-layers"), span=8),
                dmc.GridCol(
                    info_panel(
                        "Last shape clicked",
                        dmc.Stack(
                            [
                                dmc.Badge(
                                    id="vec-badge",
                                    color="grape",
                                    children="none yet",
                                    size="lg",
                                ),
                                dmc.Text(
                                    "Click any shape on the map.", size="sm", c="dimmed"
                                ),
                            ],
                            gap="sm",
                        ),
                    ),
                    span=4,
                ),
            ]
        ),
        code_panel("Vector primitives", JS),
        dcc.Store(id="vec-store"),
    ],
    gap="md",
)


@callback(
    Output("vec-badge", "children"),
    Input("vec-store", "data"),
    prevent_initial_call=True,
)
def show_shape(d):
    return d["shape"] if d else "none yet"
