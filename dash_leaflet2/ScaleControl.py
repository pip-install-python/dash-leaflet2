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


class ScaleControl(Component):
    """A ScaleControl component.
ScaleControl shows a metric and/or imperial scale bar in a map corner.
Wraps Leaflet 2's built-in `Control.Scale` (lives on the Control namespace
but not exported by the ESM — we reach in through `Control.Scale`).

Keyword arguments:

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- imperial (boolean; default False):
    Show imperial (mi/ft) bar. Default False.

- maxWidth (number; default 100):
    Maximum bar width in pixels. Default 100.

- metric (boolean; default True):
    Show metric (km/m) bar. Default True.

- position (a value equal to: 'topleft', 'topright', 'bottomleft', 'bottomright'; default 'bottomleft'):
    \"topleft\" | \"topright\" | \"bottomleft\" | \"bottomright\".
    Default \"bottomleft\". [MUTABLE].

- updateWhenIdle (boolean; default False):
    Only redraw the bar when the map stops moving. Default False."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'ScaleControl'


    def __init__(
        self,
        position: typing.Optional[Literal["topleft", "topright", "bottomleft", "bottomright"]] = None,
        metric: typing.Optional[bool] = None,
        imperial: typing.Optional[bool] = None,
        maxWidth: typing.Optional[NumberType] = None,
        updateWhenIdle: typing.Optional[bool] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'className', 'imperial', 'maxWidth', 'metric', 'position', 'style', 'updateWhenIdle']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'className', 'imperial', 'maxWidth', 'metric', 'position', 'style', 'updateWhenIdle']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(ScaleControl, self).__init__(**args)

setattr(ScaleControl, "__init__", _explicitize_args(ScaleControl.__init__))
