"""
Walking Sim — top-down RPG-style walking with the full pirate-captain sprite
library. Uses all 4 animation types (idle / walking / running / jumping) across
all 8 compass directions.

## Model

  * **Map stays north-up.** Bearing isn't driven. Pan-only camera-follow keeps
    the character at viewport center as they move; the world doesn't spin
    around them.
  * **Sprite stays at viewport center, with NO `rotationAngle` transform.**
    The character "turns" by selecting a different directional sprite frame.
  * **8-way D-pad input.** Arrow keys are direct compass directions: ArrowUp
    = north, ArrowRight = east, ArrowUp+ArrowRight = north-east, etc. The
    touch joystick is read the same way — its angle becomes a heading, its
    magnitude becomes a speed throttle. (This replaces the prior turn-and-
    throttle scheme; the joystick angle naturally maps to direction and the
    8 sprite poses become reachable.)
  * **Animation state machine:**
       speed = 0                      → `idle`,    facing SOUTH (toward camera)
       0 < speed < 0.6 * MAX_SPEED    → `walking`, facing heading
       speed ≥ 0.6 * MAX_SPEED        → `running`, facing heading
       Space pressed                  → `jumping`, plays through once
                                         then returns to active state
  * **Heading → direction** is snapped to the nearest 45° (one of 8 buckets).

## Controls

  * Arrow keys (with combinations): walk in that compass direction
  * Space: jump
  * Cmd / Ctrl + Arrow: pan the camera away from the walker
  * Touch joystick (auto-shown on mobile): drag = walk in that direction at
    a magnitude-scaled speed
  * Click the top-right MiniMap to toggle WALK ↔ EXPLORE mode. Each toggle
    is animated with a smooth `map.flyTo()` — the walker NEVER teleports.
      - WALK: the rAF loop drives the character (this whole file's behavior).
        Minimap shows broad surrounding context (zoom-5), free-pan disabled.
      - EXPLORE: the rAF loop sits out — no input is read, no center is pushed.
        The map is a normal dl2 map (pan/zoom freely). The joystick is hidden.
        The minimap "inverses" — it now pins on the WALKER's last position at
        zoom+3 (a small "return-home" preview).
      - Entry (WALK → EXPLORE): we snapshot the walker's position + the
        walking zoom, then flyTo the walker at a pulled-back zoom so the
        user can scout.
      - Exit (EXPLORE → WALK): flyTo BACK to that snapshot — the walker
        stays put exactly where they were (you can't use this as a
        teleport). The rAF's per-frame `center: pos` push is suppressed
        for the flyTo's duration so it can't snap-jump mid-glide.

## Tile stack

  * Main map: **Esri World Imagery** (satellite, 100%) with an **Esri
    NatGeo World Map** overlay on top at 50%. The NatGeo overlay's tiles
    cap at z16 (`maxZoom=16`) — it's invisible at walking zoom (18) where
    the satellite carries the scene, and progressively blends in as the
    EXPLORE flyTo pulls back to wider context.
  * MiniMap: **Esri World Street Map** — a flat reference map that reads
    well in a 160×160 thumbnail at any zoom level.
"""

import flexlayout_dash as dfl
import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, clientside_callback, dcc, html
from dash_iconify import DashIconify
from dl2_shared import info_panel

# Esri ArcGIS tile services. Note the {z}/{y}/{x} order (ArcGIS convention) —
# Leaflet's URL templating doesn't care about order, the placeholders are pure
# text substitution.
ESRI_WORLD_IMAGERY = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
ESRI_NATGEO = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}"
)
ESRI_STREET = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Street_Map/MapServer/tile/{z}/{y}/{x}"
)
# USGS National Map Hydro Cached — transparent raster overlay where every water
# feature (lake, river, ocean) is drawn as solid blue and land is fully
# transparent. The walking-sim uses it for BOTH visual feedback (a tinted
# overlay so the user sees the water) AND as the collision source — the rAF
# loop fetches the same tiles via a CORS-friendly hidden <canvas> and rejects
# any step that lands on a non-transparent pixel.
#
# Cap: z16. Beyond that the server 404s, so set `maxNativeZoom=16` to make
# Leaflet upscale the z16 tile at the walking zoom (z18) instead of breaking.
USGS_HYDRO = (
    "https://basemap.nationalmap.gov/arcgis/rest/services/"
    "USGSHydroCached/MapServer/tile/{z}/{y}/{x}"
)
USGS_HYDRO_MAX_NATIVE_Z = 16
ESRI_ATTR_IMAGERY = (
    "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, "
    "and the GIS User Community"
)
ESRI_ATTR_NATGEO = (
    "Tiles &copy; Esri &mdash; National Geographic, Esri, DeLorme, NAVTEQ, "
    "UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, iPC"
)

START = [28.022, -97.053]
START_ZOOM = 18

# Physics — kept in deg/sec; the integrator multiplies by dt. MAX_SPEED tuned
# so the character makes a brisk walking pace at zoom 18 and a clear running
# pace once over 60% speed (the running-animation threshold).
MIN_SPEED = 0.0
MAX_SPEED = 0.000016
ACCEL_PER_S = 0.000045  # ≈0.35 s from 0 → MAX_SPEED
DECEL_PER_S = 0.000060  # quicker auto-decel when input released
RUN_THRESHOLD = 0.60  # fraction of MAX_SPEED above which we use running animation
JUMP_DURATION_MS = 700  # one play-through of the jumping animation

SPRITE_SIZE = 72

# Sprite library layout — keep these constants in sync with
# assets/sprites/pirate_captain/. Frame counts must match the actual file
# counts in each direction folder.
DIRECTIONS = [
    "north",
    "north-east",
    "east",
    "south-east",
    "south",
    "south-west",
    "west",
    "north-west",
]
FRAMES_PER_ANIM = {"idle": 4, "walking": 6, "running": 8, "jumping": 9}


def _frames(anim: str, direction: str) -> list:
    n = FRAMES_PER_ANIM[anim]
    return [
        f"/assets/sprites/pirate_captain/{anim}/{direction}/frame_{i:03d}.png"
        for i in range(n)
    ]


# Build the full sprite map: SPRITES[anim][direction] -> list of frame URLs.
# Sent into the rAF loop as a single JS object so frame swaps are pure lookups.
SPRITES = {anim: {d: _frames(anim, d) for d in DIRECTIONS} for anim in FRAMES_PER_ANIM}

# Per-animation frame interval (ms). Running is faster, idle is slower —
# tuned to feel like a real walk / jog / breathing rhythm.
FRAME_MS = {
    "idle": 240,
    "walking": 110,
    "running": 70,
    "jumping": JUMP_DURATION_MS // 9,
}

# The initial DivIcon HTML — a single <img> slot. The rAF loop hot-swaps
# `.src` on every frame tick to play whichever animation is current.
SPRITE_DIVICON_HTML = (
    f'<img class="ws-sprite-frame" '
    f'src="{SPRITES["idle"]["south"][0]}" '
    f'style="width:{SPRITE_SIZE}px; height:{SPRITE_SIZE}px; '
    f'display:block; image-rendering:pixelated; pointer-events:none;">'
)


def _joystick_div(prefix: str):
    return html.Div(
        # `id` so a clientside callback can flip its inline display when mode changes
        # — we hide the joystick whenever the user clicks the minimap into EXPLORE.
        id=f"{prefix}-joystick",
        className="dl2-joystick",
        children=[
            html.Div(
                className="dl2-joystick-base",
                id=f"{prefix}-joystick-base",
                children=html.Div(
                    className="dl2-joystick-controller",
                    id=f"{prefix}-joystick-controller",
                ),
            ),
            html.Div(
                className="dl2-joystick-hint",
                children=[
                    DashIconify(icon="mdi:gesture-tap", width=14),
                    html.Span(" Drag to walk · tap center to stop"),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------
# Pane builders for the DashFlexLayout shell.
# Map gets the wide left tab; HUD + Controls share two tabs on the right.
# Splitting these into functions keeps the dfl `children=` list readable
# and mirrors the pattern in docs/tile-selector/example.py.
# ---------------------------------------------------------------------


def _map_pane():
    """Walker map + touch joystick. Returns a position:relative wrapper so
    the joystick (absolute) anchors to the map even inside the dfl tab."""
    return html.Div(
        className="ws-map-pane",
        children=[
            dl2.Map(
                id="ws-map",
                center=START,
                zoom=START_ZOOM,
                bearing=0,
                style={"height": "100%", "width": "100%"},
                children=[
                    # Two-layer basemap: Esri World Imagery (satellite, 100%) +
                    # Esri NatGeo World Map overlay (50%, caps at z16). At
                    # walking zoom (18) only the satellite is visible; NatGeo
                    # fades in as the EXPLORE flyTo pulls back.
                    dl2.TileLayer(
                        id="ws-tile-satellite",
                        url=ESRI_WORLD_IMAGERY,
                        attribution=ESRI_ATTR_IMAGERY,
                        opacity=1.0,
                    ),
                    dl2.TileLayer(
                        id="ws-tile-natgeo",
                        url=ESRI_NATGEO,
                        attribution="",
                        opacity=0.5,
                        maxZoom=16,
                    ),
                    # USGS Hydro: visible tint + collision source for the rAF
                    # loop. maxNativeZoom=16 because the server 404s past z16.
                    dl2.TileLayer(
                        id="ws-tile-hydro",
                        url=USGS_HYDRO,
                        attribution="",
                        opacity=0.35,
                        maxNativeZoom=USGS_HYDRO_MAX_NATIVE_Z,
                        maxZoom=22,
                    ),
                    dl2.Marker(
                        id="ws-walker",
                        position=START,
                        iconOptions={
                            "html": SPRITE_DIVICON_HTML,
                            "className": "ws-sprite-icon",
                            "iconSize": [SPRITE_SIZE, SPRITE_SIZE],
                            "iconAnchor": [SPRITE_SIZE // 2, SPRITE_SIZE // 2],
                        },
                        # No rotation — direction is conveyed by swapping the
                        # IMG src to a different 8-direction frame.
                        rotateWithMap=False,
                        rotationAngle=0,
                    ),
                    dl2.Polyline(
                        id="ws-trail",
                        positions=[START],
                        color="#1971c2",
                        weight=3,
                        opacity=0.5,
                        dashArray="4,4",
                    ),
                    # Minimap doubles as the WALK ↔ EXPLORE switch. A clientside
                    # callback flips ws-mode on every n_clicks bump.
                    dl2.MiniMap(
                        id="ws-minimap",
                        position="topright",
                        url=ESRI_STREET,
                        width=160,
                        height=160,
                        zoomLevelOffset=-5,
                        toggleDisplay=True,
                    ),
                ],
            ),
            _joystick_div("ws"),
        ],
    )


def _hud_pane():
    """Live state readouts: MODE / FACING / STATE / TERRAIN / BLOCKS /
    POSITION / throttle / viewport. All ids identical to the previous
    layout so existing callbacks bind unchanged."""
    return html.Div(
        className="ws-side-pane",
        children=dmc.Stack(
            [
                info_panel(
                    "HUD",
                    dmc.Stack(
                        [
                            dmc.Group(
                                [
                                    dmc.Stack(
                                        [
                                            dmc.Text("MODE", size="xs", c="dimmed"),
                                            dmc.Badge(
                                                id="ws-mode-badge",
                                                color="green",
                                                variant="light",
                                                size="lg",
                                                children="walk",
                                            ),
                                        ],
                                        gap=2,
                                    ),
                                    dmc.Stack(
                                        [
                                            dmc.Text("FACING", size="xs", c="dimmed"),
                                            dmc.Badge(
                                                id="ws-direction",
                                                color="blue",
                                                variant="light",
                                                size="lg",
                                                children="south",
                                            ),
                                        ],
                                        gap=2,
                                    ),
                                    dmc.Stack(
                                        [
                                            dmc.Text("STATE", size="xs", c="dimmed"),
                                            dmc.Badge(
                                                id="ws-anim",
                                                color="cyan",
                                                variant="light",
                                                size="lg",
                                                children="idle",
                                            ),
                                        ],
                                        gap=2,
                                    ),
                                ],
                                justify="space-between",
                            ),
                            dmc.Progress(
                                id="ws-throttle-bar",
                                value=0,
                                color="cyan",
                                size="sm",
                            ),
                            # TERRAIN: pixel sampled under the walker on the
                            # USGS Hydro overlay. BLOCKS: count of frames the
                            # rAF loop rejected because the step landed on water.
                            dmc.Group(
                                [
                                    dmc.Stack(
                                        [
                                            dmc.Text("TERRAIN", size="xs", c="dimmed"),
                                            dmc.Badge(
                                                id="ws-terrain",
                                                color="lime",
                                                variant="light",
                                                size="lg",
                                                children="land",
                                            ),
                                        ],
                                        gap=2,
                                    ),
                                    dmc.Stack(
                                        [
                                            dmc.Text("BLOCKS", size="xs", c="dimmed"),
                                            dmc.Badge(
                                                id="ws-blocks",
                                                color="gray",
                                                variant="light",
                                                size="lg",
                                                children="0",
                                            ),
                                        ],
                                        gap=2,
                                    ),
                                ],
                                justify="flex-start",
                                gap="md",
                            ),
                            dmc.Group(
                                [
                                    dmc.Text("POSITION", size="xs", c="dimmed"),
                                    dmc.Code(
                                        id="ws-position",
                                        children="...",
                                        style={"fontSize": "11px"},
                                    ),
                                ],
                                justify="space-between",
                            ),
                        ],
                        gap="sm",
                    ),
                ),
                info_panel(
                    "Viewport",
                    dmc.Code(
                        id="ws-viewport",
                        block=True,
                        style={"fontSize": "11px", "minHeight": "100px"},
                    ),
                ),
            ],
            gap="md",
            p="md",
        ),
    )


def _controls_pane():
    """Keyboard cheat sheet — no dynamic state, just reference."""
    return html.Div(
        className="ws-side-pane",
        children=dmc.Stack(
            [
                info_panel(
                    "Keyboard",
                    dmc.Stack(
                        [
                            dmc.Group(
                                [
                                    dmc.Kbd("←"),
                                    dmc.Kbd("→"),
                                    dmc.Kbd("↑"),
                                    dmc.Kbd("↓"),
                                    dmc.Text("8-way D-pad", size="sm"),
                                ],
                                gap="xs",
                            ),
                            dmc.Group(
                                [
                                    dmc.Kbd("↑"),
                                    dmc.Text("+", size="sm"),
                                    dmc.Kbd("→"),
                                    dmc.Text("= NE  (any 2 = diagonal)", size="sm"),
                                ],
                                gap="xs",
                            ),
                            dmc.Group(
                                [dmc.Kbd("Space"), dmc.Text("jump", size="sm")],
                                gap="xs",
                            ),
                            dmc.Divider(),
                            dmc.Group(
                                [
                                    dmc.Kbd("⌘"),
                                    dmc.Text("+", size="sm"),
                                    dmc.Kbd("←/→/↑/↓"),
                                    dmc.Text("pan camera", size="sm"),
                                ],
                                gap="xs",
                            ),
                        ],
                        gap=6,
                    ),
                ),
                info_panel(
                    "Touch",
                    dmc.Stack(
                        [
                            dmc.Group(
                                [
                                    DashIconify(icon="mdi:gesture-tap", width=16),
                                    dmc.Text(
                                        "Drag the joystick to walk — its angle "
                                        "is the heading, its magnitude is the "
                                        "speed throttle.",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ],
                                gap="xs",
                                wrap="nowrap",
                                align="flex-start",
                            ),
                        ],
                        gap=6,
                    ),
                ),
                info_panel(
                    "Minimap",
                    dmc.Text(
                        "Click the top-right minimap to toggle WALK ↔ EXPLORE. "
                        "Each toggle is animated with a smooth flyTo — the "
                        "walker never teleports.",
                        size="sm",
                    ),
                ),
            ],
            gap="md",
            p="md",
        ),
    )


# ---------------------------------------------------------------------
# DashFlexLayout model — walker map left (67%), HUD + Controls tabs
# share the right column (33%).
#
# tabEnableRenderOnDemand=False keeps every tab's DOM mounted at page
# load so the rAF loop's set_props calls (HUD updates) keep landing
# even when the user has switched away from the HUD tab. Same gotcha
# the tile-selector page documents.
# ---------------------------------------------------------------------
WS_MODEL = {
    "global": {
        "tabEnableClose": False,
        "tabEnableFloat": False,
        "tabEnableRename": False,
        "tabSetEnableMaximize": True,
        "tabEnableRenderOnDemand": False,
    },
    "layout": {
        "type": "row",
        "weight": 100,
        "children": [
            {
                "type": "tabset",
                "weight": 67,
                "children": [
                    {"type": "tab", "name": "Walking Sim", "id": "ws-pane-map"},
                ],
            },
            {
                "type": "tabset",
                "weight": 33,
                "selected": 0,
                "children": [
                    {"type": "tab", "name": "HUD", "id": "ws-pane-hud"},
                    {"type": "tab", "name": "Controls", "id": "ws-pane-controls"},
                ],
            },
        ],
    },
}


component = html.Div(
    id="ws-shell",
    # Initial class matches the default ws-mode='walk' so the zoom control
    # is hidden on first paint — no flash-of-visible-zoom before the
    # mode→class clientside callback fires.
    className="ws-flush-shell ws-mode-walk",
    children=[
        dfl.DashFlexLayout(
            id="ws-flex",
            model=WS_MODEL,
            useStateForModel=True,
            supportsPopout=False,
            children=[
                dfl.Tab(id="ws-pane-map", children=_map_pane()),
                dfl.Tab(id="ws-pane-hud", children=_hud_pane()),
                dfl.Tab(id="ws-pane-controls", children=_controls_pane()),
            ],
        ),
        dcc.Store(id="ws-tick", data=0),
        # 'walk' | 'explore'. Driven by minimap clicks; consumed by the rAF
        # loop (window._ws_mode mirrors it so the loop can read it without
        # re-binding). The flyTo anchor lives in window globals — see
        # toggle_mode_from_minimap below.
        dcc.Store(id="ws-mode", data="walk"),
    ],
)


clientside_callback(
    f"""
    (mapId) => {{
        // dfl mounts the tab's DOM asynchronously via React portals, so the
        // clientside callback can fire BEFORE the ws-map div is in the
        // document. The original early-return then bailed permanently —
        // leaving Leaflet's keyboard module enabled (arrows panned the map)
        // and the rAF loop / joystick wiring unrun. Poll until the div
        // arrives, then run the rest of setup exactly once.
        const runSetup = () => {{
        const root = document.getElementById('ws-map');
        if (!root) {{ setTimeout(runSetup, 80); return; }}
        if (root.dataset.wsLoopRunning) return;
        root.dataset.wsLoopRunning = '1';

        const SPRITES = {SPRITES!r};
        const FRAME_MS = {FRAME_MS!r};
        const MIN_SPEED = {MIN_SPEED};
        const MAX_SPEED = {MAX_SPEED};
        const ACCEL_PER_S = {ACCEL_PER_S};
        const DECEL_PER_S = {DECEL_PER_S};
        const RUN_THRESHOLD = {RUN_THRESHOLD};
        const JUMP_DURATION_MS = {JUMP_DURATION_MS};

        // 0=N, 1=NE, 2=E, 3=SE, 4=S, 5=SW, 6=W, 7=NW — matches DIRECTIONS order
        const DIR_NAMES = ['north','north-east','east','south-east',
                           'south','south-west','west','north-west'];
        const headingToDir = (h) => {{
            const idx = Math.round(((h % 360) + 360) % 360 / 45) % 8;
            return DIR_NAMES[idx];
        }};
        // Convert a (dx, dy) input vector (screen coords: +y down) to a compass
        // bearing in degrees (0=N, 90=E, 180=S, 270=W).
        const vecToHeading = (dx, dy) => {{
            const rad = Math.atan2(dx, -dy);   // y-down → compass
            return (rad * 180 / Math.PI + 360) % 360;
        }};

        const state = {{
            lat: {START[0]}, lng: {START[1]},
            heading: 0,           // last MOVEMENT heading (0=N)
            lastDir: 'south',     // last direction we picked for the sprite
            speed: 0,
            trail: [[{START[0]}, {START[1]}]],
            keys: new Set(),
            lastFrame: performance.now(),
            lastSpriteSwap: 0,
            spriteIdx: 0,
            currentAnim: 'idle',
            jumpEndsAt: 0,
            terrain: 'land',      // last-known terrain under the walker
            blocks: 0,            // count of full-block (slide failed) frames
            lastTerrainPushed: 'land',
            lastBlocksPushed: 0,
        }};

        // --- USGS Hydro collision sampler --------------------------------
        // The Hydro tileset is a TRANSPARENT raster overlay — water = solid
        // blue pixel, land = alpha 0. We fetch the same tile URLs that the
        // visible Hydro TileLayer fetches (with `crossOrigin='anonymous'` so
        // we can read pixels — verified CORS-OK on basemap.nationalmap.gov),
        // draw them into a 256-px scratch canvas once, and keep the raw
        // ImageData. Per-step terrain check = one Uint8 array lookup.
        //
        // Cap is z16 (the server 404s above). We always sample at z16 even
        // though the map is at z18 — Leaflet's `map.project([lat,lng], 16)`
        // gives the global pixel coord at z16 regardless of the displayed
        // zoom, and 2 m/px is plenty for a coastline-style barrier.
        const HYDRO_URL = {USGS_HYDRO!r};
        const HYDRO_Z = {USGS_HYDRO_MAX_NATIVE_Z};
        const sampleCanvas = document.createElement('canvas');
        sampleCanvas.width = 256; sampleCanvas.height = 256;
        const sampleCtx = sampleCanvas.getContext('2d', {{ willReadFrequently: true }});
        const tileCache = new Map();  // "z/x/y" -> {{ ready, data, errored }}

        const getHydroTile = (z, x, y) => {{
            const key = z + '/' + x + '/' + y;
            const cached = tileCache.get(key);
            if (cached) return cached;
            const entry = {{ ready: false, data: null, errored: false }};
            tileCache.set(key, entry);
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => {{
                sampleCtx.clearRect(0, 0, 256, 256);
                sampleCtx.drawImage(img, 0, 0, 256, 256);
                try {{
                    entry.data = sampleCtx.getImageData(0, 0, 256, 256).data;
                    entry.ready = true;
                }} catch (e) {{ entry.errored = true; }}
            }};
            img.onerror = () => {{ entry.errored = true; }};
            img.src = HYDRO_URL.replace('{{z}}', z)
                               .replace('{{x}}', x)
                               .replace('{{y}}', y);
            return entry;
        }};

        // Returns 'water' | 'land' | 'unknown' (tile not yet loaded).
        // 'unknown' = pass — we don't want to freeze the walker on first
        // boot waiting for a fetch; tiles cache within ~200 ms.
        const sampleTerrainAt = (lat, lng) => {{
            const m = root.__dl2_map;
            if (!m) return 'unknown';
            const pt = m.project([lat, lng], HYDRO_Z);
            const tx = Math.floor(pt.x / 256);
            const ty = Math.floor(pt.y / 256);
            const inX = Math.floor(pt.x - tx * 256);
            const inY = Math.floor(pt.y - ty * 256);
            const tile = getHydroTile(HYDRO_Z, tx, ty);
            if (tile.errored) return 'land';   // assume passable if tile broken
            if (!tile.ready || !tile.data) return 'unknown';
            const alpha = tile.data[(inY * 256 + inX) * 4 + 3];
            return alpha > 16 ? 'water' : 'land';
        }};

        // Warm up a 3x3 tile block around (lat, lng). Cheap on cache-hit; on
        // cache-miss it queues the fetch so by the time the walker arrives,
        // the pixels are ready. Called on init + when the walker crosses a
        // tile boundary.
        let lastWarmTx = null, lastWarmTy = null;
        const prewarm = (lat, lng) => {{
            const m = root.__dl2_map;
            if (!m) return;
            const pt = m.project([lat, lng], HYDRO_Z);
            const tx = Math.floor(pt.x / 256);
            const ty = Math.floor(pt.y / 256);
            if (tx === lastWarmTx && ty === lastWarmTy) return;
            lastWarmTx = tx; lastWarmTy = ty;
            for (let dy = -1; dy <= 1; dy++) {{
                for (let dx = -1; dx <= 1; dx++) {{
                    getHydroTile(HYDRO_Z, tx + dx, ty + dy);
                }}
            }}
        }};
        // Kick off the first prewarm as soon as the map handle appears.
        const prewarmWhenReady = () => {{
            if (root.__dl2_map) prewarm(state.lat, state.lng);
            else setTimeout(prewarmWhenReady, 50);
        }};
        prewarmWhenReady();

        window._dl2_joystick = window._dl2_joystick || {{ x: 0, y: 0, active: false }};
        const joy = window._dl2_joystick;

        // Mode flag mirrored from the ws-mode dcc.Store via a tiny clientside
        // callback (see set_ws_mode_flag below). Default 'walk' until the toggle
        // hook fires. The rAF tick reads this on every frame — when it's
        // 'explore' the loop skips input + camera-follow so the map operates
        // like a normal dl2 map.
        window._ws_mode = window._ws_mode || 'walk';

        // --- keyboard ---
        // Disable Leaflet's keyboard module — see flight_sim.py header for why.
        // tl;dr: Leaflet intercepts arrows once the map has focus and
        // stopPropagation()s the event, so our window listener never fires.
        const disableLeafletKeyboard = () => {{
            const m = root.__dl2_map;
            if (m && m.keyboard && typeof m.keyboard.disable === 'function') {{
                try {{ m.keyboard.disable(); }} catch (e) {{}}
                return;
            }}
            setTimeout(disableLeafletKeyboard, 80);
        }};
        disableLeafletKeyboard();

        const PAN_STEP_PX = 60;
        const panBy = (dx, dy) => {{
            const m = root.__dl2_map;
            if (m && typeof m.panBy === 'function') m.panBy([dx, dy]);
        }};
        const onDown = (e) => {{
            const t = e.target;
            if (t && /input|textarea|select/i.test(t.tagName)) return;
            if (e.metaKey || e.ctrlKey) {{
                if (e.key === 'ArrowLeft')  {{ panBy(-PAN_STEP_PX, 0); e.preventDefault(); }}
                if (e.key === 'ArrowRight') {{ panBy(PAN_STEP_PX, 0);  e.preventDefault(); }}
                if (e.key === 'ArrowUp')    {{ panBy(0, -PAN_STEP_PX); e.preventDefault(); }}
                if (e.key === 'ArrowDown')  {{ panBy(0, PAN_STEP_PX);  e.preventDefault(); }}
                return;
            }}
            if (['ArrowLeft','ArrowRight','ArrowUp','ArrowDown',' ','Space'].includes(e.key)) {{
                state.keys.add(e.key);
                if ((e.key === ' ' || e.key === 'Space') && state.jumpEndsAt <= performance.now()) {{
                    // Start a jump (cooldown enforced)
                    state.jumpEndsAt = performance.now() + JUMP_DURATION_MS;
                    state.currentAnim = 'jumping';
                    state.spriteIdx = 0;
                    state.lastSpriteSwap = performance.now();
                }}
                e.preventDefault();
            }}
        }};
        const onUp = (e) => state.keys.delete(e.key);
        window.addEventListener('keydown', onDown);
        window.addEventListener('keyup', onUp);

        // --- touch joystick ---
        const base = document.getElementById('ws-joystick-base');
        const ctrl = document.getElementById('ws-joystick-controller');
        if (base && ctrl && !base.dataset.wired) {{
            base.dataset.wired = '1';
            const reset = () => {{
                ctrl.style.transform = 'translate(-50%, -50%)';
                joy.x = 0; joy.y = 0; joy.active = false;
            }};
            reset();
            let activePtr = null;
            base.addEventListener('pointerdown', (e) => {{
                if (activePtr !== null) return;
                activePtr = e.pointerId;
                base.setPointerCapture(e.pointerId);
                joy.active = true;
                e.preventDefault();
            }});
            base.addEventListener('pointermove', (e) => {{
                if (e.pointerId !== activePtr) return;
                const r = base.getBoundingClientRect();
                const radius = r.width / 2;
                const dx = e.clientX - (r.left + radius);
                const dy = e.clientY - (r.top + radius);
                const mag = Math.sqrt(dx*dx + dy*dy);
                const k = mag > radius ? radius / mag : 1;
                const cx = dx * k, cy = dy * k;
                ctrl.style.transform = `translate(calc(-50% + ${{cx}}px), calc(-50% + ${{cy}}px))`;
                joy.x = cx / radius;
                joy.y = cy / radius;
            }});
            const onPtrUp = (e) => {{
                if (e.pointerId !== activePtr) return;
                try {{ base.releasePointerCapture(e.pointerId); }} catch (err) {{}}
                activePtr = null;
                reset();
            }};
            base.addEventListener('pointerup', onPtrUp);
            base.addEventListener('pointercancel', onPtrUp);
        }}

        // Preload all sprite URLs so the first walking step / first running-step
        // / first jump doesn't show a transparent flash while the PNG decodes.
        for (const anim of Object.keys(SPRITES)) {{
            for (const dir of Object.keys(SPRITES[anim])) {{
                for (const src of SPRITES[anim][dir]) {{
                    const i = new Image(); i.src = src;
                }}
            }}
        }}

        const tick = (now) => {{
            const dt = Math.min(0.1, (now - state.lastFrame) / 1000);
            state.lastFrame = now;

            // EXPLORE mode: bail out before reading input or pushing the camera.
            // The map operates as a normal dl2 map (free pan/zoom); the walker
            // stays put visually. We DO publish the walker's last-known position
            // to a window var so the page can snapshot it on a back-to-walk
            // toggle (and pin the minimap on it via centerFixed).
            if (window._ws_mode === 'explore') {{
                window._ws_walker_pos = [state.lat, state.lng];
                if (!document.getElementById('ws-map')) return;
                requestAnimationFrame(tick);
                return;
            }}

            // --- read input → direction vector (dx, dy) in screen coords ---
            const k = state.keys;
            let dx = 0, dy = 0;
            if (k.has('ArrowUp'))    dy -= 1;
            if (k.has('ArrowDown'))  dy += 1;
            if (k.has('ArrowLeft'))  dx -= 1;
            if (k.has('ArrowRight')) dx += 1;
            if (joy.active && (Math.abs(joy.x) > 0.05 || Math.abs(joy.y) > 0.05)) {{
                // Joystick takes precedence when actively engaged. (If both
                // keys and joystick are active we trust the joystick because
                // it's the "more deliberate" input on touch devices.)
                dx = joy.x; dy = joy.y;
            }}
            const inputMag = Math.min(1, Math.sqrt(dx*dx + dy*dy));

            // --- update heading + speed ---
            if (inputMag > 0.05) {{
                state.heading = vecToHeading(dx, dy);
                // Ramp speed toward target (target = inputMag * MAX_SPEED)
                const target = inputMag * MAX_SPEED;
                if (state.speed < target) {{
                    state.speed = Math.min(target, state.speed + ACCEL_PER_S * dt);
                }} else {{
                    state.speed = Math.max(target, state.speed - DECEL_PER_S * dt);
                }}
            }} else {{
                // No input → decel to zero.
                state.speed = Math.max(MIN_SPEED, state.speed - DECEL_PER_S * dt);
            }}

            // --- integrate position (with Hydro-collision slide) ---
            //
            // Take the desired step, but before committing it ask the Hydro
            // sampler whether the destination is water. If yes, try sliding
            // along each axis separately — so walking diagonally INTO a
            // coastline glides along it instead of jamming. If even the slide
            // is blocked, the walker is up against a wall: we bleed speed
            // off faster than normal decel and tick the BLOCKS counter.
            if (state.speed > 0) {{
                const hd = state.heading * Math.PI / 180;
                const stepLat = state.speed * Math.cos(hd) * dt * 60;
                const stepLng = state.speed * Math.sin(hd) * dt * 60;

                const tryMove = (dLat, dLng) => {{
                    const t = sampleTerrainAt(state.lat + dLat, state.lng + dLng);
                    // 'unknown' (tile mid-load) = allow so the player isn't
                    // frozen during initial paint; 'water' = reject.
                    if (t === 'water') return false;
                    state.lat += dLat;
                    state.lng += dLng;
                    return true;
                }};

                let moved = tryMove(stepLat, stepLng);
                if (!moved) {{
                    // Try axis-only slides (lng-only, then lat-only).
                    if (tryMove(0, stepLng))      moved = true;
                    else if (tryMove(stepLat, 0)) moved = true;
                }}
                if (!moved) {{
                    // Truly walled in this frame. Bleed speed off ~4× faster
                    // than normal decel so we don't grind against the wall.
                    state.speed = Math.max(MIN_SPEED, state.speed - DECEL_PER_S * dt * 4);
                    state.blocks += 1;
                }}

                if (state.trail.length === 0 ||
                    Math.hypot(state.lat - state.trail[state.trail.length-1][0],
                               state.lng - state.trail[state.trail.length-1][1]) > 0.00003) {{
                    state.trail.push([state.lat, state.lng]);
                    if (state.trail.length > 200) state.trail.shift();
                }}
            }}

            // Refresh the cached terrain readout (used by the HUD) AND keep
            // the tile prewarm in sync with the walker's current tile.
            const here = sampleTerrainAt(state.lat, state.lng);
            if (here !== 'unknown') state.terrain = here;
            prewarm(state.lat, state.lng);

            // --- animation state machine ---
            // Priority: jumping > running > walking > idle. The jumping animation
            // runs once through (length is JUMP_DURATION_MS); when it ends, we
            // fall back to whichever movement state is active.
            const speedFrac = state.speed / MAX_SPEED;
            let nextAnim, nextDir;
            const jumping = now < state.jumpEndsAt;
            if (jumping) {{
                nextAnim = 'jumping';
                // Lock direction at jump-start (use heading at start, or south if idle).
                nextDir = state.lastDir;
            }} else if (speedFrac >= RUN_THRESHOLD) {{
                nextAnim = 'running';
                nextDir = headingToDir(state.heading);
            }} else if (state.speed > MAX_SPEED * 0.02) {{
                nextAnim = 'walking';
                nextDir = headingToDir(state.heading);
            }} else {{
                nextAnim = 'idle';
                nextDir = 'south';   // face the user when idle
            }}

            // On a state TRANSITION, reset the frame index so the new animation
            // starts at frame 0 (otherwise a transition mid-cycle can look jumpy).
            if (nextAnim !== state.currentAnim || nextDir !== state.lastDir) {{
                state.currentAnim = nextAnim;
                state.lastDir = nextDir;
                state.spriteIdx = 0;
                state.lastSpriteSwap = now - FRAME_MS[nextAnim];  // force immediate swap
            }}

            // --- swap sprite frame on the interval ---
            const interval = FRAME_MS[state.currentAnim];
            const frames = SPRITES[state.currentAnim][state.lastDir];
            if (now - state.lastSpriteSwap >= interval) {{
                state.lastSpriteSwap = now;
                state.spriteIdx = (state.spriteIdx + 1) % frames.length;
                const imgs = document.querySelectorAll('.ws-sprite-frame');
                imgs.forEach((img) => {{ img.src = frames[state.spriteIdx]; }});
            }}

            // --- push state to components (camera-follow translation only) ---
            const pos = [state.lat, state.lng];
            window._ws_walker_pos = pos;
            dash_clientside.set_props('ws-walker', {{ position: pos }});
            // The mode-toggle flyTo (see toggle_mode_from_minimap below) sets
            // `window._ws_skip_camera_until` to the timestamp the flyTo ends.
            // While that's in the future, skip the per-frame center push so the
            // glide animation isn't fought by an instant `setView(pos)` on every
            // tick (Map.tsx's external-center effect uses {{animate: false}}).
            if (!(window._ws_skip_camera_until && now < window._ws_skip_camera_until)) {{
                dash_clientside.set_props('ws-map',    {{ center: pos }});  // bearing stays 0
            }}
            dash_clientside.set_props('ws-trail',  {{ positions: state.trail }});

            // HUD
            const pct = Math.round(speedFrac * 100);
            dash_clientside.set_props('ws-direction',    {{ children: state.lastDir }});
            dash_clientside.set_props('ws-anim',         {{ children: state.currentAnim }});
            dash_clientside.set_props('ws-throttle-bar', {{ value: pct }});
            dash_clientside.set_props('ws-position',     {{ children: pos[0].toFixed(5) + ', ' + pos[1].toFixed(5) }});
            // Only push terrain/blocks when they CHANGE — these update much
            // less often than position, and Dash's set_props is not free.
            if (state.terrain !== state.lastTerrainPushed) {{
                state.lastTerrainPushed = state.terrain;
                dash_clientside.set_props('ws-terrain', {{
                    children: state.terrain,
                    color: state.terrain === 'water' ? 'blue' : 'lime',
                }});
            }}
            if (state.blocks !== state.lastBlocksPushed) {{
                state.lastBlocksPushed = state.blocks;
                dash_clientside.set_props('ws-blocks', {{
                    children: String(state.blocks),
                    color: state.blocks > 0 ? 'red' : 'gray',
                }});
            }}

            if (!document.getElementById('ws-map')) return;
            requestAnimationFrame(tick);
        }};
        requestAnimationFrame(tick);
        }};  // end runSetup
        runSetup();
        return window.dash_clientside.no_update;
    }}
    """,
    Output("ws-tick", "data"),
    Input("ws-map", "id"),
)


@callback(Output("ws-viewport", "children"), Input("ws-map", "viewport"))
def viewport(vp):
    if not vp:
        return "—"
    return ("center: [{:.5f}, {:.5f}]\nzoom: {}\nbearing: {}° (north-up)").format(
        vp["center"][0],
        vp["center"][1],
        vp["zoom"],
        round(vp.get("bearing") or 0),
    )


# --- WALK ↔ EXPLORE: minimap click is the mode switch ------------------------
# Each click on the minimap (anywhere on its tiles — the corner toggle button is
# excluded by MiniMap itself) bumps ws-minimap.n_clicks. We flip ws-mode on every
# bump and run a `flyTo` animation; the walker is NEVER moved. Done clientside so
# the toggle feels instant and so we can talk to the Leaflet map directly via the
# handle Map.tsx publishes on the root div as `__dl2_map`.
clientside_callback(
    """
    (n, currentMode) => {
        if (!n) return window.dash_clientside.no_update;
        const next = currentMode === 'walk' ? 'explore' : 'walk';
        // Mirror to the window flag the rAF loop reads. Doing this here instead
        // of in a separate "mode -> flag" callback removes a round-trip and
        // avoids a one-tick gap where the loop still drives the camera mid-
        // transition.
        window._ws_mode = next;

        const m = document.getElementById('ws-map')?.__dl2_map;
        if (!m) return next;

        // Animation budget for both flyTos (seconds). Long enough to feel
        // deliberate, short enough not to annoy. Picked by feel.
        const FLY_DURATION = 1.5;
        // EXPLORE pulls the camera back by this many zoom levels for scouting.
        const EXPLORE_ZOOM_OUT = 4;

        if (next === 'explore') {
            // WALK -> EXPLORE: snapshot the walker's pos + the walking zoom
            // so the return flyTo can land exactly where we left them. Then
            // fly OUT to a wider vantage centered on the walker.
            const walkerPos = window._ws_walker_pos
                              || [m.getCenter().lat, m.getCenter().lng];
            window._ws_walk_anchor = walkerPos;
            window._ws_walk_zoom = m.getZoom();
            const minZ = (typeof m.getMinZoom === 'function')
                            ? m.getMinZoom() : 1;
            const targetZoom = Math.max(minZ, m.getZoom() - EXPLORE_ZOOM_OUT);
            m.flyTo(walkerPos, targetZoom, { duration: FLY_DURATION });
        } else {
            // EXPLORE -> WALK: the walker did NOT move while we were exploring,
            // so fly BACK to the same anchor + walking zoom we snapshotted on
            // entry. Suppress the rAF's per-frame center push until the flyTo
            // ends, otherwise its instant `setView(pos)` snap-jumps the map
            // before the glide can play. The +100ms guard absorbs any easing
            // tail Leaflet adds beyond the nominal duration.
            const target = window._ws_walk_anchor
                            || window._ws_walker_pos
                            || [m.getCenter().lat, m.getCenter().lng];
            const targetZoom = window._ws_walk_zoom || 18;
            window._ws_skip_camera_until = performance.now()
                                           + (FLY_DURATION * 1000) + 100;
            m.flyTo(target, targetZoom, { duration: FLY_DURATION });
        }
        return next;
    }
    """,
    Output("ws-mode", "data"),
    Input("ws-minimap", "n_clicks"),
    State("ws-mode", "data"),
    prevent_initial_call=True,
)


# Mirror ws-mode -> the MiniMap's `centerFixed` + `zoomLevelOffset` + the HUD
# badge. WALK = broad context (track main map, zoom -5); EXPLORE = pin on the
# walker, zoom +3 (a small "return-home" preview). Reading the walker position
# from the window var avoids a Store round-trip — the rAF loop has been
# publishing it every tick.
clientside_callback(
    """
    (mode) => {
        const wp = window._ws_walker_pos || null;
        if (mode === 'explore') {
            return [wp, 3, 'explore', 'orange'];
        }
        // walk: clear the fixed center so the inner map tracks the main map again.
        return [null, -5, 'walk', 'green'];
    }
    """,
    Output("ws-minimap", "centerFixed"),
    Output("ws-minimap", "zoomLevelOffset"),
    Output("ws-mode-badge", "children"),
    Output("ws-mode-badge", "color"),
    Input("ws-mode", "data"),
)


# Hide the joystick wrapper while in EXPLORE mode (the user is now using the
# map normally — joystick has nothing to drive). Toggling display via inline
# style respects the existing `.dl2-joystick` CSS so the hover-opacity etc.
# stays correct when shown again.
clientside_callback(
    """
    (mode) => ({ display: mode === 'explore' ? 'none' : '' })
    """,
    Output("ws-joystick", "style"),
    Input("ws-mode", "data"),
)


# Mirror ws-mode onto the flush-shell className so CSS can gate any UI that
# should differ between modes (currently: the Leaflet zoom control, hidden in
# WALK / shown in EXPLORE — see assets/walking_sim.css). Setting className from
# the same shape that markup writes ('ws-flush-shell ws-mode-<mode>') keeps the
# host class deterministic and easy to grep for.
clientside_callback(
    """
    (mode) => 'ws-flush-shell ws-mode-' + (mode || 'walk')
    """,
    Output("ws-shell", "className"),
    Input("ws-mode", "data"),
)


# No color-scheme tile swap here: the Esri tile stack (World Imagery + NatGeo
# overlay) is theme-independent. The app's light/dark toggle still affects DMC
# chrome and the Leaflet UI glass styling, just not the tiles themselves.
