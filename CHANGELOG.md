# Changelog

All notable changes to **dash-leaflet2** are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Because
the project tracks `leaflet@2.0.0-alpha.1`, the **0.x** line is itself alpha — APIs
will move until v2 leaves alpha upstream.

---

## [Unreleased]

Nothing yet.

---

## [0.2.0] — 2026-07-28

First public release: the project splits into a private R&D checkout and this
public mirror, which is what ships to PyPI and to https://leaflet.2plot.dev.

### Added — public release preparation

The project is split into a private R&D checkout and this **public mirror**, which
is what ships to PyPI and to https://leaflet.2plot.dev.

- **`/tile-selector` rewritten** as a lean, self-contained page documenting the
  `dl2.TileSelector` component — click / shift-drag selection, the
  `{z, x, y, url, bounds}` data boundary, and the `[MUTABLE]` round-trip that lets
  a Clear button write `selectedTiles` back from Python. The previous 3,700-line
  AI tile-generation lab stays internal.
- **`scripts/smoke_test.py`** — headless suite driving the app through the backend's
  test client (no socket, no browser): page registration with duplicate-path
  detection, layout construction plus JSON serialisation of every example, and an
  HTTP sweep of every route, `/_dash-layout`, `/_dash-dependencies`, `/healthz`,
  `/llms.txt`, `/robots.txt` and `/sitemap.xml`.
- **`scripts/compat_matrix.py`** — builds a throwaway virtualenv per Dash version
  (4.1.0 / 4.2.0 / 4.3.0 / 4.4.1 by default), installs the docs site into each, runs
  the smoke suite, and writes `COMPATIBILITY.md`. Optional `--browser` leg boots each
  venv for real and collects console errors with Playwright. This is what turns the
  `dash>=4.1` claim into evidence.
- **`scripts/sync_from_rnd.py`** — pulls R&D work forward into the mirror behind an
  explicit denylist. Pull, not push: a new R&D docs page surfaces as NEW for approval
  rather than leaking by being forgotten upstream.
- **2plot network integration**, all dormant without environment keys:
  `lib/ad_client.py` (2plot.dev ad slots in the docs aside), `lib/satellite_analytics.py`
  (signed traffic rollups to 2plot.ai, `/healthz`, SPA page-view beacon),
  `lib/auth.py` (Clerk satellite of the 2plot.ai primary, including the two
  dash-clerk-auth 0.9.0 satellite fixes), and `lib/page_visibility.py` +
  `pages/control_board.py` (four-tier page visibility re-checked on every render,
  editable live at `/admin/control-board`).
- **Deployment**: `Dockerfile`, `.dockerignore`, `render.yaml` and `DEPLOYMENT.md`
  for `leaflet.2plot.dev`.
- **`vendor/`** — the two docs-only packages that are not on PyPI
  (`dash_emoji_mart` 0.0.5, `flexlayout_dash` 1.1.0) are committed here so
  `pip install -r requirements.txt` works from a clean clone. Neither is needed by
  the `dash_leaflet2` package, which still requires only `dash>=4.1`.

### Changed

- `app.py` → **`run.py`**, with `HOST` / `PORT` / `DASH_DEBUG` read from the
  environment so the compatibility matrix can run several Dash versions side by side.
- `requirements.txt` rewritten: the vendored packages install from relative
  `./vendor/` paths instead of absolute `file:///Users/...` URLs, and the Dash pin
  carries a `# COMPAT-MATRIX: dash` tag the matrix script strips per run.
- README rebuilt for the public release; `pyproject.toml` gained full trove
  classifiers and project URLs pointing at the documentation site.

---

## [0.1.0] — 2026-07-04

### Added — `crossOrigin` on TileLayer + ImageOverlay

`dl2.TileLayer` and `dl2.ImageOverlay` surface Leaflet's `crossOrigin` option
(`"anonymous" | "use-credentials" | ""`). Setting it makes the underlying `<img>`
loads CORS-mode so canvas captures (map screenshots / html2canvas thumbnails) can
read the pixels without tainting the canvas — requested by SailsBoard's
save-time-thumbnail pipeline. **Opt-in with no default**: a CORS-mode img fails to
load entirely against a host that doesn't answer `Access-Control-Allow-Origin`, so
leave it unset for tile providers you don't control. Construction-time only (for
`ImageOverlay`, `setUrl` and the editable drag/resize/rotate transforms reuse the
same img element, so the attribute set at construction persists).

### Added — dash-leaflet 1.x parity work (compiled `dl2.*` package)

Closes the surface gap downstream projects (SailsBoard's harbor map being the
canonical one) hit when migrating off `dash-leaflet` 1.x. Every item below is
verified end-to-end in a new live showcase page under `/docs/<slug>/`.

**TileLayer pro props** — `dl2.TileLayer` gains `minZoom`, `bounds`, `errorTileUrl`,
`zIndex`, `subdomains`, `detectRetina`, `tms`. `opacity` + `zIndex` are `[MUTABLE]`
via `setOpacity` / `setZIndex`. Lets downstream apps clip tile requests to a
geographic box, hide 404 tiles with a transparent PNG, stack multiple tile layers
explicitly, and shard CDN load across `{s}` subdomains. Showcase: `/tilelayer-pro-props`.

**Map pro props** — `dl2.Map` gains `minZoom`, `maxZoom`, `maxBounds`, `zoomControl`,
`keyboard`, plus the 6 interaction-disable handlers: `dragging`, `scrollWheelZoom`,
`doubleClickZoom`, `boxZoom`, `pinchZoom` (v2's name for v1's `touchZoom`), and
`tapHold`. All of zoom/bounds/keyboard/the 5 user-flippable handlers are `[MUTABLE]`
— a callback can lock dragging while a walkthrough plays, kill scroll-wheel zoom in a
detail-preview panel, etc. `pinchZoom` writes through to both `pinchZoom` (v2) and
`touchZoom` (v1 alias) so the prop name stays stable as Leaflet 2 evolves. Showcase:
`/map-pro-props`.

**GeoJSON clustering** — `dl2.GeoJSON` adds the dash-leaflet 1.x clustering surface
backed by [SuperCluster v8](https://github.com/mapbox/supercluster): `cluster`,
`superClusterOptions`, `pointToLayer`, `clusterToLayer`, `hideout`,
`zoomToBoundsOnClick`, `spiderfyOnMaxZoom`. `pointToLayer` / `clusterToLayer` accept
a JS source string compiled via `new Function(...)` at construction time; both
receive a `ctx = { hideout, leaflet, map }` argument so user code can build any
Leaflet 2 layer without depending on a global. Non-point features (LineString,
Polygon) pass through unclustered. Showcase: `/geojson-cluster`.

**LayerGroup + FeatureGroup** — new `dl2.LayerGroup` and `dl2.FeatureGroup`
components. Children of either attach to the group instead of the map via a
forwarding `LeafletMapContext` proxy (`makeForwardingMapProxy` in
`layersControl-shared.ts`) that intercepts `addLayer`/`removeLayer` but transparently
forwards every other map method (`latLngToLayerPoint`, `on`, `getCenter`, ...) to the
real map — required for layers like Marker whose rotation effect needs the real
projection. FeatureGroup additionally emits a combined `geojson` of its vector
children plus an aggregate `n_clicks` and `n_layers` counter. Showcase: `/layer-group`.

**ScaleControl** — `dl2.ScaleControl` wraps Leaflet 2's `Control.Scale` (lives on the
`Control` namespace but is not ESM-exported by `leaflet@2.0.0-alpha.1`, so we reach
through `(Control as any).Scale`). Props: `position` (mutable), `metric`, `imperial`,
`maxWidth`, `updateWhenIdle`. Showcase: `/scale-fullscreen-image`.

**FullScreenControl** — `dl2.FullScreenControl` is a thin custom `Control` that wraps
the browser's native `requestFullscreen()` / `exitFullscreen()` API around the map
container (Leaflet 2 itself does not ship a fullscreen control). Round-trips
`fullscreen` (boolean) and `n_clicks` to Dash so a callback can react when the user
enters or leaves fullscreen. Showcase: `/scale-fullscreen-image`.

**ImageOverlay** — `dl2.ImageOverlay` wraps `leaflet.ImageOverlay`. Mutable `url`,
`bounds`, `opacity`, `zIndex`; optional `interactive=True` lets the image fire
`n_clicks`. Useful for previewing a raster scan before slicing it into tiles, draping
a single static image onto a geographic box, or showing a non-tiled overlay. Showcase:
`/scale-fullscreen-image`.

- **Editable transform controls** — set `editable=True` for a TextMarker-style control
  system: click to select, drag the body to **move** (translates `bounds`), drag the corner
  dot to **resize** (scales `bounds` about the `anchor`, which stays pinned), and the top dot
  to **rotate** (a CSS-transform visual rotation pivoting at the `anchor` — `bounds` stay
  axis-aligned since Leaflet's ImageOverlay has no native geo-rotation). The white anchor dot
  sits at the chosen `anchor`. New props `editable`, `selected` (two-way), `rotation`
  (two-way), `anchor`; `bounds` becomes two-way and `n_transforms` counts move/resize commits.

**TextMarker** — new `dl2.TextMarker`: editable, draggable, styleable text placed on
the map like a Marker (implements Route A of the `text-caption-marker-proposal`). It is
a Leaflet 2 `Marker` whose icon is a content-sized, optionally-`contentEditable` text box
rendered into the icon via a React portal, reusing Marker's drag lifecycle + the
transform-reprojection trick (so rotation survives Leaflet's constant transform rewrites).
- **Placement**: anchored to `[lat, lng]`; when `position` is omitted it spawns at the
  **center of the current viewport** and writes that position back. `anchor` (9 positions)
  picks which point of the box sits on the latlng — that point is also the rotation pivot.
- **Direct manipulation**: drag to move (writes `position` + `n_drags`), double-click to
  edit inline (writes `text` + `n_edits`), and when `selected` a corner **resize** handle
  (→ `fontSize`) and a **rotate** handle (→ `rotation`, Shift-snaps to 15°) appear.
- **Style**: `color`, `backgroundColor`, `fontFamily`, `fontSize`, `fontWeight`,
  `fontStyle`, `padding`, `borderRadius`, `rotation`, `rotateWithMap` — all `[MUTABLE]`
  two-way (the contextual glass toolbar that shows while selected edits them and round-trips
  every change to Dash, so a host can also drive style from props). `selected` is two-way
  (clicking the label selects it; a map-background click deselects); `showToolbar` hides the
  built-in toolbar for hosts that supply their own.
- **Two size models** via `scaleWithZoom` (+ `referenceZoom`): `false` (default) is a
  constant screen-size HUD caption (`fontSize` is literal px at every zoom); `true` is
  geographic sizing — the on-screen size scales by `2^(zoom − referenceZoom)` so the caption
  keeps a fixed ground footprint as the camera flies. `referenceZoom` defaults to the zoom at
  which the label was created.
- Anchor offset is applied via the icon's **margin** (not baked into the transform) so
  Leaflet's own mid-drag positioning and ours never disagree; a post-handle-drag `click` is
  swallowed so resize/rotate don't deselect.
- The white selection dot (which doubles as the resize grip) is drawn at the chosen `anchor`
  point — `bottom` → bottom-center, `top-left` → top-left, … (`center` → bottom-right so it
  never covers the text) — so you can see where the label is pinned. Resize now references the
  box center (the dot sits at the anchor, so an anchor-referenced ratio would divide by ~0).
- `selected` is **uncontrolled when omitted**: the marker self-manages selection (click to
  select, two-stage map-click to deselect) and a map-event bus keeps only one TextMarker
  selected at a time. Pass an explicit `selected` to drive it from the host. The anchor model
  + dot positioning now live in the shared `src/ts/anchor.ts` (used by the editable ImageOverlay too).

**EditControl `text` tool (proposal Route B)** — `dl2.EditControl` gains a `text` tool
alongside `marker` / `polyline` / `polygon` / …. Picking it and clicking the map drops an
inline-editable caption that round-trips through the **same `geojson` channel** as every other
shape — a GeoJSON `Point` carrying `kind:"text"` + the caption style (`text`, `color`,
`fontSize`, `fontFamily`, `fontWeight`) in `properties`. In edit mode the caption is draggable
and double-click re-opens the inline editor; cancel/revert rebuilds captions as text icons (not
pins). Enable per-tool with `draw={"text": True}`. Showcase: `/text-marker`.

### Added — docs site (`docs/<slug>/`)

Five new markdown-driven showcase pages, each with a focused "limited working
example" `example.py` next to the markdown:

- `/tilelayer-pro-props` — two stacked tile layers (OSM base with `subdomains` +
  `detectRetina`; CARTO labels-only overlay clipped to a Rockport, TX `bounds` box
  with a transparent `errorTileUrl`). Sliders drive `opacity` + `zIndex` live.
- `/map-pro-props` — 6-handler Switch panel + zoom RangeSlider + `maxBounds` toggle
  + live viewport readback. Flipping a Switch immediately disables the matching
  Leaflet handler on the live map.
- `/geojson-cluster` — 200 synthetic vessel positions colored by category via a JS
  `pointToLayer` reading a Python-shipped `hideout` color map; cluster bubbles take
  the dominant category's color. Cluster-radius slider tunes
  `superClusterOptions.radius` live.
- `/layer-group` — two maps: one `LayerGroup` of three markers behind a single
  Switch (the whole group toggles together), one `FeatureGroup` wrapping four shapes
  and emitting combined `geojson` + bumping `n_clicks` on any child click.
- `/scale-fullscreen-image` — one map with the scale bar (position + metric/imperial
  Switches), the fullscreen button (reports `fullscreen` + `n_clicks`), and a
  swappable `ImageOverlay` with opacity slider.
- `/text-marker` — a selected `TextMarker` you drag / edit / resize / rotate / restyle
  on the map (or drive from the right column: text, color, font size, rotation, anchor,
  `scaleWithZoom`), a second caption with `scaleWithZoom=True` that holds its ground size,
  and the `EditControl` `text` tool wired in (click the T, click the map, type — the
  caption shows up in `EditControl.geojson` as a `kind:"text"` Point). Live readback panel.

### Added — supporting work

- New runtime dependency: `supercluster@^8.0.1` (bundled into `dash_leaflet2.js`).
  The 0.0.1 wheel sat at ~261 KiB; with clustering + the four new components the
  bundle is now ~263 KiB.
- `src/ts/types/leaflet.d.ts` — extended for `Map.setMinZoom` / `setMaxZoom` /
  `setMaxBounds` / `getMinZoom` / `getMaxZoom`, `Map.keyboard`, `TileLayer.setOpacity`
  / `setZIndex`, `ImageOverlay`, plus a minimal ambient `supercluster` module.
- `src/ts/layersControl-shared.ts` — new `makeForwardingMapProxy(onAdd, onRemove,
  getRealMap)` builds a JS-`Proxy`-based map stand-in that intercepts
  `addLayer`/`removeLayer` but forwards every other property access to the real map.
  Used by `LayerGroup` and `FeatureGroup`; the existing thin `makeMapProxy` is kept
  for `BaseLayer`/`Overlay` where forwarding is unwanted.
- `src/ts/theme.css` — cluster-bubble glass styling (`.dl2-cluster-bubble` and
  `.dl2-cluster-{32,40,48,56}` sizes) + fullscreen-button styling
  (`.dl2-fullscreen-control`, `.dl2-fullscreen-button`).

### Added — earlier in Unreleased

- **`dl2.TileSelector`** — a map control that turns the map into a tile picker:
  click or shift-drag to select tiles, which round-trip to Python as
  `{z, x, y, url, bounds}`, keyed by `z/x/y` so selections survive pan and zoom.
- **Compare Lab** (`/compare-lab`) — tileset comparison surface: an `EasyButton` +
  Popover + `dash_mui_charts.TreeViewPro` driving a clientside reconciler over a
  stack of `TileLayer` overlays (visibility, opacity, z-order, deletion), seeded
  with synthetic SVG overlays so every interaction responds in under a second.
- **Walking Sim** (`/walking-sim`) — Esri Imagery + NatGeo layered basemaps with a
  street-tile minimap; flyTo between WALK / EXPLORE modes.
- **Sub-toolbar + live drawing feedback** in `dl2.EditControl` — vertex-handle previews,
  cursor-following guide tooltip, dashed rubber-band, context-sensitive fly-out actions
  (Finish / Delete-last-point / Cancel during draw; Save / Cancel during edit).

### Fixed
- **Cross-zoom prompt engineering** — the AI was pasting descendant references as
  visible rectangular insets with duplicated features and a seam. Rewrote SOURCE +
  CROSS-ZOOM REFERENCE labels and the addendum to forbid pasting/insets and to assert
  the source tile as the geometric ground truth for all four quadrants.
- **Tileset comparison overlay layering** — z15 (later-added, larger) was covering z16
  at every viewport zoom. Added zoom-meets-tile filtering: among overlapping tree-checked
  tiles, only the deepest zoom the viewport has met shows (`z15` at vz=13–15, `z16` at
  vz=16, `z17` at vz=17+). Standalone tiles unaffected. Set `zIndex = 400 + tileZ` so
  any transient overlap keeps the finer tile on top.
- **EasyButton popover toggle** — `dmc.Popover.opened` is not pushed through `setProps`
  after internal state changes; switched to a DOM-read clientside pattern reading
  `.mantine-Popover-dropdown` `offsetParent`.
- **`MUI TreeView` overlay flicker** — refactored to "mount-everything-hide-via-opacity"
  with `transition: opacity 120ms ease`; checkbox-row double-click bounces no longer
  tear overlays off the map.

---

## [0.0.1] — 2026-05-22

First **alpha** release. Build a wheel from source (`python -m build`); not yet on PyPI.

### Added — components shipped in the wheel

| Component | Wraps | Notes |
|---|---|---|
| `dl2.Map` | `leaflet.Map` | `viewport` + `clickData` round-trip; React-context bridge replaces react-leaflet |
| `dl2.TileLayer` | `leaflet.TileLayer` | `url`, `attribution`, `maxZoom`, `opacity` |
| `dl2.Marker` | `leaflet.Marker` | default / `icon` / `emoji` / `iconify` / full `iconOptions` icon modes; bundled marker images (base64) |
| `dl2.Polyline`, `dl2.Polygon`, `dl2.Rectangle`, `dl2.Circle`, `dl2.CircleMarker` | corresponding `leaflet.*` | vector path props + click round-trip |
| `dl2.GeoJSON` | `leaflet.GeoJSON` | `data`, `style`, `clickFeature`; `pointToLayer` sets the bundled default icon to dodge v2's stale `Icon.Default()` trap |
| `dl2.Popup`, `dl2.Tooltip` | `leaflet.Popup`, `leaflet.Tooltip` | render arbitrary Dash content through React portals |
| `dl2.LayersControl` + `dl2.BaseLayer` + `dl2.Overlay` | custom (`Control` subclass) | v2's `Layers` class is not ESM-exported; ships our own with `RegisterContext` |
| `dl2.EditControl` | native v2 toolbar `Control` | leaflet-draw is v1-only; our native replacement draws marker / polyline / polygon / rectangle / circle + delete with GeoJSON round-trip |
| `dl2.EasyButton` | `leaflet.Control` | Iconify icon, `n_clicks` / `n_dblclicks` |
| `dl2.AttributionControl` | `leaflet.Control.Attribution` | `prefix`, custom `attribution` |
| `dl2.KeyboardControl` | custom (`Control`) | DOM key listeners → `lastKey` / `n_events` |
| `dl2.MiniMap` | custom (`Control`) | second `leaflet.Map` instance pinned to a corner |
| `dl2.TileSelector` | custom (`Control`) | hover-highlight, click-toggle, shift+drag box-select; `selectedTiles` round-trip with `{z, x, y, url, bounds}` |
| `dl2.Tooltip`, `dl2.Popup` | (see above) | bind to any layer via React portal |

### Added — hooks/CDN showcase (`run.py`)
- 20+ pages under `docs/` demonstrating v2 features through the `dash.hooks` API with
  no build step: pointer events, canvas overlay, ES6 subclassing, `ResizeObserver`
  sizing, vector layers, emoji/iconify markers, layers control, draw + edit + measure,
  easy button, MiniMap, basic rotation, flight sim, walking sim, events→Python, flyTo,
  attribution control, tile-layers-pro, tile-selector, compare-lab.
- DMC AppShell + sidebar + dark-mode toggle; FastAPI backend by default
  (`DASH_BACKEND=flask python run.py` to fall back).

### Added — developer tooling
- `.claude/` directory: 1 subagent (`leaflet2-component-author`), 2 skills
  (`build-and-verify`, `new-component`), 3 path-scoped rules
  (`leaflet2-v2-api.md`, `dash-components.md`, `showcase-pages.md`).
- Webpack + `dash-generate-components` build pipeline; Python classes generated from TS
  JSDoc; default marker icons inlined as base64 to dodge v2's CSS-path detection.

### Known gotchas
- v2's UMD global is **`window.leaflet`** (not `window.L`).
- No lowercase factories — `new Marker(...)`, not `L.marker(...)`.
- v2 fires **pointer events** (`pointermove`/`pointerdown`), not mouse events.
- `BlanketOverlay._onMoveEnd()` clears the canvas after drawing — Canvas renderer
  workaround: `requestAnimationFrame(() => renderer._update())` after `moveend`/`zoomend`.
- v2 ships no TypeScript types — minimal ambient declarations at
  `src/ts/types/leaflet.d.ts`.

[Unreleased]: https://github.com/pip-install-python/dash-leaflet2/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pip-install-python/dash-leaflet2/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/pip-install-python/dash-leaflet2/releases/tag/v0.0.1
