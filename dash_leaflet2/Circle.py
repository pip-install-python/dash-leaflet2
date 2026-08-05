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


class Circle(Component):
    """A Circle component.
Circle draws a circle with a radius in meters (it grows/shrinks with zoom). For a
fixed-pixel circle use CircleMarker. Place it as a child of Map. Wraps Leaflet 2's Circle.

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

- n_clicks (number; optional):
    Times the circle has been clicked. [READONLY].

- radius (number; default 100):
    Radius in METERS (geographic). [MUTABLE].

- weight (number; default 3):
    Stroke width in pixels. [MUTABLE]."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'Circle'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        center: typing.Optional[typing.Tuple[NumberType, NumberType]] = None,
        radius: typing.Optional[NumberType] = None,
        color: typing.Optional[str] = None,
        weight: typing.Optional[NumberType] = None,
        fillColor: typing.Optional[str] = None,
        fillOpacity: typing.Optional[NumberType] = None,
        n_clicks: typing.Optional[NumberType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'center', 'className', 'color', 'fillColor', 'fillOpacity', 'n_clicks', 'radius', 'style', 'weight']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'center', 'className', 'color', 'fillColor', 'fillOpacity', 'n_clicks', 'radius', 'style', 'weight']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(Circle, self).__init__(children=children, **args)

setattr(Circle, "__init__", _explicitize_args(Circle.__init__))
