"""ES6 Subclassing — custom Control + a BlanketOverlay canvas layer."""

import dash_mantine_components as dmc
from dl2_shared import code_panel, header, info_panel, map_div

JS = """// v2 uses standard ES6 classes — no more L.Class.extend.

class CenterControl extends leaflet.Control {        // custom control
    onAdd(map) {
        const div = leaflet.DomUtil.create("div", "dl2-ctl");
        map.on("move zoom", () => div.textContent = map.getCenter());
        return div;
    }
}
new CenterControl({position: "topright"}).addTo(map);

class GlowLayer extends leaflet.BlanketOverlay {     // custom canvas renderer
    _initContainer() { this._container = leaflet.DomUtil.create("canvas"); }
    _onSettled() {                                   // re-paint after each settle
        for (const p of this._points) {
            const lp = this._map.latLngToLayerPoint([p.lat, p.lng]);
            // …draw a radial glow at (lp - this._bounds.min)…
        }
    }
}
new GlowLayer(sensors).addTo(map);"""

component = dmc.Stack(
    [
        header(
            "ES6 Subclassing",
            "v2 dropped the bespoke L.Class.extend in favour of standard ES6 classes, "
            "so extending Leaflet types is idiomatic JavaScript. This map adds a custom "
            "Control (top-right, live center/zoom) and a custom canvas layer built on "
            "BlanketOverlay — v2's generalized renderer base class.",
            badge="extensibility",
        ),
        map_div("subclassing"),
        dmc.Grid(
            [
                dmc.GridCol(
                    info_panel(
                        "Custom Control",
                        dmc.Text(
                            "class CenterControl extends leaflet.Control — a plain ES6 subclass "
                            "overriding onAdd(). Watch the top-right box update as you pan/zoom.",
                            size="sm",
                        ),
                    ),
                    span=6,
                ),
                dmc.GridCol(
                    info_panel(
                        "BlanketOverlay layer",
                        dmc.Text(
                            "class GlowLayer extends leaflet.BlanketOverlay paints 40 geo-anchored "
                            "sensor glows onto one <canvas>. _onSettled() re-projects them on every "
                            "pan/zoom — the hook for WebGL/canvas overlays without fighting SVG.",
                            size="sm",
                        ),
                    ),
                    span=6,
                ),
            ]
        ),
        code_panel("Extending Leaflet 2 with ES6 classes", JS),
    ],
    gap="md",
)
