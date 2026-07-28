# AUTO GENERATED FILE - DO NOT EDIT

import typing  # noqa: F401
from typing_extensions import TypedDict, NotRequired, Literal # noqa: F401
from dash.development.base_component import Component, _explicitize_args

ComponentSingleType = typing.Union[str, int, float, Component, None]
ComponentType = typing.Union[
    ComponentSingleType,
    typing.Sequence[ComponentSingleType],
]

NumberType = typing.Union[
    typing.SupportsFloat, typing.SupportsInt, typing.SupportsComplex
]


class TileLayer(Component):
    """A TileLayer component.
TileLayer loads and displays a raster tile basemap. Place it as a child of
Map. Wraps Leaflet 2's TileLayer.

Keyword arguments:

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- attribution (string; default '&copy; OpenStreetMap contributors'):
    Attribution HTML shown in the bottom-right of the map.

- bounds (list of 2 elements: [list of 2 elements: [number, number], list of 2 elements: [number, number]]; optional):
    Geographic bounds outside of which no tiles are requested, as
    `[[south, west], [north, east]]`. Same as Leaflet's
    `LatLngBounds`. Cheaper than server-side 404s for out-of-area
    requests.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- crossOrigin (string; optional):
    Adds the `crossOrigin` attribute to every tile img element. Pass
    \"anonymous\" to make tile loads CORS-mode so canvas captures (map
    screenshots / html2canvas) can read the pixels. The tile host must
    answer with Access-Control-Allow-Origin or the tiles fail to load
    entirely — leave unset for hosts you don't control.
    \"use-credentials\" and \"\" are also valid. Construction-time
    only.

- detectRetina (boolean; default False):
    If True, request tiles at 2x resolution on hi-DPI displays (loads
    twice as many tiles but renders sharper).

- errorTileUrl (string; optional):
    URL of an image shown in place of any tile that fails to load. A
    1x1 transparent PNG data URL is the common \"hide broken tiles\"
    trick.

- maxNativeZoom (number; optional):
    Maximum zoom level that the tile source actually has tiles for.
    Leaflet upscales tiles from this zoom when the map zooms in past
    it (instead of 404-ing). Useful for overlays whose cache caps
    below the map's max zoom — e.g. USGS Hydro is only cached to z16;
    set `maxNativeZoom=16` and the z16 tile will be shown at z17/z18.

- maxZoom (number; default 19):
    Maximum zoom level for this tile layer.

- minZoom (number; default 0):
    Minimum zoom level at which this tile layer is visible. Below this
    zoom Leaflet stops requesting tiles entirely (no 404 thrash on
    out-of-range historical / harbor-cropped pyramids). Default 0.

- opacity (number; default 1):
    Layer opacity, 0..1. [MUTABLE].

- subdomains (string | list of strings; optional):
    Subdomains substituted into the URL `{s}` placeholder. Accepts an
    array like `['a','b','c']` or a string `'abc'` (each character is
    a subdomain).

- tms (boolean; default False):
    If True, inverts Y coordinates so this layer works with TMS-shaped
    tile pyramids (Leaflet defaults to XYZ).

- url (string; default 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'):
    Tile URL template, e.g.
    \"https://tile.openstreetmap.org/{z}/{x}/{y}.png\". Updating it
    swaps the basemap. [MUTABLE].

- zIndex (number; optional):
    Explicit z-index for the tile layer's DOM pane. Higher = renders
    on top. Useful when stacking multiple tile layers and DOM mount
    order alone is insufficient. [MUTABLE]."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'TileLayer'


    def __init__(
        self,
        url: typing.Optional[str] = None,
        attribution: typing.Optional[str] = None,
        minZoom: typing.Optional[NumberType] = None,
        maxZoom: typing.Optional[NumberType] = None,
        maxNativeZoom: typing.Optional[NumberType] = None,
        bounds: typing.Optional[typing.Tuple[typing.Tuple[NumberType, NumberType], typing.Tuple[NumberType, NumberType]]] = None,
        errorTileUrl: typing.Optional[str] = None,
        zIndex: typing.Optional[NumberType] = None,
        subdomains: typing.Optional[typing.Union[str, typing.Sequence[str]]] = None,
        detectRetina: typing.Optional[bool] = None,
        tms: typing.Optional[bool] = None,
        opacity: typing.Optional[NumberType] = None,
        crossOrigin: typing.Optional[str] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'attribution', 'bounds', 'className', 'crossOrigin', 'detectRetina', 'errorTileUrl', 'maxNativeZoom', 'maxZoom', 'minZoom', 'opacity', 'style', 'subdomains', 'tms', 'url', 'zIndex']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'attribution', 'bounds', 'className', 'crossOrigin', 'detectRetina', 'errorTileUrl', 'maxNativeZoom', 'maxZoom', 'minZoom', 'opacity', 'style', 'subdomains', 'tms', 'url', 'zIndex']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(TileLayer, self).__init__(**args)

setattr(TileLayer, "__init__", _explicitize_args(TileLayer.__init__))
