# AUTO GENERATED FILE - DO NOT EDIT

import typing  # noqa: F401
from typing_extensions import TypedDict, NotRequired, Literal # noqa: F401
from dash.development.base_component import Component, _explicitize_args
try:
    from dash.types import NumberType  # noqa: F401
except ImportError:
    # Backwards compatibility for dash<=4.1.0
    if typing.TYPE_CHECKING:
        raise
    NumberType = typing.Union[  # noqa: F401
        typing.SupportsFloat, typing.SupportsInt, typing.SupportsComplex
    ]

ComponentSingleType = typing.Union[str, int, float, Component, None]
ComponentType = typing.Union[
    ComponentSingleType,
    typing.Sequence[ComponentSingleType],
]


class GeoJSON(Component):
    """A GeoJSON component.
GeoJSON renders a GeoJSON object — typically fed from a Python callback via the `data`
prop. Set `cluster=True` to collapse dense point sets via SuperCluster (the same backend
dash-leaflet 1's clustering uses). Custom `pointToLayer` / `clusterToLayer` JS strings
plus a `hideout` passthrough let you style features without round-tripping through Python.
Place it as a child of Map. Wraps Leaflet 2's GeoJSON layer.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    Popup / Tooltip children bound to the whole layer.

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- clickFeature (dict; optional):
    `properties` of the most recently clicked feature. [READONLY].

- cluster (boolean; default False):
    Turn on supercluster-based point clustering. Markers within
    `superClusterOptions.radius` pixels collapse into a single cluster
    bubble; zooming in expands them. Only point geometries cluster;
    vector features (LineString, Polygon) are passed through
    unchanged.

- clusterToLayer (string; optional):
    JavaScript source for a function that builds the layer shown in
    place of a SuperCluster cluster. Signature: `(feature, latlng,
    index, ctx) => Layer`. The default is a small DivIcon with the
    cluster's point count.

- data (dict; optional):
    A GeoJSON FeatureCollection / Feature / geometry object.
    [MUTABLE].

- hideout (dict with strings as keys and values of type boolean | number | string | dict | list; optional):
    Arbitrary pass-through data made available to `pointToLayer` /
    `clusterToLayer` as `ctx.hideout`. Use it to ship colour maps,
    label dictionaries, or threshold values from Python without
    re-evaluating the JS function. [MUTABLE].

- n_clicks (number; optional):
    Number of times any feature has been clicked. [READONLY].

- pointToLayer (string; optional):
    JavaScript source for a function that converts an individual point
    feature into a layer. Signature: `(feature, latlng, ctx) =>
    Layer`, where `ctx = { hideout, leaflet, map }`. Pass the function
    body as a string; it is wrapped in `new Function(...)` at
    construction time. The default uses the bundled DEFAULT_ICON.

- spiderfyOnMaxZoom (boolean; default False):
    Reserved for future support — at max zoom, \"spiderfy\"
    overlapping markers into a ring so each is individually
    selectable. Currently a no-op (clicking the cluster at maxZoom
    still triggers zoomToBoundsOnClick).

- superClusterOptions (dict with strings as keys and values of type boolean | number | string | dict | list; optional):
    Tuning for the underlying SuperCluster index: `{ radius,
    minPoints, maxZoom, minZoom, extent }`. Defaults: `{ radius: 80,
    minPoints: 2, maxZoom: 16, minZoom: 0, extent: 512 }`. See
    https://github.com/mapbox/supercluster#options for the full list.

- zoomToBoundsOnClick (boolean; default True):
    If True, clicking a cluster fits the map to that cluster's
    children's bounds. Default True."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'GeoJSON'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        data: typing.Optional[dict] = None,
        style: typing.Optional[typing.Any] = None,
        cluster: typing.Optional[bool] = None,
        superClusterOptions: typing.Optional[typing.Dict[typing.Union[str, float, int], typing.Any]] = None,
        pointToLayer: typing.Optional[str] = None,
        clusterToLayer: typing.Optional[str] = None,
        hideout: typing.Optional[typing.Dict[typing.Union[str, float, int], typing.Any]] = None,
        zoomToBoundsOnClick: typing.Optional[bool] = None,
        spiderfyOnMaxZoom: typing.Optional[bool] = None,
        n_clicks: typing.Optional[NumberType] = None,
        clickFeature: typing.Optional[dict] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'className', 'clickFeature', 'cluster', 'clusterToLayer', 'data', 'hideout', 'n_clicks', 'pointToLayer', 'spiderfyOnMaxZoom', 'style', 'superClusterOptions', 'zoomToBoundsOnClick']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'className', 'clickFeature', 'cluster', 'clusterToLayer', 'data', 'hideout', 'n_clicks', 'pointToLayer', 'spiderfyOnMaxZoom', 'style', 'superClusterOptions', 'zoomToBoundsOnClick']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(GeoJSON, self).__init__(children=children, **args)

setattr(GeoJSON, "__init__", _explicitize_args(GeoJSON.__init__))
