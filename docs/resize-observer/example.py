"""ResizeObserver Sizing — no gray tiles in collapsible layouts."""

import dash_mantine_components as dmc
from dash import Input, Output, clientside_callback, html
from dl2_shared import info_panel


component = dmc.Stack(
    [
        dmc.Button(
            "Toggle side panel", id="resize-toggle", color="green", variant="light"
        ),
        html.Div(
            id="resize-row",
            className="dl2-resize-row",
            children=[
                html.Div(className="leaflet2-map", **{"data-demo": "resize-observer"}),
                html.Div(
                    className="dl2-resize-panel",
                    children=[
                        dmc.Title("Side panel", order=5),
                        dmc.Text(
                            "Opening/closing me changes the map's width. Watch it reflow "
                            "instantly — no gray tiles, no manual resize call.",
                            size="sm",
                            c="dimmed",
                        ),
                    ],
                ),
            ],
        ),
        info_panel(
            "Why this matters in Dash",
            dmc.Text(
                "Dash layouts lean on tabs, accordions and AppShell panels that hide/resize "
                "content. With dash-leaflet (Leaflet 1) you wire invalidateSize on every "
                "visibility change. With v2 it's automatic.",
                size="sm",
            ),
        ),
    ],
    gap="md",
)

# Toggle the .open class on the flex row; Leaflet's ResizeObserver does the rest.
clientside_callback(
    """
    function(n) {
        var r = document.getElementById('resize-row');
        if (r) { r.classList.toggle('open'); }
        return window.dash_clientside.no_update;
    }
    """,
    Output("resize-toggle", "id"),
    Input("resize-toggle", "n_clicks"),
    prevent_initial_call=True,
)
