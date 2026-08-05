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


class EditControl(Component):
    """An EditControl component.
EditControl renders a Leaflet draw/edit toolbar (native v2 — leaflet-draw is Leaflet
1-only). Place it as a child of dl2.Map. Shapes are kept in an internal FeatureGroup and
surfaced via the `geojson` prop. The Edit section appears only when at least one shape
exists. A contextual sub-toolbar appears while a tool is active (Finish / Delete last
point / Cancel during draw; Save / Cancel during edit; Clear all / Cancel during remove).

Keyword arguments:

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- action (dict; optional):
    The most recent action, dash-leaflet-shaped:   {layer_type:
    'polygon', type: 'created'|'edited'|'deleted', n_actions: int}
    Bumps every time something happens — useful as a sole Input for
    \"anything changed\". [READONLY].

    `action` is a dict with keys:

    - layer_type (string; optional)

    - type (string; optional)

    - n_actions (number; required)

- activeMode (a value equal to: 'edit', 'remove'; optional):
    The currently active edit/remove mode, or None. [READONLY].

- activeTool (a value equal to: 'text', 'circle', 'marker', 'polyline', 'polygon', 'rectangle', 'circlemarker'; optional):
    The currently active draw tool, or None. Emitted whenever a tool
    is activated or cleared — pages can use this to open a popover
    when the user clicks a draw icon (mirrors the `/easy-button`
    popover-on-button-click pattern). [READONLY].

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- draw (dict with strings as keys and values of type boolean; optional):
    Per-tool enable/disable for the Draw section, e.g. {rectangle:
    False, marker: True}. Tools not listed default to enabled.

- drawToolbar (dict; optional):
    Python -> control: setting this prop activates a draw tool or
    dispatches an action on the currently active tool. Bump `n_clicks`
    to ensure the prop registers as changed. Shape: {mode?: tool name,
    action?: 'finish'|'cancel'|'delete last point', n_clicks: int}.
    [MUTABLE].

    `drawToolbar` is a dict with keys:

    - mode (a value equal to: 'text', 'circle', 'marker', 'polyline', 'polygon', 'rectangle', 'circlemarker'; optional)

    - action (string; optional)

    - n_clicks (number; optional)

- edit (dict with strings as keys and values of type boolean; optional):
    Per-mode enable/disable for the Edit section, e.g. {remove:
    False}. Modes not listed default to enabled. The Edit section only
    appears once at least one shape exists.

- editToolbar (dict; optional):
    Python -> control: enter edit/remove mode or dispatch
    save/cancel/clear-all. Bump `n_clicks` to ensure the prop changes.
    Shape: {mode?: 'edit'|'remove', action?: 'save'|'cancel'|'clear
    all', n_clicks: int}. [MUTABLE].

    `editToolbar` is a dict with keys:

    - mode (a value equal to: 'edit', 'remove'; optional)

    - action (string; optional)

    - n_clicks (number; optional)

- featureClick (dict; optional):
    The most recent feature click. Only fires while `editMode ===
    'edit'` — clicks on features in normal view mode do NOT emit this.
    The click is NOT propagated to the map (we set
    `bubblingMouseEvents: False`) so a Map.clickData callback only
    fires on empty-map clicks. Shape: {id, layerType, n_clicks}.
    [READONLY].

    `featureClick` is a dict with keys:

    - id (string; required)

    - layerType (string; required)

    - n_clicks (number; required)

- featureUpdate (dict; optional):
    Python -> control: update or remove a single feature by its
    _dl2_id. Bump `n_clicks` each call to ensure the prop registers as
    changed. Shape:   {id, style?, properties?, remove?, n_clicks}   -
    style:      Leaflet path style options to apply via setStyle
    (color, weight, fillOpacity, ...)   - properties: merged into the
    feature's properties (e.g. {name: \"Lighthouse\"})   - remove:
    drop the feature from the FeatureGroup [MUTABLE].

    `featureUpdate` is a dict with keys:

    - id (string; required)

    - style (dict; optional)

    - properties (dict; optional)

    - remove (boolean; optional)

    - n_clicks (number; required)

- geojson (dict; optional):
    All currently drawn shapes as a GeoJSON FeatureCollection.
    [READONLY].

- lastAction (dict; optional):
    Brief metadata for the most recent draw / delete event (legacy
    shape). [READONLY].

- measurementSystem (a value equal to: 'metric', 'imperial'; default 'metric'):
    Unit system for the live drawing previews — drives the radius
    readout in the circle tool and the area readout in the rectangle
    tool.  - 'metric' (default): meters / kilometers for distance; m²
    / hectares / km² for area. - 'imperial' (US customary): feet /
    miles for distance; ft² / acres / mi² for area.  Each formatter
    auto-picks the largest readable unit for the current magnitude
    (e.g. a 5 km radius reads \"5.00 km\"; a 50 m radius reads \"50
    m\"). [MUTABLE].

- n_drawn (number; optional):
    Total shapes drawn since mount (decrements on delete). [READONLY].

- position (string; default 'topleft'):
    Control position: \"topleft\" | \"topright\" | \"bottomleft\" |
    \"bottomright\".

- shapeOptions (dict; default { color: '#2f9e44', weight: 3, fillOpacity: 0.2 }):
    Path style applied to drawn vectors (color, weight, fillOpacity,
    ...).

- showMeasurementTooltips (boolean; default False):
    When True, every committed shape gets a permanent Leaflet tooltip
    showing its measured area (rectangle / circle / polygon) or length
    (polyline), formatted with the configured `measurementSystem`.
    [READONLY]."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'EditControl'
    DrawToolbar = TypedDict(
        "DrawToolbar",
            {
            "mode": NotRequired[Literal["text", "circle", "marker", "polyline", "polygon", "rectangle", "circlemarker"]],
            "action": NotRequired[str],
            "n_clicks": NotRequired[NumberType]
        }
    )

    EditToolbar = TypedDict(
        "EditToolbar",
            {
            "mode": NotRequired[Literal["edit", "remove"]],
            "action": NotRequired[str],
            "n_clicks": NotRequired[NumberType]
        }
    )

    Action = TypedDict(
        "Action",
            {
            "layer_type": NotRequired[str],
            "type": NotRequired[str],
            "n_actions": NumberType
        }
    )

    FeatureClick = TypedDict(
        "FeatureClick",
            {
            "id": str,
            "layerType": str,
            "n_clicks": NumberType
        }
    )

    FeatureUpdate = TypedDict(
        "FeatureUpdate",
            {
            "id": str,
            "style": NotRequired[dict],
            "properties": NotRequired[dict],
            "remove": NotRequired[bool],
            "n_clicks": NumberType
        }
    )


    def __init__(
        self,
        position: typing.Optional[str] = None,
        draw: typing.Optional[typing.Dict[typing.Union[str, float, int], bool]] = None,
        edit: typing.Optional[typing.Dict[typing.Union[str, float, int], bool]] = None,
        shapeOptions: typing.Optional[dict] = None,
        measurementSystem: typing.Optional[Literal["metric", "imperial"]] = None,
        drawToolbar: typing.Optional["DrawToolbar"] = None,
        editToolbar: typing.Optional["EditToolbar"] = None,
        geojson: typing.Optional[dict] = None,
        n_drawn: typing.Optional[NumberType] = None,
        lastAction: typing.Optional[dict] = None,
        action: typing.Optional["Action"] = None,
        activeTool: typing.Optional[Literal["text", "circle", "marker", "polyline", "polygon", "rectangle", "circlemarker"]] = None,
        activeMode: typing.Optional[Literal["edit", "remove"]] = None,
        featureClick: typing.Optional["FeatureClick"] = None,
        featureUpdate: typing.Optional["FeatureUpdate"] = None,
        showMeasurementTooltips: typing.Optional[bool] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'action', 'activeMode', 'activeTool', 'className', 'draw', 'drawToolbar', 'edit', 'editToolbar', 'featureClick', 'featureUpdate', 'geojson', 'lastAction', 'measurementSystem', 'n_drawn', 'position', 'shapeOptions', 'showMeasurementTooltips', 'style']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'action', 'activeMode', 'activeTool', 'className', 'draw', 'drawToolbar', 'edit', 'editToolbar', 'featureClick', 'featureUpdate', 'geojson', 'lastAction', 'measurementSystem', 'n_drawn', 'position', 'shapeOptions', 'showMeasurementTooltips', 'style']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(EditControl, self).__init__(**args)

setattr(EditControl, "__init__", _explicitize_args(EditControl.__init__))
