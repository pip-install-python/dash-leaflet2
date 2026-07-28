"""
Layers Control — the compiled dl2.LayersControl component.

Demonstrates the real Python API (this is what users would write), not the JS DEMO style
used by the other showcase pages. Two-way: the UI radios/checkboxes write activeBase /
activeOverlays back to Python; Python callbacks also push those props to flip the control.
"""

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, State, callback
from dl2_locations import MINNEAPOLIS
from dl2_shared import code_panel, header, info_panel

OSM = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
CARTO_LIGHT = "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
CARTO_DARK = "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
ATTR = (
    '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> '
    '&copy; <a href="https://carto.com/attributions">CARTO</a>'
)

SENSORS = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "buoy 1"},
            # GeoJSON is [lon, lat] — the opposite order to Leaflet.
            "geometry": {"type": "Point", "coordinates": MINNEAPOLIS.at_lonlat(2.2, 1.0)},
        },
        {
            "type": "Feature",
            "properties": {"name": "buoy 2"},
            "geometry": {"type": "Point", "coordinates": MINNEAPOLIS.at_lonlat(-1.1, -2.9)},
        },
        {
            "type": "Feature",
            "properties": {"name": "buoy 3"},
            "geometry": {"type": "Point", "coordinates": MINNEAPOLIS.at_lonlat(4.5, -1.0)},
        },
    ],
}

CODE = '''dl2.Map(children=[
    dl2.LayersControl(id="lc", children=[
        dl2.BaseLayer(dl2.TileLayer(url=CARTO_LIGHT), name="Light", checked=True),
        dl2.BaseLayer(dl2.TileLayer(url=CARTO_DARK),  name="Dark"),
        dl2.BaseLayer(dl2.TileLayer(url=OSM),         name="OSM"),
        dl2.Overlay(dl2.Polygon(...),  name="Harbor zone", checked=True),
        dl2.Overlay(dl2.Circle(...),   name="Buoy radius"),
        dl2.Overlay(dl2.GeoJSON(data=SENSORS), name="Sensors"),
    ]),
])

# activeBase / activeOverlays are TWO-WAY:
@callback(Output("out", "children"),
          Input("lc", "activeBase"), Input("lc", "activeOverlays"))
def show(b, o):
    return f"{b} | {o}"

@callback(Output("lc", "activeBase"), Input("dark-btn", "n_clicks"),
          prevent_initial_call=True)
def force_dark(_):
    return "Dark"'''

component = dmc.Stack(
    [
        header(
            "Layers Control",
            "dl2.LayersControl renders a Leaflet control with N base layers (radio) and M "
            "overlays (checkbox). BaseLayer/Overlay capture their child layer via a React-context "
            "map proxy and register it with the control. activeBase + activeOverlays are two-way.",
            badge="dl2.LayersControl",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dl2.Map(
                            id="lc-map",
                            center=MINNEAPOLIS.center,
                            zoom=12,
                            style={"height": "60vh"},
                            children=[
                                dl2.LayersControl(
                                    id="lc",
                                    position="topright",
                                    children=[
                                        dl2.BaseLayer(
                                            dl2.TileLayer(
                                                url=CARTO_LIGHT, attribution=ATTR
                                            ),
                                            name="Light",
                                            checked=True,
                                        ),
                                        dl2.BaseLayer(
                                            dl2.TileLayer(
                                                url=CARTO_DARK, attribution=ATTR
                                            ),
                                            name="Dark",
                                        ),
                                        dl2.BaseLayer(
                                            dl2.TileLayer(url=OSM), name="OSM"
                                        ),
                                        dl2.Overlay(
                                            dl2.Polygon(
                                                # (north_km, east_km) offsets
                                                positions=MINNEAPOLIS.ring([
                                                    (3.3, -4.9),
                                                    (4.5, 2.9),
                                                    (-1.1, 4.9),
                                                    (-2.2, -2.9),
                                                ]),
                                                color="#2f9e44",
                                                fillOpacity=0.25,
                                                children=dl2.Tooltip(
                                                    children="harbor zone"
                                                ),
                                            ),
                                            name="Harbor zone",
                                            checked=True,
                                        ),
                                        dl2.Overlay(
                                            dl2.Circle(
                                                center=MINNEAPOLIS.at(-2.2, 1.0),
                                                radius=1500,
                                                color="#e8590c",
                                                fillOpacity=0.2,
                                                children=dl2.Tooltip(
                                                    children="buoy radius"
                                                ),
                                            ),
                                            name="Buoy radius",
                                        ),
                                        dl2.Overlay(
                                            dl2.GeoJSON(
                                                data=SENSORS,
                                                style={"color": "#9c36b5", "weight": 2},
                                            ),
                                            name="Sensors",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        shadow="sm",
                        radius="md",
                        withBorder=True,
                        style={"overflow": "hidden"},
                    ),
                    span=8,
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            info_panel(
                                "Active state (map → Python)",
                                dmc.Code(
                                    id="lc-out",
                                    block=True,
                                    style={
                                        "minHeight": "84px",
                                        "whiteSpace": "pre-wrap",
                                    },
                                ),
                            ),
                            info_panel(
                                "Python → control",
                                dmc.Stack(
                                    [
                                        dmc.Text(
                                            "Pick a base from a Python callback:",
                                            size="sm",
                                            c="dimmed",
                                        ),
                                        dmc.Group(
                                            [
                                                dmc.Button(
                                                    "Light",
                                                    id="lc-btn-light",
                                                    size="xs",
                                                    variant="light",
                                                    color="gray",
                                                ),
                                                dmc.Button(
                                                    "Dark",
                                                    id="lc-btn-dark",
                                                    size="xs",
                                                    variant="light",
                                                    color="dark",
                                                ),
                                                dmc.Button(
                                                    "OSM",
                                                    id="lc-btn-osm",
                                                    size="xs",
                                                    variant="light",
                                                    color="blue",
                                                ),
                                            ]
                                        ),
                                        dmc.Text(
                                            "Toggle an overlay from Python:",
                                            size="sm",
                                            c="dimmed",
                                            mt="sm",
                                        ),
                                        dmc.Group(
                                            [
                                                dmc.Button(
                                                    "Toggle Buoy radius",
                                                    id="lc-btn-buoy",
                                                    size="xs",
                                                    variant="light",
                                                    color="orange",
                                                ),
                                                dmc.Button(
                                                    "Toggle Sensors",
                                                    id="lc-btn-sensors",
                                                    size="xs",
                                                    variant="light",
                                                    color="grape",
                                                ),
                                            ]
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
        code_panel("dl2.LayersControl pattern", CODE),
    ],
    gap="md",
)


# Two-way: map -> Python (state readout) ----------------------------------------
@callback(
    Output("lc-out", "children"),
    Input("lc", "activeBase"),
    Input("lc", "activeOverlays"),
)
def show_active(base, overlays):
    return f"activeBase:\n  {base}\nactiveOverlays:\n  {overlays}"


# Two-way: Python -> map (button-driven base switch) ----------------------------
@callback(
    Output("lc", "activeBase", allow_duplicate=True),
    Input("lc-btn-light", "n_clicks"),
    prevent_initial_call=True,
)
def to_light(_):
    return "Light"


@callback(
    Output("lc", "activeBase", allow_duplicate=True),
    Input("lc-btn-dark", "n_clicks"),
    prevent_initial_call=True,
)
def to_dark(_):
    return "Dark"


@callback(
    Output("lc", "activeBase", allow_duplicate=True),
    Input("lc-btn-osm", "n_clicks"),
    prevent_initial_call=True,
)
def to_osm(_):
    return "OSM"


def _toggle(current, name):
    current = list(current or [])
    return [o for o in current if o != name] if name in current else current + [name]


@callback(
    Output("lc", "activeOverlays", allow_duplicate=True),
    Input("lc-btn-buoy", "n_clicks"),
    State("lc", "activeOverlays"),
    prevent_initial_call=True,
)
def toggle_buoy(_, current):
    return _toggle(current, "Buoy radius")


@callback(
    Output("lc", "activeOverlays", allow_duplicate=True),
    Input("lc-btn-sensors", "n_clicks"),
    State("lc", "activeOverlays"),
    prevent_initial_call=True,
)
def toggle_sensors(_, current):
    return _toggle(current, "Sensors")
