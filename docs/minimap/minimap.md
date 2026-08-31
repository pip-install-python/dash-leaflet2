---
name: "MiniMap"
description: "small overview map pinned to a corner of the main map."
endpoint: "/minimap"
package: dash-leaflet2
category: "Controls (compiled dl2.*)"
icon: "tabler:map-pin"
lastmod: 2026-07-28
---

.. llms_copy::MiniMap

.. toc::

### Overview

Demonstrates `dl2.MiniMap`, the native Leaflet 2 replacement for the leaflet-minimap
plugin (Leaflet-1-only). The corner toggle uses the standard class
`leaflet-control-minimap-toggle-display leaflet-control-minimap-toggle-display-<position>`
so existing CSS targeting those hooks keeps working. Two-way `minimized` prop —
the user's click round-trips to Python, and a Python callback can collapse/expand the
minimap from a button.

### Live demo

.. exec::docs.minimap.example
    :code: false

### The shape

.. source::docs/minimap/example.py
    :region: map
    :caption: dl2.MiniMap — placement + two-way toggle
    :defaultExpanded: true
    :withExpandedButton: false

### Source

.. source::docs/minimap/example.py
    :defaultExpanded: false
    :withExpandedButton: true
