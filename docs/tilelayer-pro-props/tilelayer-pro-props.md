---
name: "TileLayer pro props"
description: "minZoom, bounds, errorTileUrl, zIndex, subdomains, detectRetina, tms — the dash-leaflet 1.x TileLayer surface ported to dl2."
endpoint: "/tilelayer-pro-props"
package: dash-leaflet2
category: "Layers"
icon: "tabler:map-2"
lastmod: 2026-07-28
---

.. llms_copy::TileLayer pro props

.. toc::

### Overview

Until now `dl2.TileLayer` accepted only `url`, `attribution`, `maxZoom`,
`maxNativeZoom`, and `opacity` — the bare minimum to paint a basemap. This
release fills in the rest of the dash-leaflet 1.x surface that downstream
projects (e.g. SailsBoard's harbor map) depend on:

| Prop            | What it does |
|-----------------|--------------|
| `minZoom`       | Lower zoom bound; below this Leaflet stops requesting tiles. |
| `bounds`        | `[[s,w],[n,e]]` — Leaflet skips tile requests outside this box (cheaper than server-side 404s). |
| `errorTileUrl`  | URL of the image painted in place of any 404 tile. A 1×1 transparent PNG hides them. |
| `zIndex`        | Stacking order across multiple tile layers (highest wins). |
| `subdomains`    | Substituted into the `{s}` placeholder in the URL template. |
| `detectRetina`  | Request 2× tiles on hi-DPI displays. |
| `tms`           | Y-flip for TMS-shaped pyramids. |

### Live demo

.. exec::docs.tilelayer-pro-props.example
    :code: false

### Source

.. source::docs/tilelayer-pro-props/example.py
    :defaultExpanded: false
    :withExpandedButton: true
