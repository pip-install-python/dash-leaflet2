---
name: "Map pro props"
description: "minZoom, maxZoom, maxBounds, zoomControl, keyboard — the dash-leaflet 1.x Map options ported to dl2."
endpoint: "/map-pro-props"
package: dash-leaflet2
category: "Layers"
icon: "tabler:viewport-narrow"
lastmod: 2026-07-28
---

.. llms_copy::Map pro props

.. toc::

### Overview

`dl2.Map` previously exposed only `center`, `zoom`, `bearing`, `viewport`,
`preferCanvas`, and `attributionControl`. This release adds the remaining
constraint / interaction props that dash-leaflet 1.x exposed:

| Prop              | What it does |
|-------------------|--------------|
| `minZoom`         | Lower zoom bound applied by the map (largest of map.minZoom and any TileLayer.minZoom wins). |
| `maxZoom`         | Upper zoom bound applied by the map. |
| `maxBounds`       | `[[s,w],[n,e]]` — pan beyond the edges bounces back to the box. |
| `zoomControl`     | Show the built-in `+/-` zoom buttons. Constructor-only. |
| `keyboard`        | Arrow-key panning + `+`/`-` zooming. |
| `dragging`        | Pointer drag-pan. |
| `scrollWheelZoom` | Mouse-wheel zoom. |
| `doubleClickZoom` | Double-click zoom-in. |
| `boxZoom`         | Shift-drag box-zoom selection. |
| `pinchZoom`       | Touch pinch-zoom (v2's name for v1's `touchZoom`). |
| `tapHold`         | Mobile-safari long-press emulation (constructor-only). |

Every interaction-handler prop is two-way and `[MUTABLE]` — a Dash callback can
disable scroll-wheel zoom for a single panel mode, lock dragging while a
walkthrough plays, and so on.

### Live demo

.. exec::docs.map-pro-props.example
    :code: false

### The shape

.. source::docs/map-pro-props/example.py
    :region: map
    :caption: Map with the new pro props
    :defaultExpanded: true
    :withExpandedButton: false

### Source

.. source::docs/map-pro-props/example.py
    :defaultExpanded: false
    :withExpandedButton: true
