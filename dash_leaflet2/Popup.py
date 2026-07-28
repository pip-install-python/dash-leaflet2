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


class Popup(Component):
    """A Popup component.
Popup shows content in a balloon bound to its parent layer (Marker, Polygon, ...).
Children are rendered through a React portal, so any Dash component works as popup
content. Wraps Leaflet 2's Popup.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    Popup content — any Dash/HTML children, rendered live via a React
    portal.

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- autoClose (boolean; optional):
    If True, opening a popup closes other popups. Leaflet defaults to
    True; set False to allow multiple popups open simultaneously.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- closeButton (boolean; default True):
    Show the close (×) button.

- closeOnClick (boolean; optional):
    If True, clicking the map closes the popup. Leaflet defaults to
    True; set False for form popups that should stay open while the
    user is interacting.

- maxWidth (number; default 300):
    Max width in pixels.

- minWidth (number; default 50):
    Min width in pixels.

- opened (boolean; optional):
    Controlled open state — when set, the popup follows this prop
    (True → open, False → closed) instead of waiting for a click on
    the parent layer. [MUTABLE]."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'Popup'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        maxWidth: typing.Optional[NumberType] = None,
        minWidth: typing.Optional[NumberType] = None,
        closeButton: typing.Optional[bool] = None,
        closeOnClick: typing.Optional[bool] = None,
        autoClose: typing.Optional[bool] = None,
        opened: typing.Optional[bool] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'autoClose', 'className', 'closeButton', 'closeOnClick', 'maxWidth', 'minWidth', 'opened', 'style']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'autoClose', 'className', 'closeButton', 'closeOnClick', 'maxWidth', 'minWidth', 'opened', 'style']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(Popup, self).__init__(children=children, **args)

setattr(Popup, "__init__", _explicitize_args(Popup.__init__))
