---
name: "TextMarker"
description: "Editable, draggable, styleable text placed on the map like a Marker — drag to move, double-click to edit, on-canvas resize/rotate handles, and a style toolbar; round-trips position/text/rotation/fontSize/color back to Dash."
endpoint: "/text-marker"
package: dash-leaflet2
category: "Markers"
icon: "mdi:format-text"
lastmod: 2026-07-28
---

.. llms_copy::TextMarker

.. toc::

### Overview

`dl2.TextMarker` is editable, draggable, styleable text anchored to a `[lat, lng]` — used
exactly like a `dl2.Marker`. Under the hood it is a Leaflet 2 `Marker` whose icon is a
content-sized, optionally-`contentEditable` text box, so it pans and zooms with the basemap and
behaves like a first-class map feature. It closes the "captions can't live on the map" gap from
the `text-caption-marker-proposal` hand-off.

| Interaction | Result |
|---|---|
| **Drag** the label | moves it; writes `position` back (+ bumps `n_drags`) |
| **Double-click** | inline-edit the text; commit on blur / Enter writes `text` back (+ `n_edits`) |
| **Resize handle** (corner) | scales `fontSize` |
| **Rotate handle** (top) | sets `rotation` (hold Shift to snap to 15°) |
| **Style toolbar** (while selected) | font family / size, bold / italic, text & background color, rotation — each round-trips to Dash |
| Click the label / empty map | toggles `selected` (two-way, so a host can drive selection) |

When `position` is omitted the label spawns at the center of the current viewport and writes
that position back, so you can drop a caption with no coordinates and read where it landed.

The white **anchor dot** (which also doubles as the resize grip) is drawn at the chosen
`anchor` — pick `bottom` and it sits at the bottom-center, `top-left` and it sits at the
top-left, etc. — so you can always see where the label is pinned. `center` is special-cased
to the bottom-right corner so the dot never covers the text.

Two size models via `scaleWithZoom`:

- `False` (default) — a constant screen-size HUD caption: `fontSize` is literal px at every
  zoom (like a Tooltip).
- `True` — geographic sizing: the on-screen size grows/shrinks by `2^(zoom − referenceZoom)`,
  so the caption keeps a fixed *ground* footprint as the camera flies (like a polygon's edge).

### Live demo

Drag the "Fisherman's Wharf" caption, double-click to retype it, and use the on-canvas
handles + glass toolbar — or drive every prop from the right column. The red "PIER 39" label
has `scaleWithZoom=True`, so zoom in/out to watch it hold its ground size. The `T` tool in the
top-right toolbar is the `EditControl` `text` tool (Route B): click it, click the map, and type —
the caption is added to `EditControl.geojson` as a `kind:"text"` Point.

.. exec::docs.text-marker.example
    :code: false

### Route B — the EditControl `text` tool

`dl2.EditControl` gains a `text` tool alongside `marker` / `polyline` / `polygon` / …. Picking it
and clicking the map drops an inline-editable caption that participates in the same `geojson`
round-trip as every other shape — a GeoJSON `Point` carrying the caption + style in
`properties`:

```json
{
  "type": "Feature",
  "geometry": { "type": "Point", "coordinates": [-122.41, 37.808] },
  "properties": {
    "kind": "text", "text": "Fisherman's Wharf",
    "color": "#111827", "fontSize": 18,
    "fontFamily": "system-ui, sans-serif", "fontWeight": 600
  }
}
```

In edit mode the caption is draggable and double-click re-opens the inline editor. Enable it
per-tool with `draw={"text": True}` (and disable the others to get a text-only toolbar).

### The shape

.. source::docs/text-marker/example.py
    :region: minimal
    :caption: A caption that places, styles, and round-trips like a Marker
    :defaultExpanded: true
    :withExpandedButton: false

### Source

.. source::docs/text-marker/example.py
    :defaultExpanded: false
    :withExpandedButton: true
