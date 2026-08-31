"""
Emoji & Iconify markers — a live DashEmojiMart picker + a full Iconify catalogue search,
both driving a Leaflet 2 DivIcon marker and both following the app's light/dark scheme.

Mirrors dash-leaflet's emoji_marker.py, on Leaflet 2, using the exact DivIcon technique
baked into the compiled dl2.Marker (emoji / iconify modes). The emoji picker is the real
DashEmojiMart component (>= 0.0.5; PyPI 0.0.3 is broken in this Dash 4 / React 18.2 setup).
The Iconify picker searches the full 200k+ catalogue via the Iconify API
(https://api.iconify.design/search). Selecting from either swaps the marker's icon at
runtime via clientside callbacks that call into the JS-mounted map (DL2.emojiIconify).
"""

import dash_mantine_components as dmc
from dash import Input, Output, clientside_callback, dcc, html
from dash_emoji_mart import DashEmojiMart
from dash_iconify import DashIconify
from dl2_shared import map_div


component = dmc.Stack(
    [
        dmc.Grid(
            [
                dmc.GridCol(map_div("emoji-iconify", height="58vh"), span=7),
                dmc.GridCol(
                    dmc.Stack(
                        [
                            dmc.Paper(
                                [
                                    dmc.Group(
                                        [
                                            dmc.Text("Icon size", size="sm", fw=600),
                                            dmc.Text(
                                                id="ei-readout",
                                                size="sm",
                                                c="green",
                                                ff="monospace",
                                            ),
                                        ],
                                        justify="space-between",
                                    ),
                                    dmc.Slider(
                                        id="ei-size",
                                        min=20,
                                        max=72,
                                        value=40,
                                        step=2,
                                        mb="sm",
                                        marks=[
                                            {"value": 20, "label": "20"},
                                            {"value": 72, "label": "72"},
                                        ],
                                    ),
                                    dmc.Divider(label="Iconify catalogue", my="xs"),
                                    dmc.Group(
                                        [
                                            dmc.TextInput(
                                                id="ei-iconify",
                                                value="anchor",
                                                placeholder="Search icons…",
                                                leftSection=DashIconify(
                                                    icon="mdi:magnify"
                                                ),
                                                style={"flex": 1},
                                            ),
                                            DashIconify(
                                                id="ei-preview",
                                                icon="mdi:map-marker",
                                                width=28,
                                            ),
                                        ],
                                        align="center",
                                        mb="xs",
                                    ),
                                    html.Div(
                                        id="ei-iconify-grid",
                                        className="ei-iconify-grid",
                                        children="Type to search 200k+ Iconify icons…",
                                    ),
                                    dmc.Divider(label="Emoji", my="xs"),
                                    DashEmojiMart(
                                        id="ei-emoji",
                                        theme="auto",
                                        perLine=8,
                                        emojiSize=22,
                                        emojiButtonSize=30,
                                        previewPosition="none",
                                    ),
                                ],
                                shadow="sm",
                                radius="md",
                                p="md",
                                withBorder=True,
                            ),
                        ],
                        gap="md",
                    ),
                    span=5,
                ),
            ]
        ),
        dcc.Store(id="ei-iconify-status"),
    ],
    gap="md",
)


# Emoji picked in DashEmojiMart -> update the marker DivIcon + readout.
clientside_callback(
    """
    function(emoji) {
        var ctx = window.DL2 && window.DL2.emojiIconify;
        if (!emoji || !ctx) return window.dash_clientside.no_update;
        ctx.setEmoji(emoji);
        return 'emoji ' + emoji;
    }
    """,
    Output("ei-readout", "children"),
    Input("ei-emoji", "value"),
    prevent_initial_call=True,
)

# Iconify search -> query the Iconify API and render the catalogue grid. Each result button
# calls DL2.iconifyPick(name) which updates the marker + readout + preview.
clientside_callback(
    """
    async function(query) {
        var grid = document.getElementById('ei-iconify-grid');
        if (!grid) return window.dash_clientside.no_update;
        if (!query || query.trim().length < 2) {
            grid.innerHTML = 'Type to search 200k+ Iconify icons…';
            return 0;
        }
        try {
            var url = 'https://api.iconify.design/search?query=' + encodeURIComponent(query.trim()) + '&limit=60';
            var data = await (await fetch(url)).json();
            var icons = (data && data.icons) || [];
            if (!icons.length) { grid.innerHTML = 'No icons found for “' + query + '”'; return 0; }
            grid.innerHTML = icons.map(function(name) {
                return '<button class="ei-icon-btn" title="' + name + '" ' +
                       'onclick="window.DL2.iconifyPick(&quot;' + name + '&quot;)">' +
                       '<iconify-icon icon="' + name + '" width="22"></iconify-icon></button>';
            }).join('');
            return icons.length;
        } catch (e) {
            grid.innerHTML = 'Iconify search failed';
            return -1;
        }
    }
    """,
    Output("ei-iconify-status", "data"),
    Input("ei-iconify", "value"),
)

# Size slider -> re-apply the current size to whichever icon is active.
clientside_callback(
    """
    function(size) {
        var ctx = window.DL2 && window.DL2.emojiIconify;
        if (!ctx) return window.dash_clientside.no_update;
        ctx.setSize(size);
        return ctx.last.type + ' ' + ctx.last.val + ' @ ' + size + 'px';
    }
    """,
    Output("ei-readout", "children", allow_duplicate=True),
    Input("ei-size", "value"),
    prevent_initial_call=True,
)

# Sync DashEmojiMart's theme to the app's color scheme (the header toggle: checked=light).
clientside_callback(
    # Same fix as the tile swap: read the STORE, not the header ActionIcon.
    "(scheme) => (scheme === 'dark' ? 'dark' : 'light')",
    Output("ei-emoji", "theme"),
    Input("color-scheme-storage", "data"),
)
