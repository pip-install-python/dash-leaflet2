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


class EasyButton(Component):
    """An EasyButton component.
EasyButton adds a single-icon control to the map. Use it for quick map-level actions
(open a panel, locate, zoom-home, etc.); the click is reported back to Dash as n_clicks.
Icons come from Iconify (any of the 200k+ icons), e.g. "mdi:emoticon-happy-outline".
Place it as a child of dl2.Map.

Keyword arguments:

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- icon (string; default 'mdi:circle-medium'):
    Iconify icon name, e.g. \"mdi:emoticon-happy-outline\" or
    \"mdi:crosshairs-gps\".

- iconSize (number; default 18):
    Icon size in pixels.

- n_clicks (number; default 0):
    Number of times the button has been clicked. [READONLY].

- n_dblclicks (number; default 0):
    Number of times the button has been double-clicked. [READONLY].

- position (string; default 'topleft'):
    \"topleft\" | \"topright\" | \"bottomleft\" | \"bottomright\".

- title (string; optional):
    Tooltip text shown on hover."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'EasyButton'


    def __init__(
        self,
        position: typing.Optional[str] = None,
        icon: typing.Optional[str] = None,
        iconSize: typing.Optional[NumberType] = None,
        title: typing.Optional[str] = None,
        n_clicks: typing.Optional[NumberType] = None,
        n_dblclicks: typing.Optional[NumberType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'className', 'icon', 'iconSize', 'n_clicks', 'n_dblclicks', 'position', 'style', 'title']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'className', 'icon', 'iconSize', 'n_clicks', 'n_dblclicks', 'position', 'style', 'title']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(EasyButton, self).__init__(**args)

setattr(EasyButton, "__init__", _explicitize_args(EasyButton.__init__))
