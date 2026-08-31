"""
FlyTo — smooth viewport transitions, modelled on dash-leaflet's `viewport` API.

`dl2.Map.flyTo` is a [MUTABLE] trigger prop. Setting it dispatches the matching
Leaflet 2 method (`flyTo` / `setView` / `panTo` / `fitBounds` / `flyToBounds` /
`panInsideBounds`). The `flyTo` and `flyToBounds` transitions give the smooth
glide-and-zoom motion the old dash-leaflet doc page demos with "Fly to Paris".

Companion events:
  - `n_movestart` increments when a transition BEGINS
  - `n_moveend`   increments when it COMPLETES
  - `viewport`    is the existing READONLY state read-back

A "FLYING…" HUD is the canonical use of the counter pair — show it while
`n_movestart > n_moveend`, otherwise show "IDLE".

Trigger payload shape:
    {
        'transition': 'flyTo',          # or setView, panTo, fitBounds, ...
        'center': [lat, lng],
        'zoom': 11,
        'options': {'duration': 2.5, 'easeLinearity': 0.25},
        'n_clicks': bump_me,            # required — bump per call to retrigger
    }
"""

import dash
import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import (
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    ctx,
    dcc,
    html,
    no_update,
)
from dash_iconify import DashIconify
from dl2_tiles import POSITRON, register_theme_swap
from dl2_shared import header, info_panel

# Basemap pair for this page. dl2_tiles owns the light/dark wiring so
# every example themes the same way — see register_theme_swap below.
TILES = POSITRON
TILE_URL = TILES.url("light")
ATTR = TILES.attribution()

# A small grand-tour. Each city has a sensible target zoom (CARTO lights up
# urban detail nicely at z=11–12). The `bounds` entry triggers flyToBounds
# instead of flyTo to demo the bounds-driven variant.
CITIES = [
    {
        "name": "Paris",
        "icon": "twemoji:eiffel-tower",
        "lat": 48.864716,
        "lng": 2.349014,
        "zoom": 12,
        "color": "blue",
    },
    {
        "name": "Tokyo",
        "icon": "twemoji:mount-fuji",
        "lat": 35.689487,
        "lng": 139.691711,
        "zoom": 11,
        "color": "red",
    },
    {
        "name": "Sydney",
        "icon": "twemoji:bridge-at-night",
        "lat": -33.86882,
        "lng": 151.2093,
        "zoom": 12,
        "color": "cyan",
    },
    {
        "name": "Rio",
        "icon": "twemoji:flag-brazil",
        "lat": -22.9068,
        "lng": -43.1729,
        "zoom": 11,
        "color": "green",
    },
    {
        "name": "Cape Town",
        "icon": "twemoji:mountain",
        "lat": -33.9249,
        "lng": 18.4241,
        "zoom": 11,
        "color": "orange",
    },
    {
        "name": "Reykjavík",
        "icon": "twemoji:snow-capped-mountain",
        "lat": 64.1466,
        "lng": -21.9426,
        "zoom": 11,
        "color": "indigo",
    },
    {
        "name": "New York",
        "icon": "twemoji:statue-of-liberty",
        "lat": 40.7128,
        "lng": -74.0060,
        "zoom": 12,
        "color": "grape",
    },
]

# Bounds-based examples — center+zoom can't frame a bbox without manual math,
# bounds transitions can. We pick three with different visual character:
#   * Hawaii      — flyToBounds: smooth pan+zoom into a tight island chain.
#   * Italy       — fitBounds:   instant snap (animate:False default) to a country.
#   * Mediterranean — panInsideBounds: only pans if the current view is OUTSIDE
#                     the bbox; if you're already inside it, the call is a no-op.
HAWAII_BOUNDS = [[18.91, -160.25], [22.24, -154.80]]
ITALY_BOUNDS = [[36.65, 6.62], [47.10, 18.52]]
MEDITERRANEAN_BOUNDS = [[30.0, -6.0], [46.0, 36.0]]

START = [25.0, -30.0]  # Atlantic — a "neutral" starting view
START_ZOOM = 3




# ---- layout ----------------------------------------------------------------


def city_button(c):
    return dmc.Button(
        c["name"],
        id={"type": "fly-city", "name": c["name"]},
        color=c["color"],
        variant="light",
        size="xs",
        fullWidth=True,
        leftSection=DashIconify(icon=c["icon"], width=16),
    )


component = dmc.Stack(
    [
        header(
            "FlyTo — smooth viewport transitions",
            "Setting the new `flyTo` prop on dl2.Map dispatches Leaflet 2's "
            "`flyTo` / `setView` / `panTo` / `fitBounds` / `flyToBounds` / `panInsideBounds`. "
            "Pair with `n_movestart` + `n_moveend` for a flying-state HUD. The grand-tour button "
            "chains seven flyTo calls — each waits for the previous to finish before launching "
            "the next.",
            badge="dl2.Map.flyTo",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        # region map
                        dl2.Map(
                            id="fly-map",
                            center=START,
                            zoom=START_ZOOM,
                            style={"height": "62vh"},
                            children=[
                                dl2.TileLayer(
                                    id="fly-tile", url=TILE_URL, attribution=ATTR
                                ),
                                # One marker per city — useful both visually and as a click target.
                                *[
                                    dl2.Marker(
                                        position=[c["lat"], c["lng"]],
                                        iconify=c["icon"],
                                        iconSize=30,
                                        children=[
                                            dl2.Tooltip(children=c["name"]),
                                        ],
                                    )
                                    for c in CITIES
                                ],
                            ],
                        ),
                        # endregion
                        shadow="sm",
                        radius="md",
                        withBorder=True,
                        style={"overflow": "hidden"},
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
                                                dmc.Text(
                                                    "STATE", size="xs", c="dimmed"
                                                ),
                                                dmc.Badge(
                                                    id="fly-state",
                                                    color="gray",
                                                    variant="light",
                                                    size="lg",
                                                    children="idle",
                                                ),
                                            ],
                                            justify="space-between",
                                        ),
                                        dmc.Group(
                                            [
                                                dmc.Text(
                                                    "MOVES", size="xs", c="dimmed"
                                                ),
                                                dmc.Code(
                                                    id="fly-counts",
                                                    children="start: 0 / end: 0",
                                                    style={"fontSize": "11px"},
                                                ),
                                            ],
                                            justify="space-between",
                                        ),
                                        dmc.Code(
                                            id="fly-viewport",
                                            block=True,
                                            style={
                                                "fontSize": "11px",
                                                "minHeight": "70px",
                                            },
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                            info_panel(
                                "Transition",
                                dmc.Stack(
                                    [
                                        dmc.SegmentedControl(
                                            id="fly-transition",
                                            data=[
                                                {"value": "flyTo", "label": "flyTo"},
                                                {
                                                    "value": "setView",
                                                    "label": "setView",
                                                },
                                                {"value": "panTo", "label": "panTo"},
                                            ],
                                            value="flyTo",
                                            size="xs",
                                            fullWidth=True,
                                        ),
                                        dmc.Stack(
                                            [
                                                dmc.Group(
                                                    [
                                                        dmc.Text(
                                                            "duration",
                                                            size="xs",
                                                            c="dimmed",
                                                        ),
                                                        dmc.Code(
                                                            id="fly-duration-val",
                                                            children="2.5s",
                                                            style={"fontSize": "11px"},
                                                        ),
                                                    ],
                                                    justify="space-between",
                                                ),
                                                dmc.Slider(
                                                    id="fly-duration",
                                                    min=0.5,
                                                    max=6,
                                                    step=0.25,
                                                    value=2.5,
                                                    marks=[
                                                        {"value": v}
                                                        for v in [1, 2, 3, 4, 5, 6]
                                                    ],
                                                ),
                                            ],
                                            gap=2,
                                        ),
                                        dmc.Stack(
                                            [
                                                dmc.Group(
                                                    [
                                                        dmc.Text(
                                                            "easeLinearity",
                                                            size="xs",
                                                            c="dimmed",
                                                        ),
                                                        dmc.Code(
                                                            id="fly-ease-val",
                                                            children="0.25",
                                                            style={"fontSize": "11px"},
                                                        ),
                                                    ],
                                                    justify="space-between",
                                                ),
                                                dmc.Slider(
                                                    id="fly-ease",
                                                    min=0.05,
                                                    max=1.0,
                                                    step=0.05,
                                                    value=0.25,
                                                    marks=[
                                                        {"value": 0.25},
                                                        {"value": 0.5},
                                                        {"value": 0.75},
                                                        {"value": 1.0},
                                                    ],
                                                ),
                                            ],
                                            gap=2,
                                        ),
                                    ],
                                    gap="sm",
                                ),
                            ),
                            info_panel(
                                "Destinations",
                                dmc.SimpleGrid(
                                    cols=2,
                                    spacing="xs",
                                    verticalSpacing="xs",
                                    children=[city_button(c) for c in CITIES],
                                ),
                            ),
                            info_panel(
                                "Bounds transitions",
                                dmc.Stack(
                                    [
                                        dmc.Text(
                                            "These need a bbox, not a center+zoom — the SegmentedControl "
                                            "above doesn't apply.",
                                            size="xs",
                                            c="dimmed",
                                        ),
                                        dmc.Button(
                                            "flyToBounds → Hawaii",
                                            id="fly-hawaii",
                                            color="lime",
                                            variant="light",
                                            size="xs",
                                            fullWidth=True,
                                            leftSection=DashIconify(
                                                icon="twemoji:beach-with-umbrella",
                                                width=16,
                                            ),
                                        ),
                                        dmc.Button(
                                            "fitBounds → Italy (instant)",
                                            id="fly-italy",
                                            color="red",
                                            variant="light",
                                            size="xs",
                                            fullWidth=True,
                                            leftSection=DashIconify(
                                                icon="twemoji:flag-italy", width=16
                                            ),
                                        ),
                                        dmc.Button(
                                            "panInsideBounds → Mediterranean",
                                            id="fly-med",
                                            color="cyan",
                                            variant="light",
                                            size="xs",
                                            fullWidth=True,
                                            leftSection=DashIconify(
                                                icon="twemoji:water-wave", width=16
                                            ),
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                            info_panel(
                                "Tour",
                                dmc.Stack(
                                    [
                                        # Button shows "Start tour" when idle, "Stop tour" while running —
                                        # state is mirrored from ws-tour-state via the callback below so
                                        # the user can SEE the tour is active without staring at the map.
                                        dmc.Button(
                                            "Start grand tour (7 cities)",
                                            id="fly-tour",
                                            color="violet",
                                            variant="light",
                                            size="xs",
                                            fullWidth=True,
                                            leftSection=DashIconify(
                                                id="fly-tour-icon",
                                                icon="twemoji:globe-with-meridians",
                                                width=16,
                                            ),
                                        ),
                                        # Progress text — "leg 3 / 7: Sydney" while running, hidden otherwise.
                                        dmc.Text(
                                            id="fly-tour-progress",
                                            size="xs",
                                            c="dimmed",
                                            children="",
                                        ),
                                        dmc.Button(
                                            "Home",
                                            id="fly-home",
                                            color="gray",
                                            variant="light",
                                            size="xs",
                                            fullWidth=True,
                                            leftSection=DashIconify(
                                                icon="mdi:home-map-marker", width=16
                                            ),
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                        ],
                        gap="md",
                    ),
                    span={"base": 12, "md": 4},
                ),
            ]
        ),
        # Tour driver: stepper + tick keep the grand-tour moving from city to city.
        dcc.Store(id="fly-tour-state", data={"running": False, "i": -1}),
        dcc.Interval(id="fly-tour-tick", interval=400, disabled=True),
    ],
    gap="md",
)


# ---- live duration / ease readouts ----------------------------------------
clientside_callback(
    "(v) => `${v.toFixed(2)}s`",
    Output("fly-duration-val", "children"),
    Input("fly-duration", "value"),
)
clientside_callback(
    "(v) => v.toFixed(2)",
    Output("fly-ease-val", "children"),
    Input("fly-ease", "value"),
)


# ---- single-click city: trigger flyTo --------------------------------------
@callback(
    Output("fly-map", "flyTo"),
    Input({"type": "fly-city", "name": dash.ALL}, "n_clicks"),
    State("fly-transition", "value"),
    State("fly-duration", "value"),
    State("fly-ease", "value"),
    State("fly-map", "flyTo"),
    prevent_initial_call=True,
)
def fly_to_city(_, transition, duration, ease, prev):
    triggered = ctx.triggered_id
    if not triggered:
        return no_update
    # Pattern-matching ids fire on initial mount with n_clicks=None — guard so
    # mounting the buttons doesn't immediately fly somewhere.
    if not any(ctx.triggered) or all(
        t.get("value") in (None, 0) for t in ctx.triggered
    ):
        return no_update
    city = next((c for c in CITIES if c["name"] == triggered["name"]), None)
    if not city:
        return no_update
    bump = (prev or {}).get("n_clicks", 0) + 1
    return {
        "transition": transition or "flyTo",
        "center": [city["lat"], city["lng"]],
        "zoom": city["zoom"],
        "options": {"duration": float(duration), "easeLinearity": float(ease)},
        "n_clicks": bump,
    }


# ---- specials: Hawaii (flyToBounds), Home (flyTo), Tour --------------------
@callback(
    Output("fly-map", "flyTo", allow_duplicate=True),
    Input("fly-hawaii", "n_clicks"),
    State("fly-duration", "value"),
    State("fly-ease", "value"),
    State("fly-map", "flyTo"),
    prevent_initial_call=True,
)
def fly_to_hawaii(_, duration, ease, prev):
    bump = (prev or {}).get("n_clicks", 0) + 1
    return {
        "transition": "flyToBounds",
        "bounds": HAWAII_BOUNDS,
        "options": {
            "duration": float(duration),
            "easeLinearity": float(ease),
            "padding": [40, 40],
        },
        "n_clicks": bump,
    }


@callback(
    Output("fly-map", "flyTo", allow_duplicate=True),
    Input("fly-italy", "n_clicks"),
    State("fly-map", "flyTo"),
    prevent_initial_call=True,
)
def fit_italy(_, prev):
    # fitBounds: instant snap (Map.tsx defaults animate:False). Demonstrates the
    # difference from flyToBounds — same bbox-driven framing, no animation.
    bump = (prev or {}).get("n_clicks", 0) + 1
    return {
        "transition": "fitBounds",
        "bounds": ITALY_BOUNDS,
        "options": {"padding": [30, 30]},
        "n_clicks": bump,
    }


@callback(
    Output("fly-map", "flyTo", allow_duplicate=True),
    Input("fly-med", "n_clicks"),
    State("fly-duration", "value"),
    State("fly-ease", "value"),
    State("fly-map", "flyTo"),
    prevent_initial_call=True,
)
def pan_inside_mediterranean(_, duration, ease, prev):
    # panInsideBounds: a no-op if the current view is already inside the bbox,
    # otherwise pans the minimum amount to bring the view inside (zoom is kept).
    # Click this from far away (NYC) to see motion; click again from inside the
    # Med to see nothing happen — that's the intended Leaflet semantic.
    bump = (prev or {}).get("n_clicks", 0) + 1
    return {
        "transition": "panInsideBounds",
        "bounds": MEDITERRANEAN_BOUNDS,
        "options": {"duration": float(duration), "easeLinearity": float(ease)},
        "n_clicks": bump,
    }


@callback(
    Output("fly-map", "flyTo", allow_duplicate=True),
    Input("fly-home", "n_clicks"),
    State("fly-duration", "value"),
    State("fly-ease", "value"),
    State("fly-map", "flyTo"),
    prevent_initial_call=True,
)
def fly_home(_, duration, ease, prev):
    bump = (prev or {}).get("n_clicks", 0) + 1
    return {
        "transition": "flyTo",
        "center": START,
        "zoom": START_ZOOM,
        "options": {"duration": float(duration), "easeLinearity": float(ease)},
        "n_clicks": bump,
    }


# ---- Grand tour ------------------------------------------------------------
# Pressing "Grand tour" arms the loop. The Interval ticks every 400 ms; on
# each tick we check whether we should launch the NEXT leg. We launch when:
#   * no leg is in flight (n_movestart == n_moveend), AND
#   * we have at least one leg already finished since the last launch (so we
#     don't fire two legs back-to-back on the same idle moment).
@callback(
    Output("fly-tour-state", "data"),
    Output("fly-tour-tick", "disabled"),
    Input("fly-tour", "n_clicks"),
    State("fly-tour-state", "data"),
    prevent_initial_call=True,
)
def start_tour(_, st):
    if not _:
        return no_update, no_update
    # Toggle off if already running.
    if (st or {}).get("running"):
        return {"running": False, "i": -1}, True
    return {"running": True, "i": -1}, False


@callback(
    Output("fly-map", "flyTo", allow_duplicate=True),
    Output("fly-tour-state", "data", allow_duplicate=True),
    Output("fly-tour-tick", "disabled", allow_duplicate=True),
    Input("fly-tour-tick", "n_intervals"),
    State("fly-tour-state", "data"),
    State("fly-map", "n_movestart"),
    State("fly-map", "n_moveend"),
    State("fly-map", "flyTo"),
    prevent_initial_call=True,
)
def tour_step(_, st, n_start, n_end, prev):
    st = st or {"running": False, "i": -1}
    if not st.get("running"):
        return no_update, no_update, no_update
    # Wait for current leg to finish.
    if (n_start or 0) > (n_end or 0):
        return no_update, no_update, no_update
    i = st.get("i", -1) + 1
    if i >= len(CITIES):
        return no_update, {"running": False, "i": -1}, True
    city = CITIES[i]
    bump = (prev or {}).get("n_clicks", 0) + 1
    return (
        {
            "transition": "flyTo",
            "center": [city["lat"], city["lng"]],
            "zoom": city["zoom"],
            "options": {"duration": 2.5, "easeLinearity": 0.25},
            "n_clicks": bump,
        },
        {"running": True, "i": i},
        False,
    )


# ---- Tour button: label + icon + per-leg progress text --------------------
# Without this, the tour runs silently — the button never changes appearance,
# so users can't tell whether their click did anything. Mirror the tour state
# (running flag + leg index) into the button label / icon / progress line.
@callback(
    Output("fly-tour", "children"),
    Output("fly-tour", "color"),
    Output("fly-tour-icon", "icon"),
    Output("fly-tour-progress", "children"),
    Input("fly-tour-state", "data"),
)
def tour_button(st):
    st = st or {"running": False, "i": -1}
    if not st.get("running"):
        return (
            "Start grand tour (7 cities)",
            "violet",
            "twemoji:globe-with-meridians",
            "",
        )
    i = st.get("i", -1)
    # While running, i is the index of the leg CURRENTLY in flight (or just
    # completed). Clamp to [0, len) so the readout never shows leg 0 of 7 at -1.
    leg = max(0, min(i, len(CITIES) - 1))
    city = CITIES[leg]["name"]
    return (
        "Stop tour",
        "red",
        "mdi:stop-circle-outline",
        f"leg {leg + 1} of {len(CITIES)}: {city}",
    )


# ---- HUD: flying vs idle, counters, viewport ------------------------------
@callback(
    Output("fly-state", "children"),
    Output("fly-state", "color"),
    Output("fly-counts", "children"),
    Input("fly-map", "n_movestart"),
    Input("fly-map", "n_moveend"),
)
def hud_state(n_start, n_end):
    n_start = n_start or 0
    n_end = n_end or 0
    flying = n_start > n_end
    return (
        ("flying…" if flying else "idle"),
        ("orange" if flying else "gray"),
        f"start: {n_start} / end: {n_end}",
    )


@callback(Output("fly-viewport", "children"), Input("fly-map", "viewport"))
def viewport(vp):
    if not vp:
        return "—"
    c = vp["center"]
    return f"center: [{c[0]:.4f}, {c[1]:.4f}]\nzoom:   {vp['zoom']}"


# ---- light/dark theme sync -------------------------------------------------
register_theme_swap("fly-tile", TILES)
