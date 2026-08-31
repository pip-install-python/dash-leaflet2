"""Vector Layers — Polygon / Polyline / Circle / CircleMarker."""

import dash_mantine_components as dmc
from dash import Input, Output, callback, dcc
from dl2_shared import info_panel, map_div


component = dmc.Stack(
    [
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
