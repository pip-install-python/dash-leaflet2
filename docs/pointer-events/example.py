"""Pointer Events — Leaflet 2's headline change."""

import dash_mantine_components as dmc
from dash import Input, Output, callback, dcc, html
from dl2_shared import code_panel, header, info_panel, map_div

JS = """// v2 fires POINTER events; the old mousemove/mousedown are gone.
map.on("pointermove", (e) => {
    const oe = e.originalEvent;        // a native PointerEvent
    console.log(oe.pointerType,        // "mouse" | "pen" | "touch"
                oe.pressure,           // 0..1 (real for a stylus)
                oe.tiltX, oe.tiltY,    // pen tilt
                e.latlng);             // geo coordinate
});"""

component = dmc.Stack(
    [
        header(
            "Pointer Events",
            "v2 replaced Leaflet 1's separate mouse/touch code paths with one unified "
            "PointerEvents model. Each Leaflet event's originalEvent is a native "
            "PointerEvent — so pen pressure, tilt and pointerType are first-class. "
            "Ideal for stylus annotation over a CV/streaming pipeline.",
            badge="v2 headline",
        ),
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
        code_panel("The v2 pointer API", JS),
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
