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


class FeatureGroup(Component):
    """A FeatureGroup component.
FeatureGroup is like LayerGroup but extends `leaflet.FeatureGroup` — it can
emit a combined GeoJSON of its vector children and broadcasts a single
`click` event no matter which child was clicked. Use it when grouping
shapes you want to treat as one unit (typical companion for `EditControl`).
Wraps Leaflet 2's FeatureGroup.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    Any number of layer children (Marker, Polygon, Circle, ...).

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- geojson (dict; optional):
    Combined GeoJSON FeatureCollection of all children (vectors only).
    [READONLY].

- n_clicks (number; optional):
    Number of times any child layer has been clicked. [READONLY].

- n_layers (number; optional):
    Number of times the group's children were modified. [READONLY]."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'FeatureGroup'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        n_clicks: typing.Optional[NumberType] = None,
        geojson: typing.Optional[dict] = None,
        n_layers: typing.Optional[NumberType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'className', 'geojson', 'n_clicks', 'n_layers', 'style']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'className', 'geojson', 'n_clicks', 'n_layers', 'style']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(FeatureGroup, self).__init__(children=children, **args)

setattr(FeatureGroup, "__init__", _explicitize_args(FeatureGroup.__init__))
