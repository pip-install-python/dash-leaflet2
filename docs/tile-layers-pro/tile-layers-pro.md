---
name: "Tile Layers (Pro)"
description: "EasyButton + Popover + MultiSelect + TreeViewPro."
endpoint: "/tile-layers-pro"
package: dash-leaflet2
category: "Controls (compiled dl2.*)"
icon: "tabler:layers-difference"
---

.. llms_copy::Tile Layers (Pro)

.. toc::

### Overview

The SailsBoard `create_layers_card` pattern, rebuilt against dl2 and the
no-key, no-payment tile catalog ported into `pages/_tile_catalog.py`.

  * Click the EasyButton (📚 top-left) → DMC Popover opens beside it.
  * Inside the popover:
      - `dmc.MultiSelect` lists every provider in the catalog, each row
        rendered with a tiny rotating cube preview (renderTileCubeFace
        in assets/tile_cube.js).
      - `dash_mui_charts.TreeViewPro` shows the active stack — one
        "Active tilesets" group, one leaf per slug, with an opacity
        slider and a kebab menu (Show info / Remove layer).
  * Single source of truth: `dcc.Store(id="tlp-state")` shaped
        `{"order": [slug, …], "sliders": {slug: 0..100}}`.

Add / remove / reorder / opacity changes all rewrite the Store; one
output callback derives the Map's `LayerGroup` children + the
`renderoption` cube payload from it.

The base layer (`esri_world_imagery`) is pinned at the bottom of the
stack and excluded from the MultiSelect — kebab "Remove layer" is a
no-op on it, so the map can never end up empty.

### Live demo

.. exec::docs.tile-layers-pro.example
    :code: false

### Source

.. source::docs/tile-layers-pro/example.py
    :defaultExpanded: false
    :withExpandedButton: true
