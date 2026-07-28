---
name: walking-sim
description: Technical wiring of /walking-sim — top-down 8-way RPG-style walker on a dl2.Map with sprite-sheet animation, USGS hydro pixel-collision, free pan/zoom EXPLORE mode, and a touch joystick. Use when porting or debugging this page or building a sibling sim.
---

# /walking-sim — technical wiring

A rAF-driven character that walks an 8-direction pirate-captain sprite over Esri
World Imagery, with water tiles (USGS Hydro) acting as solid collision. One big
clientside callback owns the entire game loop; Dash callbacks are thin wrappers
around mode flips. Total: 1,129 lines (`docs/walking-sim/example.py`).

## Map of the file

| Lines | What it does |
| --- | --- |
| 1-59 | Module docstring — the mental model (north-up, sprite-frame turning, 8-way D-pad, animation state machine, WALK ↔ EXPLORE) |
| 61-156 | Imports + tile-URL constants + sprite constants (`SPRITE_SIZE=72`, `FRAMES_PER_ANIM`, `FRAME_MS`, `SPRITES` dict — flat 8×4 = 32 directional frame lists) |
| 168-191 | `_joystick_div(prefix)` — the touch joystick markup (relative-positioned host with `dl2-joystick-base` + `controller`) |
| 200-280 | `_map_pane()` — `dl2.Map` + 3 tile layers + `dl2.Marker` (DivIcon img slot) + `dl2.Polyline` trail + `dl2.MiniMap` |
| 282-407 | `_hud_pane()` — MODE / FACING / STATE / TERRAIN / BLOCKS / POSITION badges + viewport code block |
| 409-492 | `_controls_pane()` — keyboard cheatsheet, static |
| 504-562 | `WS_MODEL` (dfl layout) + `component` (the page object — dfl + 2 dcc.Stores) |
| 565-998 | **The single big clientside_callback** — the entire game loop. See "The rAF loop" below |
| 1001-1010 | `viewport()` server callback — pretty-prints the map's `viewport` prop into the HUD code block |
| 1019-1073 | `toggle_mode_from_minimap` clientside — minimap click ⇒ WALK ↔ EXPLORE flyTo |
| 1081-1124 | Mode-mirror clientside callbacks — minimap `centerFixed`, joystick visibility, host className |

## Component anchors (DOM ids)

These are the ids the rAF loop and clientside callbacks reach for. They MUST be
present in the layout — the loop's first action is `getElementById('ws-map')`
followed by a `__dl2_map` lookup.

| Id | Type | Role |
| --- | --- | --- |
| `ws-shell` | `html.Div` | flush-shell host; className tracks mode (`ws-mode-walk` / `ws-mode-explore`) |
| `ws-map` | `dl2.Map` | the gameplay map — also the `__dl2_map` carrier |
| `ws-tile-satellite` / `ws-tile-natgeo` / `ws-tile-hydro` | `dl2.TileLayer` | base + overlay + collision-source |
| `ws-walker` | `dl2.Marker` | sprite holder — its `iconOptions.html` contains the `<img class="ws-sprite-frame">` |
| `ws-trail` | `dl2.Polyline` | breadcrumb path (last 200 positions) |
| `ws-minimap` | `dl2.MiniMap` | clicked to toggle EXPLORE; `centerFixed` / `zoomLevelOffset` mode-driven |
| `ws-joystick` (+ `-base`, `-controller`) | `html.Div` | touch input wrapper, hidden in EXPLORE |
| `ws-tick` | `dcc.Store` | Output target — never read; the loop owns its state in JS closures |
| `ws-mode` | `dcc.Store` | "walk" or "explore"; written by minimap click, read by 3 sibling callbacks |
| `ws-direction` / `ws-anim` / `ws-throttle-bar` / `ws-position` / `ws-terrain` / `ws-blocks` / `ws-viewport` / `ws-mode-badge` | various | HUD readouts, written via `set_props` |

## The rAF loop (lines 565-998)

The whole loop is one f-string with the SPRITES dict / physics constants /
collision-tile URL templated in. The pattern is the load-bearing trick:

```python
clientside_callback(
    f"""(mapId) => {{ ... const SPRITES = {SPRITES!r}; ... }}""",
    Output("ws-tick", "data"),
    Input("ws-map", "id"),
)
```

Pinned by `Input("ws-map", "id")` — fires exactly once when the dl2.Map mounts.
The function bails on re-entry via `root.dataset.wsLoopRunning = '1'`. Inside the
closure:

1. **Setup phase** (runs once):
   - `runSetup` polls every 80ms until `document.getElementById('ws-map')` exists,
     because dfl mounts the map tab's DOM via a React portal after the callback
     fires. The original code returned early on a missing root and never recovered.
   - Defines a USGS-Hydro tile cache (`Map<"z/x/y", {ready,data,errored}>`) + a
     `sampleTerrainAt(lat, lng)` function that does one alpha lookup in the
     pre-decoded tile bitmap.
   - `disableLeafletKeyboard()` polls for `m.keyboard.disable()` — Leaflet's
     keyboard module steals arrow keys before our `window` listener sees them.
   - Wires `keydown` / `keyup` for arrows + space (jump) + Cmd/Ctrl-arrow (pan).
   - Wires the joystick: `pointerdown` → capture, `pointermove` → store
     `joy.x` / `joy.y` in [-1, 1], `pointerup` → reset.
   - Pre-decodes every sprite URL with `new Image(); i.src = url` so the first
     animation frame swap doesn't flash transparent while a PNG decodes.

2. **`tick(now)` — the per-frame loop** (called via `requestAnimationFrame`):
   - **EXPLORE early-return**: when `window._ws_mode === 'explore'`, publishes
     the last walker position to `window._ws_walker_pos` and reschedules.
     No input read, no camera push.
   - **Input → vector**: arrow keys → `(dx, dy)` ∈ {-1, 0, 1}²; joystick
     overrides when actively engaged.
   - **Heading + speed**: `vecToHeading(dx, dy)` returns compass degrees;
     speed ramps toward `target = mag * MAX_SPEED` with `ACCEL_PER_S` /
     `DECEL_PER_S`.
   - **Hydro-collision slide**: try the full step. If `sampleTerrainAt`
     returns `'water'`, try the lng-only slide, then the lat-only slide.
     If all three are blocked, bleed 4× decel and increment `state.blocks`.
     `'unknown'` (tile not loaded yet) is treated as pass so a fresh page
     load doesn't freeze the walker.
   - **Animation state machine**: `jumping > running > walking > idle`,
     where running fires above `RUN_THRESHOLD * MAX_SPEED`. On transition
     the frame index resets to 0; jumping locks direction to `state.lastDir`
     at jump-start.
   - **Sprite hot-swap**: every `FRAME_MS[anim]` the `.src` of every
     `.ws-sprite-frame` img is rewritten to the next URL in the
     `SPRITES[anim][dir]` array. The DivIcon container never re-mounts.
   - **Push outputs**: `set_props('ws-walker', {position: pos})`,
     `set_props('ws-map', {center: pos})` (camera follow),
     `set_props('ws-trail', {positions: state.trail})`, plus HUD readouts.
     Terrain / blocks are pushed only on CHANGE (cheap).
   - **flyTo suppression**: while `window._ws_skip_camera_until > now`, the
     per-frame `center` push is skipped so the EXPLORE-exit flyTo can play
     without being fought by an instant `setView(pos)` on every tick.

## WALK ↔ EXPLORE (lines 1019-1124)

Minimap `n_clicks` → flip `ws-mode.data` AND `window._ws_mode` from the same
clientside callback (no round-trip — the rAF loop reads the window flag the
instant it changes).

- **WALK → EXPLORE**: snapshot `window._ws_walker_pos` into `_ws_walk_anchor` +
  `m.getZoom()` into `_ws_walk_zoom`; `m.flyTo(walkerPos, zoom - 4)`.
- **EXPLORE → WALK**: set `window._ws_skip_camera_until = now + FLY_DURATION*1000 + 100`;
  `m.flyTo(_ws_walk_anchor, _ws_walk_zoom)`. The walker never moves while in
  EXPLORE, so flyTo lands the camera back on top of it.

Three sibling clientside callbacks mirror the mode:
- `ws-minimap.centerFixed` + `zoomLevelOffset`: WALK = follow main map at zoom-5;
  EXPLORE = pin on walker at zoom+3.
- `ws-joystick.style.display`: hidden in EXPLORE.
- `ws-shell.className`: `ws-flush-shell ws-mode-<mode>` so CSS can hide the
  Leaflet zoom control in WALK (see `assets/walking_sim.css`).

## CSS (assets/walking_sim.css)

- `.ws-flush-shell` is `position: fixed` with `top` / `left` set to the AppShell's
  header + navbar offsets (74 lines total).
- `.ws-mode-walk .leaflet-control-zoom` is `display: none` — in walk mode the
  zoom is locked to whatever the rAF loop sees.
- `.ws-sprite-frame { image-rendering: pixelated; pointer-events: none; }` —
  prevents anti-aliasing of the 8px source bitmap and lets clicks reach the map.

## Sprite asset layout (assets/sprites/pirate_captain/)

```
pirate_captain/<anim>/<direction>/frame_<idx:03d>.png
```

`anim ∈ {idle, walking, running, jumping}`, `direction` is one of 8 compass slugs,
`idx` zero-padded to 3 digits. Frame counts: idle=4, walking=6, running=8,
jumping=9. Each frame is 64×64 RGBA PNG, displayed at 72×72 (the DivIcon
upscales 8 px). Any sprite exporter that emits this exact layout drops in, so a
generated sprite drops in without code changes.

## Required runtime files when porting

- `docs/walking-sim/example.py` itself (rename / re-house the layout function as
  needed; expose `component` as your page's layout)
- `assets/walking_sim.css`
- `assets/sprites/pirate_captain/**` (32 directories × N frames)
- `dl2_shared.info_panel` (or inline the helper — see repo root `dl2_shared.py`)
- `dash_leaflet2 >= 0.0.1`, `flexlayout_dash >= 1.1.0`, `dash_iconify`,
  `dash_mantine_components >= 2.4`

## Non-obvious traps

1. **`Input("ws-map", "id")` is the only mount signal you'll get**. If the dl2.Map
   re-mounts (e.g. tab close/open), the loop's `data-ws-loop-running` flag
   prevents re-init. To support remount, clear that dataset attribute in the
   unmount path.
2. **CORS** on the Hydro tile sample: `img.crossOrigin = 'anonymous'`. USGS
   National Map serves CORS-OK headers — change the URL and the alpha read will
   throw a SecurityError.
3. **`maxNativeZoom=16` on the hydro layer** — server 404s above z16. Without it
   the tile fetches break at the walking zoom (z18).
4. **Avoid `animate: true` on the camera-follow `setView`**. The compiled
   `dl2.Map` Python→Leaflet center effect uses `{animate: false}` for exactly
   this reason — a 250ms animation starting every rAF would dog-pile.
5. **The Esri NatGeo overlay** is layered at 50% opacity and caps at z16. At
   walking zoom (18) it's invisible (no tile), at EXPLORE-out it fades in.
   That's the only "level-of-detail" trick on the page — it doesn't need any
   custom logic.
6. **EXPLORE doesn't teleport.** The walker stays put visually because the rAF
   loop early-returns. The state object's `lat/lng` are also untouched. On
   EXPLORE → WALK, flyTo returns the camera; the walker is exactly where you
   left it.
