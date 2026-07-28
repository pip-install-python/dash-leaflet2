"""
GeoJSON clustering — limited working example.

200 random vessel-position points around Rockport, TX. The hideout dict ships a
{category: color} map into the JS pointToLayer so circles paint without a
Python round-trip. Slider on the right tunes superClusterOptions.radius live.
"""

import json
import random

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, callback, html
from dl2_shared import code_panel, header, info_panel

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
        lat = 28.02 + (rng.random() - 0.5) * 0.20
        lng = -97.05 + (rng.random() - 0.5) * 0.25
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

CODE = """dl2.GeoJSON(
    id="cluster-geo",
    data=feature_collection,                # 200 vessel points
    cluster=True,
    superClusterOptions={"radius": 80, "minPoints": 2, "maxZoom": 16},
    zoomToBoundsOnClick=True,
    hideout={"colors": {"fishing": "#4dabf7", "sailing": "#69db7c", ...}},
    pointToLayer='''
        function (feature, latlng, ctx) {
            const color = ctx.hideout.colors[feature.properties.category] || '#868e96';
            return new ctx.leaflet.CircleMarker(latlng, {radius: 6, color, fillOpacity: 0.85});
        }
    ''',
    clusterToLayer='''
        function (feature, latlng, index, ctx) {
            const count = feature.properties.point_count;
            // ... figure out the dominant category from the cluster's leaves,
            //     build a colored DivIcon
            return new ctx.leaflet.Marker(latlng, {icon: ...});
        }
    ''',
)"""


component = dmc.Stack(
    [
        header(
            "GeoJSON clustering",
            "200 vessel points around Rockport, TX. The hideout dict ships a "
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
                            center=[28.02, -97.05],
                            zoom=10,
                            style={"height": "60vh"},
                            children=[
                                dl2.TileLayer(),
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
        code_panel("dl2.GeoJSON with clustering", CODE),
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
