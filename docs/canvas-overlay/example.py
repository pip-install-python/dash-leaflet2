"""Canvas Renderer — dense point clouds through one <canvas>."""

import dash_mantine_components as dmc
from dash import html
from dl2_shared import info_panel, map_div


component = dmc.Stack(
    [
        info_panel(
            "Render benchmark",
            html.Div(id="canvas-hud", className="dl2-hud", children="rendering…"),
        ),
        map_div("canvas-overlay"),
    ],
    gap="md",
)
