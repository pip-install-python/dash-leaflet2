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


class LayerGroup(Component):
    """A LayerGroup component.
LayerGroup bundles N layers so they can be added/removed together. Drop child
layers (Marker, Polygon, Circle, GeoJSON, ...) inside it; each is added to a
shared `leaflet.LayerGroup` instead of the map directly. Place it as a child
of `dl2.Map` — or of `dl2.Overlay` inside a LayersControl, to toggle the
whole group as one entry. Wraps Leaflet 2's LayerGroup.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    Any number of layer children (Marker, Polygon, Circle, GeoJSON,
    ...).

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- className (string; optional):
    Often-used CSS class name(s) for the root element."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'LayerGroup'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'className', 'style']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'className', 'style']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(LayerGroup, self).__init__(children=children, **args)

setattr(LayerGroup, "__init__", _explicitize_args(LayerGroup.__init__))
