"""ES6 Subclassing — custom Control + a BlanketOverlay canvas layer."""

import dash_mantine_components as dmc
from dl2_shared import info_panel, map_div


component = dmc.Stack(
    [
        map_div("subclassing"),
        dmc.Grid(
            [
                dmc.GridCol(
                    info_panel(
                        "Custom Control",
                        dmc.Text(
                            "class CenterControl extends leaflet.Control — a plain ES6 subclass "
                            "overriding onAdd(). Watch the top-right box update as you pan/zoom.",
                            size="sm",
                        ),
                    ),
                    span=6,
                ),
                dmc.GridCol(
                    info_panel(
                        "BlanketOverlay layer",
                        dmc.Text(
                            "class GlowLayer extends leaflet.BlanketOverlay paints 40 geo-anchored "
                            "sensor glows onto one <canvas>. _onSettled() re-projects them on every "
                            "pan/zoom — the hook for WebGL/canvas overlays without fighting SVG.",
                            size="sm",
                        ),
                    ),
                    span=6,
                ),
            ]
        ),
    ],
    gap="md",
)
