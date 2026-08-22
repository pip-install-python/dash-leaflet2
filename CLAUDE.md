# dash-leaflet2 — public mirror (2plot_leaflet)

A **Leaflet 2-native** component library for **Dash 4**. `dash-leaflet` is frozen on
react-leaflet → Leaflet 1.9; this project wraps **Leaflet 2 core directly** (no
react-leaflet) and is a generation ahead. Owner: Pip Install Python LLC. PyPI:
`dash-leaflet2`, import `dash_leaflet2 as dl2`. Docs: https://leaflet.2plot.dev

## This repo is the PUBLIC MIRROR

The private R&D checkout is `../dash-leaflet2`. It keeps two pages that must never
ship — `docs/sprite-generator/` (AI sprite authoring shell) and the 3,700-line
`docs/tile-selector/` AI tile-generation lab. **This repo ships its own lean
`/tile-selector` page** documenting the `dl2.TileSelector` component instead.

Pull R&D work forward with `python scripts/sync_from_rnd.py` (dry run by default).
It is a *pull*, not a push: a new R&D docs page shows up as NEW for you to approve
or add to `DENY_DOCS`, so nothing leaks by being forgotten upstream. Files this
mirror owns outright — `run.py`, `README.md`, `requirements.txt`, the `lib/`
network clients, `pages/`, `scripts/`, `vendor/`, `Dockerfile`, `render.yaml` —
are never overwritten (`MIRROR_OWNED`).

## Two parallel deliverables (both live in this repo)

| | What | Where | Status |
|---|---|---|---|
| **Docs site** | `dash.hooks` + CDN, no build step — proves Leaflet 2 renders in Dash and round-trips events | `run.py`, `docs/`, `assets/leaflet2_maps.js` | 27 pages, deployed |
| **Component package** | Real bundled `dl2.*` components (TS → webpack → generated Python) | `src/ts/`, built into `dash_leaflet2/` | 26 components |

The site de-risks; the package is the durable artifact. Keep both working.
`usage.py` demos the compiled package; `run.py` is the documentation site.

## 2plot network wiring (all dormant without env keys)

`lib/ad_client.py` → 2plot.dev ads · `lib/analytics_tracker.py` +
`lib/traffic_rollup.py` + `lib/satellite_reporter.py` → 2plot.ai traffic (the
boilerplate's trio; it replaced the Gen-1 single-module tracker in the
1.3.x instrumentation sync — `traffic_rollup._SKIP` must stay byte-identical
to the boilerplate's) · `lib/auth.py` → Clerk satellite of 2plot.ai ·
`lib/access.py` (+ `page_tiers` / `hub_client` / `gate_layouts` / `agent_key`)
→ the gate · `lib/page_visibility.py` + `pages/control_board.py` →
`/admin/control-board`. Full reference in `DEPLOYMENT.md`. These are shared
drop-in modules — when fixing a bug in `ad_client.py` or the analytics trio,
the fix probably belongs in the other satellites too (canonical source:
`../dash-documentation-boilerplate`).

## The gate (this repo is the fleet's pilot)

`lib/access.py` is the enforcement engine; `lib/page_visibility.py` was demoted
to the control board's **override store + UX** and no longer resolves access or
wraps layouts. A verdict resolves from three inputs, in order: the board's
override (most local, wins — that is what a live toggle is), the frontmatter
registration in `page_tiers`, then the hub's ceiling, which only ever restricts.

Two lanes, deliberately different: `resolve_page_access` answers what a BROWSER
gets (`gate_layouts` renders the card), `check` answers what a MACHINE fetch
gets (`/<page>/llms.txt`, crawler HTML, prerender) and honours `?key=` plus the
`llms_public` axis. A key never unlocks a layout.

Frontmatter: `tier:` is canonical, `visibility:` is an accepted alias for the
same four values, and ONE declared value feeds both ledgers — they were
independent keys before this pass, which let a page declare one tier and be
enforced at another.

Two postures that look like bugs and are not: docs fall **open** without Clerk
(documentation must not brick over a missing credential) while admin fails
**closed**; and a hub failure resolves to `gated`, never `allow`, never `deny`.

Shipped **dark**: `run.py` wires the policy with `force=True` even though every
tier is public, so the verdict path (and the prerender's use of it) runs in
production before `PAGE_DEFAULT_TIER=auth` turns it on. That env flip is the
whole change, and flipping it back is the rollback.

## Commands

```bash
# Component package (TS -> JS bundle + generated Python classes)
npm install                 # one-time: build toolchain
npm run build               # build:js (webpack) + build:backends (dash-generate-components)
npm run build:js            # webpack only (after .tsx edits)
npm run build:backends      # regenerate Python classes only (after prop/type edits)

# Run
pip install -r requirements.txt
python run.py               # documentation site  -> http://127.0.0.1:8050
python usage.py             # compiled dl2.*      -> http://127.0.0.1:8060

# Test
python scripts/smoke_test.py          # pages register, layouts render, routes 200
python scripts/compat_matrix.py       # a venv per Dash version -> COMPATIBILITY.md
python scripts/sync_from_rnd.py       # dry-run the pull from ../dash-leaflet2

# Package
python -m build --wheel     # PyPI-installable wheel in dist/
```

Two docs-only deps come from PyPI with load-bearing version floors:
`dash-emoji-mart>=0.0.5` (0.0.3 errors on init) for `/emoji-iconify` +
`/easy-button`, and `flexlayout-dash>=1.1.0` (1.1.0 renamed the import to
`flexlayout_dash`) for `/walking-sim`. Both were vendored tarballs until their
working builds reached PyPI. Neither is needed by the `dash_leaflet2` package
itself — that needs only `dash>=4.1`.

`vendor/` now holds exactly one tarball: `dash_clerk_auth-1.0.5.tar.gz`, which
is vendored across every 2plot satellite rather than published to PyPI. It
requires Python >=3.10, which binds the docs site only (Docker is 3.12); the
package keeps `requires-python >=3.9`. 1.0.5 is a SECURITY floor: this site renders the
Clerk menu (`components/header.py`), so it was exposed to the avatar/session
race fixed there. Its `clerk-backend-api<8` cap (widened in 1.0.1) is what lets
`requirements.txt` hold the `cryptography>=50.0.0` security floor.

## Critical Leaflet 2.0.0-alpha.1 facts (these cost real debugging time)

- Version is **`2.0.0-alpha.1`** WITH the dot. The dotless `2.0.0-alpha1` **404s** on unpkg.
- The global UMD build exposes **`window.leaflet`**, NOT `window.L` (the `L` global was dropped).
- v2 has **no lowercase factory functions** — no `L.marker()`/`L.icon()`/`L.tileLayer()`.
  Use `new Marker(...)`, `new Icon(...)`, `new TileLayer(...)`.
- v2 fires **pointer events** (`pointermove`/`pointerdown`), not `mousemove`/`mousedown`.
  The Leaflet event's `.originalEvent` is a native `PointerEvent` (`.pointerType`,
  `.pressure`, `.tiltX/Y`).
- **Canvas-clear bug:** `BlanketOverlay._onMoveEnd()` draws (`_onSettled`) then calls
  `_resizeContainer()`, which sets `canvas.width` and wipes the bitmap. So the Canvas
  renderer and any `BlanketOverlay` subclass go blank after pan/zoom. Workaround: re-issue
  a redraw on the next animation frame after `moveend`/`zoomend`. SVG renderer is unaffected.
- v2 ships **no TypeScript types**; we keep a minimal ambient declaration at
  `src/ts/types/leaflet.d.ts`. Extend it as the component set grows.
- **Default marker icons**: when bundled (not CDN), v2's CSS-based icon-path detection
  fails. Import the images (`leaflet/dist/images/*.png`, webpack `asset/inline` → base64).
  All icon logic lives in `src/ts/icons.ts` (`buildMarkerIcon` + `DEFAULT_ICON`).
  - Subtle trap: `Marker`'s default `icon` option is a shared `new Icon.Default()` created
    at Leaflet module-load time — BEFORE our `icons.ts` config runs — so anything relying
    on it (notably `GeoJSON` point features) gets the stale bare-URL icon and 404s. Fix per
    consumer: pass an explicit icon (our Marker always does) or set `pointToLayer` →
    `new Marker(latlng, {icon: DEFAULT_ICON})` (our GeoJSON does).
- **Marker icon modes**: `icons.ts` builds default / image (`icon`) / `emoji` / `iconify`
  (via the bundled `iconify-icon` web component, lazy-loading from the Iconify API) / full
  `iconOptions` DivIcon. `iconify-icon` is a runtime dependency. DivIcons set
  `tooltipAnchor`/`popupAnchor: [0, -size]` so tooltips/popups open above the pin.
- **Liquid-glass theme + light/dark tiles** (`src/ts/theme.css` in the package,
  `assets/style.css` in the showcase): Leaflet tooltips, popups, zoom bar, and attribution
  use `color-mix(... mantine-color-body ... transparent)` + `backdrop-filter` for a
  theme-aware glass look. Showcase tiles auto-swap CARTO light_all↔dark_all via a
  `MutationObserver` on `<html data-mantine-color-scheme>` (see `DL2.setMapTheme` in
  `assets/leaflet2_maps.js`). Showcase CSS uses `!important` (assets load BEFORE the
  hooks-injected `leaflet.css`); the compiled package's load order is correct via webpack.
- **LayersControl** (custom, extends `Control`): v2's bundled `Layers` class is NOT
  exported by the ESM, so we wrap our own. UI rendered via React portal; `BaseLayer` /
  `Overlay` children register through `RegisterContext` (`src/ts/layersControl-shared.ts`)
  using a map-proxy that captures the child layer's `addTo` call. `active` is DERIVED from
  `entries[].initialChecked` + a `toggles` override; `activeBase` / `activeOverlays` props
  sync into toggles only when they differ from `lastEmit*Ref` (defeats a real self-echo
  race where our own setProps round-trips back as props and wipes the initial state).
- **EditControl** (native v2): leaflet-draw is Leaflet 1-only (15 v1-isms, 31 mouse-event
  usages) — DOA on v2. We ship a native replacement: a toolbar `Control` + click-based
  drawing handlers (marker / polyline / polygon / rectangle / circle / delete) that drop
  shapes into an internal `FeatureGroup` and round-trip `geojson` + `n_drawn` + `lastAction`
  to Python. Polyline / polygon use `dblclick` to finish (with `doubleClickZoom.disable()`).

## Conventions

- **Components**: defaults via destructured default parameters, **never `Component.defaultProps`**
  (React 18.3 deprecation warning; `react-docgen@5` reads both, so defaults survive).
- Prop docs: tag `[MUTABLE]` (accepts callback updates Python→map) or `[READONLY]`
  (written back map→Python) in the JSDoc — it shows up in the generated Python docstrings.
- Event handlers bound once in `useEffect([map])` must not close over changing props
  (use a `useRef` for counters — see `Marker.tsx` `n_clicks`).
- **Build pipeline gotchas**: `dash-generate-components` needs `pyyaml`; we dropped
  `--r-prefix`/`--jl-prefix` (R/JL generation crashes + we target PyPI only). `__init__.py`
  is hand-maintained (registers `_js_dist`); everything else in `dash_leaflet2/` is generated.
- **Showcase JS** (`assets/leaflet2_maps.js`): a new example = one `DEMOS` entry + one
  `docs/<slug>/{<slug>.md, example.py}` pair (`example.py` exports `component`). JS→Python uses `toStore()` (hardened `set_props` with retry — don't bypass it).
- **`lastmod:` rides the prose.** Every `docs/<slug>/<slug>.md` declares a
  sitemap date; `dash-improve-my-llms` >= 2.6.0 emits it verbatim and omits the
  tag when absent. Edit a page's prose → bump its `lastmod` in the SAME commit.
  Never script these from file mtimes (they reset on every Docker build, which
  re-creates the every-page-changed-today sitemap the 2.6.1 floor exists to
  end). The initial values came from `git log -1 --format=%cs -- <file>`.
  `tests/test_seo_icons.py` fails if the sitemap ever emits a date no page
  declared, and if crawler-head icon discovery comes back empty.

## More detail

Path-scoped rules in `.claude/rules/` load automatically when you open relevant files:
`leaflet2-v2-api.md` (any Leaflet code), `dash-components.md` (`src/ts/components/`),
`showcase-pages.md` (`docs/`). To scaffold a new component, use the `/new-component` skill.
