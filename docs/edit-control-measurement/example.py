"""
Edit Control + Measurement — popover-driven drawing, recoloring, and per-feature labels.

Builds on top of /edit-control. Three states (view / create / edit) and a single
dmc.Popover anchored next to the EditControl icon strip — the same anchor pattern as
/easy-button, but driven by EditControl's `activeTool` + `featureClick` instead of an
EasyButton click. ColorPicker is live in BOTH phases:

- create (after clicking a draw icon, before drawing) → updates EditControl.shapeOptions
  so the NEXT shape is drawn in that color
- create (after drawing, before Create/Cancel) → applies via featureUpdate to the just-
  drawn shape so the user can tweak the color before finalizing
- edit (after clicking a feature in edit mode) → applies via featureUpdate to that
  feature live

Every committed shape gets a permanent Leaflet tooltip with its area / radius / length
(showMeasurementTooltips=True on the EditControl); the Metric / Imperial toggle in the
right rail drives the unit system.
"""

import json

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
from dl2_shared import code_panel, header, info_panel

CARTO_LIGHT = "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
CARTO_DARK = "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
ATTR = (
    '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> '
    '&copy; <a href="https://carto.com/attributions">CARTO</a>'
)

DEFAULT_COLOR = "#2f9e44"
PRESET_COLORS = [
    "#2f9e44",
    "#1971c2",
    "#e8590c",
    "#9c36b5",
    "#d6336c",
    "#fab005",
    "#0ca678",
    "#495057",
]

CODE = """dl2.EditControl(
    id="ec",
    showMeasurementTooltips=True,   # permanent area/radius/length labels
    measurementSystem="metric",     # 'metric' | 'imperial' (live)
    shapeOptions={"color": "#2f9e44"},   # color of the NEXT shape (live)
    edit={"remove": False},         # use our popover Delete instead
)

# EditControl emits, page reacts:
#   activeTool   -> open popover, mode='create' (when truthy)
#   action       -> capture {id} of the just-drawn shape as pending
#   activeMode   -> mode='edit' when user clicks the edit icon
#   featureClick -> select the clicked feature; open popover with its data

# Page commands EditControl back:
#   shapeOptions      -> next-draw color (color picker before drawing)
#   featureUpdate     -> {id, style?, properties?, remove?, n_clicks}
#                        applies color/name/delete live to one feature"""


# ---- form layouts (rendered into the popover dropdown) ---------------------


def form_create(name, color):
    """Popover form for create mode: name + color + Cancel / Create."""
    return dmc.Stack(
        [
            dmc.Group(
                [
                    DashIconify(
                        icon="mdi:plus-circle-outline",
                        width=18,
                        color="var(--mantine-color-green-6)",
                    ),
                    dmc.Text("Add a shape", size="sm", fw=600),
                ],
                gap=6,
            ),
            dmc.TextInput(
                id="ecm-name",
                value=name or "",
                placeholder="Name (optional)",
                size="xs",
            ),
            dmc.ColorPicker(
                id="ecm-color",
                value=color or DEFAULT_COLOR,
                format="hex",
                swatches=PRESET_COLORS,
                size="xs",
                fullWidth=True,
            ),
            dmc.Group(
                [
                    dmc.Button(
                        "Cancel",
                        id="ecm-cancel",
                        size="xs",
                        variant="light",
                        color="gray",
                    ),
                    dmc.Button(
                        "Create",
                        id="ecm-create",
                        size="xs",
                        color="green",
                        leftSection=DashIconify(icon="mdi:check", width=14),
                    ),
                ],
                gap="xs",
                grow=True,
            ),
        ],
        gap="xs",
        style={"minWidth": "240px", "maxWidth": "260px"},
    )


def form_edit(name, color):
    """Popover form for edit-selected mode: name + color + Delete / Done."""
    return dmc.Stack(
        [
            dmc.Group(
                [
                    DashIconify(
                        icon="mdi:pencil-outline",
                        width=18,
                        color="var(--mantine-color-blue-6)",
                    ),
                    dmc.Text("Edit shape", size="sm", fw=600),
                ],
                gap=6,
            ),
            dmc.TextInput(
                id="ecm-name",
                value=name or "",
                placeholder="Name (optional)",
                size="xs",
            ),
            dmc.ColorPicker(
                id="ecm-color",
                value=color or DEFAULT_COLOR,
                format="hex",
                swatches=PRESET_COLORS,
                size="xs",
                fullWidth=True,
            ),
            dmc.Group(
                [
                    dmc.Button(
                        "Delete",
                        id="ecm-delete",
                        size="xs",
                        color="red",
                        variant="light",
                        leftSection=DashIconify(icon="mdi:delete-outline", width=14),
                    ),
                    dmc.Button(
                        "Done", id="ecm-done", size="xs", variant="light", color="gray"
                    ),
                ],
                gap="xs",
                grow=True,
            ),
        ],
        gap="xs",
        style={"minWidth": "240px", "maxWidth": "260px"},
    )


# ---- layout ----------------------------------------------------------------

component = dmc.Stack(
    [
        header(
            "Edit Control + Measurement",
            "Click a draw icon (top-left) → a popover opens with a name field and color "
            "picker; pick a color, then click the map to draw — the shape uses that color "
            "live. After drawing, Create finalizes or Cancel removes it. Enter Edit mode "
            "(pencil icon, visible once a shape exists) and click any shape to recolor / "
            "rename / delete it; clicking the map outside any shape closes the popover.",
            badge="dl2.EditControl + popover",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    html.Div(
                        # Relative wrapper so the Popover anchor positions absolutely over the
                        # EditControl icon strip — exactly the easy_button.py pattern.
                        style={"position": "relative"},
                        children=[
                            dmc.Paper(
                                dl2.Map(
                                    id="ecm-map",
                                    center=[28.02, -97.05],
                                    zoom=12,
                                    style={"height": "62vh"},
                                    children=[
                                        dl2.TileLayer(
                                            id="ecm-tile",
                                            url=CARTO_LIGHT,
                                            attribution=ATTR,
                                        ),
                                        dl2.EditControl(
                                            id="ecm-ec",
                                            position="topleft",
                                            showMeasurementTooltips=True,
                                            measurementSystem="metric",
                                            shapeOptions={
                                                "color": DEFAULT_COLOR,
                                                "weight": 3,
                                                "fillOpacity": 0.25,
                                            },
                                            # Disable EditControl's built-in remove mode —
                                            # delete happens via our popover Delete button.
                                            edit={"remove": False},
                                        ),
                                    ],
                                ),
                                shadow="sm",
                                radius="md",
                                withBorder=True,
                                style={"overflow": "hidden"},
                            ),
                            # Popover anchor — 1px-wide invisible div parked just to the right
                            # of the EditControl icon strip (~36px strip width + 10px map
                            # padding + 6px gap ≈ 52px). Height covers the strip so the popover
                            # opens at a sensible y when any draw icon is clicked.
                            dmc.Popover(
                                id="ecm-popover",
                                opened=False,
                                position="right-start",
                                offset=10,
                                withArrow=True,
                                arrowSize=10,
                                shadow="lg",
                                radius="md",
                                # Fully controlled — open/close only via callbacks, never
                                # auto-close (clicking the map needs to STAY interactive
                                # during create mode for drawing).
                                closeOnClickOutside=False,
                                closeOnEscape=False,
                                clickOutsideEvents=[],
                                keepMounted=True,
                                children=[
                                    dmc.PopoverTarget(
                                        html.Div(id="ecm-anchor"),
                                        boxWrapperProps={
                                            "style": {
                                                "position": "absolute",
                                                "top": "10px",
                                                "left": "52px",
                                                "width": "1px",
                                                "height": "30px",
                                                "pointerEvents": "none",
                                                "zIndex": 600,
                                            }
                                        },
                                    ),
                                    dmc.PopoverDropdown(
                                        html.Div(id="ecm-popover-content"),
                                        p="sm",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    span=8,
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            info_panel(
                                "Mode",
                                dmc.Group(
                                    [
                                        dmc.Badge(
                                            id="ecm-mode-badge",
                                            color="gray",
                                            variant="light",
                                            children="view",
                                        ),
                                        DashIconify(
                                            id="ecm-mode-icon",
                                            icon="mdi:eye-outline",
                                            width=20,
                                            color="var(--mantine-color-dimmed)",
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                            info_panel(
                                "Units (measurementSystem)",
                                dmc.SegmentedControl(
                                    id="ecm-units",
                                    value="metric",
                                    data=[
                                        {"value": "metric", "label": "Metric"},
                                        {"value": "imperial", "label": "Imperial"},
                                    ],
                                    size="xs",
                                    fullWidth=True,
                                ),
                            ),
                            info_panel(
                                "Last action",
                                dmc.Code(
                                    id="ecm-action",
                                    block=True,
                                    style={"minHeight": "60px", "fontSize": "11px"},
                                ),
                            ),
                            info_panel(
                                "Features",
                                html.Div(
                                    id="ecm-list",
                                    children=dmc.Text(
                                        "Click a draw tool (top-left of the map) to start.",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ),
                            ),
                        ],
                        gap="md",
                    ),
                    span=4,
                ),
            ]
        ),
        code_panel("Pattern", CODE),
        # State stores
        dcc.Store(id="ecm-mode", data="view"),  # 'view' | 'create' | 'edit'
        dcc.Store(
            id="ecm-pending-id", data=None
        ),  # id of just-drawn shape (create mode)
        dcc.Store(id="ecm-selected-id", data=None),  # id of selected shape (edit mode)
        dcc.Store(id="ecm-features", data={}),  # id -> {name, color, type}
        dcc.Store(id="ecm-current-color", data=DEFAULT_COLOR),
        dcc.Store(id="ecm-current-name", data=""),
        dcc.Store(id="ecm-drawtool-tick", data=0),  # n_clicks tick for drawToolbar
        dcc.Store(id="ecm-name-wired"),  # dummy: signals one-time listener wired
        # Dedicated keystroke-bridge store: a clientside delegate writes the current
        # value of the name input here on every `input` event. Kept SEPARATE from
        # `ecm-current-name` because that store is an Output of the orchestrator,
        # and clientside set_props writes to a prop that has a server callback as
        # Output don't reliably retrigger other Input callbacks in Dash 4.
        dcc.Store(id="ecm-name-bridge", data=""),
    ],
    gap="md",
)


# ---- orchestrator: maps EditControl + map signals to mode/selection state --
#
# One callback handles all the state transitions. The five Inputs are the
# "things that happen on the map":
#   activeTool / activeMode / action / featureClick (from EditControl) +
#   clickData (from Map; only fires for clicks outside any feature in edit mode
#   because EditControl sets bubblingMouseEvents:false on layers there).


@callback(
    Output("ecm-mode", "data"),
    Output("ecm-pending-id", "data"),
    Output("ecm-selected-id", "data"),
    Output("ecm-popover", "opened"),
    Output("ecm-features", "data"),
    Output("ecm-current-color", "data"),
    Output("ecm-current-name", "data"),
    Input("ecm-ec", "activeTool"),
    Input("ecm-ec", "activeMode"),
    Input("ecm-ec", "action"),
    Input("ecm-ec", "featureClick"),
    Input("ecm-map", "clickData"),
    State("ecm-mode", "data"),
    State("ecm-pending-id", "data"),
    State("ecm-selected-id", "data"),
    State("ecm-features", "data"),
    State("ecm-current-color", "data"),
    prevent_initial_call=True,
)
def orchestrate(
    active_tool,
    active_mode,
    action,
    feature_click,
    map_click,
    mode,
    pending_id,
    selected_id,
    features,
    current_color,
):
    # When multiple Inputs change in the same tick (e.g. clickData fires WITH
    # action.created on every shape commit, because the second mouse click that
    # finishes the shape also propagates as a Map click), `ctx.triggered[0]`
    # only reports one of them. We need to inspect the whole triggered set and
    # pick a branch by priority — action-events FIRST so a 'created' is never
    # masked by the commit click.
    triggered_props = {t["prop_id"] for t in ctx.triggered}
    features = dict(features or {})
    nu = [no_update] * 7

    # Priority 1: action events carry state-changing payloads (id + measurements).
    if "ecm-ec.action" in triggered_props and action:
        a_type = action.get("type")
        a_id = action.get("id")
        if a_type == "created" and a_id:
            features[a_id] = {
                "name": "",
                "color": current_color or DEFAULT_COLOR,
                "type": action.get("layer_type") or "shape",
                "area_m2": float(action.get("area_m2") or 0),
                "length_m": float(action.get("length_m") or 0),
            }
            return (no_update, a_id, no_update, True, features, no_update, "")
        if a_type in ("restyled", "geometry-changed") and a_id and a_id in features:
            features[a_id] = {
                **features[a_id],
                "area_m2": float(
                    action.get("area_m2") or features[a_id].get("area_m2", 0)
                ),
                "length_m": float(
                    action.get("length_m") or features[a_id].get("length_m", 0)
                ),
            }
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                features,
                no_update,
                no_update,
            )
        if a_type == "deleted" and a_id:
            features.pop(a_id, None)
            return (
                no_update,
                no_update,
                no_update,
                no_update,
                features,
                no_update,
                no_update,
            )
        # Action fired but with nothing actionable — fall through to other branches.

    # Priority 2: activeTool change — user clicked a draw icon in EditControl.
    if "ecm-ec.activeTool" in triggered_props:
        if active_tool:
            return ("create", None, None, True, features, no_update, "")
        # activeTool → None: don't auto-exit (could be commit OR cancel; the
        # popover Cancel/Create button handles the explicit transition).

    # Priority 3: activeMode change.
    if "ecm-ec.activeMode" in triggered_props:
        if active_mode == "edit":
            return ("edit", None, None, False, features, no_update, no_update)
        if active_mode is None and mode == "edit":
            return ("view", None, None, False, features, no_update, no_update)

    # Priority 4: feature click in edit mode → select.
    if "ecm-ec.featureClick" in triggered_props and mode == "edit" and feature_click:
        sid = feature_click.get("id")
        f = features.get(sid, {})
        return (
            no_update,
            no_update,
            sid,
            True,
            features,
            f.get("color") or DEFAULT_COLOR,
            f.get("name") or "",
        )

    # Priority 5: empty-map click in edit mode → deselect.
    if "ecm-map.clickData" in triggered_props and mode == "edit" and selected_id:
        return (no_update, no_update, None, False, features, no_update, no_update)

    return nu


# ---- popover content (varies by mode + selection) --------------------------
@callback(
    Output("ecm-popover-content", "children"),
    Input("ecm-mode", "data"),
    Input("ecm-pending-id", "data"),
    Input("ecm-selected-id", "data"),
    State("ecm-features", "data"),
    State("ecm-current-color", "data"),
)
def render_popover_content(mode, pending_id, selected_id, features, current_color):
    features = features or {}
    if mode == "create":
        f = features.get(pending_id) if pending_id else None
        return form_create(
            (f or {}).get("name", ""),
            (f or {}).get("color") or current_color or DEFAULT_COLOR,
        )
    if mode == "edit" and selected_id:
        f = features.get(selected_id) or {}
        return form_edit(f.get("name", ""), f.get("color") or DEFAULT_COLOR)
    # view mode (or edit-without-selection): render nothing — popover is hidden anyway.
    return html.Div()


# ---- color picker change ---------------------------------------------------
#
# Three branches:
#   1. mode='create' AND no pending id  -> update EditControl.shapeOptions so the
#      NEXT drawn shape uses this color
#   2. mode='create' WITH pending id    -> apply featureUpdate.style to the just-
#      drawn shape (lets the user tweak the color before clicking Create)
#   3. mode='edit'  WITH selected id    -> apply featureUpdate.style to that
#      shape live


@callback(
    Output("ecm-ec", "shapeOptions"),
    Output("ecm-ec", "featureUpdate"),
    Output("ecm-features", "data", allow_duplicate=True),
    Output("ecm-current-color", "data", allow_duplicate=True),
    Input("ecm-color", "value"),
    State("ecm-mode", "data"),
    State("ecm-pending-id", "data"),
    State("ecm-selected-id", "data"),
    State("ecm-features", "data"),
    State("ecm-ec", "featureUpdate"),
    State("ecm-current-color", "data"),
    prevent_initial_call=True,
)
def on_color_change(
    color, mode, pending_id, selected_id, features, last_fu, current_color
):
    if not color:
        return no_update, no_update, no_update, no_update
    # Guard against mount-fire echoes (popover content remounts → ColorPicker
    # value Input fires with the same color we just stored).
    if color == current_color and not (pending_id or selected_id):
        return no_update, no_update, no_update, no_update
    target_id = pending_id or selected_id
    features = dict(features or {})
    if target_id:
        last_n = (last_fu or {}).get("n_clicks", 0)
        features[target_id] = {**features.get(target_id, {}), "color": color}
        return (
            no_update,
            {"id": target_id, "style": {"color": color}, "n_clicks": last_n + 1},
            features,
            color,
        )
    if mode == "create":
        # No pending shape yet — set the NEXT draw color via shapeOptions.
        return (
            {"color": color, "weight": 3, "fillOpacity": 0.25},
            no_update,
            no_update,
            color,
        )
    return no_update, no_update, no_update, color


# ---- name input change -----------------------------------------------------
# DMC TextInput in v2.7 / Mantine v8 doesn't surface every keystroke through
# the Dash `value` prop (`Input("ecm-name", "value")` only fires on blur, not
# on input). We bridge it manually with a delegated `input` listener on the
# popover-content node — it catches keystrokes from whichever name input is
# currently mounted (the popover content swaps between create / edit forms
# that both contain a `#ecm-name`) and writes into `ecm-current-name.data`.
clientside_callback(
    """
    () => {
        const root = document.getElementById('ecm-popover-content');
        if (root && !root._dl2_name_wired) {
            root._dl2_name_wired = true;
            root.addEventListener('input', (e) => {
                if (e.target && e.target.id === 'ecm-name') {
                    try {
                        window.dash_clientside.set_props(
                            'ecm-name-bridge', { data: e.target.value || '' }
                        );
                    } catch (err) {
                        console.error('[ecm-name bridge] set_props failed', err);
                    }
                }
            });
            return 'wired';
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("ecm-name-wired", "data"),
    Input("ecm-popover-content", "id"),
)


@callback(
    Output("ecm-ec", "featureUpdate", allow_duplicate=True),
    Output("ecm-features", "data", allow_duplicate=True),
    Output("ecm-current-name", "data", allow_duplicate=True),
    Input("ecm-name-bridge", "data"),
    State("ecm-pending-id", "data"),
    State("ecm-selected-id", "data"),
    State("ecm-features", "data"),
    State("ecm-ec", "featureUpdate"),
    prevent_initial_call=True,
)
def on_name_change(name, pending_id, selected_id, features, last_fu):
    target_id = pending_id or selected_id
    features = dict(features or {})
    if not target_id:
        return no_update, no_update, no_update
    # Echo guard: skip if value matches what we already stored.
    if (features.get(target_id, {}) or {}).get("name") == (name or ""):
        return no_update, no_update, no_update
    last_n = (last_fu or {}).get("n_clicks", 0)
    features[target_id] = {**features.get(target_id, {}), "name": name or ""}
    return (
        {"id": target_id, "properties": {"name": name or ""}, "n_clicks": last_n + 1},
        features,
        name or "",
    )


# ---- Cancel button (create mode) -------------------------------------------
@callback(
    Output("ecm-mode", "data", allow_duplicate=True),
    Output("ecm-pending-id", "data", allow_duplicate=True),
    Output("ecm-popover", "opened", allow_duplicate=True),
    Output("ecm-ec", "drawToolbar"),
    Output("ecm-ec", "featureUpdate", allow_duplicate=True),
    Output("ecm-features", "data", allow_duplicate=True),
    Output("ecm-drawtool-tick", "data"),
    Input("ecm-cancel", "n_clicks"),
    State("ecm-pending-id", "data"),
    State("ecm-drawtool-tick", "data"),
    State("ecm-ec", "featureUpdate"),
    State("ecm-features", "data"),
    prevent_initial_call=True,
)
def on_cancel(n, pending_id, dt_tick, last_fu, features):
    # Mount-fire guard: dynamic mount → Dash fires n_clicks=None despite
    # prevent_initial_call. Without this, Cancel triggers on popover open.
    if not n:
        return [no_update] * 7
    dt = (dt_tick or 0) + 1
    if pending_id:
        last_n = (last_fu or {}).get("n_clicks", 0)
        features = dict(features or {})
        features.pop(pending_id, None)
        return (
            "view",
            None,
            False,
            {"action": "cancel", "n_clicks": dt},
            {"id": pending_id, "remove": True, "n_clicks": last_n + 1},
            features,
            dt,
        )
    return (
        "view",
        None,
        False,
        {"action": "cancel", "n_clicks": dt},
        no_update,
        no_update,
        dt,
    )


# ---- Create button (create mode) -------------------------------------------
@callback(
    Output("ecm-mode", "data", allow_duplicate=True),
    Output("ecm-pending-id", "data", allow_duplicate=True),
    Output("ecm-popover", "opened", allow_duplicate=True),
    Input("ecm-create", "n_clicks"),
    State("ecm-pending-id", "data"),
    prevent_initial_call=True,
)
def on_create(n, pending_id):
    if not n:
        return no_update, no_update, no_update
    # Whether a shape was drawn or not, "Create" finishes the create flow.
    return "view", None, False


# ---- Delete button (edit mode, selected feature) ---------------------------
@callback(
    Output("ecm-selected-id", "data", allow_duplicate=True),
    Output("ecm-popover", "opened", allow_duplicate=True),
    Output("ecm-ec", "featureUpdate", allow_duplicate=True),
    Output("ecm-features", "data", allow_duplicate=True),
    Input("ecm-delete", "n_clicks"),
    State("ecm-selected-id", "data"),
    State("ecm-ec", "featureUpdate"),
    State("ecm-features", "data"),
    prevent_initial_call=True,
)
def on_delete(n, selected_id, last_fu, features):
    if not n or not selected_id:
        return [no_update] * 4
    last_n = (last_fu or {}).get("n_clicks", 0)
    features = dict(features or {})
    features.pop(selected_id, None)
    return (
        None,
        False,
        {"id": selected_id, "remove": True, "n_clicks": last_n + 1},
        features,
    )


# ---- Done button (edit mode, selected) -------------------------------------
@callback(
    Output("ecm-selected-id", "data", allow_duplicate=True),
    Output("ecm-popover", "opened", allow_duplicate=True),
    Input("ecm-done", "n_clicks"),
    prevent_initial_call=True,
)
def on_done(n):
    if not n:
        return no_update, no_update
    return None, False


# ---- units toggle ----------------------------------------------------------
@callback(Output("ecm-ec", "measurementSystem"), Input("ecm-units", "value"))
def set_units(v):
    return v or "metric"


# ---- mode badge readout ----------------------------------------------------
@callback(
    Output("ecm-mode-badge", "children"),
    Output("ecm-mode-badge", "color"),
    Output("ecm-mode-icon", "icon"),
    Output("ecm-mode-icon", "color"),
    Input("ecm-mode", "data"),
)
def mode_readout(mode):
    if mode == "create":
        return (
            "create",
            "green",
            "mdi:plus-circle-outline",
            "var(--mantine-color-green-6)",
        )
    if mode == "edit":
        return "edit", "blue", "mdi:pencil-outline", "var(--mantine-color-blue-6)"
    return "view", "gray", "mdi:eye-outline", "var(--mantine-color-dimmed)"


# ---- last action readout ---------------------------------------------------
@callback(Output("ecm-action", "children"), Input("ecm-ec", "action"))
def action_readout(a):
    return json.dumps(a, indent=1) if a else "—"


# ---- area / length formatting (mirrors src/ts/components/EditControl.tsx) --
# Python-side formatting lets us re-format already-emitted measurements when
# the Metric/Imperial toggle flips, without round-tripping back through the
# TS layer. The constants match the TS helpers character-for-character.

MI2_IN_M2 = 2_589_988.110336  # 1 mi²
ACRE_IN_M2 = 4046.8564224  # 1 acre = 43,560 ft²
M2_TO_FT2 = 10.7639104  # 1 m²   = 10.7639 ft²
HA_IN_M2 = 10_000  # 1 ha
KM2_IN_M2 = 1_000_000  # 1 km²
M_TO_FT = 3.28084
MI_IN_M = 1609.344


def fmt_area(m2: float, units: str) -> str:
    if not m2 or m2 <= 0:
        return "—"
    if units == "imperial":
        if m2 >= MI2_IN_M2:
            return f"{m2 / MI2_IN_M2:.2f} mi²"
        if m2 >= ACRE_IN_M2:
            return f"{m2 / ACRE_IN_M2:.2f} acres"
        return f"{round(m2 * M2_TO_FT2):,} ft²"
    if m2 >= KM2_IN_M2:
        return f"{m2 / KM2_IN_M2:.2f} km²"
    if m2 >= HA_IN_M2:
        return f"{m2 / HA_IN_M2:.2f} ha"
    return f"{round(m2):,} m²"


def fmt_length(m: float, units: str) -> str:
    if not m or m <= 0:
        return "—"
    if units == "imperial":
        return f"{m / MI_IN_M:.2f} mi" if m >= MI_IN_M else f"{round(m * M_TO_FT):,} ft"
    return f"{m / 1000:.2f} km" if m >= 1000 else f"{round(m):,} m"


# ---- features list readout -------------------------------------------------
@callback(
    Output("ecm-list", "children"),
    Input("ecm-features", "data"),
    Input("ecm-units", "value"),
)
def features_readout(features, units):
    features = features or {}
    units = units or "metric"
    if not features:
        return dmc.Text(
            "Click a draw tool (top-left of the map) to start.", size="sm", c="dimmed"
        )
    rows = []
    total_m2 = 0.0
    for fid, f in features.items():
        name = f.get("name") or "(unnamed)"
        area_m2 = float(f.get("area_m2") or 0)
        length_m = float(f.get("length_m") or 0)
        # Pick the right measurement for this shape: area for filled shapes,
        # length for polylines, em-dash for shapes with no metric (markers).
        measure = (
            fmt_area(area_m2, units)
            if area_m2 > 0
            else (fmt_length(length_m, units) if length_m > 0 else "—")
        )
        total_m2 += area_m2
        rows.append(
            dmc.Group(
                [
                    html.Div(
                        style={
                            "width": 14,
                            "height": 14,
                            "borderRadius": 3,
                            "border": "1px solid var(--mantine-color-default-border)",
                            "background": f.get("color") or DEFAULT_COLOR,
                        }
                    ),
                    dmc.Text(
                        measure,
                        size="xs",
                        c="dimmed",
                        ff="monospace",
                        style={"width": 86},
                    ),
                    dmc.Text(name, size="sm", fw=500, truncate=True),
                ],
                gap="xs",
                wrap="nowrap",
            )
        )
    # Append a divider + total area row (only counts shapes that have area —
    # polylines / markers are excluded from the sum).
    if total_m2 > 0:
        rows.append(dmc.Divider(my=4))
        rows.append(
            dmc.Group(
                [
                    html.Div(style={"width": 14, "height": 14}),  # spacer for alignment
                    dmc.Text(
                        "Total", size="xs", c="dimmed", fw=600, style={"width": 86}
                    ),
                    dmc.Text(
                        fmt_area(total_m2, units),
                        size="sm",
                        fw=700,
                        c="var(--mantine-color-green-6)",
                    ),
                ],
                gap="xs",
                wrap="nowrap",
            )
        )
    return dmc.Stack(rows, gap=4)


# ---- theme sync (light/dark) — mirrors /easy-button -----------------------
clientside_callback(
    "(checked) => (checked ? '%s' : '%s')" % (CARTO_LIGHT, CARTO_DARK),
    Output("ecm-tile", "url"),
    Input("color-scheme-toggle", "checked"),
)
