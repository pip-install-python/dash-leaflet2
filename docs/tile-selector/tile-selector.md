---
name: "Tile Selector"
description: "pick map tiles by clicking or shift-dragging, and round-trip them to Python."
endpoint: "/tile-selector"
package: dash-leaflet2
category: "Controls (compiled dl2.*)"
icon: "tabler:grid-4x4"
---

.. llms_copy::Tile Selector

.. toc::

### Overview

`dl2.TileSelector` is a map **control** that turns the map into a tile picker.
While it is armed the cursor becomes a crosshair, a dashed outline tracks the
tile under the pointer at the current zoom, and:

- **click** a tile to add or remove it from the selection
- **shift-drag** a box to capture every tile inside it

Place it as a child of `dl2.Map`, anywhere among the other layers.

### The data boundary

Each selected tile round-trips to Python as a dict:

```python
{
    "z": 11, "x": 470, "y": 843,
    "url": "https://tile.openstreetmap.org/11/470/843.png",
    "bounds": [south, west, north, east],
}
```

`tileUrl` decides which template those `url` values are built from — it does
**not** have to match the `dl2.TileLayer` you are displaying. The demo below
renders CARTO light tiles but hands back OpenStreetMap PNG URLs, which is the
usual shape when the map is a picker for some other tileset.

Selections are keyed by `z/x/y`, so panning and zooming never lose them.

### Props

| Prop | Type | Default | What it does |
|------|------|---------|--------------|
| `selectedTiles` | list of dicts | `[]` | The selection. **`[MUTABLE]`** — an output (user clicks) *and* an input (write `[]` to clear). |
| `tileUrl` | string | OSM `{z}/{x}/{y}` | Template the returned `url` values are built from. |
| `position` | string | `'topleft'` | `topleft` / `topright` / `bottomleft` / `bottomright`. |
| `hoverColor` | string | `'#fa5252'` | Colour of the dashed outline under the cursor. |
| `selectedColor` | string | `'#228be6'` | Stroke and fill of selected-tile rectangles and the box-drag preview. |

Because `selectedTiles` is `[MUTABLE]`, a plain callback both reads the user's
picks and pushes new state back — the Clear button in the demo is one line.

### Live demo

.. exec::docs.tile-selector.example
    :code: false

### Source

.. source::docs/tile-selector/example.py
    :defaultExpanded: false
    :withExpandedButton: true
