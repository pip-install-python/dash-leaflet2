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


class CircleMarker(Component):
    """A CircleMarker component.
CircleMarker draws a circle with a fixed pixel radius (it stays the same size at every
zoom). For a metric radius use Circle. Place it as a child of Map. Wraps Leaflet 2's
CircleMarker.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    Popup / Tooltip children.

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- center (list of 2 elements: [number, number]; default [51.505, -0.09]):
    Center as [lat, lng]. [MUTABLE].

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- color (string; default '#3388ff'):
    Stroke color. [MUTABLE].

- fillColor (string; optional):
    Fill color (defaults to stroke color). [MUTABLE].

- fillOpacity (number; default 0.2):
    Fill opacity, 0..1. [MUTABLE].

- interactive (boolean; optional):
    Whether the circle captures pointer events (fires clicks, blocks
    the map click underneath). Set False for a non-interactive
    decoration / context overlay so it never intercepts clicks meant
    for the map. Construction-only. @default True.

- n_clicks (number; optional):
    Times the marker has been clicked. [READONLY].

- radius (number; default 10):
    Radius in PIXELS (fixed; does not scale with zoom). [MUTABLE].

- weight (number; default 3):
    Stroke width in pixels. [MUTABLE]."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'CircleMarker'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        center: typing.Optional[typing.Tuple[NumberType, NumberType]] = None,
        radius: typing.Optional[NumberType] = None,
        color: typing.Optional[str] = None,
        weight: typing.Optional[NumberType] = None,
        fillColor: typing.Optional[str] = None,
        fillOpacity: typing.Optional[NumberType] = None,
        interactive: typing.Optional[bool] = None,
        n_clicks: typing.Optional[NumberType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'center', 'className', 'color', 'fillColor', 'fillOpacity', 'interactive', 'n_clicks', 'radius', 'style', 'weight']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'center', 'className', 'color', 'fillColor', 'fillOpacity', 'interactive', 'n_clicks', 'radius', 'style', 'weight']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(CircleMarker, self).__init__(children=children, **args)

setattr(CircleMarker, "__init__", _explicitize_args(CircleMarker.__init__))
