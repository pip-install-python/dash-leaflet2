---
name: "Basic Rotation"
description: "`bearing` on dl2.Map + dl2.KeyboardControl"
endpoint: "/rotation-basic"
package: dash-leaflet2
category: "Rotation & Sims"
icon: "tabler:rotate-360"
lastmod: 2026-07-28
---

.. llms_copy::Basic Rotation

.. toc::

### Overview

The minimum-viable mirror of dash-leaflet's `rotation_basic.py`, adapted to
the dash-leaflet2 primitives we just added:

  * `dl2.Map(bearing=...)`        — CSS-rotated map pane
  * `dl2.KeyboardControl()`       — arrow keys rotate, Cmd/Ctrl+Arrow pans
  * `dl2.Marker(rotateWithMap=False)` — icon stays in a fixed SCREEN
    orientation (upright) while the map rotates around it. The opposite mode,
    `rotateWithMap=True`, is what flight-sim / walking-sim use for sprites
    that should rotate together with the world.

CAVEAT (documented in dl2.Map's docstring too): this is CSS rotation, not
coordinate-correct rotation. Tiles, markers, polygons render in the right
place visually; click-to-latlng resolution at non-zero bearing is OFF by
the rotation amount because Leaflet's hit-testing doesn't know we rotated.
For a basic showcase + flight/walking sims (camera-follow), this is fine.

### Live demo

.. exec::docs.rotation-basic.example
    :code: false

### The shape

.. source::docs/rotation-basic/example.py
    :region: map
    :caption: Pattern
    :defaultExpanded: true
    :withExpandedButton: false

### Source

.. source::docs/rotation-basic/example.py
    :defaultExpanded: false
    :withExpandedButton: true
