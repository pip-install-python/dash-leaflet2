"""
AttributionControl — explicit control over the attribution box.

Mirrors dash-leaflet 1.x: pass `attributionControl=False` to the Map to suppress
Leaflet 2's built-in attribution control, then add a `dl2.AttributionControl`
as a child to position it explicitly and customize the prefix.

  • `position` ∈ {'topleft','topright','bottomleft','bottomright'} — [MUTABLE]
  • `prefix`   — string of HTML (any anchor / icon / text), or `False` to hide
                 the Leaflet link entirely. [MUTABLE]

Bonus: a Switch toggles whether the `dl2.AttributionControl` is mounted at all —
which proves the `attributionControl=False` map option does suppress the bundled
default (without our component, no box appears).
"""

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import (
    Input,
    Output,
    State,
    callback,
    clientside_callback,
    dcc,
    html,
    no_update,
)
from dash_iconify import DashIconify
from dl2_tiles import VOYAGER, register_theme_swap
from dl2_locations import BOSTON
from dl2_shared import code_panel, header, info_panel

# Basemap pair for this page. dl2_tiles owns the light/dark wiring so
# every example themes the same way — see register_theme_swap below.
TILES = VOYAGER
TILE_URL = TILES.url("light")
ATTR = TILES.attribution()

# Three sample prefixes the user can flip between with a SegmentedControl. The
# "Custom" branch reads the live TextInput value instead.
PREFIX_PRESETS = {
    "leaflet": (
        '<a target="_blank" href="https://leafletjs.com" '
        'title="A JavaScript library for interactive maps">Leaflet</a>'
    ),
    "branded": (
        '<a href="https://pipinstallpython.com" target="_blank" '
        'style="display:inline-flex;align-items:center;'
        'text-decoration:none;color:inherit;">'
        "🛰️&nbsp;<b>dash-leaflet2</b></a>"
    ),
    "none": False,
}

CODE = """import dash_leaflet2 as dl2

dl2.Map(
    attributionControl=False,          # suppress Leaflet 2's built-in control
    children=[
        dl2.TileLayer(),
        dl2.AttributionControl(
            id="attr",
            position="bottomright",
            prefix='<a href="https://pipinstallpython.com">dash-leaflet2</a>',
        ),
    ],
)

# Both `position` and `prefix` are MUTABLE — drive them from callbacks.
@callback(Output("attr", "prefix"), Input("custom-prefix", "value"))
def update_prefix(text):
    return text or False     # False hides the prefix entirely
"""


component = dmc.Stack(
    [
        header(
            "AttributionControl",
            "Explicit control over the attribution box. Set `attributionControl=False` on "
            "the Map to suppress Leaflet 2's built-in control, then add a "
            "`dl2.AttributionControl` child to choose its corner and prefix HTML. The "
            "prefix accepts any HTML (anchors, emoji, inline-styled brand marks) — pass "
            "`False` to hide it entirely.",
            badge="dl2.AttributionControl",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dl2.Map(
                            id="attr-map",
                            center=BOSTON.center,
                            zoom=10,
                            attributionControl=False,
                            style={"height": "60vh"},
                            children=[
                                dl2.TileLayer(
                                    id="attr-tile", url=TILE_URL, attribution=ATTR
                                ),
                                dl2.Marker(
                                    position=BOSTON.center,
                                    iconify="mdi:lighthouse-on",
                                    iconColor="#e8590c",
                                    iconSize=32,
                                ),
                                # The component is rendered into a Dash child by the
                                # "mount" callback below — Python toggles whether it's
                                # in the children list at all.
                                html.Div(id="attr-mount"),
                            ],
                        ),
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
                                "Mounted?",
                                dmc.Stack(
                                    [
                                        dmc.Switch(
                                            id="attr-mounted",
                                            label="Render dl2.AttributionControl",
                                            description="Off → map's attributionControl=False shows nothing.",
                                            checked=True,
                                            size="sm",
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                            info_panel(
                                "Position",
                                dmc.SegmentedControl(
                                    id="attr-position",
                                    data=[
                                        {"value": "topleft", "label": "TL"},
                                        {"value": "topright", "label": "TR"},
                                        {"value": "bottomleft", "label": "BL"},
                                        {"value": "bottomright", "label": "BR"},
                                    ],
                                    value="bottomright",
                                    size="xs",
                                    fullWidth=True,
                                ),
                            ),
                            info_panel(
                                "Prefix",
                                dmc.Stack(
                                    [
                                        dmc.SegmentedControl(
                                            id="attr-prefix-preset",
                                            data=[
                                                {
                                                    "value": "leaflet",
                                                    "label": "Leaflet link",
                                                },
                                                {
                                                    "value": "branded",
                                                    "label": "Branded",
                                                },
                                                {"value": "none", "label": "Hidden"},
                                                {"value": "custom", "label": "Custom"},
                                            ],
                                            value="branded",
                                            size="xs",
                                            fullWidth=True,
                                        ),
                                        dmc.Textarea(
                                            id="attr-prefix-custom",
                                            placeholder='HTML allowed, e.g. <a href="...">my site</a>',
                                            minRows=2,
                                            maxRows=5,
                                            autosize=True,
                                            size="xs",
                                            value='🌐 <a href="https://example.com">my site</a>',
                                        ),
                                        dmc.Text(
                                            "Picking 'Custom' wires the textarea live to "
                                            "AttributionControl.prefix.",
                                            size="xs",
                                            c="dimmed",
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ),
                            info_panel(
                                "Live state",
                                dmc.Stack(
                                    [
                                        dmc.Text("position", size="xs", c="dimmed"),
                                        dmc.Code(
                                            id="attr-state-position",
                                            children="bottomright",
                                        ),
                                        dmc.Text(
                                            "prefix HTML (None = hidden)",
                                            size="xs",
                                            c="dimmed",
                                        ),
                                        dmc.Code(
                                            id="attr-state-prefix",
                                            block=True,
                                            style={
                                                "fontSize": "11px",
                                                "whiteSpace": "pre-wrap",
                                            },
                                        ),
                                    ],
                                    gap=4,
                                ),
                            ),
                        ],
                        gap="md",
                    ),
                    span={"base": 12, "md": 4},
                ),
            ]
        ),
        code_panel(
            "dl2.AttributionControl — explicit positioning + custom prefix", CODE
        ),
        # Internal store: holds the resolved prefix value (string or False).
        dcc.Store(id="attr-resolved-prefix", data=PREFIX_PRESETS["branded"]),
    ],
    gap="md",
)


# ---- prefix preset/custom -> resolved prefix value -------------------------
@callback(
    Output("attr-resolved-prefix", "data"),
    Input("attr-prefix-preset", "value"),
    Input("attr-prefix-custom", "value"),
)
def resolve_prefix(preset, custom):
    if preset == "custom":
        # Empty custom -> False (hide); otherwise the raw HTML string.
        return custom or False
    return PREFIX_PRESETS.get(preset, PREFIX_PRESETS["leaflet"])


# ---- mount / unmount the AttributionControl child --------------------------
@callback(
    Output("attr-mount", "children"),
    Input("attr-mounted", "checked"),
    Input("attr-position", "value"),
    Input("attr-resolved-prefix", "data"),
)
def render_attribution_control(mounted, position, prefix):
    if not mounted:
        return []
    return dl2.AttributionControl(
        id="attr-ctl",
        position=position or "bottomright",
        prefix=prefix,
    )


# ---- live readouts ----------------------------------------------------------
@callback(
    Output("attr-state-position", "children"),
    Output("attr-state-prefix", "children"),
    Input("attr-position", "value"),
    Input("attr-resolved-prefix", "data"),
)
def state_readouts(position, prefix):
    if prefix is False:
        return (position or "bottomright"), "False  (prefix hidden)"
    return (position or "bottomright"), prefix or "(empty string — prefix hidden)"


# ---- light/dark tile swap (existing pattern) -------------------------------
register_theme_swap("attr-tile", TILES)
