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


class Tooltip(Component):
    """A Tooltip component.
Tooltip shows a small label on hover (or permanently), bound to its parent layer
(Marker, Polygon, ...). Children render through a React portal, so any Dash component
works as content. Wraps Leaflet 2's Tooltip.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    Tooltip content — any Dash/HTML children, rendered live via a
    React portal.

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- direction (string; default 'auto'):
    Placement: \"right\" | \"left\" | \"top\" | \"bottom\" |
    \"center\" | \"auto\".

- opacity (number; default 0.9):
    Tooltip opacity, 0..1.

- permanent (boolean; default False):
    If True, the tooltip stays open instead of showing only on hover."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'Tooltip'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        permanent: typing.Optional[bool] = None,
        direction: typing.Optional[str] = None,
        opacity: typing.Optional[NumberType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'className', 'direction', 'opacity', 'permanent', 'style']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'className', 'direction', 'opacity', 'permanent', 'style']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(Tooltip, self).__init__(children=children, **args)

setattr(Tooltip, "__init__", _explicitize_args(Tooltip.__init__))
