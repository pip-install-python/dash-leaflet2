---
name: "Canvas Renderer"
description: "dense point clouds through one <canvas>."
endpoint: "/canvas-overlay"
package: dash-leaflet2
category: "v2 capabilities"
icon: "tabler:chart-dots"
lastmod: 2026-07-28
---

.. llms_copy::Canvas Renderer

.. toc::

### Overview

This page demonstrates Canvas Renderer.

### Live demo

.. exec::docs.canvas-overlay.example
    :code: false

### Canvas-backed markers

```javascript
// preferCanvas routes every CircleMarker through the Canvas renderer:
// one <canvas> instead of N SVG nodes — the substrate for live vessel
// positions, sensor swarms and heatmaps.
const map = new leaflet.Map(el, {preferCanvas: true}).setView(center, 11);
for (let i = 0; i < 8000; i++) {
    new leaflet.CircleMarker(points[i], {radius: 3, stroke: false}).addTo(group);
}
```

### Source

.. source::docs/canvas-overlay/example.py
    :defaultExpanded: false
    :withExpandedButton: true
