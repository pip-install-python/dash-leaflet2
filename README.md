<div align="center">

# dash-leaflet2

**Leaflet 2-native mapping components for [Plotly Dash](https://dash.plotly.com) 4.**

No react-leaflet · unified Pointer Events · `BlanketOverlay` canvas/WebGL layers · ES6-class subclassing · `ResizeObserver` sizing · map rotation · liquid-glass theme · full Dash callback interoperability.

[![PyPI version](https://img.shields.io/pypi/v/dash-leaflet2?color=blue)](https://pypi.org/project/dash-leaflet2/)
[![Python](https://img.shields.io/pypi/pyversions/dash-leaflet2)](https://pypi.org/project/dash-leaflet2/)
[![Dash 4.1+](https://img.shields.io/badge/Dash-4.1%2B-1a1a2e?logo=plotly&logoColor=white)](https://dash.plotly.com/)
[![Leaflet 2 alpha](https://img.shields.io/badge/Leaflet-2.0.0--alpha.1-199900?logo=leaflet&logoColor=white)](https://leafletjs.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white)](https://discord.gg/WEnZR35mrK)
[![YouTube](https://img.shields.io/badge/YouTube-%402plotai-FF0000?logo=youtube&logoColor=white)](https://www.youtube.com/channel/UC6Bmo0t0ZUpU_xKBYW0bJuQ)

**[Documentation](https://leaflet.2plot.dev)** · [Discord](https://discord.gg/WEnZR35mrK) · [YouTube](https://www.youtube.com/channel/UC6Bmo0t0ZUpU_xKBYW0bJuQ) · [GitHub](https://github.com/pip-install-python/dash-leaflet2)

<br/>

_Maintained by **[Pip Install Python LLC](https://pip-install-python.com)**._

</div>

---

## Overview

`dash-leaflet` is frozen on [react-leaflet](https://react-leaflet.js.org/) → Leaflet 1.9.
react-leaflet has no Leaflet 2 line, and its architecture is built around Leaflet 1.x's
context and lifecycle model — so a Leaflet-2-native component **cannot** ride react-leaflet.

`dash-leaflet2` wraps **Leaflet 2 core directly** through a small React-context bridge.
That sheds the entire react-leaflet abstraction layer and unlocks v2's headline features:

- **Unified Pointer Events** — one event model for mouse, touch and stylus. The Leaflet
  event's `.originalEvent` is a native `PointerEvent`, so `pointerType`, `pressure` and
  `tiltX` / `tiltY` reach your Python callbacks
- **`BlanketOverlay` canvas / WebGL layers** — draw your own renderer across the whole
  viewport instead of fighting the DOM layer system
- **ES6-class subclassing** — extend Leaflet 2 classes in plain JS and mount the result
  as a Dash component
- **`ResizeObserver` sizing** — no more grey tiles when a map is born inside a hidden
  tab, accordion or drawer
- **Map rotation** — `bearing` as a first-class, two-way prop, with a keyboard control
- **Liquid-glass theme** — tooltips, popups, the zoom bar and attribution use
  `color-mix()` + `backdrop-filter`, so they read correctly in light *and* dark mode

The package ships the compiled JS bundle — Leaflet 2, the marker images and the theme CSS
all live inside `dash_leaflet2.js`. A normal `pip install` needs no Node and no
`external_scripts`.

> **Status: alpha.** This tracks Leaflet `2.0.0-alpha.1`, so the `0.x` line is itself
> alpha and APIs will move until v2 leaves alpha upstream. See
> [CHANGELOG.md](./CHANGELOG.md) for what's shipped, fixed and known-broken.

## Installation

```bash
pip install dash-leaflet2
```

Requires `dash>=4.1`. See [Dash compatibility](#dash-compatibility) for the tested matrix.

## Quick Start

```python
from dash import Dash, Input, Output, callback, html
import dash_leaflet2 as dl2

app = Dash(__name__)

app.layout = html.Div([
    dl2.Map(
        id="map",
        center=[28.0206, -97.0544],
        zoom=12,
        style={"height": "70vh"},
        children=[
            dl2.TileLayer(url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"),
            dl2.Marker(
                id="pin",
                position=[28.0206, -97.0544],
                draggable=True,
                children=dl2.Tooltip("Drag me"),
            ),
        ],
    ),
    html.Pre(id="out"),
])


@callback(Output("out", "children"), Input("pin", "position"))
def show(position):
    return f"marker at {position}"


if __name__ == "__main__":
    app.run(debug=True)
```

Drag the pin and `position` round-trips to Python. No JS, no `external_scripts`, no
Leaflet CSS link — the bundle carries all of it.

## Documentation

Full documentation, with a live interactive demo on every page:

### 📚 **[leaflet.2plot.dev](https://leaflet.2plot.dev)**

Every page also serves `/<page>/llms.txt` — the prose plus the complete example source,
directive-expanded and ready to paste into a chat window.

You can also run the docs site locally:

```bash
pip install -r requirements.txt
python run.py                 # open http://127.0.0.1:8050
```

…or the standalone component harness, which exercises the compiled `dl2.*` surface
without the docs shell:

```bash
python usage.py               # open http://127.0.0.1:8060
```

## Components

26 components, all loading from the single bundled JS file.

### Core

| Component | What it is |
|-----------|------------|
| `Map` | The root container. Owns the Leaflet 2 map instance and provides it to children through React context. Two-way `center` / `zoom` / `bearing` / `bounds`, plus the full pro-prop surface (`minZoom`, `maxBounds`, `zoomSnap`, inertia, …). |
| `TileLayer` | Raster tile basemap. `minZoom`, `bounds`, `errorTileUrl`, `zIndex`, `subdomains`, `detectRetina`, `tms`, `crossOrigin`; `opacity` and `zIndex` are `[MUTABLE]`. |
| `Marker` | Icon at a position, hosting `Popup` / `Tooltip` children. Icon modes: default pin, custom image, `emoji`, or any [Iconify](https://iconify.design/) icon. Draggable markers write `position` back to Dash. |
| `Popup` / `Tooltip` | Balloon and hover label bound to a parent layer. Children render through a React portal, so **any** Dash component works as content. |

### Layers

| Component | What it is |
|-----------|------------|
| `GeoJSON` | Renders a GeoJSON object from a callback. `cluster=True` collapses dense point sets via SuperCluster; custom `pointToLayer` / `clusterToLayer` JS strings supported. |
| `LayerGroup` | Bundles N layers so they add and remove together. |
| `FeatureGroup` | Like `LayerGroup`, but emits a combined GeoJSON of its vector children and broadcasts one `click` regardless of which child was hit. |
| `ImageOverlay` | Drapes a static image over a bounding box. With `editable`, gains click-to-select, drag-to-move, corner-resize and rotate handles; `bounds` / `rotation` / `selected` round-trip. |

### Vectors

| Component | What it is |
|-----------|------------|
| `Circle` | Radius in **meters** — grows and shrinks with zoom. |
| `CircleMarker` | Radius in **pixels** — constant size at every zoom. |
| `Polyline` | Multi-segment line from `[lat, lng]` points. |
| `Polygon` | Filled closed shape from `[lat, lng]` points. |
| `Rectangle` | Axis-aligned box from geographic bounds. |

### Controls

| Component | What it is |
|-----------|------------|
| `LayersControl` + `BaseLayer` / `Overlay` | Base-layer radio group and overlay checkboxes. A custom implementation — Leaflet 2's bundled `Layers` class is not exported by its ESM. |
| `EditControl` | Native v2 draw/edit toolbar (leaflet-draw is Leaflet-1-only and DOA on v2). Marker / polyline / polygon / rectangle / circle / delete, round-tripping `geojson`, `n_drawn` and `lastAction`. |
| `AttributionControl` | Explicit attribution box. `position` and `prefix` are both `[MUTABLE]`; `prefix=False` hides the Leaflet link. |
| `ScaleControl` | Metric and/or imperial scale bar. |
| `FullScreenControl` | Toggles the map container through the browser's native `requestFullscreen()`. Leaflet 2 ships no fullscreen control. |
| `MiniMap` | Corner overview map tracking the main map's center and zoom, with a viewport rectangle and a collapse toggle. |
| `EasyButton` | Single-icon control for a map-level action; the click arrives as `n_clicks`. Icons from Iconify. |
| `KeyboardControl` | Window-level key listener driving rotation and pan. Renders no DOM — a pure side-effect component. |
| `TileSelector` | Turns the map into a tile picker: click or shift-drag to select tiles, which round-trip as `{z, x, y, url, bounds}`. |
| `TextMarker` | Editable, draggable, styleable text on the map. Double-click to edit; on-canvas resize / rotate handles and a contextual toolbar when `selected`. |

Full prop tables are generated into each `dash_leaflet2/<Component>.py` docstring by
`dash-generate-components`, and rendered on every documentation page.

## The data boundary

- **Two-way props are marked in the docstrings.** `[MUTABLE]` means Python callbacks can
  push the value into the map; `[READONLY]` means the map writes it back. `Map.center`,
  `Map.zoom`, `Map.bearing`, `Marker.position`, `TileSelector.selectedTiles`,
  `ImageOverlay.bounds` and `EditControl.geojson` all round-trip in both directions.
- **Events are props, not a separate channel.** Clicks land as `n_clicks`, drags as an
  updated `position`, draws as `geojson` + `lastAction` — so a plain `@callback` is the
  whole integration.
- **Pointer events carry v2's extra data.** Pointer props report `pointerType`, `pressure`
  and `tiltX` / `tiltY` from the native `PointerEvent`, which Leaflet 1 could not express.
- **Only JSON crosses the boundary.** Tiles, canvas bitmaps and the Leaflet instances
  themselves stay in the browser.

## Dash compatibility

`dash-leaflet2` targets **Dash 4.1 and up**. That range is verified, not assumed —
`scripts/compat_matrix.py` builds a throwaway virtualenv per Dash version, installs the
full documentation site into each, and runs the smoke suite there:

```bash
python scripts/compat_matrix.py                    # 4.1.0, 4.2.0, 4.3.0, 4.4.1
python scripts/compat_matrix.py 4.4.1 --backends flask fastapi
python scripts/compat_matrix.py --browser          # + Playwright console-error sweep
```

Results land in [COMPATIBILITY.md](./COMPATIBILITY.md). The per-version harness is
`scripts/smoke_test.py`, which also runs standalone:

```bash
python scripts/smoke_test.py
```

It checks that every markdown page registered a route with no duplicate paths, that every
page layout builds and survives Dash's JSON encoder, and that every route plus
`/_dash-layout`, `/_dash-dependencies`, `/healthz`, `/llms.txt`, `/robots.txt` and
`/sitemap.xml` answers over the backend's test client. No socket, no browser.

## Development

```bash
# Install dependencies
npm install                  # TypeScript + webpack toolchain
pip install -r requirements.txt

# Build the JS bundle + regenerate the Python wrappers
npm run build                # webpack UMD bundle + dash-generate-components
npm run build:js             # webpack only (after .tsx edits)
npm run build:backends       # regenerate Python classes only (after prop changes)
npm run watch                # JS-only rebuild loop

# Run
python run.py                # documentation site  → http://127.0.0.1:8050
python usage.py              # component harness   → http://127.0.0.1:8060

# Test
python scripts/smoke_test.py

# Build a distribution
python -m build --wheel
```

- TypeScript source of truth is `src/ts/` — `components/` holds the public components;
  `icons.ts`, `theme.css`, `useLayer.ts` and `layersControl-shared.ts` are the shared
  plumbing; `types/leaflet.d.ts` is our ambient declaration (Leaflet 2 ships no types).
- **After editing `src/ts/components/*.tsx` you must `npm run build`** — the Python
  classes and the JS bundle are generated artifacts.
- The built bundle and generated wrappers are committed, so `pip install -e .` works
  without npm.
- `dash_leaflet2/__init__.py` is hand-maintained (it registers `_js_dist`);
  `dash-generate-components` does not regenerate it.
- Defaults go in destructured default parameters, **never** `Component.defaultProps`
  (React 18.3 deprecation warning; `react-docgen@5` reads both, so the defaults survive).
- Keep the version in sync across `package.json`, `pyproject.toml` and `lib/constants.py`
  when cutting a release.

### Documentation site

Each page is a `docs/<slug>/<slug>.md` with frontmatter plus a `docs/<slug>/example.py`
exporting a `component`. `pages/markdown.py` walks them and registers each as a Dash page;
`.. exec::` embeds the live demo, `.. source::` renders the example source, and
`.. kwargs::` generates the prop table. Adding a page is two files and no routing code.

The deployed site at `leaflet.2plot.dev` also runs as a
[2plot](https://2plot.ai) network satellite — ad slots, traffic rollups, Clerk sign-in and
an admin page-visibility board. Every one of those is dormant without its environment
keys, so a local `python run.py` is just the docs. See [DEPLOYMENT.md](./DEPLOYMENT.md).

## Requirements

- Python >= 3.8
- Dash >= 4.1
- Node.js >= 16 — only to rebuild the JS bundle

## Leaflet 2 notes

Leaflet 2 is a genuine break from 1.x, and these cost real debugging time:

- The version string is **`2.0.0-alpha.1`**, with the dot. The dotless form 404s on unpkg.
- The UMD build exposes **`window.leaflet`**, not `window.L` — the `L` global is gone.
- There are **no lowercase factory functions**. Use `new Marker(...)`, not `L.marker(...)`.
- v2 fires **pointer events** (`pointermove` / `pointerdown`), not `mousemove` / `mousedown`.
- **Canvas-clear bug:** `BlanketOverlay._onMoveEnd()` draws and then calls
  `_resizeContainer()`, which sets `canvas.width` and wipes the bitmap — so the Canvas
  renderer goes blank after pan/zoom. We re-issue a redraw on the next animation frame
  after `moveend` / `zoomend`. The SVG renderer is unaffected.
- **Default marker icons** need explicit wiring when bundled: v2's CSS-based icon-path
  detection fails, and `Marker`'s default icon is a shared instance created at module-load
  time. All of it is handled in `src/ts/icons.ts`.

The [documentation site](https://leaflet.2plot.dev) covers each of these with a live page.

## Community & support

Come build with us:

- 💬 **Discord** — [discord.gg/WEnZR35mrK](https://discord.gg/WEnZR35mrK)
- ▶️ **YouTube** — [@2plotai](https://www.youtube.com/channel/UC6Bmo0t0ZUpU_xKBYW0bJuQ)
- 🐛 **Issues** — [github.com/pip-install-python/dash-leaflet2/issues](https://github.com/pip-install-python/dash-leaflet2/issues)

## More from Pip Install Python LLC

dash-leaflet2 is one of several tools built and maintained by **Pip Install Python LLC**:

| Project                                                                  | What it is                                                      |
|--------------------------------------------------------------------------|-----------------------------------------------------------------|
| 📚 **[Pip Install Python](https://pip-install-python.com)**               | Open-source documentation index for the Python & Dash ecosystem |
| 🎞️ **[dash-nle-timeline](https://pypi.org/project/dash-nle-timeline/)** | Frame-accurate NLE timeline & scene compositor for Dash          |
| 🔀 **[PiratesBargain.com](https://piratesbargain.com)**                   | E-commerce / digital commerce                                   |
| 🧠 **[ai-agent.buzz](https://ai-agent.buzz)**                             | Infinite AI canvas                                              |
| 🎬 **[2plot.media](https://2plot.media)**                                 | Videography application                                         |

## License

MIT — see [LICENSE](LICENSE). Built by **[Pip Install Python LLC](https://pip-install-python.com)**
to bring a generation-ahead mapping stack into the Dash framework.
