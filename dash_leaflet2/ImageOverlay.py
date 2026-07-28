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


class ImageOverlay(Component):
    """An ImageOverlay component.
ImageOverlay drapes a single static image over a geographic bounding box. With `editable`
it gains a TextMarker-style transform control system: click to select, drag to move, a corner
handle to resize (scaling the bounds about the `anchor`), and a top handle to rotate (a visual
CSS rotation pivoting at the `anchor`). The white anchor dot marks where the image is pinned.
`bounds`, `rotation`, and `selected` round-trip back to Dash. Wraps Leaflet 2's ImageOverlay.

Keyword arguments:

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- alt (string; optional):
    Alt-text / title for the image element.

- anchor (a value equal to: 'center', 'left', 'right', 'bottom', 'top', 'top-left', 'top-right', 'bottom-left', 'bottom-right'; default 'center'):
    Which point of the image is the rotation pivot + resize anchor +
    where the white anchor dot is drawn. One of center | top-left |
    top | top-right | left | right | bottom-left | bottom |
    bottom-right. @default \"center\". [MUTABLE].

- bounds (dict with strings as keys and values of type list of 2 elements: [number, number]; default [[0, 0], [0, 0]]):
    Geographic bounds the image is stretched to, `[[south, west],
    [north, east]]`. Two-way when `editable`: dragging / resizing
    writes it back. [MUTABLE].

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- crossOrigin (string; optional):
    Adds the `crossOrigin` attribute to the img element. Pass
    \"anonymous\" to make the image load CORS-mode so canvas captures
    (map screenshots / html2canvas) can read the pixels. The host must
    answer with Access-Control-Allow-Origin or the image fails to load
    entirely — leave unset for hosts you don't control.
    \"use-credentials\" and \"\" are also valid. Construction-time
    only.

- editable (boolean; default False):
    Enable the on-map transform controls: click to select, then drag
    to move, drag the corner handle to resize, and the top handle to
    rotate. @default False.

- interactive (boolean; default False):
    If True, the image is wrapped in an interactive layer that fires
    click events. Forced on when `editable`.

- n_clicks (number; optional):
    Number of times the image has been clicked. [READONLY].

- n_transforms (number; optional):
    Bumped on each drag-move / resize commit. [READONLY].

- opacity (number; default 1):
    Layer opacity, 0..1. [MUTABLE].

- rotation (number; default 0):
    Visual rotation in degrees, CW. Applied as a CSS transform
    pivoting at the `anchor` (Leaflet's ImageOverlay has no native
    geographic rotation, so the image's `bounds` stay axis-aligned and
    only the rendered pixels rotate). The rotate handle writes it
    back. [MUTABLE].

- selected (boolean; optional):
    Whether the transform chrome (outline + resize/rotate handles) is
    shown. Two-way: clicking the image selects it, a map-background
    click clears it. Only meaningful when `editable`. [MUTABLE].

- url (string; default ''):
    URL of the image. [MUTABLE].

- zIndex (number; optional):
    Explicit z-index for the overlay pane. [MUTABLE]."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'ImageOverlay'


    def __init__(
        self,
        url: typing.Optional[str] = None,
        bounds: typing.Optional[typing.Dict[typing.Union[str, float, int], typing.Tuple[NumberType, NumberType]]] = None,
        opacity: typing.Optional[NumberType] = None,
        alt: typing.Optional[str] = None,
        crossOrigin: typing.Optional[str] = None,
        interactive: typing.Optional[bool] = None,
        zIndex: typing.Optional[NumberType] = None,
        editable: typing.Optional[bool] = None,
        selected: typing.Optional[bool] = None,
        rotation: typing.Optional[NumberType] = None,
        anchor: typing.Optional[Literal["center", "left", "right", "bottom", "top", "top-left", "top-right", "bottom-left", "bottom-right"]] = None,
        n_clicks: typing.Optional[NumberType] = None,
        n_transforms: typing.Optional[NumberType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'alt', 'anchor', 'bounds', 'className', 'crossOrigin', 'editable', 'interactive', 'n_clicks', 'n_transforms', 'opacity', 'rotation', 'selected', 'style', 'url', 'zIndex']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'alt', 'anchor', 'bounds', 'className', 'crossOrigin', 'editable', 'interactive', 'n_clicks', 'n_transforms', 'opacity', 'rotation', 'selected', 'style', 'url', 'zIndex']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(ImageOverlay, self).__init__(**args)

setattr(ImageOverlay, "__init__", _explicitize_args(ImageOverlay.__init__))
