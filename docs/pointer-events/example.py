"""Pointer Events — Leaflet 2's headline change."""

import dash_mantine_components as dmc
from dash import Input, Output, callback, dcc, html
from dl2_shared import info_panel, map_div


component = dmc.Stack(
    [
        dmc.Grid(
            [
                dmc.GridCol(map_div("pointer-events"), span=8),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            info_panel(
                                "Live pointer (clientside HUD)",
                                html.Div(
                                    id="pe-live",
                                    className="dl2-hud",
                                    children="move the pointer over the map…",
                                ),
                            ),
                            info_panel(
                                "Round-tripped to Python",
                                dmc.Stack(
                                    [
                                        dmc.Text(
                                            "Throttled pointermove + every pointerdown reach a @callback:",
                                            size="sm",
                                            c="dimmed",
                                        ),
                                        dmc.Code(
                                            id="pe-py",
                                            block=True,
                                            style={"minHeight": "120px"},
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                        ],
                        gap="md",
                    ),
                    span=4,
                ),
            ]
        ),
        dcc.Store(id="pe-store"),
    ],
    gap="md",
)


@callback(
    Output("pe-py", "children"), Input("pe-store", "data"), prevent_initial_call=True
)
def show_pointer(d):
    if not d:
        return "—"
    return (
        f"event:       {d['event']}\n"
        f"pointerType: {d['pointerType']}\n"
        f"pressure:    {d['pressure']}\n"
        f"lat, lng:    {d['lat']}, {d['lng']}"
    )
