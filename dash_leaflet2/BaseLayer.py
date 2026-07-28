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


class BaseLayer(Component):
    """A BaseLayer component.
BaseLayer wraps a layer (typically a TileLayer) and registers it as a base layer in the
parent LayersControl. Bases are mutually exclusive (radio). Place it as a child of
LayersControl, with a single layer component (e.g. TileLayer) as its own child.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    The Leaflet layer (typically a dl2.TileLayer) controlled by this
    entry.

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- checked (boolean; default False):
    Initially selected base layer? Exactly one base is active at a
    time.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- name (string; default 'Base'):
    Display name shown in the LayersControl (also the radio's
    identity)."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'BaseLayer'


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

        super(BaseLayer, self).__init__(children=children, **args)

setattr(BaseLayer, "__init__", _explicitize_args(BaseLayer.__init__))
