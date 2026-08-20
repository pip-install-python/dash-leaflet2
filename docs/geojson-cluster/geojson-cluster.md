---
name: "GeoJSON clustering"
description: "SuperCluster-backed point clustering for dl2.GeoJSON — cluster, pointToLayer, clusterToLayer, hideout, superClusterOptions."
endpoint: "/geojson-cluster"
package: dash-leaflet2
category: "Layers"
icon: "tabler:circles-relation"
lastmod: 2026-07-28
---

.. llms_copy::GeoJSON clustering

.. toc::

### Overview

dash-leaflet 1.x lets `GeoJSON` collapse dense point sets into clusters that
expand on zoom. dl2 now does the same — `dl2.GeoJSON(cluster=True, ...)` runs
the [SuperCluster](https://github.com/mapbox/supercluster) index that
dash-leaflet 1.x uses, and accepts the same customization hooks:

| Prop                  | What it does |
|-----------------------|--------------|
| `cluster`             | Turn clustering on/off. |
| `superClusterOptions` | `{radius, minPoints, maxZoom, minZoom, extent}` — tuning passed to SuperCluster. |
| `pointToLayer`        | JS function source `(feature, latlng, ctx) => layer` for individual points. |
| `clusterToLayer`      | JS function source `(feature, latlng, index, ctx) => layer` for cluster bubbles. |
| `hideout`             | `dict` passed to your JS as `ctx.hideout` — color maps, label dicts, anything. |
| `zoomToBoundsOnClick` | Click a cluster to fly the camera to fit its children. |

The JS function source is wrapped in `new Function(...)` at construction
time. `ctx` carries `{ hideout, leaflet, map }` so your function can build
any Leaflet 2 layer without depending on a global.

### Live demo

200 random "vessel positions" around San Diego, CA, colored by category. Pan
out and they collapse into glass bubbles; pan in and they expand. Click a
cluster and you fly to its children's bounding box.

.. exec::docs.geojson-cluster.example
    :code: false

### Source

.. source::docs/geojson-cluster/example.py
    :defaultExpanded: false
    :withExpandedButton: true
