---
name: "ResizeObserver Sizing"
description: "no gray tiles in collapsible layouts."
endpoint: "/resize-observer"
package: dash-leaflet2
category: "v2 capabilities"
icon: "tabler:resize"
lastmod: 2026-07-28
---

.. llms_copy::ResizeObserver Sizing

.. toc::

### Overview

This page demonstrates ResizeObserver Sizing.

### Live demo

.. exec::docs.resize-observer.example
    :code: false

### It just works

```javascript
// Leaflet 2 observes its container with a ResizeObserver (trackResize,
// default ON). When the container changes size — opening a side panel, a tab,
// an accordion — the map re-renders itself. No more:
//     map.invalidateSize();   // the classic Leaflet 1 dance
const map = new leaflet.Map(el).setView([29.7589, -95.3677], 12);
```

### Source

.. source::docs/resize-observer/example.py
    :defaultExpanded: false
    :withExpandedButton: true
