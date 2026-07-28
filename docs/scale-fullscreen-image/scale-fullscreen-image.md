---
name: "Scale, FullScreen, ImageOverlay"
description: "Three small controls / overlays that close the remaining dl1 gaps: ScaleControl, FullScreenControl, ImageOverlay."
endpoint: "/scale-fullscreen-image"
package: dash-leaflet2
category: "Controls (compiled dl2.*)"
icon: "tabler:tool"
---

.. llms_copy::Scale, FullScreen, ImageOverlay

.. toc::

### Overview

Three thin wrappers around Leaflet 2 building blocks that dash-leaflet 1.x exposed
and dl2 didn't yet:

| Component         | Wraps |
|-------------------|-------|
| `ScaleControl`    | `Control.Scale` — metric / imperial scale bar in any corner. |
| `FullScreenControl` | A small `Control` over the browser's `requestFullscreen()` API. Reports `fullscreen` and `n_clicks` back to Dash. |
| `ImageOverlay`    | `ImageOverlay` — drape one image onto a geographic bounding box. Two-way `url`, `bounds`, `opacity`, `zIndex`. With `editable` it gains a TextMarker-style transform control system. |

### Editable ImageOverlay (resize · rotate · move)

Set `editable=True` and the overlay becomes a draggable, resizable, rotatable object — the
same control language as `dl2.TextMarker`:

- **Click** the image to select it (chrome + handles appear).
- **Drag** the body to move it (translates `bounds`).
- **Drag the corner dot** to resize — the bounds scale about the `anchor`, which stays pinned.
  That dot is also the **white anchor marker**: it sits at whichever `anchor` you choose
  (`center` defaults to the bottom-right corner).
- **Drag the top dot** to rotate. Rotation is a CSS-transform visual rotation pivoting at the
  `anchor` — Leaflet's `ImageOverlay` has no native geographic rotation, so `bounds` stay
  axis-aligned and only the rendered pixels turn.

`bounds`, `rotation`, and `selected` round-trip back to Dash (plus an `n_transforms` counter).

### Live demo

A single map with all three pieces: scale bar bottom-left, fullscreen button top-left, and an
editable image overlay — select it, then drag to move, resize from the corner/anchor dot, and
rotate from the top dot. Change the anchor pivot and watch the white dot follow.

.. exec::docs.scale-fullscreen-image.example
    :code: false

### Source

.. source::docs/scale-fullscreen-image/example.py
    :defaultExpanded: false
    :withExpandedButton: true
