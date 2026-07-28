"""Named map locations for the documentation examples.

Every live demo used to open on the same patch of Rockport, TX, which made the
documentation read as one map shown twenty-six times. Each example now opens
somewhere different, and this module is the registry that keeps it that way:
pick a `Location` here rather than pasting a literal `center=[lat, lon]`.

Why a registry and not just different literals
----------------------------------------------
Most examples draw *geometry* around their center — polygons, image-overlay
bounds, pan clamps, jittered point clouds. Moving a demo from 28°N to 49°N and
keeping the same degree offsets would squash every shape east-to-west, because a
degree of longitude is ~98 km at Rockport and only ~73 km in Vancouver. So the
helpers below take **kilometres** and convert, which keeps a "3 km box" the same
real-world size wherever it lands.

Usage
-----
    from dl2_locations import VANCOUVER

    dl2.Map(center=VANCOUVER.center, zoom=VANCOUVER.zoom, children=[...])

    # 2 km north, 3 km east of the center
    dl2.Marker(position=VANCOUVER.at(north_km=2, east_km=3))

    # a 12 x 16 km box centred on the city, as [[s, w], [n, e]]
    dl2.ImageOverlay(bounds=VANCOUVER.bounds(6, 8))

Adding an example? Take an unused location from :data:`ALL` — `python
-m dl2_locations` prints which ones are still free by scanning `docs/`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Mean length of a degree of latitude, in km. Good to ~0.1% anywhere, which is
# far tighter than any demo needs.
_KM_PER_DEG_LAT = 111.32


@dataclass(frozen=True)
class Location:
    """A named place a documentation example can open on."""

    key: str
    label: str          # "Vancouver, BC"
    lat: float
    lon: float
    zoom: int
    blurb: str          # one clause on what you're looking at, for page prose

    # ---- basics ----------------------------------------------------------
    @property
    def center(self) -> list[float]:
        """`[lat, lon]` — the shape Leaflet and every dl2 component want."""
        return [self.lat, self.lon]

    @property
    def lonlat(self) -> list[float]:
        """`[lon, lat]` — GeoJSON's axis order, which is the other way round."""
        return [self.lon, self.lat]

    # ---- offsets in real-world units --------------------------------------
    def at(self, north_km: float = 0.0, east_km: float = 0.0) -> list[float]:
        """A point `north_km` / `east_km` from the center, as `[lat, lon]`.

        Longitude is scaled by `cos(lat)`, so the same call describes the same
        ground distance at every location.
        """
        dlat = north_km / _KM_PER_DEG_LAT
        dlon = east_km / (_KM_PER_DEG_LAT * math.cos(math.radians(self.lat)))
        return [round(self.lat + dlat, 6), round(self.lon + dlon, 6)]

    def at_lonlat(self, north_km: float = 0.0, east_km: float = 0.0) -> list[float]:
        """:meth:`at`, in GeoJSON's `[lon, lat]` order."""
        lat, lon = self.at(north_km, east_km)
        return [lon, lat]

    def bounds(self, half_ns_km: float, half_ew_km: float) -> list[list[float]]:
        """A box centred here, as Leaflet's `[[south, west], [north, east]]`."""
        return [
            self.at(-half_ns_km, -half_ew_km),
            self.at(half_ns_km, half_ew_km),
        ]

    def ring(self, points: list[tuple[float, float]]) -> list[list[float]]:
        """Translate a list of `(north_km, east_km)` offsets into `[lat, lon]`.

        Handy for polygons and polylines: describe the shape once in kilometres
        and it renders identically wherever the demo is set.
        """
        return [self.at(n, e) for n, e in points]

    # ---- slippy tiles ------------------------------------------------------
    def tile(self, zoom: int) -> tuple[int, int]:
        """The XYZ tile `(x, y)` containing this location at `zoom`."""
        lat_rad = math.radians(self.lat)
        n = 2 ** zoom
        x = int((self.lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    def tile_key(self, zoom: int) -> str:
        """`"z/x/y"` for this location — the key format the demos use."""
        x, y = self.tile(zoom)
        return f"{zoom}/{x}/{y}"

    def nested_tile_keys(self, start_zoom: int, levels: int = 3) -> list[str]:
        """`levels` tile keys where each is the NW child of the one before.

        `compare-lab` needs genuine ancestor/descendant nesting to exercise its
        cross-zoom association math, and the NW child of `(x, y)` is always
        `(2x, 2y)` — so walking down from one real tile guarantees it.
        """
        x, y = self.tile(start_zoom)
        keys = []
        for i in range(levels):
            keys.append(f"{start_zoom + i}/{x}/{y}")
            x, y = x * 2, y * 2
        return keys


# ---------------------------------------------------------------------------
# The registry
#
# One location per example. Coordinates sit on something worth looking at —
# a harbour, a river confluence, a downtown core — rather than a centroid in a
# suburb, because the demo is the first impression of the component.
# ---------------------------------------------------------------------------

VANCOUVER = Location(
    "vancouver", "Vancouver, BC", 49.2860, -123.1200, 12,
    "Coal Harbour and the downtown peninsula, with the North Shore mountains behind",
)
PORTLAND = Location(
    "portland", "Portland, OR", 45.5202, -122.6742, 12,
    "the Willamette cutting through downtown, bridges every few blocks",
)
NEW_YORK = Location(
    "new_york", "New York, NY", 40.7484, -73.9857, 12,
    "Midtown Manhattan, with the island's grid running to the rivers on both sides",
)
CHICAGO = Location(
    "chicago", "Chicago, IL", 41.8827, -87.6233, 12,
    "the Loop against the Lake Michigan shoreline",
)
DALLAS = Location(
    "dallas", "Dallas, TX", 32.7791, -96.8005, 12,
    "downtown Dallas inside the freeway ring",
)
HOUSTON = Location(
    "houston", "Houston, TX", 29.7589, -95.3677, 12,
    "downtown Houston where the bayou bends",
)
SEATTLE = Location(
    "seattle", "Seattle, WA", 47.6062, -122.3321, 12,
    "downtown between Elliott Bay and Lake Union",
)
SAN_FRANCISCO = Location(
    "san_francisco", "San Francisco, CA", 37.7955, -122.3937, 12,
    "the Embarcadero waterfront and the bay",
)
BOSTON = Location(
    "boston", "Boston, MA", 42.3601, -71.0589, 12,
    "the harbour and the tangle of streets that predate the grid",
)
DENVER = Location(
    "denver", "Denver, CO", 39.7392, -104.9903, 12,
    "downtown Denver with the Front Range to the west",
)
TORONTO = Location(
    "toronto", "Toronto, ON", 43.6426, -79.3871, 12,
    "the waterfront and the islands across the harbour",
)
MONTREAL = Location(
    "montreal", "Montréal, QC", 45.5017, -73.5673, 12,
    "Vieux-Montréal along the St. Lawrence",
)
MIAMI = Location(
    "miami", "Miami, FL", 25.7743, -80.1937, 12,
    "Biscayne Bay, the causeways and the beach barrier island",
)
SAN_DIEGO = Location(
    "san_diego", "San Diego, CA", 32.7157, -117.1611, 12,
    "the natural harbour, with Coronado closing it off",
)
PHILADELPHIA = Location(
    "philadelphia", "Philadelphia, PA", 39.9526, -75.1652, 12,
    "Center City between the Schuylkill and the Delaware",
)
MINNEAPOLIS = Location(
    "minneapolis", "Minneapolis, MN", 44.9778, -93.2650, 12,
    "downtown on the Mississippi, lakes scattered to the southwest",
)
PITTSBURGH = Location(
    "pittsburgh", "Pittsburgh, PA", 40.4406, -79.9959, 12,
    "the Golden Triangle where three rivers meet — unmistakable at any zoom",
)
HONOLULU = Location(
    "honolulu", "Honolulu, HI", 21.3069, -157.8583, 12,
    "Waikīkī, Diamond Head and the reef line",
)
NASHVILLE = Location(
    "nashville", "Nashville, TN", 36.1627, -86.7816, 12,
    "downtown inside the Cumberland's horseshoe bend",
)
AUSTIN = Location(
    "austin", "Austin, TX", 30.2672, -97.7431, 12,
    "downtown along Lady Bird Lake",
)
CHARLESTON = Location(
    "charleston", "Charleston, SC", 32.7833, -79.9333, 12,
    "the peninsula between the Ashley and the Cooper",
)
SAVANNAH = Location(
    "savannah", "Savannah, GA", 32.0776, -81.0912, 15,
    "the historic district's grid of squares — a genuinely walkable street plan",
)
SALT_LAKE_CITY = Location(
    "salt_lake_city", "Salt Lake City, UT", 40.7608, -111.8910, 12,
    "downtown with the Wasatch Range rising immediately east",
)
WASHINGTON_DC = Location(
    "washington_dc", "Washington, DC", 38.8899, -77.0091, 12,
    "the National Mall between the Capitol and the Potomac",
)
NEW_ORLEANS = Location(
    "new_orleans", "New Orleans, LA", 29.9511, -90.0715, 12,
    "the French Quarter inside the Mississippi's crescent",
)

# Not North America. `rotation-basic` has always opened on London — it is the
# canonical Leaflet example view, which is the right nod for the page that
# demonstrates v2's rotation. Registered so the audit knows it is taken.
LONDON = Location(
    "london", "London, UK", 51.5050, -0.0900, 12,
    "the City and the Thames — Leaflet's own canonical example view",
)

ALL: tuple[Location, ...] = (
    VANCOUVER, PORTLAND, NEW_YORK, CHICAGO, DALLAS, HOUSTON,
    SEATTLE, SAN_FRANCISCO, BOSTON, DENVER, TORONTO, MONTREAL,
    MIAMI, SAN_DIEGO, PHILADELPHIA, MINNEAPOLIS, PITTSBURGH, HONOLULU,
    NASHVILLE, AUSTIN, CHARLESTON, SAVANNAH, SALT_LAKE_CITY,
    WASHINGTON_DC, NEW_ORLEANS, LONDON,
)

BY_KEY = {loc.key: loc for loc in ALL}


def _audit() -> None:
    """Print which locations are used by which example, and which are free.

    Scans three places, because the demos are wired three different ways:
    the Python examples import from here, `usage.py` does too, and the
    hooks/CDN showcase pages are driven by a parallel `CITY` table inside
    `assets/leaflet2_maps.js`. Reporting only the first would call Vancouver
    "free" while the home page is sitting on it.
    """
    import re
    from pathlib import Path

    root = Path(__file__).parent
    used: dict[str, list[str]] = {}

    def mark(symbol: str, where: str) -> None:
        if symbol in globals() and where not in used.setdefault(symbol, []):
            used[symbol].append(where)

    for example in sorted((root / "docs").glob("*/example.py")):
        for group in re.findall(r"from dl2_locations import ([A-Z_, ]+)", example.read_text()):
            for symbol in (s.strip() for s in group.split(",")):
                mark(symbol, example.parent.name)

    usage = root / "usage.py"
    if usage.exists():
        for group in re.findall(r"from dl2_locations import ([A-Z_, ]+)", usage.read_text()):
            for symbol in (s.strip() for s in group.split(",")):
                mark(symbol, "usage.py")

    # The JS half: `CITY.<camelCase>` referenced inside a DEMOS builder. Map
    # each camelCase key back to this module's SNAKE_CASE symbol.
    js = root / "assets" / "leaflet2_maps.js"
    if js.exists():
        text = js.read_text()
        demo = "?"
        for line in text.splitlines():
            found = re.search(r'^\s{4}"?([a-zA-Z-]+)"?\(el, L\)', line)
            if found:
                demo = found.group(1)
            for key in re.findall(r"CITY\.([a-zA-Z]+)", line):
                snake = re.sub(r"(?<!^)(?=[A-Z])", "_", key).upper()
                mark(snake, f"{demo} (js)")

    print(f"{len(ALL)} locations registered\n")
    for loc in ALL:
        pages = used.get(loc.key.upper(), [])
        print(f"  {loc.label:<22} {', '.join(pages) if pages else '— free'}")

    free = [loc for loc in ALL if loc.key.upper() not in used]
    print(f"\n{len(ALL) - len(free)} in use, {len(free)} free")
    if free:
        print("Free for a new example: " + ", ".join(loc.key.upper() for loc in free))


if __name__ == "__main__":
    _audit()
