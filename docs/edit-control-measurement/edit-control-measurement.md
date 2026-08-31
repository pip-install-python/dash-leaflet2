---
name: "Edit Control + Measurement"
description: "popover-driven drawing, recoloring, and per-feature labels."
endpoint: "/edit-control-measurement"
package: dash-leaflet2
category: "Controls (compiled dl2.*)"
icon: "tabler:ruler-measure"
lastmod: 2026-07-28
---

.. llms_copy::Edit Control + Measurement

.. toc::

### Overview

Builds on top of /edit-control. Three states (view / create / edit) and a single
dmc.Popover anchored next to the EditControl icon strip — the same anchor pattern as
/easy-button, but driven by EditControl's `activeTool` + `featureClick` instead of an
EasyButton click. ColorPicker is live in BOTH phases:

- create (after clicking a draw icon, before drawing) → updates EditControl.shapeOptions
  so the NEXT shape is drawn in that color
- create (after drawing, before Create/Cancel) → applies via featureUpdate to the just-
  drawn shape so the user can tweak the color before finalizing
- edit (after clicking a feature in edit mode) → applies via featureUpdate to that
  feature live

Every committed shape gets a permanent Leaflet tooltip with its area / radius / length
(showMeasurementTooltips=True on the EditControl); the Metric / Imperial toggle in the
right rail drives the unit system.

### Live demo

.. exec::docs.edit-control-measurement.example
    :code: false

### The shape

.. source::docs/edit-control-measurement/example.py
    :region: map
    :caption: Pattern
    :defaultExpanded: true
    :withExpandedButton: false

### Source

.. source::docs/edit-control-measurement/example.py
    :defaultExpanded: false
    :withExpandedButton: true
