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


class MiniMap(Component):
    """A MiniMap component.
MiniMap adds a small overview map in a corner of the main map. The overview tracks
the main map's center + zoom (with a configurable offset) and draws a rectangle showing
the main viewport. Click the corner toggle to collapse/expand. Place it as a child of
dl2.Map.
*
Native Leaflet 2 — `leaflet-minimap` (the Leaflet 1 plugin) does not run on v2.

Keyword arguments:

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- aimingRectOptions (dict; default {        color: '#3388ff',        weight: 1,        fillColor: '#3388ff',        fillOpacity: 0.15,        interactive: False,    }):
    Leaflet path options for the aiming rectangle that shows the main
    map's viewport bounds on the minimap. Defaults to a translucent
    blue stroke.

- attribution (string; default ''):
    Attribution shown by the inner minimap. Empty by default — the
    main map already attributes.

- centerFixed (list of 2 elements: [number, number]; optional):
    When set to `[lat, lng]`, the inner minimap anchors on this point
    instead of tracking the main map's center. The aiming rectangle
    still reflects the main map's bounds — so the rectangle drifts
    off-minimap if the main map is panned far from the fixed point.
    Pass `None` (or omit) to follow the main map. Useful for
    \"return-home\" style affordances, where the minimap pins on a
    player / marker and clicking it (see `n_clicks`) snaps the main
    map back to them. [MUTABLE].

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- height (number; default 150):
    Expanded height in pixels. Default 150.

- minimized (boolean; optional):
    Whether the minimap starts (or currently is) minimized. Two-way:
    setting it from a Python callback collapses/expands the minimap;
    the user clicking the toggle button also writes it back.
    [MUTABLE].

- n_clicks (number; default 0):
    Number of times the user has clicked anywhere on the inner minimap
    (excluding the corner expand/collapse toggle). Increments per
    click — pair with `prevent_initial_call=True` to use the minimap
    as a button. [READONLY].

- position (a value equal to: 'topleft', 'topright', 'bottomleft', 'bottomright'; default 'bottomright'):
    Control position: 'topleft' | 'topright' | 'bottomleft' |
    'bottomright'. Default 'bottomright'.

- toggleDisplay (boolean; default True):
    Show the [⤡] toggle button. Default True.

- url (string; default 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'):
    Tile URL template for the inner minimap basemap. Defaults to OSM.

- width (number; default 150):
    Expanded width in pixels. Default 150.

- zoomLevelOffset (number; default -5):
    Zoom-level offset from the main map (negative = zoomed out further
    than the main). Default -5: a 150x150 minimap shows the main map's
    neighbourhood."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'MiniMap'


    def __init__(
        self,
        position: typing.Optional[Literal["topleft", "topright", "bottomleft", "bottomright"]] = None,
        url: typing.Optional[str] = None,
        attribution: typing.Optional[str] = None,
        width: typing.Optional[NumberType] = None,
        height: typing.Optional[NumberType] = None,
        zoomLevelOffset: typing.Optional[NumberType] = None,
        toggleDisplay: typing.Optional[bool] = None,
        minimized: typing.Optional[bool] = None,
        aimingRectOptions: typing.Optional[dict] = None,
        centerFixed: typing.Optional[typing.Tuple[NumberType, NumberType]] = None,
        n_clicks: typing.Optional[NumberType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'aimingRectOptions', 'attribution', 'centerFixed', 'className', 'height', 'minimized', 'n_clicks', 'position', 'style', 'toggleDisplay', 'url', 'width', 'zoomLevelOffset']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'aimingRectOptions', 'attribution', 'centerFixed', 'className', 'height', 'minimized', 'n_clicks', 'position', 'style', 'toggleDisplay', 'url', 'width', 'zoomLevelOffset']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(MiniMap, self).__init__(**args)

setattr(MiniMap, "__init__", _explicitize_args(MiniMap.__init__))
