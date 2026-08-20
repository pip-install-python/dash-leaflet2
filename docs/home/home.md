---
name: "Home"
description: "Leaflet 2 (alpha) mapping components for Plotly Dash 4, without react-leaflet."
endpoint: "/"
package: dash-leaflet2
category: "Start here"
icon: "tabler:home"
lastmod: 2026-08-01
---

.. llms_copy::Home

.. toc::

# dash-leaflet2 — Leaflet 2 maps for Dash

> **`dash-leaflet2`** wraps **Leaflet 2 core directly** — no react-leaflet — and
> ships it as real Dash components. By [Pip Install Python](https://github.com/2plotai).

### Overview

`dash-leaflet` is frozen on react-leaflet, which has no Leaflet 2 line, so it
cannot move past Leaflet 1.9. This library skips that abstraction entirely and
drives Leaflet 2 core itself, which is what puts v2's headline features inside
reach of a Python callback:

- **Unified Pointer Events** — one event model for mouse, touch and stylus, with
  `pointerType`, `pressure` and `tiltX` / `tiltY` reaching your callbacks
- **`BlanketOverlay` canvas / WebGL layers** — your own renderer across the
  whole viewport, instead of the DOM layer system
- **ES6-class subclassing** — extend a Leaflet 2 class and mount the result
- **`ResizeObserver` sizing** — no grey tiles for a map born in a hidden tab
- **Map rotation** — `bearing` as a first-class, two-way prop

The demo below is the whole claim in one page: Leaflet `2.0.0-alpha.1`,
rendering inside Dash 4, with no JavaScript build step.

### Watch the introduction

[Dash Leaflet 2.0: Drone Tracking, Image Overlays & Map Packages in
Python](https://youtu.be/Wlmw98JrJZI) — drone tracking, image overlays and map
packages, built with this library.

.. exec::docs.home.video
    :code: false
    :border: false

### Live demo

.. exec::docs.home.example
    :code: false

### Source

.. source::docs/home/example.py
    :defaultExpanded: false
    :withExpandedButton: true
