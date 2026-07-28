import React, { useEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import {
    Control,
    DomEvent,
    LatLngBounds,
    Point,
    Rectangle as LeafletRectangle,
} from 'leaflet';
import { useLeafletMap } from '../context';
import { DashComponentProps } from '../props';

// TileSelector lets the user hover-highlight individual basemap tiles and click to
// add/remove them from a multi-select that's reported back to Python. Selections
// persist across zoom levels — each entry is keyed by (z, x, y), so the same tile
// at a different zoom is a different selection. Two ways to add: single click toggles
// one tile, shift+drag captures every tile inside a box. Each entry includes the
// tile's geographic bounds (south, west, north, east) so downstream code can turn the
// selection into GeoJSON without doing its own web-mercator math.

const TILE_SIZE = 256;

type Tile = { z: number; x: number; y: number };
type TileInfo = Tile & {
    url: string;
    /** Tile's geographic bounds as [south, west, north, east] degrees. */
    bounds: [number, number, number, number];
};

const tileKey = (t: Tile) => `${t.z}/${t.x}/${t.y}`;

function fillTileUrl(template: string, z: number, x: number, y: number) {
    return template
        .replace('{s}', 'a')
        .replace('{z}', String(z))
        .replace('{x}', String(x))
        .replace('{y}', String(y));
}

function tileAtLatLng(map: any, latlng: any): Tile {
    const z = map.getZoom();
    const p = map.project(latlng, z);
    return { z, x: Math.floor(p.x / TILE_SIZE), y: Math.floor(p.y / TILE_SIZE) };
}

function tileCornersLatLng(map: any, z: number, x: number, y: number): [any, any] {
    // Use unproject(point, z) so corners are correct at the TILE's zoom, not the map's —
    // lets selections at z=5 stay correctly placed while the map is at z=14 (and vice versa).
    const nw = map.unproject(new Point(x * TILE_SIZE, y * TILE_SIZE), z);
    const se = map.unproject(new Point((x + 1) * TILE_SIZE, (y + 1) * TILE_SIZE), z);
    return [nw, se];
}

function tileBoundsLLBounds(map: any, z: number, x: number, y: number): LatLngBounds {
    const [nw, se] = tileCornersLatLng(map, z, x, y);
    return new LatLngBounds(nw, se);
}

type Props = {
    /** "topleft" | "topright" | "bottomleft" | "bottomright". */
    position?: string;
    /** Tile URL template — same `{s}/{z}/{x}/{y}` form as a TileLayer URL. */
    tileUrl?: string;
    /**
     * Currently selected tiles, each `{z, x, y, url, bounds: [s, w, n, e]}`. Two-way:
     * clicks + shift-drag add/remove tiles (component → Python); Python callbacks can
     * also push (e.g. a Clear button writes `[]`). [MUTABLE]
     */
    selectedTiles?: TileInfo[];
    /** Color of the hover outline. */
    hoverColor?: string;
    /** Stroke + fill color of selected-tile rectangles (and the box-drag preview). */
    selectedColor?: string;
} & DashComponentProps;

/**
 * TileSelector adds a toggle button to the map. While active, the cursor becomes a
 * crosshair, a dashed outline tracks the tile under the cursor at the current map zoom,
 * and clicking a tile adds/removes it from the multi-select. Holding Shift while dragging
 * captures every tile inside the resulting box. Selections persist across zooms (each
 * tile is keyed by z/x/y). Place it as a child of dl2.Map.
 */
const TileSelector = ({
    position = 'topleft',
    tileUrl = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    selectedTiles = [],
    hoverColor = '#fa5252',
    selectedColor = '#228be6',
    setProps,
}: Props) => {
    const map = useLeafletMap();
    const containerRef = useRef<HTMLDivElement | null>(null);
    if (!containerRef.current) containerRef.current = document.createElement('div');
    const [active, setActive] = useState(false);
    const hoverRectRef = useRef<LeafletRectangle | null>(null);
    const selectedRectsRef = useRef<Map<string, LeafletRectangle>>(new Map());

    // Mirror of selectedTiles for handlers — refs avoid closure-staleness when the user
    // clicks (or shift-drags) faster than the prop round-trip can re-attach handlers.
    const tilesRef = useRef<TileInfo[]>(selectedTiles || []);
    tilesRef.current = selectedTiles || [];
    const tileUrlRef = useRef(tileUrl);
    tileUrlRef.current = tileUrl;

    // Build a fully-populated TileInfo (with url + bounds) from a {z,x,y} key.
    const buildTileInfo = (t: Tile): TileInfo => {
        const [nw, se] = tileCornersLatLng(map, t.z, t.x, t.y);
        return {
            ...t,
            url: fillTileUrl(tileUrlRef.current, t.z, t.x, t.y),
            bounds: [
                +se.lat.toFixed(7), // south
                +nw.lng.toFixed(7), // west
                +nw.lat.toFixed(7), // north
                +se.lng.toFixed(7), // east
            ],
        };
    };

    // Create the Leaflet Control once the map is available.
    useEffect(() => {
        if (!map) return;
        const C = Control as any;
        const ctl = new C({ position });
        ctl.onAdd = () => {
            const el = containerRef.current!;
            el.classList.add('leaflet-bar', 'dl2-tile-selector-control');
            DomEvent.disableClickPropagation(el);
            DomEvent.disableScrollPropagation(el);
            return el;
        };
        ctl.addTo(map);
        return () => {
            ctl.remove();
            if (hoverRectRef.current) {
                hoverRectRef.current.remove();
                hoverRectRef.current = null;
            }
            selectedRectsRef.current.forEach((r) => r.remove());
            selectedRectsRef.current.clear();
        };
    }, [map, position]);

    // Sync selected-tile rectangles to the selectedTiles prop (single source of truth).
    useEffect(() => {
        if (!map) return;
        const wanted = new Set((selectedTiles || []).map(tileKey));
        selectedRectsRef.current.forEach((rect, key) => {
            if (!wanted.has(key)) {
                rect.remove();
                selectedRectsRef.current.delete(key);
            }
        });
        (selectedTiles || []).forEach((t) => {
            const key = tileKey(t);
            if (!selectedRectsRef.current.has(key)) {
                const bounds = tileBoundsLLBounds(map, t.z, t.x, t.y);
                const rect = new LeafletRectangle(bounds as any, {
                    color: selectedColor,
                    weight: 2,
                    fillColor: selectedColor,
                    fillOpacity: 0.18,
                    interactive: false,
                } as any);
                rect.addTo(map);
                selectedRectsRef.current.set(key, rect);
            }
        });
    }, [map, selectedTiles, selectedColor]);

    // While active: hover outline, single-click toggle, shift-drag box-select.
    useEffect(() => {
        if (!map) return;
        const mapEl = (map as any)._container as HTMLElement;
        if (!active) {
            mapEl.style.cursor = '';
            if (hoverRectRef.current) {
                hoverRectRef.current.remove();
                hoverRectRef.current = null;
            }
            return;
        }
        mapEl.style.cursor = 'crosshair';
        // Leaflet's default Shift+drag triggers boxZoom — disable it so we own shift+drag.
        (map as any).boxZoom?.disable();

        let boxStart: any = null;
        let boxRect: LeafletRectangle | null = null;

        const cancelBox = () => {
            if (boxRect) {
                boxRect.remove();
                boxRect = null;
            }
            boxStart = null;
        };

        // Toggle map.dragging based on Shift key state — plain drag still pans the map,
        // shift+drag is captured by us. Listening on document so it works while the user's
        // cursor is anywhere on the page (map focus is finicky).
        const onKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Shift' && (map as any).dragging?.enabled?.()) {
                (map as any).dragging.disable();
            }
        };
        const onKeyUp = (e: KeyboardEvent) => {
            if (e.key === 'Shift') {
                (map as any).dragging?.enable?.();
                // Shift released mid-drag = cancel.
                cancelBox();
            }
        };
        document.addEventListener('keydown', onKeyDown);
        document.addEventListener('keyup', onKeyUp);

        const onMove = (e: any) => {
            // Update hover outline (always while active).
            const t = tileAtLatLng(map, e.latlng);
            const bounds = tileBoundsLLBounds(map, t.z, t.x, t.y);
            if (!hoverRectRef.current) {
                hoverRectRef.current = new LeafletRectangle(bounds as any, {
                    color: hoverColor,
                    weight: 2,
                    fill: false,
                    dashArray: '5 5',
                    interactive: false,
                } as any).addTo(map);
            } else {
                hoverRectRef.current.setBounds(bounds as any);
            }
            // If a shift-drag is in progress, update the box preview too.
            if (boxStart) {
                const b = new LatLngBounds(boxStart, e.latlng);
                if (!boxRect) {
                    boxRect = new LeafletRectangle(b as any, {
                        color: selectedColor,
                        weight: 1,
                        fillColor: selectedColor,
                        fillOpacity: 0.08,
                        dashArray: '4 4',
                        interactive: false,
                    } as any).addTo(map);
                } else {
                    boxRect.setBounds(b as any);
                }
            }
        };
        const onOut = () => {
            if (hoverRectRef.current) {
                hoverRectRef.current.remove();
                hoverRectRef.current = null;
            }
        };

        const onPointerDown = (e: any) => {
            if (e.originalEvent && e.originalEvent.shiftKey) {
                boxStart = e.latlng;
            }
        };

        const onPointerUp = (e: any) => {
            if (!boxStart) return;
            const start = boxStart;
            const end = e.latlng;
            cancelBox();
            // Compute all tiles whose top-left pixel falls inside the box, at current zoom.
            const z = map.getZoom();
            const p1 = map.project(start, z);
            const p2 = map.project(end, z);
            const xMin = Math.floor(Math.min(p1.x, p2.x) / TILE_SIZE);
            const xMax = Math.floor(Math.max(p1.x, p2.x) / TILE_SIZE);
            const yMin = Math.floor(Math.min(p1.y, p2.y) / TILE_SIZE);
            const yMax = Math.floor(Math.max(p1.y, p2.y) / TILE_SIZE);
            const next = tilesRef.current.slice();
            const seen = new Set(next.map(tileKey));
            for (let x = xMin; x <= xMax; x++) {
                for (let y = yMin; y <= yMax; y++) {
                    const t = { z, x, y };
                    const k = tileKey(t);
                    if (!seen.has(k)) {
                        next.push(buildTileInfo(t));
                        seen.add(k);
                    }
                }
            }
            tilesRef.current = next;
            setProps && setProps({ selectedTiles: next });
        };

        // Document pointerup catches the case where the user releases OUTSIDE the map
        // (map.on('pointerup') only fires when the pointer is over the map container).
        const onDocPointerUp = () => {
            if (boxStart) cancelBox();
        };
        document.addEventListener('pointerup', onDocPointerUp);

        const onClick = (e: any) => {
            // Shift+click is handled by the box-drag pointerdown/up path — don't double-toggle.
            if (e.originalEvent && e.originalEvent.shiftKey) return;
            const t = tileAtLatLng(map, e.latlng);
            const key = tileKey(t);
            const tiles = tilesRef.current;
            const idx = tiles.findIndex((x) => tileKey(x) === key);
            const next =
                idx >= 0
                    ? tiles.filter((_, i) => i !== idx)
                    : [...tiles, buildTileInfo(t)];
            tilesRef.current = next;
            setProps && setProps({ selectedTiles: next });
        };

        map.on('pointermove', onMove);
        map.on('pointerout', onOut);
        map.on('pointerdown', onPointerDown);
        map.on('pointerup', onPointerUp);
        map.on('click', onClick);
        return () => {
            map.off('pointermove', onMove);
            map.off('pointerout', onOut);
            map.off('pointerdown', onPointerDown);
            map.off('pointerup', onPointerUp);
            map.off('click', onClick);
            document.removeEventListener('keydown', onKeyDown);
            document.removeEventListener('keyup', onKeyUp);
            document.removeEventListener('pointerup', onDocPointerUp);
            (map as any).boxZoom?.enable();
            (map as any).dragging?.enable?.();
            mapEl.style.cursor = '';
            cancelBox();
            if (hoverRectRef.current) {
                hoverRectRef.current.remove();
                hoverRectRef.current = null;
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map, active, hoverColor, selectedColor]);

    return map && containerRef.current
        ? ReactDOM.createPortal(
              <button
                  className={`dl2-tile-selector-btn ${active ? 'active' : ''}`}
                  title={
                      active
                          ? 'Exit tile-select mode (click toggles, shift+drag selects a box)'
                          : 'Select tiles (toggle: click to add/remove, shift+drag to box-select)'
                  }
                  aria-pressed={active}
                  onClick={() => setActive(!active)}
              >
                  <iconify-icon icon="mdi:grid-large" width="18"></iconify-icon>
              </button>,
              containerRef.current
          )
        : null;
};

export default TileSelector;
