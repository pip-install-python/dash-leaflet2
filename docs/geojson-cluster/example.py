"""
GeoJSON clustering — limited working example.

200 random vessel-position points around San Diego, CA. The hideout dict ships a
{category: color} map into the JS pointToLayer so circles paint without a
Python round-trip. Slider on the right tunes superClusterOptions.radius live.
"""

import json
import random

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, callback, html
from dl2_tiles import OCEAN, register_theme_swap
from dl2_locations import SAN_DIEGO
from dl2_shared import header, info_panel

# Basemap pair for this page — dl2_tiles owns the light/dark wiring.
TILES = OCEAN

CATEGORIES = ["fishing", "sailing", "ferry", "cargo"]
COLORS = {
    "fishing": "#4dabf7",
    "sailing": "#69db7c",
    "ferry": "#ffd43b",
    "cargo": "#ff8787",
}


def make_points(n=200, seed=42):
    rng = random.Random(seed)
    features = []
    for i in range(n):
        # Scatter in kilometres, not degrees: a fixed degree jitter would
        # produce an east-west-stretched blob at low latitudes and a
        # squashed one up north. +/- 11 km N-S by +/- 13 km E-W.
        lat, lng = SAN_DIEGO.at(
            north_km=(rng.random() - 0.5) * 22.2,
            east_km=(rng.random() - 0.5) * 25.0,
        )
        category = rng.choice(CATEGORIES)
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
                "properties": {
                    "id": i,
                    "category": category,
                    "name": f"{category.title()} #{i}",
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


POINTS = make_points()

# JS source — `new Function('return (' + source + ')')()` is called per prop.
POINT_TO_LAYER = """
function (feature, latlng, ctx) {
    var color = (ctx.hideout && ctx.hideout.colors)
        ? ctx.hideout.colors[feature.properties.category] || '#868e96'
        : '#228be6';
    return new ctx.leaflet.CircleMarker(latlng, {
        radius: 6,
        color: color,
        weight: 1.5,
        fillColor: color,
        fillOpacity: 0.85
    });
}
"""

CLUSTER_TO_LAYER = """
function (feature, latlng, index, ctx) {
    var count = feature.properties.point_count;
    var leaves = index.getLeaves(feature.properties.cluster_id, Infinity);
    var counts = {};
    for (var i = 0; i < leaves.length; i++) {
        var c = leaves[i].properties.category;
        counts[c] = (counts[c] || 0) + 1;
    }
    var top = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; })[0];
    var color = (ctx.hideout && ctx.hideout.colors && ctx.hideout.colors[top]) || '#228be6';
    var size = count >= 100 ? 56 : count >= 10 ? 44 : 36;
    var html =
        '<div class="dl2-cluster-bubble" style="background:' + color
        + 'cc;color:#fff;font-weight:700;">' + count + '</div>';
    return new ctx.leaflet.Marker(latlng, {
        icon: new ctx.leaflet.DivIcon({
            html: html,
            className: '',
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2]
        })
    });
}
"""

component = dmc.Stack(
    [
        header(
            "GeoJSON clustering",
            "200 vessel points around San Diego, CA. The hideout dict ships a "
            "color map into the JS — clusters take the dominant category's "
            "color. Pan/zoom and the SuperCluster index re-renders for the "
            "new viewport.",
            badge="dl2.GeoJSON",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dl2.Map(
                            id="cl-map",
                            center=SAN_DIEGO.center,
                            zoom=10,
                            style={"height": "60vh"},
                            children=[
                                dl2.TileLayer(id="cl-tile", **TILES.kwargs("light")),
                                # region map
                                dl2.GeoJSON(
                                    id="cl-geo",
                                    data=POINTS,
                                    cluster=True,
                                    superClusterOptions={
                                        "radius": 80,
                                        "minPoints": 2,
                                        "maxZoom": 16,
                                    },
                                    zoomToBoundsOnClick=True,
                                    hideout={"colors": COLORS},
                                    pointToLayer=POINT_TO_LAYER,
                                    clusterToLayer=CLUSTER_TO_LAYER,
                                ),
                                # endregion
                            ],
                        ),
                        shadow="sm",
                        radius="md",
                        withBorder=True,
                        style={"overflow": "hidden", "height": "60vh"},
                    ),
                    span=8,
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            info_panel(
                                "Cluster radius (px)",
                                dmc.Slider(
                                    id="cl-radius",
                                    min=20,
                                    max=160,
                                    step=10,
                                    value=80,
                                    marks=[
                                        {"value": 20, "label": "20"},
                                        {"value": 80, "label": "80"},
                                        {"value": 160, "label": "160"},
                                    ],
                                ),
                            ),
                            info_panel(
                                "Categories",
                                html.Div(
                                    [
                                        dmc.Group(
                                            [
                                                html.Div(
                                                    style={
                                                        "width": "14px",
                                                        "height": "14px",
                                                        "borderRadius": "50%",
                                                        "background": COLORS[c],
                                                    }
                                                ),
                                                dmc.Text(c.title(), size="sm"),
                                            ],
                                            gap="xs",
                                        )
                                        for c in CATEGORIES
                                    ]
                                ),
                            ),
                            info_panel(
                                "Last click",
                                dmc.Code(id="cl-click-readout", block=True, children="(click a marker or cluster)"),
                            ),
                        ],
                        gap="md",
                    ),
                    span=4,
                ),
            ],
            gutter="md",
        ),
    ],
    gap="md",
)


@callback(Output("cl-geo", "superClusterOptions"), Input("cl-radius", "value"))
def update_radius(r):
    return {"radius": int(r or 80), "minPoints": 2, "maxZoom": 16}


@callback(Output("cl-click-readout", "children"), Input("cl-geo", "clickFeature"))
def show_click(feat):
    if not feat:
        return "(click a marker or cluster)"
    return json.dumps(feat, indent=2)


# Light/dark basemap, driven off the color-scheme store.
register_theme_swap("cl-tile", TILES)
