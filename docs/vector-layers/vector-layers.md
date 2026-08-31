---
name: "Vector Layers"
description: "Polygon / Polyline / Circle / CircleMarker."
endpoint: "/vector-layers"
package: dash-leaflet2
category: "Layers"
icon: "tabler:vector-triangle"
lastmod: 2026-07-28
---

.. llms_copy::Vector Layers

.. toc::

### Overview

This page demonstrates Vector Layers.

### Live demo

.. exec::docs.vector-layers.example
    :code: false

### Vector primitives

```javascript
new leaflet.Polygon([[40.7780,-74.0438],[40.7888,-73.9513],[40.7385,-73.9276]],
    {color: "#2f9e44", fillOpacity: 0.25}).addTo(map);
new leaflet.Polyline([[40.7583,-74.0319],[40.7682,-73.9513]], {weight: 4}).addTo(map);
new leaflet.Circle([40.7286,-73.9738], {radius: 1500}).addTo(map);       // metres
new leaflet.CircleMarker([40.7430,-74.0094], {radius: 10}).addTo(map); // pixels

layer.on("click", () => set_props("vec-store", {data: {shape: "polygon"}}));
```

### Source

.. source::docs/vector-layers/example.py
    :defaultExpanded: false
    :withExpandedButton: true
