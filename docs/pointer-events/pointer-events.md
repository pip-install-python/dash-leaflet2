---
name: "Pointer Events"
description: "Leaflet 2's headline change."
endpoint: "/pointer-events"
package: dash-leaflet2
category: "v2 capabilities"
icon: "tabler:pointer"
lastmod: 2026-07-28
---

.. llms_copy::Pointer Events

.. toc::

### Overview

This page demonstrates Pointer Events.

### Live demo

.. exec::docs.pointer-events.example
    :code: false

### The v2 pointer API

```javascript
// v2 fires POINTER events; the old mousemove/mousedown are gone.
map.on("pointermove", (e) => {
    const oe = e.originalEvent;        // a native PointerEvent
    console.log(oe.pointerType,        // "mouse" | "pen" | "touch"
                oe.pressure,           // 0..1 (real for a stylus)
                oe.tiltX, oe.tiltY,    // pen tilt
                e.latlng);             // geo coordinate
});
```

### Source

.. source::docs/pointer-events/example.py
    :defaultExpanded: false
    :withExpandedButton: true
