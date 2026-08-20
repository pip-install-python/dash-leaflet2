---
name: "Walking Sim"
description: "top-down RPG-style walking with the full pirate-captain sprite"
endpoint: "/walking-sim"
package: dash-leaflet2
category: "Rotation & Sims"
icon: "tabler:walk"
lastmod: 2026-07-28
---

.. llms_copy::Walking Sim

### Overview

library. Uses all 4 animation types (idle / walking / running / jumping) across
all 8 compass directions.

## Model

  * **Map stays north-up.** Bearing isn't driven. Pan-only camera-follow keeps
    the character at viewport center as they move; the world doesn't spin
    around them.
  * **Sprite stays at viewport center, with NO `rotationAngle` transform.**
    The character "turns" by selecting a different directional sprite frame.
  * **8-way D-pad input.** Arrow keys are direct compass directions: ArrowUp
    = north, ArrowRight = east, ArrowUp+ArrowRight = north-east, etc. The
    touch joystick is read the same way — its angle becomes a heading, its
    magnitude becomes a speed throttle. (This replaces the prior turn-and-
    throttle scheme; the joystick angle naturally maps to direction and the
    8 sprite poses become reachable.)
  * **Animation state machine:**
       speed = 0                      → `idle`,    facing SOUTH (toward camera)
       0 < speed < 0.6 * MAX_SPEED    → `walking`, facing heading
       speed ≥ 0.6 * MAX_SPEED        → `running`, facing heading
       Space pressed                  → `jumping`, plays through once
                                         then returns to active state
  * **Heading → direction** is snapped to the nearest 45° (one of 8 buckets).

## Controls

  * Arrow keys (with combinations): walk in that compass direction
  * Space: jump
  * Cmd / Ctrl + Arrow: pan the camera away from the walker
  * Touch joystick (auto-shown on mobile): drag = walk in that direction at
    a magnitude-scaled speed
  * Click the top-right MiniMap to toggle WALK ↔ EXPLORE mode. Each toggle
    is animated with a smooth `map.flyTo()` — the walker NEVER teleports.
      - WALK: the rAF loop drives the character (this whole file's behavior).
        Minimap shows broad surrounding context (zoom-5), free-pan disabled.
      - EXPLORE: the rAF loop sits out — no input is read, no center is pushed.
        The map is a normal dl2 map (pan/zoom freely). The joystick is hidden.
        The minimap "inverses" — it now pins on the WALKER's last position at
        zoom+3 (a small "return-home" preview).
      - Entry (WALK → EXPLORE): we snapshot the walker's position + the
        walking zoom, then flyTo the walker at a pulled-back zoom so the
        user can scout.
      - Exit (EXPLORE → WALK): flyTo BACK to that snapshot — the walker
        stays put exactly where they were (you can't use this as a
        teleport). The rAF's per-frame `center: pos` push is suppressed
        for the flyTo's duration so it can't snap-jump mid-glide.

## Tile stack

  * Main map: **Esri World Imagery** (satellite, 100%) with an **Esri
    NatGeo World Map** overlay on top at 50%. The NatGeo overlay's tiles
    cap at z16 (`maxZoom=16`) — it's invisible at walking zoom (18) where
    the satellite carries the scene, and progressively blends in as the
    EXPLORE flyTo pulls back to wider context.
  * MiniMap: **Esri World Street Map** — a flat reference map that reads
    well in a 160×160 thumbnail at any zoom level.

### Live demo

.. exec::docs.walking-sim.example
    :code: false

### Source

.. source::docs/walking-sim/example.py
    :defaultExpanded: false
    :withExpandedButton: true
