"""Home — prove Leaflet 2 alpha renders inside Dash 4."""

import dash_mantine_components as dmc
from dl2_shared import info_panel, map_div


component = dmc.Stack(
    [
        map_div("home"),
        info_panel(
            "What the other pages show",
            dmc.List(
                [
                    dmc.ListItem(
                        "Pointer Events — v2's unified pointer model (pen pressure, tilt)."
                    ),
                    dmc.ListItem(
                        "Canvas Renderer — thousands of points through one <canvas>."
                    ),
                    dmc.ListItem(
                        "ES6 Subclassing — custom Control + a BlanketOverlay canvas layer."
                    ),
                    dmc.ListItem(
                        "ResizeObserver Sizing — no more gray tiles in collapsible panels."
                    ),
                    dmc.ListItem(
                        "Vector Layers — Polygon / Polyline / Circle / CircleMarker."
                    ),
                    dmc.ListItem(
                        "Events → Python — map state round-tripped into @callback."
                    ),
                ]
            ),
        ),
    ],
    gap="md",
)
