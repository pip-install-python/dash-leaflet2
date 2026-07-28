"""
Curated, no-key, no-payment tile-provider catalog used by /tile-layers-pro.

Ported verbatim from SailsBoard's `pages/map/_create/config.py` (the same
catalog the SailsBoard /map/create page browses). Two trims for the dl2
showcase:

  * Dropped the `image`/historical kind — that path needs a per-project
    manifest produced by ``scripts/process_historical_maps.py`` plus the
    assets/map raster pyramid. We keep only `tile` (full-coverage base)
    and `overlay` (transparent layer, stacked on top of a base).
  * Dropped the SailsBoard-only attribution snippets that referenced
    private content (every provider here is verified against
    leaflet-providers v3 and alexurquhart/free-tiles).

Public surface (consumed by `pages/tile_layers_pro.py`):

  * `PROVIDERS`               — slug -> normalized provider dict
  * `PROVIDER_OPTIONS_GROUPED`— Mantine MultiSelect grouped data
  * `DEFAULT_BASE_SLUG`       — provider always pinned to the bottom of
                                the stack (Esri World Imagery — global
                                coverage, no key)
  * `sample_tile_urls(slug)`  — six tile URLs at a recognizable z=4
                                viewport for the cube chip
  * `tile_kwargs(slug)`       — kwargs ready to pass to dl2.TileLayer
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------
# Attribution snippets — short HTML strings the AttributionControl can
# render inline (same set the SailsBoard catalog uses).
# ---------------------------------------------------------------------

_ATTR_OSM = (
    '&copy; <a href="https://www.openstreetmap.org/copyright" '
    'target="_blank">OpenStreetMap</a> contributors'
)
_ATTR_CARTO = (
    f'{_ATTR_OSM} &copy; <a href="https://carto.com/attributions" '
    'target="_blank">CARTO</a>'
)
_ATTR_ESRI = (
    'Tiles &copy; <a href="https://www.esri.com/" target="_blank">Esri</a> '
    "&mdash; Esri, Maxar, Earthstar Geographics, and the GIS User Community"
)
_ATTR_USGS = (
    'Tiles courtesy of the <a href="https://usgs.gov/" target="_blank">'
    "U.S. Geological Survey</a>"
)
_ATTR_NASA = (
    'Imagery &copy; <a href="https://earthdata.nasa.gov" target="_blank">'
    "NASA EOSDIS GIBS</a>"
)
_ATTR_NOAA = (
    'Charts courtesy of <a href="https://www.charts.noaa.gov/" '
    'target="_blank">NOAA Office of Coast Survey</a>'
)
_ATTR_OPENTOPO = (
    f'{_ATTR_OSM} &copy; <a href="https://opentopomap.org" '
    'target="_blank">OpenTopoMap</a> (CC-BY-SA)'
)
_ATTR_OPENSEAMAP = (
    f'{_ATTR_OSM} &copy; <a href="https://www.openseamap.org" '
    'target="_blank">OpenSeaMap</a> contributors'
)
_ATTR_OPENRAILWAY = (
    f'{_ATTR_OSM} &copy; <a href="https://www.openrailwaymap.org" '
    'target="_blank">OpenRailwayMap</a> (CC-BY-SA)'
)


# ---------------------------------------------------------------------
# Provider buckets — same grouping order as the SailsBoard /map/create
# tileset catalog. Optional keys (defaults applied at registry-build
# time): kind="tile", min_zoom=0, max_zoom=19, subdomains=None,
# tms=False, opacity=1.0 (tile) or 0.85 (overlay).
# ---------------------------------------------------------------------

_WORLDWIDE: list[dict[str, Any]] = [
    {
        "id": "osm_mapnik",
        "label": "OpenStreetMap (Mapnik)",
        "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "attribution": _ATTR_OSM,
        "max_zoom": 19,
    },
    {
        "id": "osm_de",
        "label": "OpenStreetMap (Deutschland)",
        "url": "https://tile.openstreetmap.de/{z}/{x}/{y}.png",
        "attribution": _ATTR_OSM,
        "max_zoom": 18,
    },
    {
        "id": "osm_france",
        "label": "OpenStreetMap (France)",
        "url": "https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png",
        "attribution": _ATTR_OSM,
        "subdomains": "abc",
        "max_zoom": 20,
    },
    {
        "id": "osm_hot",
        "label": "OpenStreetMap (Humanitarian)",
        "url": "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
        "attribution": _ATTR_OSM + " · HOT",
        "subdomains": "abc",
        "max_zoom": 19,
    },
    {
        "id": "carto_positron",
        "label": "CartoDB Positron",
        "url": "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        "attribution": _ATTR_CARTO,
        "subdomains": "abcd",
        "max_zoom": 20,
    },
    {
        "id": "carto_positron_nolabels",
        "label": "CartoDB Positron (no labels)",
        "url": "https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png",
        "attribution": _ATTR_CARTO,
        "subdomains": "abcd",
        "max_zoom": 20,
    },
    {
        "id": "carto_dark",
        "label": "CartoDB Dark Matter",
        "url": "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
        "attribution": _ATTR_CARTO,
        "subdomains": "abcd",
        "max_zoom": 20,
    },
    {
        "id": "carto_dark_nolabels",
        "label": "CartoDB Dark Matter (no labels)",
        "url": "https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}.png",
        "attribution": _ATTR_CARTO,
        "subdomains": "abcd",
        "max_zoom": 20,
    },
    {
        "id": "carto_voyager",
        "label": "CartoDB Voyager",
        "url": "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png",
        "attribution": _ATTR_CARTO,
        "subdomains": "abcd",
        "max_zoom": 20,
    },
    {
        "id": "opentopomap",
        "label": "OpenTopoMap",
        "url": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "attribution": _ATTR_OPENTOPO,
        "subdomains": "abc",
        "max_zoom": 17,
    },
    {
        "id": "cyclosm",
        "label": "CyclOSM",
        "url": "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
        "attribution": _ATTR_OSM + " · CyclOSM",
        "subdomains": "abc",
        "max_zoom": 20,
    },
    {
        "id": "opnv_karte",
        "label": "OPNV Karte (transit)",
        "url": "https://tileserver.memomaps.de/tilegen/{z}/{x}/{y}.png",
        "attribution": _ATTR_OSM + " · memomaps.de",
        "max_zoom": 18,
    },
    {
        "id": "waymarked_hiking",
        "label": "Waymarked Trails — Hiking",
        "url": "https://tile.waymarkedtrails.org/hiking/{z}/{x}/{y}.png",
        "attribution": _ATTR_OSM + " · waymarkedtrails.org (CC-BY-SA)",
        "max_zoom": 18,
    },
    {
        "id": "waymarked_cycling",
        "label": "Waymarked Trails — Cycling",
        "url": "https://tile.waymarkedtrails.org/cycling/{z}/{x}/{y}.png",
        "attribution": _ATTR_OSM + " · waymarkedtrails.org (CC-BY-SA)",
        "max_zoom": 18,
    },
]

# Esri ArcGIS — {z}/{y}/{x} axis order.
_ESRI: list[dict[str, Any]] = [
    {
        "id": "esri_world_imagery",
        "label": "Esri World Imagery (satellite)",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 19,
    },
    {
        "id": "esri_world_street",
        "label": "Esri World Street Map",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 19,
    },
    {
        "id": "esri_world_topo",
        "label": "Esri World Topo Map",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 19,
    },
    {
        "id": "esri_world_terrain",
        "label": "Esri World Terrain (base)",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 13,
    },
    {
        "id": "esri_shaded_relief",
        "label": "Esri Shaded Relief",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 13,
    },
    {
        "id": "esri_world_physical",
        "label": "Esri World Physical",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Physical_Map/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 8,
    },
    {
        "id": "esri_ocean",
        "label": "Esri Ocean Basemap",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 13,
    },
    {
        "id": "esri_natgeo",
        "label": "Esri NatGeo World",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 16,
    },
    {
        "id": "esri_gray_canvas",
        "label": "Esri World Light Gray",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 16,
    },
    {
        "id": "esri_delorme",
        "label": "Esri DeLorme World Base",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/Specialty/DeLorme_World_Base_Map/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 11,
    },
    {
        "id": "esri_navigation_charts",
        "label": "Esri World Navigation Charts",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/Specialty/World_Navigation_Charts/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI + " · NGA",
        "max_zoom": 10,
    },
]

# USGS — US-only.
_USGS: list[dict[str, Any]] = [
    {
        "id": "usgs_topo",
        "label": "USGS Topo",
        "url": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_USGS,
        "max_zoom": 16,
    },
    {
        "id": "usgs_imagery",
        "label": "USGS Imagery",
        "url": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_USGS,
        "max_zoom": 16,
    },
    {
        "id": "usgs_imagery_topo",
        "label": "USGS Imagery + Topo",
        "url": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryTopo/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_USGS,
        "max_zoom": 16,
    },
    {
        "id": "usgs_hydro",
        "label": "USGS Hydro (water features)",
        "url": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSHydroCached/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_USGS,
        "max_zoom": 16,
    },
    {
        "id": "usgs_shaded_relief",
        "label": "USGS Shaded Relief",
        "url": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSShadedReliefOnly/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_USGS,
        "max_zoom": 13,
    },
]

# NOAA Office of Coast Survey — US coastal coverage; tiles 404 elsewhere.
_NOAA: list[dict[str, Any]] = [
    {
        "id": "noaa_rnc_charts",
        "label": "NOAA Raster Nautical Charts (RNC)",
        "url": "https://tileservice.charts.noaa.gov/tiles/50000_1/{z}/{x}/{y}.png",
        "attribution": _ATTR_NOAA,
        "max_zoom": 18,
    },
]

# NASA GIBS — earthdata imagery.
_NASA: list[dict[str, Any]] = [
    {
        "id": "nasa_modis_truecolor",
        "label": "NASA MODIS Terra (true color)",
        "url": (
            "https://map1.vis.earthdata.nasa.gov/wmts-webmerc/"
            "MODIS_Terra_CorrectedReflectance_TrueColor/default/"
            "/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg"
        ),
        "attribution": _ATTR_NASA,
        "max_zoom": 9,
    },
    {
        "id": "nasa_modis_bands367",
        "label": "NASA MODIS (false color · bands 3·6·7)",
        "url": (
            "https://map1.vis.earthdata.nasa.gov/wmts-webmerc/"
            "MODIS_Terra_CorrectedReflectance_Bands367/default/"
            "/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg"
        ),
        "attribution": _ATTR_NASA,
        "max_zoom": 9,
    },
    {
        "id": "nasa_viirs_citylights",
        "label": "NASA VIIRS Earth at Night (2012)",
        "url": (
            "https://map1.vis.earthdata.nasa.gov/wmts-webmerc/"
            "VIIRS_CityLights_2012/default/"
            "/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg"
        ),
        "attribution": _ATTR_NASA,
        "max_zoom": 8,
    },
]

# Game worlds — OSRS in TMS axis (y flipped).
_GAME: list[dict[str, Any]] = [
    {
        "id": "osrs_surface",
        "label": "Old School RuneScape — Surface",
        "url": (
            "https://raw.githubusercontent.com/Explv/"
            "osrs_map_full_20180601/master/0/{z}/{x}/{y}.png"
        ),
        "attribution": "Tiles &copy; Jagex / Explv (fan tool, June 2018 snapshot)",
        "min_zoom": 4,
        "max_zoom": 11,
        "tms": True,
    },
]

# Transparent overlays — composited on top of a base.
_OVERLAYS: list[dict[str, Any]] = [
    {
        "id": "overlay_openseamap",
        "label": "OpenSeaMap (sea marks)",
        "url": "https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png",
        "attribution": _ATTR_OPENSEAMAP,
        "max_zoom": 18,
        "kind": "overlay",
        "opacity": 0.95,
    },
    {
        "id": "overlay_openrailway",
        "label": "OpenRailwayMap (rails)",
        "url": "https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png",
        "attribution": _ATTR_OPENRAILWAY,
        "subdomains": "abc",
        "max_zoom": 19,
        "kind": "overlay",
        "opacity": 0.9,
    },
    {
        "id": "overlay_esri_reference",
        "label": "Esri World Reference (places & boundaries)",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 13,
        "kind": "overlay",
        "opacity": 0.95,
    },
    {
        "id": "overlay_esri_transportation",
        "label": "Esri World Transportation",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 19,
        "kind": "overlay",
        "opacity": 0.9,
    },
    {
        "id": "overlay_esri_hillshade",
        "label": "Esri World Hillshade",
        "url": "https://services.arcgisonline.com/arcgis/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}",
        "attribution": _ATTR_ESRI,
        "max_zoom": 16,
        "kind": "overlay",
        "opacity": 0.7,
    },
]


_GROUPS: list[tuple[str, str, list[dict[str, Any]]]] = [
    ("worldwide", "Worldwide basemaps", _WORLDWIDE),
    ("esri", "Esri / ArcGIS", _ESRI),
    ("usgs", "USGS (US-only)", _USGS),
    ("noaa", "NOAA nautical charts", _NOAA),
    ("nasa", "NASA Earthdata (tiles)", _NASA),
    ("game", "Game worlds", _GAME),
    ("overlays", "Transparent overlays", _OVERLAYS),
]


def _normalize(
    entry: dict[str, Any], group_key: str, group_label: str
) -> dict[str, Any]:
    out = dict(entry)
    out.setdefault("kind", "tile")
    out.setdefault("min_zoom", 0)
    out.setdefault("max_zoom", 19)
    out.setdefault("opacity", 1.0 if out["kind"] == "tile" else 0.85)
    out.setdefault("subdomains", None)
    out.setdefault("tms", False)
    out["group"] = group_key
    out["group_label"] = group_label
    return out


PROVIDERS: dict[str, dict[str, Any]] = {}
for _key, _label, _bucket in _GROUPS:
    for _entry in _bucket:
        PROVIDERS[_entry["id"]] = _normalize(_entry, _key, _label)


PROVIDER_OPTIONS_GROUPED: list[dict[str, Any]] = [
    {
        "group": label,
        "items": [{"value": entry["id"], "label": entry["label"]} for entry in bucket],
    }
    for _, label, bucket in _GROUPS
]


# Default base layer — Esri World Imagery has full global coverage and no
# key, so the user always has something to stack overlays on top of.
DEFAULT_BASE_SLUG: str = "esri_world_imagery"


def sample_tile_urls(slug: str) -> list[str]:
    """Six tile URLs at a fixed sample zoom for the cube chip.

    Earlier versions used a 3×3 block centered on the North Atlantic
    which made every chip look like uniform sky-blue ocean (OSM /
    CARTO render open ocean as a pale fill at z=4). The new sample
    set targets continental land at z=4 so each provider's tile
    paints something visually distinct — coastlines, road grids,
    relief shading — instead of an unbroken ocean swatch.

    Picks at z=4 (16×16 grid; each tile ≈ 2500 km):
      * x=4, y=6  — SE United States
      * x=7, y=5  — UK / Western Europe
      * x=8, y=5  — Eastern Europe / Russia
      * x=8, y=6  — Middle East
      * x=7, y=6  — North Africa
      * x=4, y=7  — Mexico / Central America

    The gradient fallback in the CSS handles providers whose coverage
    doesn't reach a given tile (NOAA outside US coastal waters, OSRS
    fan tileset, etc.).
    """
    provider = PROVIDERS.get(slug)
    if not provider:
        return []
    template = provider["url"]
    subdomains = provider.get("subdomains") or "a"
    z = 4
    # Land-rich samples — see docstring.
    samples = [
        (4, 6),  # SE USA
        (7, 5),  # UK / W Europe
        (8, 5),  # E Europe / Russia
        (8, 6),  # Middle East
        (7, 6),  # N Africa
        (4, 7),  # Mexico / Central America
    ]
    urls = []
    for i, (x, y) in enumerate(samples):
        # TMS flips the y-axis (Leaflet's default is XYZ).
        ty = ((1 << z) - 1 - y) if provider.get("tms") else y
        u = (
            template.replace("{s}", subdomains[i % len(subdomains)])
            .replace("{z}", str(z))
            .replace("{x}", str(x))
            .replace("{y}", str(ty))
        )
        urls.append(u)
    return urls


def tile_kwargs(slug: str, *, opacity: float | None = None) -> dict[str, Any]:
    """Kwargs ready to splat into `dl2.TileLayer(...)`."""
    provider = PROVIDERS.get(slug)
    if not provider:
        return {}
    return {
        "url": provider["url"],
        "attribution": provider["attribution"],
        "maxZoom": int(provider["max_zoom"]),
        "opacity": float(provider["opacity"] if opacity is None else opacity),
    }


def renderoption_payload() -> dict[str, dict[str, Any]]:
    """Build the per-slug payload the `renderTileCubeFace` JS reads."""
    payload: dict[str, dict[str, Any]] = {}
    for slug, provider in PROVIDERS.items():
        payload[slug] = {
            "name": provider["label"],
            "group": provider["group_label"],
            "kind": provider["kind"],
            "maxZoom": provider["max_zoom"],
            "tileUrls": sample_tile_urls(slug),
        }
    return payload
