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


class KeyboardControl(Component):
    """A KeyboardControl component.
KeyboardControl installs a window-level keyboard listener that drives map
rotation and pan. Place it as a child of <Map>. No DOM is rendered — it's a
pure side-effect component.
*
Default behavior:
  - Arrow keys rotate the map bearing (5° / press by default)
  - Cmd / Ctrl + Arrow keys pan the map (Leaflet's built-in arrow-key panning
    is suppressed by `map.keyboard.disable()` so the two don't both fire)
*
This makes the page feel like a flight sim: the arrows turn the camera, the
modifier is the "manual pan" escape hatch. Pages can flip the bindings by
passing a custom `keymap`.
*
Listens on `window`, not the map container — so a user pressing arrows while
the map div doesn't have focus still rotates. Pages with form inputs should
either set `enabled=false` while the form is focused or override the keymap.

Keyword arguments:

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- bearingStep (number; default 5):
    Degrees of map bearing change per ArrowLeft / ArrowRight keypress.
    Default 5.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- enabled (boolean; default True):
    Whether keyboard input is processed. When `False`, no key handler
    is installed. Useful for disabling controls while a modal/form is
    focused. [MUTABLE].

- keymap (dict with strings as keys and values of type string; optional):
    Direction map: each property holds the action ('rotate-cw',
    'rotate-ccw', 'pan-up', 'pan-down', 'pan-left', 'pan-right')
    triggered by a given key + modifier combination. Defaults to:
    ArrowLeft        → rotate-ccw  (turn camera left)   ArrowRight
    → rotate-cw   (turn camera right)   ArrowUp          → rotate-ccw
    (same — feels natural for flight sims)   ArrowDown        →
    rotate-cw   Cmd|Ctrl+ArrowLeft   → pan-left   Cmd|Ctrl+ArrowRight
    → pan-right   Cmd|Ctrl+ArrowUp     → pan-up   Cmd|Ctrl+ArrowDown
    → pan-down  Pages can override individual entries (e.g. flight
    sims that want ArrowUp/Down to be throttle, not rotation) by
    passing a partial object.

- lastKey (dict; optional):
    The most recent key + action processed, as { key, action,
    modifier, ts }. [READONLY].

    `lastKey` is a dict with keys:

    - key (string; required)

    - action (string; required)

    - modifier (boolean; required)

    - ts (number; required)

- n_pans (number; optional):
    Number of pan keypresses processed. [READONLY].

- n_rotations (number; optional):
    Number of bearing changes emitted (each rotate keypress
    increments). Useful as the sole Input for \"did the user
    rotate?\". [READONLY].

- panStep (number; default 80):
    Pixels of map pan per Cmd+Arrow / Ctrl+Arrow keypress. Default 80
    (matches Leaflet's own keyboard panOffset)."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'KeyboardControl'
    LastKey = TypedDict(
        "LastKey",
            {
            "key": str,
            "action": str,
            "modifier": bool,
            "ts": NumberType
        }
    )


    def __init__(
        self,
        enabled: typing.Optional[bool] = None,
        bearingStep: typing.Optional[NumberType] = None,
        panStep: typing.Optional[NumberType] = None,
        keymap: typing.Optional[typing.Dict[typing.Union[str, float, int], str]] = None,
        n_rotations: typing.Optional[NumberType] = None,
        n_pans: typing.Optional[NumberType] = None,
        lastKey: typing.Optional["LastKey"] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'bearingStep', 'className', 'enabled', 'keymap', 'lastKey', 'n_pans', 'n_rotations', 'panStep', 'style']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'bearingStep', 'className', 'enabled', 'keymap', 'lastKey', 'n_pans', 'n_rotations', 'panStep', 'style']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(KeyboardControl, self).__init__(**args)

setattr(KeyboardControl, "__init__", _explicitize_args(KeyboardControl.__init__))
