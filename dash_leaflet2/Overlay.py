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


class Overlay(Component):
    """An Overlay component.
Overlay wraps any layer and registers it as a toggleable overlay in the parent
LayersControl (checkbox). Place it as a child of LayersControl, with a single layer
component as its own child.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    The Leaflet layer (TileLayer, GeoJSON, Marker, ...) controlled by
    this entry.

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- checked (boolean; default False):
    Initially checked? Overlays are independent.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- name (string; default 'Overlay'):
    Display name shown in the LayersControl (also the checkbox's
    identity)."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'Overlay'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        name: typing.Optional[str] = None,
        checked: typing.Optional[bool] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'checked', 'className', 'name', 'style']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'checked', 'className', 'name', 'style']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(Overlay, self).__init__(children=children, **args)

setattr(Overlay, "__init__", _explicitize_args(Overlay.__init__))
