---
name: "Events → Python"
description: "full JS→Python round-trip via dcc.Store."
endpoint: "/events-python"
package: dash-leaflet2
category: "Dash integration"
icon: "tabler:bolt"
lastmod: 2026-07-28
---

.. llms_copy::Events → Python

.. toc::

### Overview

This page demonstrates Events → Python.

### Live demo

.. exec::docs.events-python.example
    :code: false

### set_props bridge

```javascript
// JS -> Python bridge uses Dash 4's clientside set_props into a dcc.Store,
// which an ordinary @callback then reads.
map.on("moveend zoomend", () => {
    const c = map.getCenter();
    window.dash_clientside.set_props("ev-store",
        {data: {lat: c.lat, lng: c.lng, zoom: map.getZoom(),
                bounds: map.getBounds()}});
});
map.on("click", (e) => window.dash_clientside.set_props(
    "ev-click-store", {data: {lat: e.latlng.lat, lng: e.latlng.lng}}));
```

### Source

.. source::docs/events-python/example.py
    :defaultExpanded: false
    :withExpandedButton: true
