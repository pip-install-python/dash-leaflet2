---
name: "Compare Lab"
description: "stack, reorder and cross-fade tile overlays from a TreeViewPro popover."
endpoint: "/compare-lab"
package: dash-leaflet2
category: "Controls (compiled dl2.*)"
icon: "tabler:flip-horizontal"
---

.. llms_copy::Compare Lab

.. toc::

### Overview

A tileset **comparison** surface: a `dl2.EasyButton` opens a Mantine `Popover`
holding a MUI TreeViewPro, and every interaction in that tree reconciles a stack
of `dl2.TileLayer` overlays on the map underneath — visibility, per-layer
opacity, z-order and deletion.

The interesting part is the **reconciler**. Overlays are never unmounted and
remounted as the tree changes; a clientside callback diffs the desired state
against what is already on the map and mutates only what differs. That is what
keeps a slider drag smooth instead of tearing down and rebuilding a TileLayer on
every frame.

The overlays here are synthetic — coloured SVG tiles seeded by a button — so the
page is a self-contained demonstration of the pattern rather than a dependency on
any particular imagery source.

### What this page demonstrates

1. **Consistent initial state.** The tree shows Esri World Imagery checked at
   80 % opacity on first paint, *and* the layer is actually on the map. Getting
   this right means the store's initial value must agree with the tree's initial
   `selectedItems` — if the reducer is `prevent_initial_call=True` and the store
   says `source_visible: False` while the tree says checked, the layer will not
   appear until the user jiggles a control. Initialise both to the same truth.
2. **Light / dark basemap.** The basemap swaps between CARTO Positron and CARTO
   Dark Matter with the app shell's colour-scheme toggle, driven by a clientside
   callback so the change is instant.
3. **Multi-zoom overlays.** "Seed 3 fake gens" drops tiles at matching z14 / z15
   / z16 coordinates near Rockport, TX, so cross-zoom relationships line up and
   the association-by-zoom logic has something real to chew on.
4. **Every tree interaction wired** — selection toggles overlay visibility,
   sliders drive opacity, the kebab menu's Remove deletes both the tree leaf and
   its overlay, and items are reorderable to drive z-order.

### Live demo

.. exec::docs.compare-lab.example
    :code: false

### Source

.. source::docs/compare-lab/example.py
    :defaultExpanded: false
    :withExpandedButton: true
