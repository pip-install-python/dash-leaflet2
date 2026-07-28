"""
Easy Button + marker creation flow with emoji picker, form popup, and view mode.

Click the smile button on the map (top-left) to enter create mode → a dmc.Popover opens
directly to the right of the button with a DashEmojiMart picker. Click the map to place
the marker; a form popup opens above it with name/type fields. Pick an emoji at any time
to update the marker's icon live. Create finalizes the marker (pushes to a markers store,
exits create mode, closes everything); Cancel discards.

(We use dmc.Popover, not dmc.HoverCard. HoverCard is hover-triggered only — it would close
the moment the user moves their mouse off the button toward the map to place a marker.
Popover supports click-triggered + controlled `opened`, same visual styling.)
"""

import dash
import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, State, callback, clientside_callback, ctx, dcc, html
from dash_emoji_mart import DashEmojiMart
from dash_iconify import DashIconify
from dl2_shared import code_panel, header, info_panel

# CARTO Positron (light) + Dark Matter — the standard light/dark pair the rest of the
# showcase already uses (see assets/leaflet2_maps.js). The tile URL is swapped at
# runtime via a clientside callback driven by the app's color-scheme toggle.
CARTO_LIGHT = "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
CARTO_DARK = "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
ATTR = (
    '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> '
    '&copy; <a href="https://carto.com/attributions">CARTO</a>'
)

MARKER_TYPES = ["Market", "Event", "Bounty", "Other"]
TYPE_COLORS = {"Market": "green", "Event": "blue", "Bounty": "grape", "Other": "gray"}

CODE = """dl2.Map(children=[
    dl2.TileLayer(),
    dl2.EasyButton(id="add", icon="mdi:emoticon-happy-outline"),
    # placed by callback after map click in create mode:
    dl2.Marker(position=pending["lat,lng"], emoji=pending["emoji"], draggable=True,
               children=dl2.Popup(opened=True, closeOnClick=False, closeButton=False,
                                  children=form_layout(pending)))
])

# Popover anchored to an invisible div positioned over the EasyButton:
dmc.Popover(opened=picker_open, position="right-start",
            children=[
                dmc.PopoverTarget(html.Div(id="anchor")),  # invisible, on top of the button
                dmc.PopoverDropdown(DashEmojiMart(id="emoji")),
            ])"""


# ---- helpers ---------------------------------------------------------------


def form_layout(pending):
    """The form rendered INSIDE the leaflet popup above the pending marker."""
    return html.Div(
        style={"minWidth": "260px", "padding": "2px"},
        children=dmc.Stack(
            [
                dmc.TextInput(
                    id="eb-name",
                    placeholder="Marker name",
                    value=(pending or {}).get("name", ""),
                    size="xs",
                ),
                dmc.SegmentedControl(
                    id="eb-type",
                    data=MARKER_TYPES,
                    value=(pending or {}).get("type", "Market"),
                    size="xs",
                    fullWidth=True,
                ),
                dmc.Group(
                    [
                        dmc.Button(
                            "Cancel",
                            id="eb-cancel",
                            size="xs",
                            variant="light",
                            color="gray",
                        ),
                        dmc.Button(
                            "Create",
                            id="eb-create",
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
        ),
    )


# ---- layout ----------------------------------------------------------------

component = dmc.Stack(
    [
        header(
            "Easy Button — marker creation flow",
            "Click the smile button on the map → emoji picker opens to its right and you enter "
            "create mode. Click the map to drop a draggable marker; a form popup opens above it "
            "for name + type. Picking a new emoji updates the marker icon live. Create finalizes; "
            "Cancel discards.",
            badge="dl2.EasyButton",
        ),
        # Toggle button for the side panel. Mirrors /resize-observer's UX so this page
        # gets the same "expand for full-screen map / collapse to see context" affordance.
        dmc.Button(
            "Toggle side panel",
            id="eb-panel-toggle",
            color="green",
            variant="light",
            leftSection=DashIconify(icon="mdi:panel-right-open", width=16),
        ),
        # Flex row: relative-positioned map wrapper on the left, collapsible info panel on
        # the right. Starts OPEN (the Mode badge + marker list are useful context while
        # creating markers); the user can collapse it for a full-width map. We bump the
        # panel width via --dl2-resize-panel-w because the code snippet inside is wider
        # than what /resize-observer's default 320px shows comfortably.
        html.Div(
            id="eb-row",
            className="dl2-resize-row open",
            style={"height": "62vh", "--dl2-resize-panel-w": "380px"},
            children=[
                html.Div(
                    # Relative container so the Popover anchor div positions absolutely over
                    # the EasyButton location inside the Paper. `dl2-resize-main` makes this
                    # the flex-grow main area (height: 100%, flex: 1 — see assets/style.css).
                    className="dl2-resize-main",
                    style={"position": "relative"},
                    children=[
                        dmc.Paper(
                            dl2.Map(
                                id="eb-map",
                                center=[28.02, -97.05],
                                zoom=12,
                                style={
                                    "height": "100%"
                                },  # fills the dmc.Paper, which fills the flex row
                                children=[
                                    dl2.TileLayer(
                                        id="eb-tile", url=CARTO_LIGHT, attribution=ATTR
                                    ),
                                    dl2.EasyButton(
                                        id="eb-add",
                                        position="topleft",
                                        icon="mdi:emoticon-happy-outline",
                                        iconSize=20,
                                        title="Add an emoji marker",
                                    ),
                                    html.Div(id="eb-pending-container"),
                                    html.Div(id="eb-markers-container"),
                                ],
                            ),
                            shadow="sm",
                            radius="md",
                            withBorder=True,
                            style={"overflow": "hidden", "height": "100%"},
                        ),
                        # Popover anchor: invisible Dash element positioned over the EasyButton.
                        # Leaflet anchors top-left controls 10px from the map edges, button is
                        # 30px wide → anchor at left:46px puts the popover dropdown right of it.
                        dmc.Popover(
                            id="eb-popover",
                            opened=False,
                            position="right-start",
                            offset=6,
                            withArrow=True,
                            arrowSize=10,
                            shadow="lg",
                            radius="md",
                            # Fully suppress the "outside click closes me" behavior — we control
                            # `opened` from the picker-open store. Listening to no events means
                            # the popover never tries to auto-close.
                            closeOnClickOutside=False,
                            closeOnEscape=False,
                            clickOutsideEvents=[],
                            keepMounted=True,
                            children=[
                                # PopoverTarget wraps its child in a dmc.Box that drops inline
                                # absolute styles on the inner element — so position the Box
                                # itself via boxWrapperProps instead.
                                dmc.PopoverTarget(
                                    html.Div(id="eb-popover-anchor"),
                                    boxWrapperProps={
                                        "style": {
                                            "position": "absolute",
                                            "top": "10px",
                                            "left": "46px",
                                            "width": "1px",
                                            "height": "30px",
                                            "pointerEvents": "none",
                                            "zIndex": 600,
                                        }
                                    },
                                ),
                                dmc.PopoverDropdown(
                                    DashEmojiMart(
                                        id="eb-emoji",
                                        theme="auto",
                                        perLine=8,
                                        emojiSize=22,
                                        emojiButtonSize=30,
                                        previewPosition="none",
                                    ),
                                    p=4,
                                ),
                            ],
                        ),
                    ],
                ),
                # Side panel — holds everything that used to live in the right grid column
                # and the bottom code panel: Mode readout, Created markers list, and the
                # snippet showing the dl2.EasyButton + marker-creation pattern.
                html.Div(
                    className="dl2-resize-panel",
                    children=dmc.Stack(
                        [
                            info_panel(
                                "Mode",
                                dmc.Group(
                                    [
                                        dmc.Badge(
                                            id="eb-mode-badge",
                                            color="gray",
                                            variant="light",
                                            children="view",
                                        ),
                                        DashIconify(
                                            id="eb-mode-icon",
                                            icon="mdi:eye-outline",
                                            width=20,
                                            color="var(--mantine-color-dimmed)",
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                            info_panel(
                                "Created markers",
                                html.Div(
                                    id="eb-list",
                                    children=dmc.Text(
                                        "Click the smile button on the map to create your first marker.",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ),
                            ),
                            code_panel(
                                "dl2.EasyButton + marker-creation pattern", CODE
                            ),
                        ],
                        gap="md",
                    ),
                ),
            ],
        ),
        # State stores
        dcc.Store(id="eb-mode", data="view"),
        dcc.Store(id="eb-pending", data=None),
        dcc.Store(id="eb-markers", data=[]),
        dcc.Store(id="eb-picker-open", data=False),
    ],
    gap="md",
)


# ---- callbacks --------------------------------------------------------------


# 1) EasyButton click → toggle create mode + picker.
@callback(
    Output("eb-mode", "data"),
    Output("eb-picker-open", "data"),
    Output("eb-pending", "data"),
    Input("eb-add", "n_clicks"),
    State("eb-mode", "data"),
    prevent_initial_call=True,
)
def toggle_create(_, mode):
    if mode == "create":
        # Toggling off while in create mode: bail out without finalizing.
        return "view", False, None
    return "create", True, None


# 2) Picker open state → DMC Popover.opened
@callback(Output("eb-popover", "opened"), Input("eb-picker-open", "data"))
def reflect_picker(opened):
    return bool(opened)


# 3) Mode badge readout.
@callback(
    Output("eb-mode-badge", "children"),
    Output("eb-mode-badge", "color"),
    Output("eb-mode-icon", "icon"),
    Output("eb-mode-icon", "color"),
    Input("eb-mode", "data"),
)
def mode_readout(mode):
    if mode == "create":
        return "create", "green", "mdi:pencil-outline", "var(--mantine-color-green-6)"
    return "view", "gray", "mdi:eye-outline", "var(--mantine-color-dimmed)"


# 4) Picking an emoji updates pending (creating a stub if none yet) + resets the picker.
@callback(
    Output("eb-pending", "data", allow_duplicate=True),
    Output("eb-emoji", "value"),
    Input("eb-emoji", "value"),
    State("eb-mode", "data"),
    State("eb-pending", "data"),
    prevent_initial_call=True,
)
def pick_emoji(emoji, mode, pending):
    if not emoji or mode != "create":
        return dash.no_update, dash.no_update
    base = pending or {}
    return {**base, "emoji": emoji}, ""


# 5) Map click while in create mode → place the pending marker (only first click).
@callback(
    Output("eb-pending", "data", allow_duplicate=True),
    Input("eb-map", "clickData"),
    State("eb-mode", "data"),
    State("eb-pending", "data"),
    prevent_initial_call=True,
)
def place_pending(click, mode, pending):
    if mode != "create" or not click:
        return dash.no_update
    if pending and "lat" in pending:
        return dash.no_update  # already placed; further clicks ignored (drag to move)
    lat, lng = click["latlng"]
    base = pending or {}
    return {
        **base,
        "lat": lat,
        "lng": lng,
        "name": base.get("name", ""),
        "type": base.get("type", "Market"),
    }


# 6) Cancel → discard pending + exit create mode.
@callback(
    Output("eb-mode", "data", allow_duplicate=True),
    Output("eb-pending", "data", allow_duplicate=True),
    Output("eb-picker-open", "data", allow_duplicate=True),
    Output("eb-emoji", "value", allow_duplicate=True),
    Input("eb-cancel", "n_clicks"),
    prevent_initial_call=True,
)
def cancel(n):
    # Cancel/Create are dynamically mounted via render_pending; Dash fires their
    # callbacks on first mount with n_clicks=None despite prevent_initial_call=True.
    # Guard against the mount-fire so it doesn't immediately close the popover.
    if not n:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    return "view", None, False, ""


# 7) Create → finalize pending (push to markers) + exit.
@callback(
    Output("eb-markers", "data"),
    Output("eb-mode", "data", allow_duplicate=True),
    Output("eb-pending", "data", allow_duplicate=True),
    Output("eb-picker-open", "data", allow_duplicate=True),
    Output("eb-emoji", "value", allow_duplicate=True),
    Input("eb-create", "n_clicks"),
    State("eb-pending", "data"),
    State("eb-name", "value"),
    State("eb-type", "value"),
    State("eb-markers", "data"),
    prevent_initial_call=True,
)
def create(n, pending, name, type_, markers):
    # Same mount-fire guard as cancel — without it, the Create button mounting fires
    # this callback with n=None and closes everything before the user can interact.
    if not n:
        return (
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
            dash.no_update,
        )
    if not pending or "lat" not in pending:
        return dash.no_update, "view", None, False, ""
    final = {**pending, "name": name or "", "type": type_ or "Market"}
    return list(markers or []) + [final], "view", None, False, ""


# 8) Render the pending marker (+ form popup) into the map.
@callback(Output("eb-pending-container", "children"), Input("eb-pending", "data"))
def render_pending(pending):
    if not pending or "lat" not in pending:
        return []
    emoji = pending.get("emoji")
    return dl2.Marker(
        id="eb-pending-marker",
        position=[pending["lat"], pending["lng"]],
        emoji=emoji,
        iconSize=34 if emoji else None,
        draggable=True,
        children=dl2.Popup(
            id="eb-pending-popup",
            opened=True,
            closeOnClick=False,
            autoClose=False,
            closeButton=False,
            maxWidth=320,
            minWidth=260,
            children=form_layout(pending),
        ),
    )


# 9) Drag the pending marker → update its position in pending.
@callback(
    Output("eb-pending", "data", allow_duplicate=True),
    Input("eb-pending-marker", "position"),
    State("eb-pending", "data"),
    prevent_initial_call=True,
)
def drag_pending(pos, pending):
    if not pending or not pos:
        return dash.no_update
    if pos[0] == pending.get("lat") and pos[1] == pending.get("lng"):
        return dash.no_update
    return {**pending, "lat": pos[0], "lng": pos[1]}


# 10) Render finalized markers (view mode).
@callback(
    Output("eb-markers-container", "children"),
    Output("eb-list", "children"),
    Input("eb-markers", "data"),
)
def render_markers(markers):
    markers = markers or []
    if not markers:
        empty = dmc.Text(
            "Click the smile button on the map to create your first marker.",
            size="sm",
            c="dimmed",
        )
        return [], empty
    children = []
    for i, m in enumerate(markers):
        emoji = m.get("emoji")
        type_ = m.get("type", "Other")
        name = m.get("name") or "(unnamed)"
        children.append(
            dl2.Marker(
                position=[m["lat"], m["lng"]],
                emoji=emoji,
                iconSize=34 if emoji else None,
                children=[
                    dl2.Tooltip(children=name),
                    dl2.Popup(
                        children=html.Div(
                            style={"minWidth": "180px"},
                            children=dmc.Stack(
                                [
                                    dmc.Text(name, fw=600, size="sm"),
                                    dmc.Badge(
                                        type_,
                                        color=TYPE_COLORS.get(type_, "gray"),
                                        variant="light",
                                        size="sm",
                                    ),
                                ],
                                gap=4,
                            ),
                        )
                    ),
                ],
            )
        )
    listing = dmc.Stack(
        [
            dmc.Group(
                [
                    dmc.Text(m.get("emoji") or "📍", size="lg"),
                    dmc.Stack(
                        [
                            dmc.Text(m.get("name") or "(unnamed)", size="sm", fw=600),
                            dmc.Badge(
                                m.get("type", "Other"),
                                color=TYPE_COLORS.get(m.get("type", "Other"), "gray"),
                                variant="light",
                                size="xs",
                            ),
                        ],
                        gap=0,
                    ),
                ],
                gap="sm",
            )
            for m in markers
        ],
        gap="sm",
    )
    return children, listing


# ---- side-panel toggle (mirrors /resize-observer) --------------------------
# Toggle the .open class on the flex row; the panel slides in/out via CSS
# transition (assets/style.css → .dl2-resize-row + .dl2-resize-panel). Because
# the map's container is a flex item, Leaflet 2's ResizeObserver picks up the
# width change and reflows the tiles automatically — no invalidateSize() needed.
clientside_callback(
    """
    (n) => {
        const r = document.getElementById('eb-row');
        if (r) r.classList.toggle('open');
        return window.dash_clientside.no_update;
    }
    """,
    Output("eb-panel-toggle", "id"),
    Input("eb-panel-toggle", "n_clicks"),
    prevent_initial_call=True,
)


# ---- theme sync (light/dark) ------------------------------------------------
# The header toggle (`color-scheme-toggle.checked`) drives the app's color scheme —
# checked=True means light. Mirror it to the dl2.TileLayer URL (CARTO Positron vs
# Dark Matter) and to DashEmojiMart's `theme` prop so the picker UI follows along
# too. Same pattern the /emoji-iconify page uses.
clientside_callback(
    "(checked) => (checked ? '%s' : '%s')" % (CARTO_LIGHT, CARTO_DARK),
    Output("eb-tile", "url"),
    Input("color-scheme-toggle", "checked"),
)

clientside_callback(
    "(checked) => (checked ? 'light' : 'dark')",
    Output("eb-emoji", "theme"),
    Input("color-scheme-toggle", "checked"),
)
