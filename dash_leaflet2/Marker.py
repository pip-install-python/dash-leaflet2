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


class Marker(Component):
    """A Marker component.
Marker displays an icon at a position and can host Popup/Tooltip children. The icon can
be the default pin, a custom image (`icon`), an `emoji`, or any Iconify icon (`iconify`,
e.g. "mdi:home"). Draggable markers write their new `position` back to Dash. Wraps
Leaflet 2's Marker. Place it as a child of Map.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    Popup / Tooltip children bound to this marker.

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- draggable (boolean; default False):
    Whether the marker can be dragged with the pointer. [MUTABLE].

- emoji (string; optional):
    A single emoji to use as the marker, e.g. \"🛥️\".

- icon (dict; optional):
    Custom image icon as Leaflet Icon options, e.g. {iconUrl,
    iconSize:[w,h], iconAnchor:[x,y]}.

- iconAnchor (list of 2 elements: [number, number]; optional):
    [x, y] icon anchor for emoji / iconify / iconOptions markers.
    Default bottom-center.

- iconColor (string; optional):
    CSS color for monochrome iconify icons.

- iconOptions (dict; optional):
    Full Leaflet DivIcon options escape hatch ({html, className,
    iconSize, iconAnchor}).

- iconSize (number; default 32):
    Pixel size for emoji / iconify markers. Default 32.

- iconify (string; optional):
    An Iconify icon name, e.g. \"mdi:home\" or \"twemoji:sailboat\"
    (loads from the Iconify API).

- n_clicks (number; optional):
    Number of times the marker has been clicked. [READONLY].

- n_drags (number; optional):
    Number of times the marker has been dragged. [READONLY].

- opacity (number; default 1):
    Marker opacity, 0..1. [MUTABLE].

- popup (string; optional):
    Convenience popup text. For rich content, use a <Popup> child
    instead.

- position (list of 2 elements: [number, number]; default [51.505, -0.09]):
    Marker position as [lat, lng]. Updating it moves the marker;
    dragging writes it back. [MUTABLE].

- rotateWithMap (boolean; default False):
    When `True`, the marker icon rotates together with the map —
    useful for vehicles, aircraft, walking characters, compass arrows,
    anything whose orientation is tied to the world. The icon's visual
    screen rotation is `bearing + rotationAngle`.  When `False`
    (default), the icon stays in a fixed screen orientation regardless
    of map bearing — useful for pins, labels, and the typical \"marker
    should always look upright\" case. The icon's visual screen
    rotation is just `rotationAngle`.  Implementation: when `False` we
    apply `rotationAngle - bearing` to the icon, which cancels the map
    pane's rotation contribution. When `True` we apply `rotationAngle`
    and let the pane's CSS rotation carry the icon.

- rotationAngle (number; default 0):
    Marker rotation in degrees (CW from north). Useful for vehicle /
    aircraft / character sprites that need to point in a direction.
    Applied via a CSS `rotate` on the icon DOM. [MUTABLE].

- tooltip (string; optional):
    Convenience tooltip text. For rich content, use a <Tooltip> child
    instead.

- zIndexOffset (number; default 0):
    z-index offset relative to other markers. [MUTABLE]."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'Marker'


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        position: typing.Optional[typing.Tuple[NumberType, NumberType]] = None,
        icon: typing.Optional[dict] = None,
        emoji: typing.Optional[str] = None,
        iconify: typing.Optional[str] = None,
        iconSize: typing.Optional[NumberType] = None,
        iconColor: typing.Optional[str] = None,
        iconAnchor: typing.Optional[typing.Tuple[NumberType, NumberType]] = None,
        iconOptions: typing.Optional[dict] = None,
        popup: typing.Optional[str] = None,
        tooltip: typing.Optional[str] = None,
        draggable: typing.Optional[bool] = None,
        opacity: typing.Optional[NumberType] = None,
        zIndexOffset: typing.Optional[NumberType] = None,
        rotationAngle: typing.Optional[NumberType] = None,
        rotateWithMap: typing.Optional[bool] = None,
        n_clicks: typing.Optional[NumberType] = None,
        n_drags: typing.Optional[NumberType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'className', 'draggable', 'emoji', 'icon', 'iconAnchor', 'iconColor', 'iconOptions', 'iconSize', 'iconify', 'n_clicks', 'n_drags', 'opacity', 'popup', 'position', 'rotateWithMap', 'rotationAngle', 'style', 'tooltip', 'zIndexOffset']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'className', 'draggable', 'emoji', 'icon', 'iconAnchor', 'iconColor', 'iconOptions', 'iconSize', 'iconify', 'n_clicks', 'n_drags', 'opacity', 'popup', 'position', 'rotateWithMap', 'rotationAngle', 'style', 'tooltip', 'zIndexOffset']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(Marker, self).__init__(children=children, **args)

setattr(Marker, "__init__", _explicitize_args(Marker.__init__))
