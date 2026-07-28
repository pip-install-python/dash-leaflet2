"""Shared layout helpers so every example page looks consistent."""

import dash_mantine_components as dmc
from dash import html


def map_div(demo_id, height="60vh", **kwargs):
    """The mount point the JS runtime (assets/leaflet2_maps.js) builds into.

    `data-demo` selects which DEMOS[...] builder runs. We wrap it in a Paper so
    it matches the dash-leaflet test app's framing.
    """
    style = {"height": height}
    style.update(kwargs.pop("style", {}))
    return dmc.Paper(
        html.Div(
            className="leaflet2-map", style=style, **{"data-demo": demo_id}, **kwargs
        ),
        shadow="sm",
        radius="md",
        withBorder=True,
        style={"overflow": "hidden"},
    )


def header(title, desc, badge=None):
    bits = [dmc.Title(title, order=1)]
    if badge:
        bits = [
            dmc.Group(
                [
                    dmc.Title(title, order=1),
                    dmc.Badge(badge, color="green", variant="light"),
                ]
            )
        ]
    bits.append(dmc.Text(desc, c="dimmed"))
    return dmc.Stack(bits, gap=4)


def code_panel(title, code):
    return dmc.Paper(
        [dmc.Title(title, order=4, mb="sm"), dmc.Code(code, block=True)],
        shadow="sm",
        radius="md",
        p="md",
        withBorder=True,
    )


def info_panel(title, children):
    return dmc.Paper(
        [dmc.Title(title, order=4, mb="sm"), children],
        shadow="sm",
        radius="md",
        p="md",
        withBorder=True,
    )
