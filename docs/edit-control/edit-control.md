---
name: "Draw & Edit"
description: "native v2 drawing/editing toolbar with full dash-leaflet-style API parity."
endpoint: "/edit-control"
package: dash-leaflet2
category: "Controls (compiled dl2.*)"
icon: "tabler:edit"
lastmod: 2026-07-28
---

.. llms_copy::Draw & Edit

.. toc::

### Overview

Mirrors dash-leaflet's EditControl prop shape (`draw`, `edit`, `drawToolbar`, `editToolbar`,
`action`) so callbacks compose the same way: bump n_clicks to dispatch from Python; read
`action` to react to any change. The contextual sub-toolbar (Finish / Delete last point /
Cancel during draw; Save / Cancel during edit; Clear all during remove) appears alongside
the icon strip while a tool/mode is active. The Edit section appears only when shapes exist.

### Live demo

.. exec::docs.edit-control.example
    :code: false

### The shape

.. source::docs/edit-control/example.py
    :region: map
    :caption: dl2.EditControl pattern (dash-leaflet API parity)
    :defaultExpanded: true
    :withExpandedButton: false

### Source

.. source::docs/edit-control/example.py
    :defaultExpanded: false
    :withExpandedButton: true
