"""
Flight Sim — single-player, keyboard + touch-joystick, rAF physics loop.

Rotation model (revised, matching DashEcommerce/pages/map/fly.py):

  * The MAP STAYS NORTH-UP — `bearing` is left at 0 on this page. The previous
    iteration rotated the camera with the heading; the user wanted the fly.py
    pattern instead, where the player gets the orientation cue from the SPRITE.
  * The MARKER ROTATES — `rotateWithMap=False` plus `rotationAngle = heading`
    drives the airplane sprite to face the direction of travel. The sprite is
    the top-down airplane PNG, intrinsically pointing UP (north) — so a
    rotationAngle of 90° = nose pointing east, 180° = south, etc.

  * The dl2.Map(bearing=…) machinery still EXISTS and the dl2-rotation-wrapper
    is still there — we just don't use it from this page. Rotation-basic still
    demonstrates the camera-rotation capability.

Controls

  * Keyboard (desktop): ArrowLeft/Right turn the plane, ArrowUp throttles,
    ArrowDown brakes, Space hard-stops, Cmd/Ctrl+Arrow pans the camera.
  * Touch joystick (mobile, auto-shown via @media (hover: none)
    and (pointer: coarse)): pushing horizontally turns, pushing vertically
    throttles/brakes — same semantic as the arrow keys but as a continuous
    analog signal. Joystick state is read by the rAF tick alongside keyboard
    state, so both work simultaneously and either input alone is enough.

The rAF physics loop stays unchanged — frame-rate-independent integration,
self-throttling to display refresh, paused when the tab is hidden.
"""

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, clientside_callback, dcc, html
from dash_iconify import DashIconify
from dl2_tiles import ESRI_STREET, register_theme_swap
from dl2_locations import MIAMI
from dl2_shared import info_panel

# Basemap pair for this page. dl2_tiles owns the light/dark wiring so
# every example themes the same way — see register_theme_swap below.
TILES = ESRI_STREET
TILE_URL = TILES.url("light")
SAT = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/"
    "MapServer/tile/{z}/{y}/{x}"
)
ATTR = TILES.attribution()

START = MIAMI.center
START_ZOOM = 15

# Physics — deg/s for the integrator (the rAF tick multiplies by dt in seconds).
MIN_SPEED = 0.0
MAX_SPEED = 0.0006
ACCEL = 0.0006  # ≈ 1 sec to top speed
BRAKE = 0.0012
TURN_RATE = 90.0  # deg/sec of heading change while turning

# Top-down green bomber sprite with built-in drop shadow. The image is ~512px,
# square, with the nose pointing UP — matches our north-up convention so the
# rotationAngle = heading mapping in the rAF loop reads naturally (heading 90°
# → sprite rotated 90° CW → nose pointing east).
AIRPLANE_SRC = "/assets/sprites/airplane_with_shadow.webp"
AIRPLANE_SIZE = 68  # bumped from 56 to give the propellers + stars room to read



def _joystick_div(prefix: str):
    """Render the joystick base + controller. CSS in style.css hides this on
    non-touch displays. The base/controller IDs are wired up in the rAF loop's
    setup JS using a unique class prefix."""
    return html.Div(
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
                    html.Span(" Drag to fly / brake"),
                ],
            ),
        ],
    )


component = dmc.Stack(
    [
        dmc.Grid(
            [
                # base 12 (stacks under map) on mobile, 8 on md+ (side-by-side).
                dmc.GridCol(
                    html.Div(
                        style={"position": "relative"},
                        children=[
                            # Height is set by the .dl2-sim-map-paper CSS class (70vh
                            # on desktop, 55vh on mobile) so the responsive height
                            # doesn't require an inline style dict.
                            dmc.Paper(
                                # region map
                                dl2.Map(
                                    id="fs-map",
                                    center=START,
                                    zoom=START_ZOOM,
                                    bearing=0,
                                    style={"height": "100%"},
                                    children=[
                                        dl2.TileLayer(
                                            id="fs-sat",
                                            url=SAT,
                                            attribution=ATTR,
                                            opacity=0.55,
                                        ),
                                        dl2.TileLayer(
                                            id="fs-tile", url=TILE_URL, opacity=0.7
                                        ),
                                        dl2.Marker(
                                            id="fs-aircraft",
                                            position=START,
                                            icon={
                                                "iconUrl": AIRPLANE_SRC,
                                                "iconSize": [
                                                    AIRPLANE_SIZE,
                                                    AIRPLANE_SIZE,
                                                ],
                                                "iconAnchor": [
                                                    AIRPLANE_SIZE // 2,
                                                    AIRPLANE_SIZE // 2,
                                                ],
                                            },
                                            rotateWithMap=False,
                                            rotationAngle=0,
                                        ),
                                        dl2.Polyline(
                                            id="fs-trail",
                                            positions=[START],
                                            color="#2f9e44",
                                            weight=2,
                                            opacity=0.6,
                                        ),
                                    ],
                                ),
                                # endregion
                                className="dl2-sim-map-paper",
                                shadow="sm",
                                radius="md",
                                withBorder=True,
                                style={"overflow": "hidden"},
                            ),
                            # Joystick overlay (mobile only — hidden by CSS otherwise).
                            _joystick_div("fs"),
                        ],
                    ),
                    span={"base": 12, "md": 8},
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            info_panel(
                                "HUD",
                                dmc.Stack(
                                    [
                                        dmc.Group(
                                            [
                                                dmc.Stack(
                                                    [
                                                        dmc.Text(
                                                            "HEADING",
                                                            size="xs",
                                                            c="dimmed",
                                                        ),
                                                        dmc.Badge(
                                                            id="fs-heading",
                                                            color="green",
                                                            variant="light",
                                                            size="lg",
                                                            children="0°",
                                                        ),
                                                    ],
                                                    gap=2,
                                                ),
                                                dmc.Stack(
                                                    [
                                                        dmc.Text(
                                                            "THROTTLE",
                                                            size="xs",
                                                            c="dimmed",
                                                        ),
                                                        dmc.Badge(
                                                            id="fs-throttle",
                                                            color="orange",
                                                            variant="light",
                                                            size="lg",
                                                            children="0%",
                                                        ),
                                                    ],
                                                    gap=2,
                                                ),
                                            ],
                                            justify="space-between",
                                        ),
                                        dmc.Progress(
                                            id="fs-throttle-bar",
                                            value=0,
                                            color="orange",
                                            size="sm",
                                            striped=True,
                                            animated=True,
                                        ),
                                        dmc.Group(
                                            [
                                                dmc.Text(
                                                    "POSITION", size="xs", c="dimmed"
                                                ),
                                                dmc.Code(
                                                    id="fs-position",
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
                                "Controls",
                                dmc.Stack(
                                    [
                                        dmc.Group(
                                            [
                                                dmc.Kbd("←"),
                                                dmc.Kbd("→"),
                                                dmc.Text("turn aircraft", size="sm"),
                                            ],
                                            gap="xs",
                                        ),
                                        dmc.Group(
                                            [
                                                dmc.Kbd("↑"),
                                                dmc.Text("throttle up", size="sm"),
                                            ],
                                            gap="xs",
                                        ),
                                        dmc.Group(
                                            [
                                                dmc.Kbd("↓"),
                                                dmc.Text("brake", size="sm"),
                                            ],
                                            gap="xs",
                                        ),
                                        dmc.Group(
                                            [
                                                dmc.Kbd("Space"),
                                                dmc.Text("hard stop", size="sm"),
                                            ],
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
                                        dmc.Divider(),
                                        dmc.Group(
                                            [
                                                DashIconify(
                                                    icon="mdi:gesture-tap", width=16
                                                ),
                                                dmc.Text(
                                                    "touch joystick auto-shows on mobile",
                                                    size="sm",
                                                    c="dimmed",
                                                ),
                                            ],
                                            gap="xs",
                                        ),
                                    ],
                                    gap=6,
                                ),
                            ),
                            info_panel(
                                "State",
                                dmc.Code(
                                    id="fs-state-readout",
                                    block=True,
                                    style={"fontSize": "11px", "minHeight": "100px"},
                                ),
                            ),
                        ],
                        gap="md",
                    ),
                    span={"base": 12, "md": 4},
                ),
            ]
        ),
        dcc.Store(id="fs-tick", data=0),
    ],
    gap="md",
)


# ---- rAF physics loop (installed once on page mount) -----------------------
clientside_callback(
    f"""
    (mapId) => {{
        const root = document.getElementById('fs-map');
        if (!root || root.dataset.fsLoopRunning) {{
            return window.dash_clientside.no_update;
        }}
        root.dataset.fsLoopRunning = '1';

        const MIN_SPEED = {MIN_SPEED};
        const MAX_SPEED = {MAX_SPEED};
        const ACCEL = {ACCEL};
        const BRAKE = {BRAKE};
        const TURN_RATE = {TURN_RATE};

        const state = {{
            lat: {START[0]}, lng: {START[1]},
            heading: 0,
            speed: 0,
            trail: [[{START[0]}, {START[1]}]],
            keys: new Set(),
            lastFrame: performance.now(),
        }};
        // Shared joystick state — written by the touch handlers below, read by
        // the rAF tick. Magnitude on each axis is normalized to [-1, +1].
        window._dl2_joystick = window._dl2_joystick || {{ x: 0, y: 0, active: false }};
        const joy = window._dl2_joystick;

        // --- keyboard ---
        // CRITICAL: disable Leaflet's built-in keyboard handler. Without this,
        // once the user clicks the map (giving it focus), Leaflet intercepts
        // ArrowLeft/Right/Up/Down via its own keyboard module and calls
        // stopPropagation — meaning the window-level listener we install
        // below never sees the event. Result: arrow keys appear to do nothing
        // on desktop (the map briefly pans, then snaps back via the rAF
        // re-centering). Disabling Leaflet's keyboard module lets the events
        // propagate up to window where our listener handles them.
        //
        // dl2.Map sets root.__dl2_map inside its mount effect (children run
        // first in React); the property may not exist yet when this setup
        // callback fires. Poll until it appears.
        const disableLeafletKeyboard = () => {{
            const m = root.__dl2_map;
            if (m && m.keyboard && typeof m.keyboard.disable === 'function') {{
                try {{ m.keyboard.disable(); }} catch (e) {{}}
                return;
            }}
            setTimeout(disableLeafletKeyboard, 80);
        }};
        disableLeafletKeyboard();

        const PAN_STEP_PX = 80;
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
                e.preventDefault();
            }}
        }};
        const onUp = (e) => state.keys.delete(e.key);
        window.addEventListener('keydown', onDown);
        window.addEventListener('keyup', onUp);

        // --- touch joystick ---
        // Hand-rolled (no dash_gauge dep). Base is a circle anchored bottom-center;
        // dragging the controller updates joy.x/joy.y in [-1, +1]. Released =>
        // controller springs back to center, joy values zero out.
        const base = document.getElementById('fs-joystick-base');
        const ctrl = document.getElementById('fs-joystick-controller');
        if (base && ctrl && !base.dataset.wired) {{
            base.dataset.wired = '1';
            const reset = () => {{
                ctrl.style.transform = 'translate(-50%, -50%)';
                joy.x = 0; joy.y = 0; joy.active = false;
            }};
            reset();
            let activePtr = null;
            const onPtrDown = (e) => {{
                if (activePtr !== null) return;
                activePtr = e.pointerId;
                base.setPointerCapture(e.pointerId);
                joy.active = true;
                e.preventDefault();
            }};
            const onPtrMove = (e) => {{
                if (e.pointerId !== activePtr) return;
                const r = base.getBoundingClientRect();
                const radius = r.width / 2;
                const dx = e.clientX - (r.left + radius);
                const dy = e.clientY - (r.top + radius);
                const mag = Math.sqrt(dx * dx + dy * dy);
                // Clamp the visual controller offset to the base radius.
                const k = mag > radius ? radius / mag : 1;
                const cx = dx * k, cy = dy * k;
                ctrl.style.transform = `translate(calc(-50% + ${{cx}}px), calc(-50% + ${{cy}}px))`;
                joy.x = cx / radius;
                joy.y = cy / radius;
            }};
            const onPtrUp = (e) => {{
                if (e.pointerId !== activePtr) return;
                try {{ base.releasePointerCapture(e.pointerId); }} catch (err) {{}}
                activePtr = null;
                reset();
            }};
            base.addEventListener('pointerdown', onPtrDown);
            base.addEventListener('pointermove', onPtrMove);
            base.addEventListener('pointerup', onPtrUp);
            base.addEventListener('pointercancel', onPtrUp);
        }}

        // --- rAF tick ---
        const tick = (now) => {{
            const dt = Math.min(0.1, (now - state.lastFrame) / 1000);
            state.lastFrame = now;

            const k = state.keys;
            // Turn input: keyboard arrows give ±1, joystick gives [-1, +1].
            // Sum them and clamp so holding the keyboard AND pushing joystick
            // doesn't double-spin.
            let turn = 0;
            if (k.has('ArrowLeft'))  turn -= 1;
            if (k.has('ArrowRight')) turn += 1;
            if (joy.active) turn += joy.x;
            turn = Math.max(-1, Math.min(1, turn));
            state.heading = (state.heading + turn * TURN_RATE * dt + 360) % 360;

            // Throttle / brake input.
            let thr = 0;
            if (k.has('ArrowUp'))   thr += 1;
            if (k.has('ArrowDown')) thr -= 1;
            if (joy.active) thr += -joy.y;  // joystick UP (-y) = throttle
            thr = Math.max(-1, Math.min(1, thr));
            if (thr > 0)      state.speed = Math.min(MAX_SPEED, state.speed + thr * ACCEL * dt * 60);
            else if (thr < 0) state.speed = Math.max(MIN_SPEED, state.speed + thr * BRAKE * dt * 60);

            if (k.has(' ') || k.has('Space')) state.speed = 0;

            if (state.speed > 0) {{
                const hd = state.heading * Math.PI / 180;
                state.lat += state.speed * Math.cos(hd) * (dt * 60);
                state.lng += state.speed * Math.sin(hd) * (dt * 60);
                if (state.trail.length === 0 ||
                    Math.hypot(state.lat - state.trail[state.trail.length-1][0],
                               state.lng - state.trail[state.trail.length-1][1]) > 0.0008) {{
                    state.trail.push([state.lat, state.lng]);
                    if (state.trail.length > 300) state.trail.shift();
                }}
            }}

            const pos = [state.lat, state.lng];
            dash_clientside.set_props('fs-aircraft', {{
                position: pos,
                rotationAngle: state.heading,   // ← marker rotates to face heading
            }});
            dash_clientside.set_props('fs-map',   {{ center: pos }});
            dash_clientside.set_props('fs-trail', {{ positions: state.trail }});

            const pct = Math.round((state.speed / MAX_SPEED) * 100);
            dash_clientside.set_props('fs-heading',      {{ children: Math.round(state.heading) + '°' }});
            dash_clientside.set_props('fs-throttle',     {{ children: pct + '%' }});
            dash_clientside.set_props('fs-throttle-bar', {{ value: pct }});
            dash_clientside.set_props('fs-position',     {{ children: pos[0].toFixed(4) + ', ' + pos[1].toFixed(4) }});

            if (!document.getElementById('fs-map')) return;
            requestAnimationFrame(tick);
        }};
        requestAnimationFrame(tick);

        return window.dash_clientside.no_update;
    }}
    """,
    Output("fs-tick", "data"),
    Input("fs-map", "id"),
)


@callback(Output("fs-state-readout", "children"), Input("fs-map", "viewport"))
def state_readout(vp):
    if not vp:
        return "—"
    return (
        "center: [{:.4f}, {:.4f}]\nzoom: {}\nbearing: {}°\n"
        "bounds: N {:.3f} S {:.3f} E {:.3f} W {:.3f}"
    ).format(
        vp["center"][0],
        vp["center"][1],
        vp["zoom"],
        round(vp.get("bearing") or 0),
        vp["bounds"]["north"],
        vp["bounds"]["south"],
        vp["bounds"]["east"],
        vp["bounds"]["west"],
    )


register_theme_swap("fs-tile", TILES)
