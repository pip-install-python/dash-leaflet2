---
name: "Easy Button"
description: "Easy Button + marker creation flow with emoji picker, form popup, and view mode."
endpoint: "/easy-button"
package: dash-leaflet2
category: "Controls (compiled dl2.*)"
icon: "tabler:hand-click"
---

.. llms_copy::Easy Button

.. toc::

### Overview

Click the smile button on the map (top-left) to enter create mode → a dmc.Popover opens
directly to the right of the button with a DashEmojiMart picker. Click the map to place
the marker; a form popup opens above it with name/type fields. Pick an emoji at any time
to update the marker's icon live. Create finalizes the marker (pushes to a markers store,
exits create mode, closes everything); Cancel discards.

(We use dmc.Popover, not dmc.HoverCard. HoverCard is hover-triggered only — it would close
the moment the user moves their mouse off the button toward the map to place a marker.
Popover supports click-triggered + controlled `opened`, same visual styling.)

### Live demo

.. exec::docs.easy-button.example
    :code: false

### Source

.. source::docs/easy-button/example.py
    :defaultExpanded: false
    :withExpandedButton: true
