---
name: "Emoji & Iconify"
description: "a live DashEmojiMart picker + a full Iconify catalogue search,"
endpoint: "/emoji-iconify"
package: dash-leaflet2
category: "Markers"
icon: "tabler:mood-smile"
lastmod: 2026-07-28
---

.. llms_copy::Emoji & Iconify

.. toc::

### Overview

both driving a Leaflet 2 DivIcon marker and both following the app's light/dark scheme.

Mirrors dash-leaflet's emoji_marker.py, on Leaflet 2, using the exact DivIcon technique
baked into the compiled dl2.Marker (emoji / iconify modes). The emoji picker is the real
DashEmojiMart component (>= 0.0.5; PyPI 0.0.3 is broken in this Dash 4 / React 18.2 setup).
The Iconify picker searches the full 200k+ catalogue via the Iconify API
(https://api.iconify.design/search). Selecting from either swaps the marker's icon at
runtime via clientside callbacks that call into the JS-mounted map (DL2.emojiIconify).

### Live demo

.. exec::docs.emoji-iconify.example
    :code: false

### Source

.. source::docs/emoji-iconify/example.py
    :defaultExpanded: false
    :withExpandedButton: true
