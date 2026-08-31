---
name: "ES6 Subclassing"
description: "custom Control + a BlanketOverlay canvas layer."
endpoint: "/subclassing"
package: dash-leaflet2
category: "v2 capabilities"
icon: "tabler:hierarchy"
lastmod: 2026-07-28
---

.. llms_copy::ES6 Subclassing

.. toc::

### Overview

This page demonstrates ES6 Subclassing.

### Live demo

.. exec::docs.subclassing.example
    :code: false

### Extending Leaflet 2 with ES6 classes

```javascript
// v2 uses standard ES6 classes — no more L.Class.extend.

class CenterControl extends leaflet.Control {        // custom control
    onAdd(map) {
        const div = leaflet.DomUtil.create("div", "dl2-ctl");
        map.on("move zoom", () => div.textContent = map.getCenter());
        return div;
    }
}
new CenterControl({position: "topright"}).addTo(map);

class GlowLayer extends leaflet.BlanketOverlay {     // custom canvas renderer
    _initContainer() { this._container = leaflet.DomUtil.create("canvas"); }
    _onSettled() {                                   // re-paint after each settle
        for (const p of this._points) {
            const lp = this._map.latLngToLayerPoint([p.lat, p.lng]);
            // …draw a radial glow at (lp - this._bounds.min)…
        }
    }
}
new GlowLayer(sensors).addTo(map);
```

### Source

.. source::docs/subclassing/example.py
    :defaultExpanded: false
    :withExpandedButton: true
