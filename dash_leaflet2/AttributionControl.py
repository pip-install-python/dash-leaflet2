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


class AttributionControl(Component):
    """An AttributionControl component.
AttributionControl adds an explicitly-controlled attribution box to the map. Place
it as a child of `dl2.Map` with `attributionControl=False` to take over from the
bundled default; both `position` and `prefix` are two-way (mutable from Python
callbacks). Pass `prefix=False` to hide the "Leaflet" link.

Keyword arguments:

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- position (a value equal to: 'topleft', 'topright', 'bottomleft', 'bottomright'; default 'bottomright'):
    Map control position. Default 'bottomright'. [MUTABLE].

- prefix (string | boolean; optional):
    HTML shown before the layer attributions. Default Leaflet's
    \"Leaflet\" link. Pass `False` (or empty string) to hide the
    prefix entirely. [MUTABLE]."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'AttributionControl'


    def __init__(
        self,
        position: typing.Optional[Literal["topleft", "topright", "bottomleft", "bottomright"]] = None,
        prefix: typing.Optional[typing.Union[str, bool]] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'className', 'position', 'prefix', 'style']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'className', 'position', 'prefix', 'style']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(AttributionControl, self).__init__(**args)

setattr(AttributionControl, "__init__", _explicitize_args(AttributionControl.__init__))
