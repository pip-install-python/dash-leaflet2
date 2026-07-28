import React, { useEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import {
    Control,
    DomEvent,
    Map as LeafletMap,
    Rectangle as LeafletRectangle,
    TileLayer as LeafletTileLayer,
} from 'leaflet';
import { useLeafletMap } from '../context';
import { DashComponentProps } from '../props';

// leaflet-minimap (the Leaflet 1 plugin dash-leaflet wraps) is L.Class.extend-based and
// targets the v1 API — DOA on v2. This is a native v2 replacement: a Leaflet Control whose
// container hosts a second small Leaflet 2 Map. We sync the inner map's view to the main
// map on every moveend/zoomend (using zoomLevelOffset to offset the zoom), and draw a
// Rectangle on the inner map showing the main map's bounds — the classic "aiming rect".
//
// The toggle button keeps the dash-leaflet/leaflet-minimap class convention
// `leaflet-control-minimap-toggle-display leaflet-control-minimap-toggle-display-<position>`
// so any existing CSS targeting those hooks keeps working.

const POSITIONS = ['topleft', 'topright', 'bottomleft', 'bottomright'] as const;
type Position = (typeof POSITIONS)[number];

type Props = {
    /** Control position: 'topleft' | 'topright' | 'bottomleft' | 'bottomright'. Default 'bottomright'. */
    position?: Position;

    /** Tile URL template for the inner minimap basemap. Defaults to OSM. */
    url?: string;

    /** Attribution shown by the inner minimap. Empty by default — the main map already attributes. */
    attribution?: string;

    /** Expanded width in pixels. Default 150. */
    width?: number;

    /** Expanded height in pixels. Default 150. */
    height?: number;

    /**
     * Zoom-level offset from the main map (negative = zoomed out further than the main).
     * Default -5: a 150x150 minimap shows the main map's neighbourhood.
     */
    zoomLevelOffset?: number;

    /** Show the [⤡] toggle button. Default true. */
    toggleDisplay?: boolean;

    /**
     * Whether the minimap starts (or currently is) minimized. Two-way: setting it from a
     * Python callback collapses/expands the minimap; the user clicking the toggle button
     * also writes it back. [MUTABLE]
     */
    minimized?: boolean;

    /**
     * Leaflet path options for the aiming rectangle that shows the main map's viewport
     * bounds on the minimap. Defaults to a translucent blue stroke.
     */
    aimingRectOptions?: object;

    /**
     * When set to `[lat, lng]`, the inner minimap anchors on this point instead of
     * tracking the main map's center. The aiming rectangle still reflects the main
     * map's bounds — so the rectangle drifts off-minimap if the main map is panned
     * far from the fixed point. Pass `null` (or omit) to follow the main map. Useful
     * for "return-home" style affordances, where the minimap pins on a player /
     * marker and clicking it (see `n_clicks`) snaps the main map back to them. [MUTABLE]
     */
    centerFixed?: [number, number] | null;

    /**
     * Number of times the user has clicked anywhere on the inner minimap (excluding
     * the corner expand/collapse toggle). Increments per click — pair with
     * `prevent_initial_call=True` to use the minimap as a button. [READONLY]
     */
    n_clicks?: number;
} & DashComponentProps;

/**
 * MiniMap adds a small overview map in a corner of the main map. The overview tracks
 * the main map's center + zoom (with a configurable offset) and draws a rectangle showing
 * the main viewport. Click the corner toggle to collapse/expand. Place it as a child of
 * dl2.Map.
 *
 * Native Leaflet 2 — `leaflet-minimap` (the Leaflet 1 plugin) does not run on v2.
 */
const MiniMap = ({
    position = 'bottomright',
    url = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution = '',
    width = 150,
    height = 150,
    zoomLevelOffset = -5,
    toggleDisplay = true,
    minimized: minimizedProp = false,
    aimingRectOptions = {
        color: '#3388ff',
        weight: 1,
        fillColor: '#3388ff',
        fillOpacity: 0.15,
        interactive: false,
    },
    centerFixed,
    n_clicks = 0,
    setProps,
}: Props) => {
    const map = useLeafletMap();
    // Counter ref so the click handler bound once in useEffect doesn't capture a stale
    // n_clicks (same pattern as Marker's clicksRef — setProps has no functional form).
    const clicksRef = useRef<number>(n_clicks || 0);
    // Mirror of centerFixed so the sync handler bound once in useEffect always sees the
    // current value (driveTool-style). Without this, flipping centerFixed from a Python
    // callback wouldn't take effect until the next mount.
    const centerFixedRef = useRef<[number, number] | null | undefined>(centerFixed);
    useEffect(() => { centerFixedRef.current = centerFixed; }, [centerFixed]);
    // The Leaflet Control's container DIV (becomes the .leaflet-control-minimap host).
    const containerRef = useRef<HTMLDivElement | null>(null);
    if (!containerRef.current) containerRef.current = document.createElement('div');
    // The inner <div> that the secondary Leaflet Map mounts into.
    const innerDivRef = useRef<HTMLDivElement | null>(null);
    const miniMapRef = useRef<LeafletMap | null>(null);
    const aimingRectRef = useRef<LeafletRectangle | null>(null);
    const tileLayerRef = useRef<LeafletTileLayer | null>(null);

    const [minimized, setMinimized] = useState<boolean>(!!minimizedProp);

    // ---- 1. Mount the Leaflet Control once the map is available -------------
    useEffect(() => {
        if (!map) return;
        const C = Control as any;
        const ctl = new C({ position });
        ctl.onAdd = () => {
            const el = containerRef.current!;
            el.classList.add('leaflet-control-minimap');
            // Don't let map drag/scroll bleed through the minimap (otherwise dragging
            // over the minimap pans the main map).
            DomEvent.disableClickPropagation(el);
            DomEvent.disableScrollPropagation(el);
            return el;
        };
        ctl.addTo(map);
        return () => ctl.remove();
    }, [map, position]);

    // ---- 2. Create the inner Leaflet 2 Map once the inner div is mounted ---
    useEffect(() => {
        if (!map || !innerDivRef.current || miniMapRef.current) return;
        const c = map.getCenter();
        const z = map.getZoom();

        const mini = new LeafletMap(innerDivRef.current, {
            // Strip every interactive affordance — the minimap is read-only navigation
            // context, not a second interactive map.
            attributionControl: !!attribution,
            zoomControl: false,
            dragging: false,
            scrollWheelZoom: false,
            doubleClickZoom: false,
            // v2 alpha renamed touchZoom -> pinchZoom; the old name still works but
            // logs a deprecation warning. Pass pinchZoom so the console stays clean.
            pinchZoom: false,
            boxZoom: false,
            keyboard: false,
        } as any);
        mini.setView([c.lat, c.lng], z + zoomLevelOffset);

        const tile = new LeafletTileLayer(url as string, { attribution });
        tile.addTo(mini);
        tileLayerRef.current = tile;

        const rect = new LeafletRectangle(map.getBounds() as any, aimingRectOptions as any);
        rect.addTo(mini);
        aimingRectRef.current = rect;

        // Sync inner map view + aiming rect on every change to the main map.
        // When centerFixed is set (read live via the ref), the inner map STAYS PUT —
        // only the aiming rectangle moves to reflect where the main map has drifted.
        const sync = () => {
            const cc = centerFixedRef.current ?? map.getCenter();
            const lat = Array.isArray(cc) ? cc[0] : cc.lat;
            const lng = Array.isArray(cc) ? cc[1] : cc.lng;
            mini.setView(
                [lat, lng],
                map.getZoom() + zoomLevelOffset,
                { animate: false } as any,
            );
            rect.setBounds(map.getBounds() as any);
        };
        map.on('moveend zoomend', sync);

        // Treat clicks anywhere on the inner minimap as button clicks. The corner
        // toggle button is rendered OUTSIDE the inner leaflet-container (it's a
        // sibling in the wrapper), so its clicks never reach this handler —
        // expand/collapse stays separate from "minimap as switch" semantics.
        const onMiniClick = () => {
            clicksRef.current += 1;
            if (setProps) setProps({ n_clicks: clicksRef.current });
        };
        mini.on('click', onMiniClick);

        miniMapRef.current = mini;
        // The inner map was created while its container was still 0×0 in some flows
        // (React renders the portal markup synchronously, but layout for absolutely-
        // positioned elements lags by a tick); invalidate on the next frame so tiles
        // load against the correct size.
        requestAnimationFrame(() => mini.invalidateSize());

        return () => {
            map.off('moveend zoomend', sync);
            mini.off('click', onMiniClick);
            mini.remove();
            miniMapRef.current = null;
            aimingRectRef.current = null;
            tileLayerRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map]);

    // ---- 3. React to mutable props ----------------------------------------
    // url
    useEffect(() => {
        if (tileLayerRef.current && url) tileLayerRef.current.setUrl(url);
    }, [url]);

    // External minimized prop -> internal state (skipped if already equal so a Python
    // setProps round-trip doesn't fight our own toggle).
    useEffect(() => {
        setMinimized((prev) => (prev === !!minimizedProp ? prev : !!minimizedProp));
    }, [minimizedProp]);

    // Whenever the visible size of the minimap changes (toggle, prop), the inner
    // Leaflet map must be told to re-measure or tiles never refill.
    useEffect(() => {
        if (!miniMapRef.current) return;
        const t = window.setTimeout(() => {
            try { miniMapRef.current?.invalidateSize(); } catch (e) {}
        }, 220);
        return () => window.clearTimeout(t);
    }, [minimized, width, height]);

    // zoomLevelOffset OR centerFixed change — re-sync immediately so the inner map
    // settles at the new anchor / zoom without waiting for the main map to move.
    useEffect(() => {
        if (!map || !miniMapRef.current) return;
        const cc = centerFixed ?? map.getCenter();
        const lat = Array.isArray(cc) ? cc[0] : cc.lat;
        const lng = Array.isArray(cc) ? cc[1] : cc.lng;
        miniMapRef.current.setView(
            [lat, lng],
            map.getZoom() + zoomLevelOffset,
            { animate: false } as any,
        );
    }, [zoomLevelOffset, centerFixed, map]);

    // ---- 4. Render via portal into the Leaflet control container -----------
    const onToggle = (e: React.MouseEvent) => {
        // Toggle is its own affordance, not a minimap-click: stop propagation so it
        // never feeds `n_clicks` (which pages use to treat the minimap as a switch).
        e.stopPropagation();
        const next = !minimized;
        setMinimized(next);
        if (setProps) setProps({ minimized: next });
    };

    if (!map || !containerRef.current) return null;

    // The wrapper is the visible chrome; when minimized we shrink it down to a small
    // square so only the toggle button remains visible at the corner.
    const wrapperStyle: React.CSSProperties = minimized
        ? { width: 24, height: 24 }
        : { width, height };

    return ReactDOM.createPortal(
        <div
            className={`leaflet-control-minimap-wrapper ${
                minimized ? 'minimized' : 'expanded'
            } pos-${position}`}
            style={wrapperStyle}
        >
            {/* Inner map div — Leaflet 2 mounts directly into this element. */}
            <div
                ref={innerDivRef}
                className="leaflet-control-minimap-inner"
                style={{
                    width,
                    height,
                    visibility: minimized ? 'hidden' : 'visible',
                }}
            />
            {toggleDisplay && (
                <button
                    type="button"
                    // Class convention matches the dash-leaflet / leaflet-minimap plugin
                    // so external CSS targeting these hooks keeps working.
                    className={`leaflet-control-minimap-toggle-display leaflet-control-minimap-toggle-display-${position}`}
                    aria-label={minimized ? 'Show minimap' : 'Hide minimap'}
                    aria-pressed={!minimized}
                    onClick={onToggle}
                />
            )}
        </div>,
        containerRef.current,
    );
};

export default MiniMap;
