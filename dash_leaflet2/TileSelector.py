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


class TileSelector(Component):
    """A TileSelector component.
TileSelector adds a toggle button to the map. While active, the cursor becomes a
crosshair, a dashed outline tracks the tile under the cursor at the current map zoom,
and clicking a tile adds/removes it from the multi-select. Holding Shift while dragging
captures every tile inside the resulting box. Selections persist across zooms (each
tile is keyed by z/x/y). Place it as a child of dl2.Map.

Keyword arguments:

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- className (string; optional):
    Often-used CSS class name(s) for the root element.

- hoverColor (string; default '#fa5252'):
    Color of the hover outline.

- position (string; default 'topleft'):
    \"topleft\" | \"topright\" | \"bottomleft\" | \"bottomright\".

- selectedColor (string; default '#228be6'):
    Stroke + fill color of selected-tile rectangles (and the box-drag
    preview).

- selectedTiles (list of dicts; optional):
    Currently selected tiles, each `{z, x, y, url, bounds: [s, w, n,
    e]}`. Two-way: clicks + shift-drag add/remove tiles (component →
    Python); Python callbacks can also push (e.g. a Clear button
    writes `[]`). [MUTABLE].

    `selectedTiles` is a list of dicts with keys:

    - z (number; required)

    - x (number; required)

    - y (number; required)

- tileUrl (string; default 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'):
    Tile URL template — same `{s}/{z}/{x}/{y}` form as a TileLayer
    URL."""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_leaflet2'
    _type = 'TileSelector'
    SelectedTiles = TypedDict(
        "SelectedTiles",
            {
            "z": NumberType,
            "x": NumberType,
            "y": NumberType
        }
    )


    def __init__(
        self,
        position: typing.Optional[str] = None,
        tileUrl: typing.Optional[str] = None,
        selectedTiles: typing.Optional[typing.Sequence[typing.Union["SelectedTiles"]]] = None,
        hoverColor: typing.Optional[str] = None,
        selectedColor: typing.Optional[str] = None,
        id: typing.Optional[typing.Union[str, dict]] = None,
        className: typing.Optional[str] = None,
        style: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'className', 'hoverColor', 'position', 'selectedColor', 'selectedTiles', 'style', 'tileUrl']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'className', 'hoverColor', 'position', 'selectedColor', 'selectedTiles', 'style', 'tileUrl']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(TileSelector, self).__init__(**args)

setattr(TileSelector, "__init__", _explicitize_args(TileSelector.__init__))
