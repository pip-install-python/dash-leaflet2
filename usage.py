"""
usage.py — the compiled dash_leaflet2 component package in action.

Demos the full step-3 surface: the core trio + vectors + popup/tooltip + GeoJSON + emoji /
iconify markers + LayersControl (base + overlays) + EditControl (draw / delete).
No hooks, no CDN — Leaflet 2 is bundled inside the component's own JS, marker icons and
liquid-glass UI come along too.

Run:
    npm run build        # build the components first (writes dash_leaflet2/)
    python usage.py      # http://127.0.0.1:8060
"""

import json

import dash_leaflet2 as dl2
from dash import Dash, Input, Output, callback, html

CENTER = [28.0206, -97.0544]

GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Sector A"},
            "geometry": {"type": "Point", "coordinates": [-97.02, 28.04]},
        },
        {
            "type": "Feature",
            "properties": {"name": "Survey line"},
            "geometry": {
                "type": "LineString",
                "coordinates": [[-97.10, 28.05], [-97.04, 28.03], [-97.00, 28.06]],
            },
        },
    ],
}

app = Dash(__name__)

app.layout = html.Div(
    style={
        "fontFamily": "system-ui, sans-serif",
        "padding": "16px",
        "maxWidth": "1100px",
        "margin": "0 auto",
    },
    children=[
        html.H2("dash-leaflet2 — compiled components"),
        html.P(
            "Layers control toggles base tiles + overlays. Edit control adds shapes to its own "
            "FeatureGroup and round-trips the GeoJSON to Python. Glass tooltips/popups follow "
            "any DMC-themed app's light/dark scheme (these vars fall back to a light look here)."
        ),
        dl2.Map(
            id="map",
            center=CENTER,
            zoom=12,
            style={"height": "62vh", "borderRadius": "8px", "overflow": "hidden"},
            children=[
                # Base + overlays managed by LayersControl (radio + checkboxes).
                dl2.LayersControl(
                    id="layers",
                    position="topright",
                    children=[
                        dl2.BaseLayer(
                            dl2.TileLayer(),
                            name="OSM",
                            checked=True,
                        ),
                        dl2.BaseLayer(
                            dl2.TileLayer(
                                url="https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
                                attribution="&copy; OpenStreetMap &copy; CARTO",
                            ),
                            name="CARTO Dark",
                        ),
                        dl2.Overlay(
                            dl2.Polygon(
                                positions=[
                                    [28.05, -97.10],
                                    [28.06, -97.02],
                                    [28.01, -97.00],
                                    [28.00, -97.08],
                                ],
                                color="#2f9e44",
                                fillOpacity=0.25,
                                children=dl2.Tooltip(children="harbor zone"),
                            ),
                            name="Harbor zone",
                            checked=True,
                        ),
                        dl2.Overlay(
                            dl2.Circle(
                                center=[28.0, -97.04],
                                radius=1500,
                                color="#e8590c",
                                fillOpacity=0.2,
                                children=dl2.Tooltip(children="buoy radius"),
                            ),
                            name="Buoy radius",
                            checked=True,
                        ),
                    ],
                ),
                # Always-on markers + GeoJSON
                dl2.Marker(
                    id="marker",
                    position=CENTER,
                    draggable=True,
                    children=[
                        dl2.Tooltip(children="drag me — position round-trips"),
                        dl2.Popup(
                            children=html.Div(
                                [
                                    html.B("dl2.Marker + dl2.Popup"),
                                    html.Br(),
                                    "Rich Dash content inside a Leaflet 2 popup.",
                                ]
                            )
                        ),
                    ],
                ),
                dl2.Marker(
                    position=[28.06, -97.02],
                    emoji="🛥️",
                    iconSize=34,
                    children=dl2.Tooltip(children="emoji marker"),
                ),
                dl2.Marker(
                    position=[27.99, -97.10],
                    iconify="mdi:lighthouse-on",
                    iconColor="#e8590c",
                    iconSize=36,
                    children=dl2.Tooltip(children="iconify lighthouse"),
                ),
                dl2.GeoJSON(
                    id="geojson", data=GEOJSON, style={"color": "#d6336c", "weight": 3}
                ),
                # Editable on-map caption — drag to move, double-click to edit, and (when
                # selected) use the on-canvas resize / rotate handles + the glass toolbar.
                # Position / text / rotation / fontSize / color all round-trip to Python.
                dl2.TextMarker(
                    id="caption",
                    text="Harbor District",
                    position=[28.05, -96.98],
                    color="#10243a",
                    backgroundColor="rgba(255,255,255,0.55)",
                    fontSize=28,
                    fontWeight=700,
                    selected=True,
                ),
                # Drawing toolbar (top-left). Drawn shapes -> EditControl.geojson.
                dl2.EditControl(id="edit", position="topleft"),
            ],
        ),
        html.Div(
            style={
                "display": "flex",
                "gap": "16px",
                "marginTop": "12px",
                "fontFamily": "monospace",
            },
            children=[
                html.Pre(
                    id="layers-out",
                    style={
                        "flex": 1,
                        "background": "#f1f3f5",
                        "padding": "10px",
                        "borderRadius": "6px",
                    },
                ),
                html.Pre(
                    id="edit-out",
                    style={
                        "flex": 2,
                        "background": "#f1f3f5",
                        "padding": "10px",
                        "borderRadius": "6px",
                        "maxHeight": "180px",
                        "overflow": "auto",
                    },
                ),
                html.Pre(
                    id="marker-out",
                    style={
                        "flex": 1,
                        "background": "#f1f3f5",
                        "padding": "10px",
                        "borderRadius": "6px",
                    },
                ),
                html.Pre(
                    id="caption-out",
                    style={
                        "flex": 1,
                        "background": "#f1f3f5",
                        "padding": "10px",
                        "borderRadius": "6px",
                    },
                ),
            ],
        ),
    ],
)


@callback(
    Output("caption-out", "children"),
    Input("caption", "text"),
    Input("caption", "position"),
    Input("caption", "rotation"),
    Input("caption", "fontSize"),
    Input("caption", "color"),
    Input("caption", "n_edits"),
    Input("caption", "n_drags"),
)
def show_caption(text, pos, rot, size, color, n_edits, n_drags):
    return (
        f"text:     {text!r}\nposition: {pos}\nrotation: {rot}\n"
        f"fontSize: {size}\ncolor:    {color}\n"
        f"n_edits:  {n_edits or 0}\nn_drags:  {n_drags or 0}"
    )


@callback(
    Output("layers-out", "children"),
    Input("layers", "activeBase"),
    Input("layers", "activeOverlays"),
)
def show_layers(base, overlays):
    return f"base:\n  {base}\noverlays:\n  {overlays}"


@callback(
    Output("edit-out", "children"),
    Input("edit", "geojson"),
    Input("edit", "n_drawn"),
    Input("edit", "lastAction"),
)
def show_edit(geo, n, last):
    if not geo:
        return "Pick a tool and click the map to start drawing."
    return (
        f"n_drawn: {n or 0}\nlastAction: {last}\n"
        f"geojson features: {len((geo or {}).get('features', []))}\n\n"
        f"{json.dumps(geo, indent=1)[:600]}"
    )


@callback(
    Output("marker-out", "children"),
    Input("marker", "n_clicks"),
    Input("marker", "n_drags"),
    Input("marker", "position"),
)
def show_marker(n, drags, pos):
    return f"clicks: {n or 0}\ndrags: {drags or 0}\nposition: {pos}"


if __name__ == "__main__":
    app.run(debug=True, port=8060)
