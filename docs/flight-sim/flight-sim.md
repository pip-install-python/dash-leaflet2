---
name: "Flight Sim"
description: "single-player, keyboard + touch-joystick, rAF physics loop."
endpoint: "/flight-sim"
package: dash-leaflet2
category: "Rotation & Sims"
icon: "tabler:plane"
---

.. llms_copy::Flight Sim

.. toc::

### Overview

Rotation model (revised, matching DashEcommerce/pages/map/fly.py):

  * The MAP STAYS NORTH-UP — `bearing` is left at 0 on this page. The previous
    iteration rotated the camera with the heading; the user wanted the fly.py
    pattern instead, where the player gets the orientation cue from the SPRITE.
  * The MARKER ROTATES — `rotateWithMap=False` plus `rotationAngle = heading`
    drives the airplane sprite to face the direction of travel. The sprite is
    the top-down airplane PNG, intrinsically pointing UP (north) — so a
    rotationAngle of 90° = nose pointing east, 180° = south, etc.

  * The dl2.Map(bearing=…) machinery still EXISTS and the dl2-rotation-wrapper
    is still there — we just don't use it from this page. Rotation-basic still
    demonstrates the camera-rotation capability.

Controls

  * Keyboard (desktop): ArrowLeft/Right turn the plane, ArrowUp throttles,
    ArrowDown brakes, Space hard-stops, Cmd/Ctrl+Arrow pans the camera.
  * Touch joystick (mobile, auto-shown via @media (hover: none)
    and (pointer: coarse)): pushing horizontally turns, pushing vertically
    throttles/brakes — same semantic as the arrow keys but as a continuous
    analog signal. Joystick state is read by the rAF tick alongside keyboard
    state, so both work simultaneously and either input alone is enough.

The rAF physics loop stays unchanged — frame-rate-independent integration,
self-throttling to display refresh, paused when the tab is hidden.

### Live demo

.. exec::docs.flight-sim.example
    :code: false

### Source

.. source::docs/flight-sim/example.py
    :defaultExpanded: false
    :withExpandedButton: true
