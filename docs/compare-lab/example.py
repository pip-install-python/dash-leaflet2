"""
Compare Lab — stack, reorder and cross-fade tile overlays from a
TreeViewPro popover.

A `dl2.EasyButton` opens a Mantine Popover holding a MUI TreeViewPro; every
interaction in that tree reconciles a stack of `dl2.TileLayer` overlays on the
map beneath it — visibility, per-layer opacity, z-order and deletion.

The interesting part is the reconciler. Overlays are never unmounted and
remounted as the tree changes; a clientside callback diffs the desired state
against what is already on the map and mutates only what differs. That is what
keeps a slider drag smooth instead of rebuilding a TileLayer every frame.

Overlays here are SYNTHETIC — coloured SVG placeholders seeded by a button — so
the page is self-contained and every interaction responds in under a second.

What this page demonstrates:

  1. **Consistent initial state.** The tree shows Esri World Imagery checked at
     80 % opacity on first paint AND the layer is actually on the map. The
     store's initial value has to agree with the tree's initial `selectedItems`:
     with a `prevent_initial_call=True` reducer, a store saying
     `source_visible=False` while the tree says checked leaves the layer
     invisible until the user jiggles a control. Both are initialised to the
     same truth here (`source_visible: True`), so render-source-layer fires
     correctly on first paint.
  2. **Light/dark basemap.** The basemap auto-swaps between CARTO Positron
     (light) and CARTO Dark Matter (dark) with the app-shell
     `color-scheme-toggle`, driven by a clientside callback so it is instant.
  3. **Multi-zoom overlays.** "Seed 3 fake gens" drops three coloured SVG tiles
     at matching z14 / z15 / z16 coordinates near Rockport, TX, so cross-zoom
     relationships line up and the association-by-zoom math has real input.
  4. **All TreeViewPro interactions wired** — selection toggles overlay
     visibility, sliders drive opacity, the kebab "Remove" deletes the leaf and
     its overlay, and items are reorderable to drive z-order.
"""

from __future__ import annotations

import base64
import os
import time

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import (
    ALL,
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
from dash_mui_charts import TreeViewPro

# ---------------------------------------------------------------------
# Constants — tile URLs, attributions, MUI key.
# ---------------------------------------------------------------------

# CARTO basemap (no `{s}` subdomain so the URL is stable for the
# clientside light/dark swap below — the swap just substitutes one URL
# template for the other).
CARTO_LIGHT = "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
CARTO_DARK = "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
CARTO_ATTR = (
    '&copy; <a href="https://openstreetmap.org/copyright">'
    "OpenStreetMap</a> &copy; "
    '<a href="https://carto.com/attributions">CARTO</a>'
)

ESRI_SAT = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
ESRI_ATTR = (
    "Tiles &copy; Esri &mdash; Esri, Maxar, Earthstar Geographics, "
    "and the GIS User Community"
)

MUI_PRO_LICENSE_KEY = os.environ.get("MUI_PRO_API_KEY", "")

# The three synthetic generation coords — chosen so the cross-zoom
# nesting math is genuine (z15 is the NW child of z14, z16 is the NW
# child of z15) and so the area aligns with the rest of the project's
# Rockport-TX demos.
SYNTH_KEYS = ["14/3776/6858", "15/7552/13716", "16/15104/27432"]
SYNTH_COLOR = ["#e64980", "#7950f2", "#15aabf"]  # one color per zoom


# ---------------------------------------------------------------------
# Tiny shared helpers (copied — not imported — to keep the lab fully
# self-contained).
# ---------------------------------------------------------------------


def parse_key(key: str) -> tuple[int, int, int]:
    z, x, y = key.split("/")
    return int(z), int(x), int(y)


def _synth_data_url(label: str, color: str) -> str:
    """A 256x256 SVG square — used as the synthetic overlay image.
    Inline data URL so no network fetch happens at render time."""
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='256' height='256'>"
        f"<rect width='256' height='256' fill='{color}' opacity='0.88'/>"
        f"<text x='128' y='128' text-anchor='middle' "
        f"dominant-baseline='middle' fill='white' "
        f"font-family='monospace' font-size='22' font-weight='700'>"
        f"{label}</text></svg>"
    )
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}"


def _synth_gen(key: str, idx: int) -> dict:
    z, x, y = parse_key(key)
    return {
        "data_url": _synth_data_url(f"z{z}", SYNTH_COLOR[idx % len(SYNTH_COLOR)]),
        "model": "synthetic",
        "n": 1,
        "source": key,
        "accepted": True,
        "ts": time.time() + idx,
    }


def _build_tree(generations: dict) -> list[dict]:
    """Build the TreeViewPro model — Custom
    Tileset group first (one leaf per generation, sorted by z, x, y),
    Source Tileset group second (one leaf: Esri World Imagery)."""
    keys = list((generations or {}).keys())

    def _zxy(k: str):
        try:
            return (0, *parse_key(k))
        except Exception:
            return (1, k, 0, 0)

    keys.sort(key=_zxy)
    custom_children: list[dict] = []
    for key in keys:
        gen = (generations or {}).get(key)
        if not (gen and gen.get("data_url")):
            continue
        z, x, y = parse_key(key)
        custom_children.append({"id": f"cust:{key}", "label": f"z{z} · {x}/{y}"})
    if not custom_children:
        custom_children.append(
            {"id": "cust:empty", "label": "(no generations — click Seed)"}
        )
    n_real = len([c for c in custom_children if c["id"] != "cust:empty"])
    return [
        {
            "id": "grp.custom",
            "label": f"Custom Tileset ({n_real})",
            "children": custom_children,
        },
        {
            "id": "grp.source",
            "label": "Source Tileset",
            "children": [
                {"id": "src:esri", "label": "Esri World Imagery (satellite)"},
            ],
        },
    ]


KEBAB_MENU = [
    {"label": "Remove", "value": "delete", "icon": "Delete"},
]


# ---------------------------------------------------------------------
# Popover builder
# ---------------------------------------------------------------------


def _compare_popover():
    return dmc.Popover(
        id="cl-compare-popover",
        opened=False,
        position="right-start",
        offset=6,
        withArrow=True,
        arrowSize=10,
        shadow="lg",
        radius="md",
        closeOnClickOutside=True,
        closeOnEscape=True,
        keepMounted=True,
        children=[
            # Anchor — invisible 1×30 strip over the EasyButton.
            dmc.PopoverTarget(
                html.Div(id="cl-compare-anchor"),
                boxWrapperProps={
                    "style": {
                        "position": "absolute",
                        "top": "60px",
                        "left": "46px",
                        "width": "1px",
                        "height": "30px",
                        "pointerEvents": "none",
                        "zIndex": 600,
                    }
                },
            ),
            dmc.PopoverDropdown(
                dmc.Stack(
                    [
                        dmc.Group(
                            [
                                DashIconify(
                                    icon="mdi:layers-search-outline",
                                    width=16,
                                    color="var(--mantine-color-blue-6)",
                                ),
                                dmc.Text("Tileset comparison", fw=600, size="sm"),
                                dmc.Badge(
                                    "LAB",
                                    color="violet",
                                    variant="light",
                                    size="xs",
                                    ml="auto",
                                ),
                            ],
                            gap="xs",
                            wrap="nowrap",
                        ),
                        dmc.Divider(),
                        dmc.Text(
                            "Synthetic playground — selection / slider / "
                            "kebab / drag-reorder all update the map in real "
                            "time. No AI calls.",
                            size="xs",
                            c="dimmed",
                        ),
                        html.Div(
                            TreeViewPro(
                                id="cl-compare-tree",
                                items=_build_tree({}),
                                defaultExpandedItems=["grp.source", "grp.custom"],
                                multiSelect=True,
                                checkboxSelection=True,
                                # MATCH the initial store value below — this is the
                                # fix for the "Source Tileset reads checked but
                                # isn't on the map" mismatch described in the module docstring.
                                selectedItems=["src:esri"],
                                isItemEditable=False,
                                itemsReordering=True,
                                showItemControls=True,
                                controlsItems=["src:esri"],
                                sliderValues={"src:esri": 80},
                                sliderMin=0,
                                sliderMax=100,
                                sliderStep=1,
                                sliderColor="blue",
                                kebabMenuItems=KEBAB_MENU,
                                licenseKey=MUI_PRO_LICENSE_KEY,
                                expandIcon="ChevronRight",
                                collapseIcon="ExpandMore",
                                itemChildrenIndentation="14px",
                                sx={
                                    "& .MuiTreeItem-content": {"paddingY": "3px"},
                                    "& .MuiTreeItem-label": {
                                        "fontSize": "12px",
                                        "width": "100%",
                                    },
                                    "& .MuiSlider-root": {
                                        "height": "2px",
                                        "padding": "8px 0",
                                    },
                                },
                            ),
                            className="tlp-tree",  # reuse /tile-layers-pro tree polish
                        ),
                    ],
                    gap=10,
                ),
                p="md",
                style={"width": "360px"},
            ),
        ],
    )


# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------

component = dmc.Stack(
    [
        dmc.Group(
            [
                dmc.Stack(
                    [
                        dmc.Title("Compare Lab", order=2, mb=0),
                        dmc.Text(
                            "Isolated harness for the Tileset Comparison popover. "
                            "Initial render shows Esri satellite at 80 % on top of "
                            "CARTO (light or dark per the app theme). Seed synthetic "
                            "generations and exercise the TreeViewPro controls; the "
                            "map reflects every change immediately.",
                            size="sm",
                            c="dimmed",
                        ),
                    ],
                    gap=2,
                ),
                dmc.Badge(
                    "polished pattern testing",
                    color="violet",
                    variant="light",
                    size="lg",
                ),
            ],
            justify="space-between",
            wrap="nowrap",
            align="start",
        ),
        dmc.Group(
            [
                dmc.Button(
                    "Seed 3 fake gens (z14 / z15 / z16)",
                    id="cl-seed",
                    leftSection=DashIconify(icon="mdi:auto-fix", width=16),
                    color="violet",
                ),
                dmc.Button(
                    "Clear all",
                    id="cl-clear",
                    variant="light",
                    color="red",
                    leftSection=DashIconify(icon="mdi:trash-can-outline", width=16),
                ),
                dmc.Tooltip(
                    label=(
                        "Synthetic overlays at z14/z15/z16, nested as ancestor/"
                        "descendant of each other so cross-zoom math is real. "
                        "Toggle / slider / kebab reorder + delete all wired."
                    ),
                    multiline=True,
                    w=320,
                    withArrow=True,
                    position="bottom",
                    children=DashIconify(
                        icon="mdi:information-outline",
                        width=18,
                        color="var(--mantine-color-dimmed)",
                    ),
                ),
            ],
            gap="xs",
        ),
        html.Div(
            # Position-relative so the popover's absolute anchor lands over
            # the EasyButton on the map.
            style={"position": "relative", "height": "72vh"},
            children=[
                dmc.Paper(
                    dl2.Map(
                        id="cl-map",
                        center=[28.02, -97.05],
                        zoom=11,
                        style={"height": "100%", "width": "100%"},
                        children=[
                            # Basemap — URL controlled by the clientside
                            # light/dark callback below.
                            dl2.TileLayer(
                                id="cl-basemap", url=CARTO_LIGHT, attribution=CARTO_ATTR
                            ),
                            # Source Tileset slot — a Python callback fills
                            # this with the Esri TileLayer when source_visible
                            # is True (which it IS at page load — that's the
                            # fix the lab is demonstrating).
                            html.Div(id="cl-source-layer-slot"),
                            # Compare popover trigger.
                            dl2.EasyButton(
                                id="cl-compare-btn",
                                position="topleft",
                                icon="mdi:layers-search-outline",
                                iconSize=20,
                                title="Tileset comparison",
                            ),
                        ],
                    ),
                    shadow="sm",
                    radius="md",
                    withBorder=True,
                    style={"overflow": "hidden", "height": "100%"},
                ),
                _compare_popover(),
            ],
        ),
        # ---- Stores ----
        # Synthetic generations dict — the shape a real generation pipeline would emit.
        dcc.Store(id="cl-generations", data={}, storage_type="memory"),
        # Compare-popover state. CRITICAL: source_visible STARTS at True so
        # the render-source-layer callback paints the Esri layer on the very
        # first run — without this, the tree shows Esri checked but the map
        # doesn't reflect it until the user nudges the slider or toggle.
        dcc.Store(
            id="cl-compare-state",
            data={
                "source_visible": True,
                "source_opacity": 80,
                "visible_customs": [],
                "custom_opacities": {},
            },
            storage_type="memory",
        ),
        # Dummy output for the clientside overlay reconciler — Dash requires
        # a concrete Output target. Nothing reads it.
        dcc.Store(id="cl-overlay-trigger", data=0, storage_type="memory"),
        # Canonical open/closed state for the compare popover. See
        # `manage_popover_state` below for why we bother with a separate
        # Store instead of just using popover.opened directly.
        dcc.Store(id="cl-popover-open", data=False, storage_type="memory"),
    ],
    gap="md",
)


# =====================================================================
# Callbacks
# =====================================================================

# Basemap light/dark swap — the app's `color-scheme-toggle` is True when
# the LIGHT theme is active (see app.py header()), so checked=True → light.
clientside_callback(
    """
    (checked) => (checked ? '%s' : '%s')
    """
    % (CARTO_LIGHT, CARTO_DARK),
    Output("cl-basemap", "url"),
    Input("color-scheme-toggle", "checked"),
)


# Source-layer slot. Critically NOT `prevent_initial_call` so it fires on
# page load with the initial source_visible=True and the Esri tile layer
# mounts right away.
@callback(
    Output("cl-source-layer-slot", "children"),
    Input("cl-compare-state", "data"),
)
def render_source_layer(state):
    state = state or {}
    if not state.get("source_visible"):
        return []
    opacity = state.get("source_opacity", 80) / 100.0
    return [
        dl2.TileLayer(
            url=ESRI_SAT,
            attribution=ESRI_ATTR,
            opacity=opacity,
            maxZoom=19,
        )
    ]


# EasyButton → popover toggle.
#
# Two clientside callbacks, no cycle:
#   1. Button click reads the popover's CURRENT visibility from the DOM
#      and flips the store. Reading the DOM at click time gives accurate
#      state even after a click-outside or Escape close (Mantine's
#      `opened` State prop is unreliable — verified empirically — but
#      the rendered DOM always reflects the truth).
#   2. Store → popover.opened (one-way drive).
#
# DomEvent.disableClickPropagation on the EasyButton stops the click
# from bubbling to document, so Mantine's outside-click handler doesn't
# fire on button clicks — the DOM read is "is the dropdown currently
# visible" and the answer is the truth at the moment we want to act.
clientside_callback(
    """
    (n) => {
      if (!n) return window.dash_clientside.no_update;
      const dd = document.querySelector('.mantine-Popover-dropdown');
      const isOpen = !!(dd && dd.offsetParent !== null);
      return !isOpen;
    }
    """,
    Output("cl-popover-open", "data"),
    Input("cl-compare-btn", "n_clicks"),
    prevent_initial_call=True,
)

clientside_callback(
    "(opened) => !!opened",
    Output("cl-compare-popover", "opened"),
    Input("cl-popover-open", "data"),
)


# TreeViewPro selection + sliders → compare-state.
# The reducer keeps visible_customs as a list, NOT
# a single boolean, so each custom leaf toggles independently). No-op
# guard skips identity-different-but-structurally-equal emissions to
# keep the cascade quiet.
@callback(
    Output("cl-compare-state", "data"),
    Input("cl-compare-tree", "selectedItems"),
    Input("cl-compare-tree", "sliderValues"),
    State("cl-compare-state", "data"),
    prevent_initial_call=True,
)
def reduce_state(selected, sliders, state):
    prev = dict(state or {})
    new = dict(prev)
    sel = set(selected or [])
    sliders = sliders or {}
    new["source_visible"] = "src:esri" in sel
    new["visible_customs"] = sorted(
        s[len("cust:") :] for s in sel if s.startswith("cust:") and s != "cust:empty"
    )
    if "src:esri" in sliders:
        new["source_opacity"] = int(sliders["src:esri"])
    new["custom_opacities"] = {
        k[len("cust:") :]: int(v)
        for k, v in sliders.items()
        if k.startswith("cust:") and k != "cust:empty"
    }
    if new == prev:
        return no_update
    return new


# Derive tree items + slider seeds from generations. The `items` no-op
# guard is what stops MUI from re-rendering the tree on every
# generations update (which would briefly reset selectedItems → the
# "vanishing tile" flicker).
@callback(
    Output("cl-compare-tree", "items"),
    Output("cl-compare-tree", "controlsItems"),
    Output("cl-compare-tree", "sliderValues"),
    Input("cl-generations", "data"),
    State("cl-compare-state", "data"),
    State("cl-compare-tree", "items"),
)
def derive_tree(generations, state, current_items):
    state = state or {}
    items = _build_tree(generations or {})
    if items == (current_items or []):
        return no_update, no_update, no_update
    opacities = state.get("custom_opacities") or {}
    controls = ["src:esri"]
    sliders = {"src:esri": state.get("source_opacity", 80)}
    for grp in items:
        if grp["id"] == "grp.custom":
            for leaf in grp.get("children") or []:
                if leaf["id"] == "cust:empty":
                    continue
                controls.append(leaf["id"])
                key = leaf["id"][len("cust:") :]
                sliders[leaf["id"]] = opacities.get(key, 90)
    return items, controls, sliders


# Auto-select new generations into selectedItems so a freshly-seeded
# overlay shows up on the map without the user opening the popover.
@callback(
    Output("cl-compare-tree", "selectedItems", allow_duplicate=True),
    Input("cl-generations", "data"),
    State("cl-compare-tree", "selectedItems"),
    prevent_initial_call=True,
)
def auto_select(gens, selected):
    selected = list(selected or [])
    sel_set = set(selected)
    changed = False
    for key, gen in (gens or {}).items():
        if not (gen and gen.get("data_url")):
            continue
        leaf_id = f"cust:{key}"
        if leaf_id not in sel_set:
            selected.append(leaf_id)
            sel_set.add(leaf_id)
            changed = True
    return selected if changed else no_update


# Seed three synthetic generations at the known nested coords.
@callback(
    Output("cl-generations", "data"),
    Input("cl-seed", "n_clicks"),
    State("cl-generations", "data"),
    prevent_initial_call=True,
)
def seed_gens(_, gens):
    gens = dict(gens or {})
    for i, key in enumerate(SYNTH_KEYS):
        gens[key] = _synth_gen(key, i)
    return gens


# Clear → wipe generations + reset selection + reset state to initial.
@callback(
    Output("cl-generations", "data", allow_duplicate=True),
    Output("cl-compare-tree", "selectedItems", allow_duplicate=True),
    Output("cl-compare-state", "data", allow_duplicate=True),
    Input("cl-clear", "n_clicks"),
    prevent_initial_call=True,
)
def clear_all(_):
    return (
        {},
        ["src:esri"],
        {
            "source_visible": True,
            "source_opacity": 80,
            "visible_customs": [],
            "custom_opacities": {},
        },
    )


# Kebab — "Remove" is the only action this page needs.
@callback(
    Output("cl-generations", "data", allow_duplicate=True),
    Output("cl-compare-tree", "selectedItems", allow_duplicate=True),
    Input("cl-compare-tree", "kebabAction"),
    State("cl-generations", "data"),
    State("cl-compare-tree", "selectedItems"),
    prevent_initial_call=True,
)
def kebab(action, gens, selected):
    if not action:
        return no_update, no_update
    item_id = action.get("itemId", "")
    what = action.get("action")
    if not item_id.startswith("cust:") or item_id == "cust:empty" or what != "delete":
        return no_update, no_update
    key = item_id[len("cust:") :]
    new_gens = dict(gens or {})
    new_gens.pop(key, None)
    new_sel = [s for s in (selected or []) if s != item_id]
    return new_gens, new_sel


# Clientside overlay reconciler — same mount-everything-hide-via-opacity
# reconciler pattern: EVERY generation stays mounted; visibility
# is purely a `setOpacity` toggle based on visible_customs membership
# AND zoom match. Immune to the MUI selectedItems flicker.
clientside_callback(
    """
    (state, generations) => {
      const log = (msg, data) => {
        try { console.log('[compare-lab] ' + msg, data ?? ''); } catch (e) {}
      };
      const root = document.getElementById('cl-map');
      const map  = root && root.__dl2_map;
      if (!map) { log('skip: no map handle'); return window.dash_clientside.no_update; }
      const L = window.leaflet || window.L;
      if (!L)  { log('skip: no Leaflet');    return window.dash_clientside.no_update; }

      const visible   = new Set((state && state.visible_customs) || []);
      const opacities = (state && state.custom_opacities) || {};
      if (!window._cl_overlays_by_key) window._cl_overlays_by_key = {};
      const reg = window._cl_overlays_by_key;
      const TILE = 256;

      // Latest state for the zoomend listener (attached once but needs
      // fresh values on every map zoom).
      window._cl_compare_visible   = visible;
      window._cl_compare_opacities = opacities;

      // 1) Remove only when the underlying generation is gone.
      let removed = 0;
      for (const key of Object.keys(reg)) {
        if (!generations || !generations[key] || !generations[key].data_url) {
          try { reg[key].overlay.remove(); } catch (e) {}
          delete reg[key];
          removed += 1;
        }
      }
      // 2) Mount or update every generation (at opacity 0 — applyVis
      //    sets the right value next).
      let added = 0, updated = 0;
      for (const [key, gen] of Object.entries(generations || {})) {
        if (!gen || !gen.data_url) continue;
        const parts = key.split('/').map(Number);
        if (parts.length !== 3 || parts.some(isNaN)) continue;
        const [z, x, y] = parts;
        const baseOpacity = ((opacities[key] ?? 90)) / 100;
        if (!reg[key]) {
          const nw = map.unproject([x * TILE, y * TILE], z);
          const se = map.unproject([(x + 1) * TILE, (y + 1) * TILE], z);
          const bounds = [[se.lat, nw.lng], [nw.lat, se.lng]];
          const overlay = new L.ImageOverlay(gen.data_url, bounds, {
            opacity: 0, interactive: false,
            className: 'cl-compare-overlay',
          });
          overlay.addTo(map);
          overlay._clKey = key;
          reg[key] = { overlay, dataUrl: gen.data_url,
                       baseOpacity, tileZ: z };
          added += 1;
        } else {
          const entry = reg[key];
          if (entry.dataUrl !== gen.data_url) {
            try { entry.overlay.setUrl(gen.data_url); } catch (e) {}
            entry.dataUrl = gen.data_url;
            updated += 1;
          }
          if (entry.baseOpacity !== baseOpacity) {
            entry.baseOpacity = baseOpacity;
            updated += 1;
          }
        }
      }

      window._cl_overlays = Object.values(reg).map(e => {
        const o = e.overlay;
        o._clTileZ       = e.tileZ;
        o._clBaseOpacity = e.baseOpacity;
        return o;
      });

      // Visibility = visible_customs membership only. No strict zoom
      // matching — that confuses users (toggling a
      // leaf at the wrong zoom looked like "nothing happened"). Geo-
      // graphic bounds keep each overlay at its TRUE scale, so smaller
      // tiles naturally nest inside larger ones (Russian doll), and
      // the user can compare across zooms simultaneously.
      const applyVis = () => {
        const vis = window._cl_compare_visible   || new Set();
        const ops = window._cl_compare_opacities || {};
        for (const o of window._cl_overlays) {
          const baseOp = (ops[o._clKey] ?? 90) / 100;
          o.setOpacity(vis.has(o._clKey) ? baseOp : 0);
        }
      };
      applyVis();
      // (zoomend listener no longer needed — visibility is zoom-
      // independent now.)

      log('done', {added, updated, removed,
                   mounted: window._cl_overlays.length,
                   visible: Array.from(visible)});
      return window._cl_overlays.length;
    }
    """,
    Output("cl-overlay-trigger", "data"),
    Input("cl-compare-state", "data"),
    Input("cl-generations", "data"),
)
