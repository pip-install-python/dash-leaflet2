"""
TileSelector — pick tiles off the map by clicking or shift-dragging.

`dl2.TileSelector` is a map control. While it is armed the cursor becomes a
crosshair, a dashed outline tracks the tile under the pointer at the current
zoom, and:

  • **click** a tile to add / remove it from the selection
  • **shift-drag** a box to capture every tile inside it

Each selected tile round-trips to Python as `{z, x, y, url, bounds}`, where
`bounds` is `[south, west, north, east]`. Selections are keyed by `z/x/y`, so
they survive panning and zooming.

`selectedTiles` is `[MUTABLE]` — it is both an output (the user's clicks) and
an input (the Clear button below writes `[]` straight back into it).
"""

import dash_leaflet2 as dl2
import dash_mantine_components as dmc
from dash import Input, Output, callback, html, no_update
from dash_iconify import DashIconify

from dl2_locations import AUSTIN
from dl2_shared import code_panel, info_panel

CARTO_LIGHT = "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
OSM = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"

CODE = """import dash_leaflet2 as dl2

dl2.Map(
    center=[30.2672, -97.7431],
    zoom=11,
    children=[
        dl2.TileLayer(url=OSM),
        dl2.TileSelector(
            id="tile-picker",
            position="topright",
            tileUrl=OSM,           # which tileset the picked URLs point at
            hoverColor="#fa5252",  # dashed outline under the cursor
            selectedColor="#228be6",
        ),
    ],
)

@callback(Output("out", "children"), Input("tile-picker", "selectedTiles"))
def show(tiles):
    return f"{len(tiles or [])} tiles selected"
"""


def _tile_row(tile):
    """One selected tile as a table row: z/x/y, bounds, and its URL."""
    s, w, n, e = tile.get("bounds") or [0, 0, 0, 0]
    return dmc.TableTr(
        [
            dmc.TableTd(
                dmc.Code(f"{tile['z']}/{tile['x']}/{tile['y']}"),
            ),
            dmc.TableTd(
                dmc.Text(f"{s:.4f}, {w:.4f} → {n:.4f}, {e:.4f}",
                         size="xs", c="dimmed", ff="monospace"),
            ),
            dmc.TableTd(
                dmc.Anchor(
                    dmc.Group(
                        [DashIconify(icon="tabler:photo", width=14), dmc.Text("PNG", size="xs")],
                        gap=4,
                    ),
                    href=tile.get("url", "#"),
                    target="_blank",
                ),
                style={"textAlign": "center"},
            ),
        ]
    )


# `component` is the name the `.. exec::` directive looks for.
component = dmc.Stack(
    [
        dmc.Alert(
            dmc.Stack(
                [
                    dmc.Text(
                        "Click the crosshair button in the map's top-right corner to arm "
                        "the selector, then click tiles — or hold Shift and drag a box.",
                        size="sm",
                    ),
                    dmc.Text(
                        "Zoom changes the tile grid; already-picked tiles stay picked "
                        "because each one is keyed by z/x/y.",
                        size="sm",
                        c="dimmed",
                    ),
                ],
                gap=4,
            ),
            title="How to use it",
            color="blue",
            variant="light",
            icon=DashIconify(icon="tabler:hand-click"),
        ),
        dmc.Paper(
            dl2.Map(
                id="ts-map",
                center=AUSTIN.center,
                zoom=11,
                style={"height": "58vh", "width": "100%"},
                children=[
                    dl2.TileLayer(
                        url=CARTO_LIGHT,
                        attribution=(
                            '&copy; <a href="https://openstreetmap.org/copyright">'
                            "OpenStreetMap</a> &copy; "
                            '<a href="https://carto.com/attributions">CARTO</a>'
                        ),
                    ),
                    dl2.TileSelector(
                        id="ts-picker",
                        position="topright",
                        # The URLs handed back in `selectedTiles` point at THIS
                        # template — it does not have to be the tileset you are
                        # displaying. Here we show CARTO but hand back OSM PNGs.
                        tileUrl=OSM,
                        hoverColor="#fa5252",
                        selectedColor="#228be6",
                    ),
                ],
            ),
            shadow="sm",
            radius="md",
            withBorder=True,
            style={"overflow": "hidden"},
        ),
        dmc.Group(
            [
                dmc.Button(
                    "Clear selection",
                    id="ts-clear",
                    variant="light",
                    color="red",
                    leftSection=DashIconify(icon="tabler:trash", width=16),
                ),
                html.Div(id="ts-count"),
            ],
            justify="space-between",
            align="center",
        ),
        info_panel("Selected tiles", html.Div(id="ts-table")),
        code_panel("Usage", CODE),
    ],
    gap="md",
)


@callback(
    Output("ts-count", "children"),
    Output("ts-table", "children"),
    Input("ts-picker", "selectedTiles"),
)
def show_selection(tiles):
    tiles = tiles or []
    badge = dmc.Badge(
        f"{len(tiles)} tile{'' if len(tiles) == 1 else 's'} selected",
        color="blue" if tiles else "gray",
        variant="light",
        size="lg",
    )
    if not tiles:
        return badge, dmc.Text(
            "Nothing selected yet — arm the control and click a tile.",
            c="dimmed", size="sm",
        )

    table = dmc.Table(
        [
            dmc.TableThead(
                dmc.TableTr(
                    [
                        dmc.TableTh("z/x/y"),
                        dmc.TableTh("bounds (S, W → N, E)"),
                        dmc.TableTh("tile", style={"textAlign": "center"}),
                    ]
                )
            ),
            # Newest first, and capped — a shift-drag at low zoom can select a
            # lot of tiles and this is a doc page, not a data grid.
            dmc.TableTbody([_tile_row(t) for t in list(reversed(tiles))[:25]]),
        ],
        striped=True,
        highlightOnHover=True,
    )
    footer = (
        dmc.Text(f"Showing the 25 most recent of {len(tiles)}.", size="xs", c="dimmed", mt="xs")
        if len(tiles) > 25
        else None
    )
    return badge, dmc.Stack([table, footer], gap=0)


@callback(
    Output("ts-picker", "selectedTiles"),
    Input("ts-clear", "n_clicks"),
    prevent_initial_call=True,
)
def clear_selection(n_clicks):
    """Python → map: writing the [MUTABLE] prop clears the component's state."""
    return [] if n_clicks else no_update
