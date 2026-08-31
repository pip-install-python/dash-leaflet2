"""Events → Python — full JS→Python round-trip via dcc.Store."""

import dash_mantine_components as dmc
from dash import Input, Output, callback, dcc
from dl2_shared import info_panel, map_div


component = dmc.Stack(
    [
        dmc.Grid(
            [
                dmc.GridCol(map_div("events-python"), span=8),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            info_panel(
                                "View state (moveend / zoomend)",
                                dmc.Code(
                                    id="ev-view",
                                    block=True,
                                    style={"minHeight": "120px"},
                                ),
                            ),
                            info_panel(
                                "Last click", dmc.Code(id="ev-click", block=True)
                            ),
                        ],
                        gap="md",
                    ),
                    span=4,
                ),
            ]
        ),
        dcc.Store(id="ev-store"),
        dcc.Store(id="ev-click-store"),
    ],
    gap="md",
)


@callback(Output("ev-view", "children"), Input("ev-store", "data"))
def show_view(d):
    if not d:
        return "pan or zoom the map…"
    b = d["bounds"]
    return (
        f"center: {d['lat']}, {d['lng']}\n"
        f"zoom:   {d['zoom']}\n"
        f"bounds: N {b['n']}  S {b['s']}\n"
        f"        E {b['e']}  W {b['w']}"
    )


@callback(
    Output("ev-click", "children"),
    Input("ev-click-store", "data"),
    prevent_initial_call=True,
)
def show_click(d):
    return f"{d['lat']}, {d['lng']}" if d else "—"
