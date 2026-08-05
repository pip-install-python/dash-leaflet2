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


class TextMarker(Component):
    """A TextMarker component.
TextMarker is editable, draggable, styleable text placed on the map like a Marker. Give it
a `position` and `text`; drag to move, double-click to edit, and (when `selected`) use the
on-canvas resize / rotate handles and the contextual toolbar to restyle it. Position, text,
rotation, font size, and color all round-trip back to Dash. When `position` is omitted the
label spawns at the center of the current viewport. Place it as a child of dl2.Map.

Keyword arguments:

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- anchor (a value equal to: 'center', 'left', 'right', 'bottom', 'top', 'top-left', 'top-right', 'bottom-left', 'bottom-right'; default 'center'):
    Which point of the text box sits on `position`. One of center |
    top-left | top | top-right | left | right | bottom-left | bottom |
    bottom-right. @default \"center\".

- backgroundColor (string; default 'transparent'):
    Box background behind the text (\"transparent\" for none).
    Editable from the toolbar. [MUTABLE].

- borderRadius (number; default 6):
    Corner radius of the background pill in px. @default 6.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- color (string; default '#111827'):
    Text color (any CSS color / Mantine var). Editable from the
    toolbar. [MUTABLE].

- draggable (boolean; default True):
    Whether the label can be dragged to a new position. @default True.

- editable (boolean; default True):
    Whether double-click enters inline text edit. @default True.

- fontFamily (string; default 'system-ui, sans-serif'):
    Font family stack, e.g. \"Inter, system-ui, sans-serif\".
    [MUTABLE].

- fontSize (number; default 24):
    Font size in screen px (the resize handle changes this).
    [MUTABLE].

- fontStyle (a value equal to: 'normal', 'italic'; default 'normal'):
    Font style: \"normal\" | \"italic\". [MUTABLE].

- fontWeight (string | number; default 600):
    Font weight (400 / 600 / 700 / \"bold\" …). [MUTABLE].

- n_clicks (number; optional):
    Number of times the label has been clicked. [READONLY].

- n_drags (number; optional):
    Number of times the label has been dragged. [READONLY].

- n_edits (number; optional):
    Bumped on each committed text edit (fires a Dash Input even for
    identical text). [READONLY].

- opacity (number; default 1):
    Caption opacity, 0..1 — fade the whole label in/out (e.g.
    keyframed transitions). @,default,1 [MUTABLE].

- padding (number; default 6):
    Box padding in px (only visible when `backgroundColor` is set).
    [MUTABLE].

- position (list of 2 elements: [number, number]; optional):
    Text anchor as [lat, lng]. Dragging the label writes it back. When
    omitted, the label is created at the current center of the map
    viewport (and that position is emitted back so Python has it).
    [MUTABLE].

- referenceZoom (number; optional):
    The zoom level at which `fontSize` is the literal screen px (only
    used when `scaleWithZoom`). Defaults to the map's zoom when the
    label is created. [MUTABLE].

- rotateWithMap (boolean; default False):
    When True the label rotates together with a rotated map
    (`Map.bearing`); when False (default) it stays upright on screen
    regardless of map bearing — like a Marker.

- rotation (number; default 0):
    Rotation in degrees, CW from upright. The rotate handle changes
    this. [MUTABLE].

- scaleWithZoom (boolean; default False):
    Geographic sizing. When False (default) the label is a constant
    screen-size HUD caption: `fontSize` is literal screen px at every
    zoom (like a Tooltip). When True the label scales with the map —
    its on-screen size grows/shrinks by 2^(zoom − referenceZoom) so it
    keeps a fixed *ground* footprint as the camera flies (like a
    polygon's edge). [MUTABLE].

- selected (boolean; optional):
    Show selection chrome (resize / rotate handles + the style
    toolbar). Two-way: clicking the label sets it True and a
    map-background click clears it, so a host can also drive selection
    from the outside. [MUTABLE].

- showToolbar (boolean; default True):
    Whether the contextual style toolbar is shown while selected.
    @default True.

- text (string; default 'Text'):
    The caption string. Double-click the label to edit it inline; the
    committed text (on blur / Enter) is written back with `n_edits`
    bumped. [MUTABLE]."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'TextMarker'


    def __init__(
        self,
        position: typing.Optional[typing.Tuple[NumberType, NumberType]] = None,
        text: typing.Optional[str] = None,
        anchor: typing.Optional[Literal["center", "left", "right", "bottom", "top", "top-left", "top-right", "bottom-left", "bottom-right"]] = None,
        color: typing.Optional[str] = None,
        backgroundColor: typing.Optional[str] = None,
        fontFamily: typing.Optional[str] = None,
        fontSize: typing.Optional[NumberType] = None,
        fontWeight: typing.Optional[typing.Union[str, NumberType]] = None,
        fontStyle: typing.Optional[Literal["normal", "italic"]] = None,
        padding: typing.Optional[NumberType] = None,
        borderRadius: typing.Optional[NumberType] = None,
        rotation: typing.Optional[NumberType] = None,
        opacity: typing.Optional[NumberType] = None,
        rotateWithMap: typing.Optional[bool] = None,
        scaleWithZoom: typing.Optional[bool] = None,
        referenceZoom: typing.Optional[NumberType] = None,
        draggable: typing.Optional[bool] = None,
        editable: typing.Optional[bool] = None,
        selected: typing.Optional[bool] = None,
        showToolbar: typing.Optional[bool] = None,
        n_clicks: typing.Optional[NumberType] = None,
        n_drags: typing.Optional[NumberType] = None,
        n_edits: typing.Optional[NumberType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'anchor', 'backgroundColor', 'borderRadius', 'className', 'color', 'draggable', 'editable', 'fontFamily', 'fontSize', 'fontStyle', 'fontWeight', 'n_clicks', 'n_drags', 'n_edits', 'opacity', 'padding', 'position', 'referenceZoom', 'rotateWithMap', 'rotation', 'scaleWithZoom', 'selected', 'showToolbar', 'style', 'text']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'anchor', 'backgroundColor', 'borderRadius', 'className', 'color', 'draggable', 'editable', 'fontFamily', 'fontSize', 'fontStyle', 'fontWeight', 'n_clicks', 'n_drags', 'n_edits', 'opacity', 'padding', 'position', 'referenceZoom', 'rotateWithMap', 'rotation', 'scaleWithZoom', 'selected', 'showToolbar', 'style', 'text']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(TextMarker, self).__init__(**args)

setattr(TextMarker, "__init__", _explicitize_args(TextMarker.__init__))
