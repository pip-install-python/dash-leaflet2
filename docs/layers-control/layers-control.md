---
name: "Layers Control"
description: "the compiled dl2.LayersControl component."
endpoint: "/layers-control"
package: dash-leaflet2
category: "Controls (compiled dl2.*)"
icon: "tabler:stack-2"
---

.. llms_copy::Layers Control

.. toc::

### Overview

Demonstrates the real Python API (this is what users would write), not the JS DEMO style
used by the other showcase pages. Two-way: the UI radios/checkboxes write activeBase /
activeOverlays back to Python; Python callbacks also push those props to flip the control.

### Live demo

.. exec::docs.layers-control.example
    :code: false

### Source

.. source::docs/layers-control/example.py
    :defaultExpanded: false
    :withExpandedButton: true
