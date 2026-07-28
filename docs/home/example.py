"""Home — prove Leaflet 2 alpha renders inside Dash 4."""

import dash_mantine_components as dmc
from dl2_shared import code_panel, header, info_panel, map_div

QUICKSTART = """# app.py  — no JS build step
from dash import Dash, hooks, html

V = "2.0.0-alpha.1"  # WITH the dot; the dotless form 404s on unpkg
hooks.stylesheet([{"external_url": f"https://unpkg.com/leaflet@{V}/dist/leaflet.css",
                   "external_only": True}])
hooks.script([{"external_url": f"https://unpkg.com/leaflet@{V}/dist/leaflet-global.js",
               "external_only": True}])   # exposes window.leaflet (NOT window.L)

app = Dash(__name__)
app.layout = html.Div(className="leaflet2-map", **{"data-demo": "home"},
                      style={"height": "60vh"})

# assets/leaflet2_maps.js mounts the map:
#   const map = new leaflet.Map(el).setView([49.286, -123.12], 12);
#   new leaflet.TileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
"""

component = dmc.Stack(
    [
        header(
            "Leaflet 2 on Dash 4",
            "dash-leaflet is frozen on react-leaflet → Leaflet 1.9. This app skips "
            "react-leaflet entirely and drives Leaflet 2 core directly — a generation "
            "ahead, with a smaller footprint and direct access to v2 features.",
            badge="2.0.0-alpha.1",
        ),
        map_div("home"),
        code_panel("How it works (zero build step)", QUICKSTART),
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
