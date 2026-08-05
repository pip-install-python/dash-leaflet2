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


class FullScreenControl(Component):
    """A FullScreenControl component.
FullScreenControl adds a single button to the map that toggles the map
container in/out of the browser's native fullscreen mode. Leaflet 2 doesn't
ship a fullscreen control — this maps the browser's `requestFullscreen()`
API onto a small `Control` subclass, matching the dash-leaflet (and
`Leaflet.fullscreen` plugin) API shape.

Keyword arguments:

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- fullscreen (boolean; optional):
    Whether the map is currently in fullscreen mode. [READONLY].

- n_clicks (number; optional):
    Number of times the button has been clicked. [READONLY].

- position (a value equal to: 'topleft', 'topright', 'bottomleft', 'bottomright'; default 'topleft'):
    \"topleft\" | \"topright\" | \"bottomleft\" | \"bottomright\".
    Default \"topleft\". [MUTABLE].

- title (string; default 'Full Screen'):
    Tooltip text when entering fullscreen. Default \"Full Screen\".

- titleCancel (string; default 'Exit Full Screen'):
    Tooltip text when leaving fullscreen. Default \"Exit Full
    Screen\"."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'FullScreenControl'


    def __init__(
        self,
        position: typing.Optional[Literal["topleft", "topright", "bottomleft", "bottomright"]] = None,
        title: typing.Optional[str] = None,
        titleCancel: typing.Optional[str] = None,
        n_clicks: typing.Optional[NumberType] = None,
        fullscreen: typing.Optional[bool] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'className', 'fullscreen', 'n_clicks', 'position', 'style', 'title', 'titleCancel']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'className', 'fullscreen', 'n_clicks', 'position', 'style', 'title', 'titleCancel']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(FullScreenControl, self).__init__(**args)

setattr(FullScreenControl, "__init__", _explicitize_args(FullScreenControl.__init__))
