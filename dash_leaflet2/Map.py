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


class Map(Component):
    """A Map component.
Map is the root Leaflet 2 map container. It owns the Leaflet map instance and
provides it to child layers (TileLayer, Marker) through React context. Set the
height via the `style` prop.

Keyword arguments:

- children (a list of or a singular dash component, string or number; optional):
    Child layers (TileLayer, Marker, ...) rendered into this map.

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- attributionControl (boolean; default True):
    Whether Leaflet 2's built-in attribution control is added to the
    map. Default True (matches Leaflet's default). Set False when you
    want to mount a `dl2.AttributionControl` child and control
    position / prefix yourself — same convention as dash-leaflet's
    `attributionControl=False` + `dl.AttributionControl(...)` pairing.
    Constructor-only — changing it after the map is built has no
    effect.

- bearing (number; optional):
    Map rotation in degrees (CW from north). 0 = north up. Implemented
    as a CSS `transform: rotate()` on the leaflet map pane — the same
    technique `leaflet-rotate` uses on Leaflet 1.x. Leaflet 2 has no
    native rotation, so we build it the same way.  **Important caveat
    (CSS rotation, not coordinate-correct rotation):** Tiles, markers,
    polygons, and zoom math are computed in Leaflet's un-rotated
    coordinate space and the whole pane is then rotated visually. That
    works perfectly for read-only views and follow-camera flight/walk
    sims (you look at the map; the camera tracks the player). It
    breaks subtly for INTERACTIVE drawing at non-zero bearing — a
    click lands at the visually-rotated screen position, which is no
    longer the same latlng Leaflet would resolve from the bare event
    coords. For drawing, keep bearing = 0. A fully coordinate-correct
    rotation is a much larger project (essentially porting
    leaflet-rotate's coord math to v2).  [MUTABLE].

- boxZoom (boolean; default True):
    Shift-drag box-zoom selection. Default True. [MUTABLE].

- center (list of 2 elements: [number, number]; default [51.505, -0.09]):
    Initial map center as [lat, lng]. Updating it from a callback
    re-centers the map. [MUTABLE].

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- clickData (dict; optional):
    Data from the most recent map click: { latlng: [lat, lng] }.
    [READONLY].

    `clickData` is a dict with keys:

    - latlng (list of 2 elements: [number, number]; required)

- doubleClickZoom (boolean; default True):
    Double-click-to-zoom. Default True. [MUTABLE].

- dragging (boolean; default True):
    Mouse / pointer drag panning. Default True. [MUTABLE].

- flyTo (dict; optional):
    Python -> map: trigger a smooth viewport transition. The map calls
    the Leaflet 2 method indicated by `transition` and ignores the
    prop until `n_clicks` bumps again (matching `drawToolbar` /
    `editToolbar` / `featureUpdate` — needed so consecutive identical
    payloads still register as changes).  Shape:   {     transition:
    'setView' | 'flyTo' | 'panTo' | 'fitBounds' | 'flyToBounds' |
    'panInsideBounds',     center?: [lat, lng],          # for setView
    / flyTo / panTo     zoom?:   number,              # optional zoom
    target (setView / flyTo)     bounds?: [[s, w], [n, e]],    # for
    fitBounds / flyToBounds / panInsideBounds     options?: object,
    # passed straight to the Leaflet method
    # (duration, easeLinearity, animate, paddingTopLeft, ...)
    n_clicks: int,   }  `flyTo` / `flyToBounds` give the smooth
    glide-and-zoom motion; `setView` is instant; `panTo` glides
    without changing zoom. See the /flyto showcase. [MUTABLE].

    `flyTo` is a dict with keys:

    - transition (a value equal to: 'flyTo', 'setView', 'panTo', 'fitBounds', 'flyToBounds', 'panInsideBounds'; optional)

    - center (list of 2 elements: [number, number]; optional)

    - zoom (number; optional)

    - bounds (list of 2 elements: [list of 2 elements: [number, number], list of 2 elements: [number, number]]; optional)

    - options (dict with strings as keys and values of type boolean | number | string | dict | list; optional)

    - n_clicks (number; required)

- keyboard (boolean; default True):
    Whether the map can be panned / zoomed with the keyboard (arrow
    keys + `+`/`-`). Default True. [MUTABLE].

- maxBounds (list of 2 elements: [list of 2 elements: [number, number], list of 2 elements: [number, number]]; optional):
    Geographic bounds the map's view is constrained inside, as
    `[[south, west], [north, east]]`. Panning past the edges is
    bounced back. [MUTABLE].

- maxZoom (number; optional):
    Maximum zoom level the user can zoom in to. When a TileLayer also
    sets `maxZoom`, Leaflet uses the *smaller* of the two. [MUTABLE].

- minZoom (number; optional):
    Minimum zoom level the user can zoom out to. When a TileLayer also
    sets `minZoom`, Leaflet uses the *larger* of the two (the most
    restrictive value wins). [MUTABLE].

- n_moveend (number; optional):
    Counter bumped on every `moveend` event (a pan / flyTo / fit
    completes). `n_moveend < n_movestart` means a transition is
    currently running. [READONLY].

- n_movestart (number; optional):
    Counter bumped on every `movestart` event (a pan / flyTo / fit
    begins). Pair with `n_moveend` to drive a \"flying…\" indicator.
    [READONLY].

- pinchZoom (boolean; default True):
    Pinch-to-zoom on touch devices. Default True. In Leaflet 1.x this
    was called `touchZoom`; in v2 it's `pinchZoom`. [MUTABLE].

- preferCanvas (boolean; default False):
    If True, render all vector layers through the Canvas renderer
    (preferred for dense point sets). [READONLY].

- scrollWheelZoom (boolean; default True):
    Mouse-wheel zoom. Default True. [MUTABLE].

- tapHold (boolean; optional):
    Mobile-safari tap-hold-to-contextmenu emulation. Defaults to True
    on mobile Safari only. [MUTABLE].

- viewport (dict; optional):
    Current view state, written back by the map on every
    moveend/zoomend as { center: [lat, lng], zoom, bearing, bounds: {
    north, south, east, west } }. Read this in callbacks. [READONLY].

    `viewport` is a dict with keys:

    - center (list of 2 elements: [number, number]; required)

    - zoom (number; required)

    - bearing (number; required)

    - bounds (dict; required)

        `bounds` is a dict with keys:

        - north (number; required)

        - south (number; required)

        - east (number; required)

        - west (number; required)

- zoom (number; default 13):
    Initial zoom level. Updating it from a callback changes the zoom.
    [MUTABLE].

- zoomControl (boolean; default True):
    Whether Leaflet's built-in +/- zoom buttons control is added.
    Default True. Constructor-only — changing it after the map is
    built has no effect."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'Map'
    ViewportBounds = TypedDict(
        "ViewportBounds",
            {
            "north": NumberType,
            "south": NumberType,
            "east": NumberType,
            "west": NumberType
        }
    )

    Viewport = TypedDict(
        "Viewport",
            {
            "center": typing.Tuple[NumberType, NumberType],
            "zoom": NumberType,
            "bearing": NumberType,
            "bounds": "ViewportBounds"
        }
    )

    ClickData = TypedDict(
        "ClickData",
            {
            "latlng": typing.Tuple[NumberType, NumberType]
        }
    )

    FlyTo = TypedDict(
        "FlyTo",
            {
            "transition": NotRequired[Literal["flyTo", "setView", "panTo", "fitBounds", "flyToBounds", "panInsideBounds"]],
            "center": NotRequired[typing.Tuple[NumberType, NumberType]],
            "zoom": NotRequired[NumberType],
            "bounds": NotRequired[typing.Tuple[typing.Tuple[NumberType, NumberType], typing.Tuple[NumberType, NumberType]]],
            "options": NotRequired[typing.Dict[typing.Union[str, float, int], typing.Any]],
            "n_clicks": NumberType
        }
    )


    def __init__(
        self,
        children: typing.Optional[ComponentType] = None,
        center: typing.Optional[typing.Tuple[NumberType, NumberType]] = None,
        zoom: typing.Optional[NumberType] = None,
        minZoom: typing.Optional[NumberType] = None,
        maxZoom: typing.Optional[NumberType] = None,
        maxBounds: typing.Optional[typing.Tuple[typing.Tuple[NumberType, NumberType], typing.Tuple[NumberType, NumberType]]] = None,
        zoomControl: typing.Optional[bool] = None,
        keyboard: typing.Optional[bool] = None,
        dragging: typing.Optional[bool] = None,
        scrollWheelZoom: typing.Optional[bool] = None,
        doubleClickZoom: typing.Optional[bool] = None,
        boxZoom: typing.Optional[bool] = None,
        pinchZoom: typing.Optional[bool] = None,
        tapHold: typing.Optional[bool] = None,
        bearing: typing.Optional[NumberType] = None,
        viewport: typing.Optional["Viewport"] = None,
        clickData: typing.Optional["ClickData"] = None,
        preferCanvas: typing.Optional[bool] = None,
        attributionControl: typing.Optional[bool] = None,
        flyTo: typing.Optional["FlyTo"] = None,
        n_movestart: typing.Optional[NumberType] = None,
        n_moveend: typing.Optional[NumberType] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['children', 'id', 'attributionControl', 'bearing', 'boxZoom', 'center', 'className', 'clickData', 'doubleClickZoom', 'dragging', 'flyTo', 'keyboard', 'maxBounds', 'maxZoom', 'minZoom', 'n_moveend', 'n_movestart', 'pinchZoom', 'preferCanvas', 'scrollWheelZoom', 'style', 'tapHold', 'viewport', 'zoom', 'zoomControl']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['children', 'id', 'attributionControl', 'bearing', 'boxZoom', 'center', 'className', 'clickData', 'doubleClickZoom', 'dragging', 'flyTo', 'keyboard', 'maxBounds', 'maxZoom', 'minZoom', 'n_moveend', 'n_movestart', 'pinchZoom', 'preferCanvas', 'scrollWheelZoom', 'style', 'tapHold', 'viewport', 'zoom', 'zoomControl']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args if k != 'children'}

        super(Map, self).__init__(children=children, **args)

setattr(Map, "__init__", _explicitize_args(Map.__init__))
