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


class LayersControl(Component):
    """A LayersControl component.
LayersControl renders a Leaflet control that lets the user pick one of N base layers and
toggle M overlays. Place dl2.BaseLayer and dl2.Overlay as its children; LayersControl
itself must be a child of dl2.Map.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    BaseLayer + Overlay children.

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- activeBase (string; optional):
    Name of the active base layer. Two-way: reflects user choice +
    accepts callback. [MUTABLE].

- activeOverlays (list of strings; optional):
    Names of currently visible overlays. Two-way. [MUTABLE].

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- collapsed (boolean; default True):
    If True, show only the toggle handle until the pointer enters.

- position (string; default 'topright'):
    \"topright\" | \"topleft\" | \"bottomright\" | \"bottomleft\"."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'LayersControl'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        position: typing.Optional[str] = None,
        collapsed: typing.Optional[bool] = None,
        activeBase: typing.Optional[str] = None,
        activeOverlays: typing.Optional[typing.Sequence[str]] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'activeBase', 'activeOverlays', 'className', 'collapsed', 'position', 'style']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'activeBase', 'activeOverlays', 'className', 'collapsed', 'position', 'style']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(LayersControl, self).__init__(children=children, **args)

setattr(LayersControl, "__init__", _explicitize_args(LayersControl.__init__))
