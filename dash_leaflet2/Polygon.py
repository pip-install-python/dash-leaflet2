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


class Polygon(Component):
    """A Polygon component.
Polygon draws a filled, closed shape from a list of [lat, lng] points. Place it as a
child of Map. Wraps Leaflet 2's Polygon.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    Popup / Tooltip children.

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- color (string; default '#3388ff'):
    Stroke color. [MUTABLE].

- fillColor (string; optional):
    Fill color (defaults to stroke color). [MUTABLE].

- fillOpacity (number; default 0.2):
    Fill opacity, 0..1. [MUTABLE].

- n_clicks (number; optional):
    Times the polygon has been clicked. [READONLY].

- opacity (number; default 1):
    Stroke opacity, 0..1. [MUTABLE].

- positions (list of list of 2 elements: [number, number]s; optional):
    Ring vertices as a list of [lat, lng] points (auto-closed).
    [MUTABLE].

- weight (number; default 3):
    Stroke width in pixels. [MUTABLE]."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'Polygon'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        positions: typing.Optional[typing.Sequence[typing.Tuple[NumberType, NumberType]]] = None,
        color: typing.Optional[str] = None,
        weight: typing.Optional[NumberType] = None,
        opacity: typing.Optional[NumberType] = None,
        fillColor: typing.Optional[str] = None,
        fillOpacity: typing.Optional[NumberType] = None,
        n_clicks: typing.Optional[NumberType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'className', 'color', 'fillColor', 'fillOpacity', 'n_clicks', 'opacity', 'positions', 'style', 'weight']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'className', 'color', 'fillColor', 'fillOpacity', 'n_clicks', 'opacity', 'positions', 'style', 'weight']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(Polygon, self).__init__(children=children, **args)

setattr(Polygon, "__init__", _explicitize_args(Polygon.__init__))
