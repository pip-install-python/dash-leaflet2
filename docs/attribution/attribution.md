---
name: "Attribution"
description: "explicit control over the attribution box."
endpoint: "/attribution"
package: dash-leaflet2
category: "Dash integration"
icon: "tabler:license"
---

.. llms_copy::Attribution

.. toc::

### Overview

Mirrors dash-leaflet 1.x: pass `attributionControl=False` to the Map to suppress
Leaflet 2's built-in attribution control, then add a `dl2.AttributionControl`
as a child to position it explicitly and customize the prefix.

  • `position` ∈ {'topleft','topright','bottomleft','bottomright'} — [MUTABLE]
  • `prefix`   — string of HTML (any anchor / icon / text), or `False` to hide
                 the Leaflet link entirely. [MUTABLE]

Bonus: a Switch toggles whether the `dl2.AttributionControl` is mounted at all —
which proves the `attributionControl=False` map option does suppress the bundled
default (without our component, no box appears).

### Live demo

.. exec::docs.attribution.example
    :code: false

### Source

.. source::docs/attribution/example.py
    :defaultExpanded: false
    :withExpandedButton: true
