"""Light/dark basemap pairs for the documentation examples.

Every live demo has to read correctly in both colour schemes. This module is
the registry that makes that a one-liner, and the single place the theme wiring
lives.

The bug this replaces
---------------------
Twelve example pages swapped their tile URL with::

    clientside_callback(
        "(checked) => (checked ? LIGHT : DARK)",
        Output("some-tile", "url"),
        Input("color-scheme-toggle", "checked"),   # <-- wrong prop
    )

``color-scheme-toggle`` is an ``ActionIcon`` (see ``components/header.py``); it
has no ``checked`` prop. The callback therefore always received ``undefined``,
``undefined ? LIGHT : DARK`` always took the dark branch, and every one of those
maps rendered its DARK basemap in light mode. The pattern was inherited from an
earlier build where the toggle really was a ``Switch``.

The source of truth is ``color-scheme-storage`` — the ``dcc.Store`` in
``components/appshell.py`` that holds the string ``"light"`` or ``"dark"``, is
persisted to localStorage, and already drives ``MantineProvider.forceColorScheme``.
:func:`register_theme_swap` reads that, so a page cannot get the polarity wrong.

Usage
-----
    from dl2_tiles import POSITRON, themed_tile, register_theme_swap

    dl2.Map(children=[themed_tile("my-tile", POSITRON)])
    register_theme_swap("my-tile", POSITRON)

`python dl2_tiles.py` prints the registry and audits which pages use which
pair, so a reviewer can see the variety at a glance.
"""
from __future__ import annotations

from dataclasses import dataclass

from _tile_catalog import PROVIDERS

# The Store in components/appshell.py holding "light" | "dark".
SCHEME_STORE_ID = "color-scheme-storage"


@dataclass(frozen=True)
class TilePair:
    """A basemap with a light and a dark form."""

    key: str
    label: str
    light: str          # provider slug in _tile_catalog
    dark: str           # provider slug in _tile_catalog
    note: str           # why this pair, for the page prose

    def _p(self, slug: str) -> dict:
        try:
            return PROVIDERS[slug]
        except KeyError as exc:  # a typo here would silently render a blank map
            raise KeyError(
                f"TilePair {self.key!r} references unknown provider {slug!r}"
            ) from exc

    def url(self, scheme: str = "light") -> str:
        return self._p(self.dark if scheme == "dark" else self.light)["url"]

    def attribution(self, scheme: str | None = None) -> str:
        """Credit for this pair.

        Called with no scheme (the normal case) this returns a **combined**
        credit naming both providers, because ``dl2.TileLayer.attribution`` is
        construction-only: the component builds the Leaflet layer once in
        ``useEffect([map])`` and only ``url`` / ``opacity`` / ``zIndex`` have
        update effects (see ``src/ts/components/TileLayer.tsx``). A theme swap
        therefore changes the tiles but can never change the credit — so the
        credit has to be true for both from the start. Pass an explicit scheme
        only when you genuinely want one side's string.
        """
        light = self._p(self.light)["attribution"]
        dark = self._p(self.dark)["attribution"]
        if scheme == "light":
            return light
        if scheme == "dark":
            return dark
        if light == dark:
            return light
        # Both are served depending on the reader's colour scheme, so both are
        # credited. Joined with a separator rather than concatenated so the two
        # provider links stay visually distinct in the attribution box.
        return f"{light} &middot; {dark}"

    def max_zoom(self) -> int:
        """The SMALLER of the two — the shared ceiling.

        Taking the light layer's max would let a user zoom past the dark
        layer's last level and hit blank tiles after a theme flip.
        """
        return min(self._p(self.light)["max_zoom"], self._p(self.dark)["max_zoom"])

    def kwargs(self, scheme: str = "light") -> dict:
        """Ready to splat into ``dl2.TileLayer(**pair.kwargs())``."""
        return {
            "url": self.url(scheme),
            # Combined credit, not this scheme's — see attribution().
            "attribution": self.attribution(),
            "maxZoom": self.max_zoom(),
        }


# ---------------------------------------------------------------------------
# The registry
#
# Pairs, not single basemaps, so every example can be read in either scheme.
# Where a genuine light/dark restyle of one cartography exists (CARTO's
# Positron/Dark Matter, Esri's Light/Dark Gray Canvas) we use it. Where it does
# not, the pair is two maps of the same character at the two ends of the
# brightness range — noted per entry, because that IS a design decision.
# ---------------------------------------------------------------------------

POSITRON = TilePair(
    "positron", "CARTO Positron / Dark Matter",
    "carto_positron", "carto_dark",
    "The reference pair — one cartography, two palettes. Neutral enough that "
    "overlaid data always wins.",
)
VOYAGER = TilePair(
    "voyager", "CARTO Voyager / Dark Matter",
    "carto_voyager", "carto_dark",
    "Voyager keeps road classes and land-use colour, so it reads as a real "
    "street map rather than a backdrop.",
)
OSM_CLASSIC = TilePair(
    "osm_classic", "OpenStreetMap / Dark Matter (no labels)",
    "osm_mapnik", "carto_dark_nolabels",
    "Standard OSM Mapnik. It has no dark form, so the dark side drops to "
    "CARTO's label-free dark base and lets the demo's own labels carry.",
)
ESRI_CANVAS = TilePair(
    "esri_canvas", "Esri Light Gray / Dark Gray Canvas",
    "esri_gray_canvas", "esri_dark_gray",
    "Esri's canvas pair — deliberately desaturated, designed as a substrate "
    "for data. The truest light/dark twin in the catalogue after Positron.",
)
ESRI_STREET = TilePair(
    "esri_street", "Esri World Street / Dark Gray Canvas",
    "esri_world_street", "esri_dark_gray",
    "Detailed street cartography in light, dropping to the muted dark canvas.",
)
TOPO = TilePair(
    "topo", "OpenTopoMap / Esri World Terrain",
    "opentopomap", "esri_world_terrain",
    "Contours and relief. Terrain is inherently light-toned, so the dark side "
    "uses Esri's flatter, darker terrain base.",
)
SATELLITE = TilePair(
    "satellite", "Esri World Imagery / USGS Imagery",
    "esri_world_imagery", "usgs_imagery",
    "Aerial imagery is photographic — it has no light or dark form. So this "
    "pair is two different sources rather than a restyle: Esri's global "
    "mosaic, and USGS's higher-contrast US imagery for the dark scheme. What "
    "really adapts on a satellite page is the map chrome — tooltips, popups "
    "and controls — via the liquid-glass theme.",
)
OCEAN = TilePair(
    "ocean", "Esri Ocean / Dark Gray Canvas",
    "esri_ocean", "esri_dark_gray",
    "Bathymetry and depth contours — the right substrate for anything marine.",
)
NATGEO = TilePair(
    "natgeo", "Esri NatGeo / Shaded Relief",
    "esri_natgeo", "esri_shaded_relief",
    "NatGeo's editorial cartography, dropping to plain shaded relief in dark "
    "where NatGeo's warm paper tone would fight the UI.",
)
PHYSICAL = TilePair(
    "physical", "Esri World Physical / Shaded Relief",
    "esri_world_physical", "esri_shaded_relief",
    "Landcover without any labels — pure backdrop.",
)
TRANSIT = TilePair(
    "transit", "ÖPNV Karte / Dark Matter",
    "opnv_karte", "carto_dark_nolabels",
    "Public-transport cartography: routes and stops promoted over roads.",
)
CYCLE = TilePair(
    "cycle", "CyclOSM / Dark Matter",
    "cyclosm", "carto_dark_nolabels",
    "Cycle infrastructure rendering — a good stress test for dense line work.",
)
USGS_TOPO = TilePair(
    "usgs_topo", "USGS Topo / USGS Imagery",
    "usgs_topo", "usgs_imagery",
    "The USGS quad sheet in light, its aerial counterpart in dark.",
)

ALL: tuple[TilePair, ...] = (
    POSITRON, VOYAGER, OSM_CLASSIC, ESRI_CANVAS, ESRI_STREET, TOPO,
    SATELLITE, OCEAN, NATGEO, PHYSICAL, TRANSIT, CYCLE, USGS_TOPO,
)

BY_KEY = {pair.key: pair for pair in ALL}


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------

def themed_tile(tile_id: str, pair: TilePair, **kwargs):
    """A ``dl2.TileLayer`` starting on the pair's LIGHT form.

    Light is the right initial render: :func:`register_theme_swap` fires on
    page load (``prevent_initial_call`` is left off) and corrects to dark
    immediately when that is the stored scheme, whereas starting dark would
    flash a dark map at every light-mode visitor.
    """
    import dash_leaflet2 as dl2

    props = pair.kwargs("light")
    props.update(kwargs)
    return dl2.TileLayer(id=tile_id, **props)


def register_theme_swap(tile_id: str, pair: TilePair) -> None:
    """Swap ``tile_id``'s url + attribution when the colour scheme changes.

    Reads ``color-scheme-storage`` (``"light"`` | ``"dark"``) — NOT the header
    ActionIcon, which has no ``checked`` prop and silently pinned every map to
    its dark basemap. ``None`` (a first visit with nothing in localStorage yet)
    is treated as light, matching the appshell's own default.
    """
    import json

    from dash import Input, Output, clientside_callback

    # `url` ONLY. `attribution` is deliberately not an output: it is
    # construction-only in dl2.TileLayer, so writing it would set a Dash prop
    # the map never reads — a control that looks wired and does nothing.
    # :meth:`TilePair.attribution` credits both providers instead.
    #
    # json.dumps, NOT repr(). Attribution and URL strings can contain double
    # quotes, so a repr() + blanket `'`->`"` swap produces invalid JavaScript
    # and the callback silently becomes a syntax error — every map then keeps
    # whatever URL it first rendered with, which is exactly the failure this
    # module exists to fix. scripts/smoke_test.py node --check's every inline
    # script to keep that from recurring.
    clientside_callback(
        f"""
        function(scheme) {{
            return scheme === "dark"
                ? {json.dumps(pair.url("dark"))}
                : {json.dumps(pair.url("light"))};
        }}
        """,
        Output(tile_id, "url"),
        Input(SCHEME_STORE_ID, "data"),
    )


def _audit() -> None:
    """Print the registry and which example uses each pair."""
    import re
    from pathlib import Path

    root = Path(__file__).parent
    used: dict[str, list[str]] = {}
    for example in sorted((root / "docs").glob("*/example.py")):
        text = example.read_text()
        for group in re.findall(r"from dl2_tiles import ([A-Z_, \n()]+)", text):
            for symbol in (s.strip(" ()\n") for s in group.split(",")):
                if symbol in globals() and isinstance(globals()[symbol], TilePair):
                    used.setdefault(symbol, []).append(example.parent.name)

    print(f"{len(ALL)} light/dark pairs registered\n")
    for pair in ALL:
        pages = used.get(pair.key.upper(), [])
        print(f"  {pair.label:<44} {', '.join(pages) if pages else '— free'}")
        print(f"      light {pair.light:<22} dark {pair.dark:<22} maxZoom {pair.max_zoom()}")
    unused = [p for p in ALL if p.key.upper() not in used]
    print(f"\n{len(ALL) - len(unused)} in use, {len(unused)} free")


if __name__ == "__main__":
    _audit()
