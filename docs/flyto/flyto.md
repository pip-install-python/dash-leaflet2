---
name: "FlyTo"
description: "smooth viewport transitions, modelled on dash-leaflet's `viewport` API."
endpoint: "/flyto"
package: dash-leaflet2
category: "Dash integration"
icon: "tabler:plane-departure"
---

.. llms_copy::FlyTo

.. toc::

### Overview

`dl2.Map.flyTo` is a [MUTABLE] trigger prop. Setting it dispatches the matching
Leaflet 2 method (`flyTo` / `setView` / `panTo` / `fitBounds` / `flyToBounds` /
`panInsideBounds`). The `flyTo` and `flyToBounds` transitions give the smooth
glide-and-zoom motion the old dash-leaflet doc page demos with "Fly to Paris".

Companion events:
  - `n_movestart` increments when a transition BEGINS
  - `n_moveend`   increments when it COMPLETES
  - `viewport`    is the existing READONLY state read-back

A "FLYING…" HUD is the canonical use of the counter pair — show it while
`n_movestart > n_moveend`, otherwise show "IDLE".

Trigger payload shape:
    {
        'transition': 'flyTo',          # or setView, panTo, fitBounds, ...
        'center': [lat, lng],
        'zoom': 11,
        'options': {'duration': 2.5, 'easeLinearity': 0.25},
        'n_clicks': bump_me,            # required — bump per call to retrigger
    }

### Live demo

.. exec::docs.flyto.example
    :code: false

### Source

.. source::docs/flyto/example.py
    :defaultExpanded: false
    :withExpandedButton: true
