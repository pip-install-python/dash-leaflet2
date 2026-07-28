"""
/tile-layers-pro — EasyButton + Popover + MultiSelect + TreeViewPro.

The SailsBoard `create_layers_card` pattern, rebuilt against dl2 and the
no-key, no-payment tile catalog ported into `pages/_tile_catalog.py`.

  * Click the EasyButton (📚 top-left) → DMC Popover opens beside it.
  * Inside the popover:
      - `dmc.MultiSelect` lists every provider in the catalog, each row
        rendered with a tiny rotating cube preview (renderTileCubeFace
        in assets/tile_cube.js).
      - `dash_mui_charts.TreeViewPro` shows the active stack — one
        "Active tilesets" group, one leaf per slug, with an opacity
        slider and a kebab menu (Show info / Remove layer).
  * Single source of truth: `dcc.Store(id="tlp-state")` shaped
        `{"order": [slug, …], "sliders": {slug: 0..100}}`.

Add / remove / reorder / opacity changes all rewrite the Store; one
output callback derives the Map's `LayerGroup` children + the
`renderoption` cube payload from it.

The base layer (`esri_world_imagery`) is pinned at the bottom of the
stack and excluded from the MultiSelect — kebab "Remove layer" is a
no-op on it, so the map can never end up empty.
"""

from __future__ import annotations

import json
import os
from typing import Any

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
from dash_mui_charts import TreeViewPro
from dl2_shared import code_panel, header, info_panel
from _tile_catalog import (
    DEFAULT_BASE_SLUG,
    PROVIDER_OPTIONS_GROUPED,
    PROVIDERS,
    renderoption_payload,
    tile_kwargs,
)


# MUI X Pro license key — read at import time (load_dotenv() in app.py
# pulls .env into the process before this module loads). Without a
# license key TreeViewPro renders without drag/slider/kebab; we surface
# the missing-key state in a Badge so the user knows.
LICENSE_KEY = os.environ.get("MUI_PRO_API_KEY", "")

# Initial active stack — Esri World Imagery on the bottom, a couple of
# user-friendly overlays seeded on top so the page lands rich.
INITIAL_ORDER: list[str] = [
    "overlay_esri_reference",
    "carto_voyager",
    DEFAULT_BASE_SLUG,
]
INITIAL_SLIDERS: dict[str, int] = {
    DEFAULT_BASE_SLUG: 100,
    "carto_voyager": 95,
    "overlay_esri_reference": 90,
}


# Default opacity (0–100) when a user adds a new layer through the
# MultiSelect — overlays land at 85 so the layer underneath stays
# visible; bases land at 100.
def _default_opacity(slug: str) -> int:
    provider = PROVIDERS.get(slug, {})
    return 100 if provider.get("kind") == "tile" else 85


# Kebab menu — shared across every leaf.
KEBAB_MENU = [
    {"label": "Show info", "value": "info", "icon": "ContentCopy"},
    {"label": "Remove layer", "value": "delete", "icon": "Delete"},
]


# ---- store derivations ------------------------------------------------------


def build_tree_items(order: list[str]) -> list[dict[str, Any]]:
    """One 'Active tilesets' group, leaves in tree-top-down order."""
    children = []
    for slug in order:
        provider = PROVIDERS.get(slug, {})
        label = provider.get("label", slug)
        if slug == DEFAULT_BASE_SLUG:
            label = f"🛰️  {label}"
        children.append({"id": slug, "label": label})
    return [{"id": "_active", "label": "Active tilesets", "children": children}]


def slugs_from_tree(ordered_items: list[dict] | None) -> list[str]:
    """Pluck leaf ids from TreeViewPro's `orderedItems` shape."""
    if not ordered_items:
        return []
    out: list[str] = []
    for node in ordered_items:
        if node.get("id") == "_active":
            for child in node.get("children") or []:
                sid = child.get("id")
                if sid:
                    out.append(sid)
            break
    return out


def build_layer_group_children(order: list[str], sliders: dict[str, int]) -> list[Any]:
    """One dl2.TileLayer per active slug, mounted bottom-up.

    `order` is tree top -> bottom = visually front -> back on the
    map. Leaflet renders later-mounted layers on top, so we reverse
    for the LayerGroup children list. The slider value (0–100) maps
    directly to TileLayer.opacity (0..1).
    """
    bottom_up = list(reversed(order))
    out: list[Any] = []
    for slug in bottom_up:
        pct = sliders.get(slug, _default_opacity(slug))
        kwargs = tile_kwargs(slug, opacity=pct / 100.0)
        if not kwargs:
            continue
        out.append(dl2.TileLayer(**kwargs))
    return out


# ---- layout -----------------------------------------------------------------

CODE = """dcc.Store(id="tlp-state", data={"order": [...], "sliders": {...}})

dl2.Map(children=[
    dl2.LayerGroup(id="tlp-stack"),
    dl2.EasyButton(id="tlp-open", icon="mdi:layers-triple-outline"),
])

# Popover anchored over the EasyButton (same trick as /easy-button)
dmc.Popover([
    dmc.PopoverTarget(html.Div(id="tlp-anchor")),
    dmc.PopoverDropdown([
        dmc.MultiSelect(
            id="tlp-multiselect",
            data=PROVIDER_OPTIONS_GROUPED,
            renderOption={"function": "renderTileCubeFace",
                          "options":  {"tilesets": renderoption_payload()}},
        ),
        TreeViewPro(
            id="tlp-tree", items=build_tree_items(order),
            itemsReordering=True, isItemEditable=True,
            showItemControls=True, sliderValues=sliders,
            kebabMenuItems=[{"label": "Remove layer", "value": "delete"}],
            licenseKey=os.environ["MUI_PRO_API_KEY"],
        ),
    ]),
])

# One reduce-style callback maps every input (multiselect change,
# tree reorder, slider drag, kebab Remove) into a new store value;
# a second callback derives the LayerGroup, MultiSelect.value, and
# the tree's items/sliderValues from that store. Single source of truth.
"""


def _popover():
    return dmc.Popover(
        id="tlp-popover",
        opened=True,  # popover opens with the page so the user sees the card immediately
        position="right-start",
        offset=6,
        withArrow=True,
        arrowSize=10,
        shadow="lg",
        radius="md",
        closeOnClickOutside=False,
        closeOnEscape=False,
        clickOutsideEvents=[],
        keepMounted=True,
        children=[
            # Invisible anchor positioned over the EasyButton (10px / 46px
            # from top-left of the map container — same numbers as
            # /easy-button). PopoverTarget wraps in a dmc.Box; the style
            # lives on boxWrapperProps so the inner Div isn't overridden.
            dmc.PopoverTarget(
                html.Div(id="tlp-anchor"),
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
                dmc.Stack(
                    [
                        dmc.Group(
                            [
                                DashIconify(
                                    icon="mdi:layers-triple-outline",
                                    width=16,
                                    color="var(--mantine-color-blue-6)",
                                ),
                                dmc.Text("Layers", fw=600, size="sm"),
                                dmc.Badge(
                                    f"{len(PROVIDERS)}",
                                    color="blue",
                                    variant="light",
                                    size="xs",
                                    radius="sm",
                                    ml="auto",
                                ),
                            ],
                            gap="xs",
                            wrap="nowrap",
                        ),
                        dmc.Divider(),
                        dmc.MultiSelect(
                            id="tlp-multiselect",
                            data=PROVIDER_OPTIONS_GROUPED,
                            value=[s for s in INITIAL_ORDER if s != DEFAULT_BASE_SLUG],
                            placeholder="Add a tileset to the stack",
                            searchable=True,
                            clearable=True,
                            hidePickedOptions=True,
                            nothingFoundMessage="No tilesets match…",
                            maxDropdownHeight=320,
                            size="xs",
                            comboboxProps={
                                "withinPortal": True,
                                "zIndex": 2147483641,
                                "shadow": "md",
                                "transitionProps": {
                                    "transition": "pop",
                                    "duration": 140,
                                },
                            },
                            renderOption={
                                "function": "renderTileCubeFace",
                                "options": {"tilesets": renderoption_payload()},
                            },
                            leftSection=DashIconify(icon="mdi:map-search", width=14),
                            classNames={
                                "dropdown": "tlp-dropdown",
                                "option": "tlp-option",
                            },
                            styles={
                                "input": {"minHeight": "36px"},
                                "dropdown": {"padding": "6px"},
                            },
                        ),
                        html.Div(
                            TreeViewPro(
                                id="tlp-tree",
                                items=build_tree_items(INITIAL_ORDER),
                                defaultExpandedItems=["_active"],
                                multiSelect=True,
                                checkboxSelection=False,
                                itemsReordering=True,
                                isItemEditable=True,
                                reorderableItems=list(INITIAL_ORDER),
                                showItemControls=True,
                                controlsItems=list(INITIAL_ORDER),
                                sliderValues=INITIAL_SLIDERS,
                                sliderMin=0,
                                sliderMax=100,
                                sliderStep=1,
                                sliderColor="blue",
                                kebabMenuItems=KEBAB_MENU,
                                licenseKey=LICENSE_KEY,
                                expandIcon="ChevronRight",
                                collapseIcon="ExpandMore",
                                itemChildrenIndentation="14px",
                                sx={
                                    "& .MuiTreeItem-content": {"paddingY": "3px"},
                                    "& .MuiTreeItem-label": {
                                        "fontSize": "13px",
                                        "width": "100%",
                                    },
                                    "& .MuiSlider-root": {
                                        "height": "2px",
                                        "padding": "8px 0",
                                    },
                                },
                            ),
                            className="tlp-tree",
                        ),
                    ],
                    gap=10,
                ),
                p="md",
                style={"width": "420px", "maxHeight": "70vh", "overflowY": "auto"},
            ),
        ],
    )


component = dmc.Stack(
    [
        header(
            "Tile Layers (Pro)",
            "Click the 📚 button on the map. The Popover opens with a MultiSelect of "
            "the no-key tileset catalog (Worldwide / Esri / USGS / NOAA / NASA / "
            "Game / Overlays) — each option rendered with a tiny rotating cube "
            "preview. The TreeViewPro below it drives the active stack: drag to "
            "reorder, slide for opacity, ⋮ for actions.",
            badge="dl2.EasyButton + dmc.Popover + TreeViewPro",
        ),
        dmc.Grid(
            [
                dmc.GridCol(
                    html.Div(
                        style={"position": "relative"},  # anchor frame for the popover
                        children=[
                            dmc.Paper(
                                dl2.Map(
                                    id="tlp-map",
                                    center=[28.05, -97.05],
                                    zoom=5,
                                    style={"height": "70vh"},
                                    attributionControl=True,  # let layer attributions surface in the corner
                                    children=[
                                        # TileLayers find the map via React context, so any
                                        # container that keeps them mounted as children works
                                        # — no need for a Leaflet-side LayerGroup.
                                        html.Div(
                                            id="tlp-stack",
                                            children=build_layer_group_children(
                                                INITIAL_ORDER,
                                                INITIAL_SLIDERS,
                                            ),
                                        ),
                                        dl2.EasyButton(
                                            id="tlp-open",
                                            position="topleft",
                                            icon="mdi:layers-triple-outline",
                                            iconSize=20,
                                            title="Layers",
                                        ),
                                    ],
                                ),
                                shadow="sm",
                                radius="md",
                                withBorder=True,
                                style={"overflow": "hidden", "height": "100%"},
                            ),
                            _popover(),
                        ],
                    ),
                    span={"base": 12, "md": 8},
                ),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            info_panel(
                                "MUI X Pro license",
                                dmc.Badge(
                                    (
                                        "Loaded from .env"
                                        if LICENSE_KEY
                                        else "MUI_PRO_API_KEY not set"
                                    ),
                                    color="green" if LICENSE_KEY else "red",
                                    variant="light",
                                    size="sm",
                                ),
                            ),
                            info_panel(
                                "Active stack (top → bottom)",
                                dmc.Code(
                                    id="tlp-readout",
                                    block=True,
                                    style={
                                        "fontSize": "11px",
                                        "whiteSpace": "pre-wrap",
                                        "minHeight": "120px",
                                    },
                                ),
                            ),
                            info_panel(
                                "Last action",
                                dmc.Code(
                                    id="tlp-action",
                                    children="…",
                                    style={"fontSize": "11px"},
                                ),
                            ),
                        ],
                        gap="md",
                    ),
                    span={"base": 12, "md": 4},
                ),
            ]
        ),
        code_panel("Single-store pattern", CODE),
        # Single source of truth. Every input (MultiSelect, tree reorder,
        # slider drag, kebab) updates this; one derivation callback rewires
        # the LayerGroup + tree props.
        dcc.Store(
            id="tlp-state",
            data={"order": list(INITIAL_ORDER), "sliders": dict(INITIAL_SLIDERS)},
            storage_type="memory",
        ),
    ],
    gap="md",
)


# ---- EasyButton toggles the popover ----------------------------------------
@callback(
    Output("tlp-popover", "opened"),
    Input("tlp-open", "n_clicks"),
    State("tlp-popover", "opened"),
    prevent_initial_call=True,
)
def toggle_popover(_, opened):
    return not bool(opened)


# ---- Inputs (MultiSelect / tree drag / slider / kebab) -> tlp-state --------
# Note: we also write `tlp-tree.sliderValues` directly from this callback
# (allow_duplicate) — but ONLY when the trigger is "slug added", so the tree
# learns about the new leaf's seeded opacity. For drag-only and reorder-only
# triggers, we return `no_update` for sliderValues to avoid pushing back the
# value the tree just sent us (the previous version round-tripped, which Dash
# correctly flagged as a circular dependency between the reducer and a
# `derive` callback that also output sliderValues).
@callback(
    Output("tlp-state", "data"),
    Output("tlp-action", "children"),
    Output("tlp-tree", "sliderValues", allow_duplicate=True),
    Output("tlp-multiselect", "value", allow_duplicate=True),
    Input("tlp-multiselect", "value"),
    Input("tlp-tree", "orderedItems"),
    Input("tlp-tree", "sliderValues"),
    Input("tlp-tree", "kebabAction"),
    State("tlp-state", "data"),
    prevent_initial_call=True,
)
def reduce_state(ms_value, ordered_items, slider_values, kebab, state):
    """Reduce every input into a new {order, sliders} value.

    The base layer (`DEFAULT_BASE_SLUG`) is forced to the BOTTOM of the
    stack regardless of where the tree puts it; the MultiSelect also
    never lists it (the user can't remove or hide it). This guarantees
    the map always has something to render against, the same way the
    SailsBoard layers card pins Esri World Imagery.
    """
    state = dict(state or {})
    order = list(state.get("order") or list(INITIAL_ORDER))
    sliders = dict(state.get("sliders") or {})
    trigger = ctx.triggered_id
    # `ctx.triggered_id` only carries the component id, but THREE inputs land
    # on the same `tlp-tree` component (orderedItems, sliderValues, kebabAction).
    # Look at the prop_id to pick the right branch — otherwise the FIRST branch
    # that finds a truthy value wins and the others never run (the kebab branch
    # never fired because `sliderValues` is always a non-empty dict).
    prop_id = ctx.triggered[0]["prop_id"] if ctx.triggered else ""
    action = "—"
    # Only set these when needed — otherwise return no_update so we don't
    # echo back values that came IN through this callback.
    push_sliders: dict | type(no_update) = no_update
    push_ms_value: list | type(no_update) = no_update

    # --- MultiSelect: add/remove overlays --------------------------------
    if trigger == "tlp-multiselect":
        new_selection = set(ms_value or [])
        # Existing overlays in order (excluding base) — preserve their order.
        existing = [s for s in order if s != DEFAULT_BASE_SLUG]
        kept = [s for s in existing if s in new_selection]
        added = [s for s in new_selection if s not in existing]
        # Newly-added slugs land at the TOP of the stack.
        next_order = added + kept + [DEFAULT_BASE_SLUG]
        # Drop sliders for removed slugs; seed sliders for added ones.
        next_sliders = {k: v for k, v in sliders.items() if k in next_order}
        for slug in next_order:
            next_sliders.setdefault(slug, _default_opacity(slug))
        order, sliders = next_order, next_sliders
        if added:
            action = f"+ added {', '.join(added)}"
            # New leaves need their sliders SEEDED so the tree knows the
            # opacity to display. Send the full sliders dict; the tree
            # only mounts new entries (existing leaves keep their state).
            push_sliders = dict(sliders)
        else:
            removed = [s for s in existing if s not in new_selection]
            action = f"− removed {', '.join(removed)}" if removed else "no-op"
            # Removed-only branches don't need to push — the leaf is gone
            # from items anyway.

    # --- Tree reorder ----------------------------------------------------
    elif prop_id.endswith(".orderedItems") and ordered_items is not None:
        # `orderedItems` falls back to `items` until the first reorder —
        # treat both the same way (it's just a nested list).
        tree_slugs = slugs_from_tree(ordered_items)
        if tree_slugs:
            # Force the base to the bottom no matter where the tree placed it.
            kept = [s for s in tree_slugs if s != DEFAULT_BASE_SLUG]
            order = kept + [DEFAULT_BASE_SLUG]
            action = "drag-reorder"

    # --- Slider drag -----------------------------------------------------
    elif prop_id.endswith(".sliderValues") and slider_values:
        # Find the slug whose value actually changed (vs current state).
        for slug, value in (slider_values or {}).items():
            if slug not in sliders or sliders[slug] != value:
                sliders[slug] = int(value)
                action = f"opacity · {slug} → {int(value)}%"
                break

    # --- Kebab action ----------------------------------------------------
    elif prop_id.endswith(".kebabAction") and kebab:
        slug = kebab.get("itemId")
        what = kebab.get("action")
        if what == "delete" and slug and slug != DEFAULT_BASE_SLUG:
            order = [s for s in order if s != slug]
            sliders.pop(slug, None)
            action = f"removed {slug}"
            # Sync the MultiSelect — it has to lose the leaf the user just
            # removed via the kebab, otherwise the chip stays in the picker.
            push_ms_value = [s for s in order if s != DEFAULT_BASE_SLUG]
        elif what == "delete" and slug == DEFAULT_BASE_SLUG:
            action = f"can't remove base layer ({DEFAULT_BASE_SLUG})"
        elif what == "info" and slug:
            provider = PROVIDERS.get(slug, {})
            action = (
                f"info · {provider.get('label', slug)} "
                f"(group={provider.get('group')}, "
                f"kind={provider.get('kind')}, "
                f"max_zoom={provider.get('max_zoom')})"
            )
        else:
            action = f"{what} · {slug}"

    return {"order": order, "sliders": sliders}, action, push_sliders, push_ms_value


# ---- Store -> Map LayerGroup + tree props + MultiSelect.value + readout ----
# NOTE: tlp-tree.sliderValues AND tlp-multiselect.value are intentionally NOT
# outputs here — the reducer pushes them directly (with allow_duplicate) only
# when it's the right semantic moment (slug added / kebab removed). Driving
# either from both directions creates a circular dependency.
@callback(
    Output("tlp-stack", "children"),
    Output("tlp-tree", "items"),
    Output("tlp-tree", "controlsItems"),
    Output("tlp-tree", "reorderableItems"),
    Output("tlp-readout", "children"),
    Input("tlp-state", "data"),
)
def derive(state):
    state = state or {"order": list(INITIAL_ORDER), "sliders": dict(INITIAL_SLIDERS)}
    order = state.get("order") or []
    sliders = state.get("sliders") or {}
    readout_lines = []
    for slug in order:
        provider = PROVIDERS.get(slug, {})
        pct = sliders.get(slug, _default_opacity(slug))
        kind = provider.get("kind", "tile")
        readout_lines.append(
            f"{slug:<28}  {pct:>3}%  {kind:<8}  ({provider.get('group_label', '?')})"
        )
    return (
        build_layer_group_children(order, sliders),
        build_tree_items(order),
        list(order),
        list(order),
        "\n".join(readout_lines) or "(empty)",
    )
