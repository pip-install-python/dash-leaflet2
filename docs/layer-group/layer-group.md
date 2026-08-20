---
name: "LayerGroup & FeatureGroup"
description: "Bundle N layers so they can be added, removed, toggled, or measured as one — wraps Leaflet 2's LayerGroup / FeatureGroup."
endpoint: "/layer-group"
package: dash-leaflet2
category: "Layers"
icon: "tabler:stack-2"
lastmod: 2026-07-28
---

.. llms_copy::LayerGroup & FeatureGroup

.. toc::

### Overview

`dl2.LayerGroup` and `dl2.FeatureGroup` mirror Leaflet's container primitives:

| Component   | When to use it |
|-------------|----------------|
| `LayerGroup`   | Bundle any layers so a single `addTo` / `remove` shows or hides the whole set. Pair with `dl2.Overlay` inside a `LayersControl` to toggle the entire group as one entry. |
| `FeatureGroup` | Like LayerGroup, but extends `leaflet.FeatureGroup` — also emits a combined `geojson` (vector children), a single `n_clicks` no matter which child was clicked, and an `n_layers` counter that bumps on add/remove. Pair with `EditControl` when you want to ship the user's drawings out of the map as one piece. |

Both components also accept any layer as a child via the same React context that
`<Map>` uses — children attach to the group via a proxy map instead of the real
map directly.

### Live demo

A switch toggles a `LayerGroup` of three markers on/off. Below it, a
`FeatureGroup` aggregates four shapes and reports its combined geojson and
the bumping `n_clicks` counter.

.. exec::docs.layer-group.example
    :code: false

### Source

.. source::docs/layer-group/example.py
    :defaultExpanded: false
    :withExpandedButton: true
