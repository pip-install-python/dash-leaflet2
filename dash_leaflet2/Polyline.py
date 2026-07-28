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


class Polyline(Component):
    """A Polyline component.
Polyline draws a multi-segment line from a list of [lat, lng] points. Place it as a
child of Map. Wraps Leaflet 2's Polyline.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    Popup / Tooltip children.

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- color (string; default '#3388ff'):
    Stroke color. [MUTABLE].

- dashArray (string; optional):
    Dash pattern, e.g. \"5,10\". [MUTABLE].

- interactive (boolean; optional):
    Whether the line captures pointer events (fires clicks, blocks the
    map click underneath). Set False for a non-interactive decoration
    / context overlay so it never intercepts clicks meant for the map.
    Construction-only. @default True.

- n_clicks (number; optional):
    Times the line has been clicked. [READONLY].

- opacity (number; default 1):
    Stroke opacity, 0..1. [MUTABLE].

- positions (list of list of 2 elements: [number, number]s; optional):
    Vertices as a list of [lat, lng] points. [MUTABLE].

- weight (number; default 3):
    Stroke width in pixels. [MUTABLE]."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'Polyline'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        positions: typing.Optional[typing.Sequence[typing.Tuple[NumberType, NumberType]]] = None,
        color: typing.Optional[str] = None,
        weight: typing.Optional[NumberType] = None,
        opacity: typing.Optional[NumberType] = None,
        dashArray: typing.Optional[str] = None,
        interactive: typing.Optional[bool] = None,
        n_clicks: typing.Optional[NumberType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'className', 'color', 'dashArray', 'interactive', 'n_clicks', 'opacity', 'positions', 'style', 'weight']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'className', 'color', 'dashArray', 'interactive', 'n_clicks', 'opacity', 'positions', 'style', 'weight']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(Polyline, self).__init__(children=children, **args)

setattr(Polyline, "__init__", _explicitize_args(Polyline.__init__))
