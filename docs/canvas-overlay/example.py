"""Canvas Renderer — dense point clouds through one <canvas>."""

import dash_mantine_components as dmc
from dash import html
from dl2_shared import code_panel, header, info_panel, map_div

JS = """// preferCanvas routes every CircleMarker through the Canvas renderer:
// one <canvas> instead of N SVG nodes — the substrate for live vessel
// positions, sensor swarms and heatmaps.
const map = new leaflet.Map(el, {preferCanvas: true}).setView(center, 11);
for (let i = 0; i < 8000; i++) {
    new leaflet.CircleMarker(points[i], {radius: 3, stroke: false}).addTo(group);
}"""

component = dmc.Stack(
    [
        header(
            "Canvas Renderer",
            "Set preferCanvas: true and every path/marker draws into a single "
            "<canvas> rather than one SVG node each. Here we drop 8,000 CircleMarkers "
            "and pan/zoom stays smooth — exactly what dense IoT / vessel-tracking "
            "layers need.",
        ),
        info_panel(
            "Render benchmark",
            html.Div(id="canvas-hud", className="dl2-hud", children="rendering…"),
        ),
        map_div("canvas-overlay"),
        code_panel("Canvas-backed markers", JS),
    ],
    gap="md",
)
