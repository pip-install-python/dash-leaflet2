import React, { useEffect, useRef, useState } from 'react';
import { Map as LeafletMap } from 'leaflet';
import 'leaflet/dist/leaflet.css';
import '../theme.css'; // liquid-glass tooltip/popup/control theme (theme-aware)
import { LeafletMapContext, LeafletBearingContext } from '../context';
import { DashComponentProps } from '../props';

type Props = {
    /**
     * Initial map center as [lat, lng]. Updating it from a callback re-centers
     * the map. [MUTABLE]
     */
    center?: [number, number];

    /**
     * Initial zoom level. Updating it from a callback changes the zoom. [MUTABLE]
     */
    zoom?: number;

    /**
     * Minimum zoom level the user can zoom out to. When a TileLayer also sets
     * `minZoom`, Leaflet uses the *larger* of the two (the most restrictive
     * value wins). [MUTABLE]
     */
    minZoom?: number;

    /**
     * Maximum zoom level the user can zoom in to. When a TileLayer also sets
     * `maxZoom`, Leaflet uses the *smaller* of the two. [MUTABLE]
     */
    maxZoom?: number;

    /**
     * Geographic bounds the map's view is constrained inside, as
     * `[[south, west], [north, east]]`. Panning past the edges is bounced back.
     * [MUTABLE]
     */
    maxBounds?: [[number, number], [number, number]];

    /**
     * Whether Leaflet's built-in +/- zoom buttons control is added. Default true.
     * Constructor-only — changing it after the map is built has no effect.
     */
    zoomControl?: boolean;

    /**
     * Whether the map can be panned / zoomed with the keyboard (arrow keys + `+`/`-`).
     * Default true. [MUTABLE]
     */
    keyboard?: boolean;

    /**
     * Mouse / pointer drag panning. Default true. [MUTABLE]
     */
    dragging?: boolean;

    /**
     * Mouse-wheel zoom. Default true. [MUTABLE]
     */
    scrollWheelZoom?: boolean;

    /**
     * Double-click-to-zoom. Default true. [MUTABLE]
     */
    doubleClickZoom?: boolean;

    /**
     * Shift-drag box-zoom selection. Default true. [MUTABLE]
     */
    boxZoom?: boolean;

    /**
     * Pinch-to-zoom on touch devices. Default true. In Leaflet 1.x this was
     * called `touchZoom`; in v2 it's `pinchZoom`. [MUTABLE]
     */
    pinchZoom?: boolean;

    /**
     * Mobile-safari tap-hold-to-contextmenu emulation. Defaults to true on
     * mobile Safari only. [MUTABLE]
     */
    tapHold?: boolean;

    /**
     * Map rotation in degrees (CW from north). 0 = north up. Implemented as a
     * CSS `transform: rotate()` on the leaflet map pane — the same technique
     * `leaflet-rotate` uses on Leaflet 1.x. Leaflet 2 has no native rotation,
     * so we build it the same way.
     *
     * **Important caveat (CSS rotation, not coordinate-correct rotation):**
     * Tiles, markers, polygons, and zoom math are computed in Leaflet's
     * un-rotated coordinate space and the whole pane is then rotated visually.
     * That works perfectly for read-only views and follow-camera flight/walk
     * sims (you look at the map; the camera tracks the player). It breaks
     * subtly for INTERACTIVE drawing at non-zero bearing — a click lands at
     * the visually-rotated screen position, which is no longer the same
     * latlng Leaflet would resolve from the bare event coords. For drawing,
     * keep bearing = 0. A fully coordinate-correct rotation is a much larger
     * project (essentially porting leaflet-rotate's coord math to v2).
     *
     * [MUTABLE]
     */
    bearing?: number;

    /**
     * Current view state, written back by the map on every moveend/zoomend as
     * { center: [lat, lng], zoom, bearing, bounds: { north, south, east, west } }.
     * Read this in callbacks. [READONLY]
     */
    viewport?: {
        center: [number, number];
        zoom: number;
        bearing: number;
        bounds: { north: number; south: number; east: number; west: number };
    };

    /**
     * Data from the most recent map click: { latlng: [lat, lng] }. [READONLY]
     */
    clickData?: { latlng: [number, number] };

    /**
     * If true, render all vector layers through the Canvas renderer (preferred
     * for dense point sets). [READONLY]
     */
    preferCanvas?: boolean;

    /**
     * Whether Leaflet 2's built-in attribution control is added to the map.
     * Default True (matches Leaflet's default). Set False when you want to
     * mount a `dl2.AttributionControl` child and control position / prefix
     * yourself — same convention as dash-leaflet's `attributionControl=False`
     * + `dl.AttributionControl(...)` pairing. Constructor-only — changing it
     * after the map is built has no effect.
     */
    attributionControl?: boolean;

    /**
     * Python -> map: trigger a smooth viewport transition. The map calls the
     * Leaflet 2 method indicated by `transition` and ignores the prop until
     * `n_clicks` bumps again (matching `drawToolbar` / `editToolbar` / `featureUpdate`
     * — needed so consecutive identical payloads still register as changes).
     *
     * Shape:
     *   {
     *     transition: 'setView' | 'flyTo' | 'panTo' | 'fitBounds' | 'flyToBounds' | 'panInsideBounds',
     *     center?: [lat, lng],          # for setView / flyTo / panTo
     *     zoom?:   number,              # optional zoom target (setView / flyTo)
     *     bounds?: [[s, w], [n, e]],    # for fitBounds / flyToBounds / panInsideBounds
     *     options?: object,             # passed straight to the Leaflet method
     *                                   # (duration, easeLinearity, animate, paddingTopLeft, ...)
     *     n_clicks: int,
     *   }
     *
     * `flyTo` / `flyToBounds` give the smooth glide-and-zoom motion; `setView`
     * is instant; `panTo` glides without changing zoom. See the /flyto showcase. [MUTABLE]
     */
    flyTo?: {
        transition?: 'setView' | 'flyTo' | 'panTo' | 'fitBounds' | 'flyToBounds' | 'panInsideBounds';
        center?: [number, number];
        zoom?: number;
        bounds?: [[number, number], [number, number]];
        options?: Record<string, any>;
        n_clicks: number;
    };

    /**
     * Counter bumped on every `movestart` event (a pan / flyTo / fit begins).
     * Pair with `n_moveend` to drive a "flying…" indicator. [READONLY]
     */
    n_movestart?: number;

    /**
     * Counter bumped on every `moveend` event (a pan / flyTo / fit completes).
     * `n_moveend < n_movestart` means a transition is currently running. [READONLY]
     */
    n_moveend?: number;

    /**
     * Child layers (TileLayer, Marker, ...) rendered into this map.
     */
    children?: React.ReactNode;
} & DashComponentProps;

/**
 * Map is the root Leaflet 2 map container. It owns the Leaflet map instance and
 * provides it to child layers (TileLayer, Marker) through React context. Set the
 * height via the `style` prop.
 */
const Map = ({
    id,
    center = [51.505, -0.09],
    zoom = 13,
    minZoom,
    maxZoom,
    maxBounds,
    zoomControl = true,
    keyboard = true,
    dragging = true,
    scrollWheelZoom = true,
    doubleClickZoom = true,
    boxZoom = true,
    pinchZoom = true,
    tapHold,
    bearing: initialBearing = 0,
    preferCanvas = false,
    attributionControl = true,
    flyTo,
    className,
    style,
    children,
    setProps,
}: Props) => {
    const elRef = useRef<HTMLDivElement>(null);
    const mapRef = useRef<LeafletMap | null>(null);
    const [ready, setReady] = useState(false);

    // Bearing is React-side state (Leaflet 2 has no native rotation). We
    // publish it via LeafletBearingContext so child components (Marker's
    // rotateWithMap, KeyboardControl's arrow-key handlers) can read/write it.
    const [bearing, setBearingState] = useState<number>(initialBearing);
    const bearingRef = useRef(bearing);
    bearingRef.current = bearing;

    // The setter passed via context — also writes back to Python through
    // setProps so a Python callback can observe what KeyboardControl did.
    const setBearing = React.useCallback((b: number) => {
        const normalized = ((b % 360) + 360) % 360;
        setBearingState(normalized);
        if (setProps) setProps({ bearing: normalized });
    }, [setProps]);

    // Apply the rotation visually by WRAPPING the leaflet map-pane in a div
    // whose transform we own. We do NOT rotate the map-pane directly because:
    //
    //   1. Leaflet writes `transform: translate3d(...)` to the map-pane on every
    //      pan tick — sharing that property would mean read-modify-write race.
    //   2. The standalone CSS `rotate` property (one would expect to compose
    //      cleanly with `transform: translate3d(...)` since they're separate
    //      props) IGNORES the element's `transform-origin` in current Chromium
    //      and rotates around what appears to be the bottom-right corner of
    //      the un-sized pane. Empirically confirmed — see the analysis in
    //      the v0.x rotation iteration notes.
    //
    // So: we make a `.dl2-rotation-wrapper` div that sits between the
    // leaflet-container and the leaflet-map-pane. The wrapper:
    //   * has the SAME size as the container (position:absolute, 100%/100%)
    //   * owns its own `transform: rotate(...)` — no Leaflet writes here
    //   * has `transform-origin: 50% 50%` (its own center == viewport center,
    //     because its size matches the container) — single static origin, no
    //     per-move recomputation needed
    //   * is `pointer-events: none` so map clicks pass through to the
    //     container's listeners (Leaflet's interactive layers explicitly set
    //     pointer-events: auto, which overrides the parent value)
    //
    // The leaflet-control-container is a SIBLING of the map-pane in the
    // container, so it stays outside the wrapper and remains axis-aligned —
    // exactly what we want for the zoom buttons, our EditControl toolbar, etc.
    useEffect(() => {
        if (!ready) return;
        const m: any = mapRef.current;
        if (!m) return;
        const pane: HTMLElement | undefined = m._mapPane;
        const container: HTMLElement | undefined = m._container;
        if (!pane || !container) return;
        // Idempotent: skip if we've already wrapped this pane.
        const existingWrapper = pane.parentElement;
        if (existingWrapper && existingWrapper.classList.contains('dl2-rotation-wrapper')) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'dl2-rotation-wrapper';
        // NOTE: transform-origin must be set in LITERAL PIXEL units, not
        // percent. Percent (`50% 50%`) appears to resolve against the union
        // of the wrapper's positioned-children content box, not the wrapper's
        // own declared 100%/100% — which puts the origin at the bottom-right
        // of where the un-rotated marker pane would have extended (NOT the
        // visible viewport center). Empirically verified on Chromium current.
        // Setting `${cw/2}px ${ch/2}px` makes the rotation honor the actual
        // viewport center.
        wrapper.style.cssText =
            'position: absolute; left: 0; top: 0; width: 100%; height: 100%;'
            + ' pointer-events: none; will-change: transform;';
        // Insert wrapper at pane's position, then move pane inside.
        container.insertBefore(wrapper, pane);
        wrapper.appendChild(pane);

        const setOrigin = () => {
            const cw = container.clientWidth;
            const ch = container.clientHeight;
            wrapper.style.transformOrigin = `${cw / 2}px ${ch / 2}px`;
        };
        setOrigin();
        m.on('resize', setOrigin);

        return () => {
            try { m.off('resize', setOrigin); } catch (e) {}
            // Unmount cleanup: if the wrapper still has the pane, put the pane
            // back in the container (Leaflet expects map._mapPane to be a
            // direct child of map._container).
            if (wrapper.contains(pane)) {
                container.insertBefore(pane, wrapper);
                wrapper.remove();
            }
        };
    }, [ready]);

    // Write the rotation onto the wrapper. Because the wrapper's
    // transform-origin is set to the literal viewport center, the rotation
    // pivots around the screen center — markers at the geographic center
    // stay fixed on screen as bearing changes.
    useEffect(() => {
        if (!ready) return;
        const m: any = mapRef.current;
        if (!m || !m._mapPane) return;
        const wrapper = m._mapPane.parentElement as HTMLElement | null;
        if (!wrapper || !wrapper.classList.contains('dl2-rotation-wrapper')) return;
        wrapper.style.transform = `rotate(${bearing}deg)`;
    }, [bearing, ready]);

    // Create the Leaflet 2 map once, on mount.
    useEffect(() => {
        if (!elRef.current || mapRef.current) return;
        const mapOptions: any = {
            preferCanvas: !!preferCanvas,
            // Leaflet 2's Map.options.attributionControl defaults to true. We
            // mirror that default; passing `False` from Python suppresses the
            // bundled control so a `dl2.AttributionControl` child can take over.
            attributionControl: attributionControl !== false,
            zoomControl: zoomControl !== false,
            keyboard: keyboard !== false,
            dragging: dragging !== false,
            scrollWheelZoom: scrollWheelZoom !== false,
            doubleClickZoom: doubleClickZoom !== false,
            boxZoom: boxZoom !== false,
            pinchZoom: pinchZoom !== false,
        };
        if (typeof tapHold === 'boolean') mapOptions.tapHold = tapHold;
        if (typeof minZoom === 'number') mapOptions.minZoom = minZoom;
        if (typeof maxZoom === 'number') mapOptions.maxZoom = maxZoom;
        if (maxBounds) mapOptions.maxBounds = maxBounds;
        const map = new LeafletMap(elRef.current, mapOptions)
            .setView(center as [number, number], zoom as number);
        mapRef.current = map;
        // Expose the Leaflet instance on the outer DOM div so clientside JS
        // (pages with their own rAF loops, page-level keyboard handlers) can
        // reach into it without crawling Leaflet's internals. This is the
        // documented escape hatch for advanced pages — see /flight-sim.
        (elRef.current as any).__dl2_map = map;

        const pushView = () => {
            if (!setProps) return;
            const c = map.getCenter();
            const b: any = map.getBounds();
            setProps({
                viewport: {
                    center: [+c.lat.toFixed(6), +c.lng.toFixed(6)],
                    zoom: map.getZoom(),
                    bearing: bearingRef.current,
                    bounds: {
                        north: +b.getNorth().toFixed(6),
                        south: +b.getSouth().toFixed(6),
                        east: +b.getEast().toFixed(6),
                        west: +b.getWest().toFixed(6),
                    },
                },
            });
        };
        map.on('moveend zoomend', pushView);
        map.on('click', (e: any) =>
            setProps && setProps({ clickData: { latlng: [+e.latlng.lat.toFixed(6), +e.latlng.lng.toFixed(6)] } })
        );

        // movestart / moveend counters — Dash pages can detect "transition in progress"
        // by `n_movestart > n_moveend`. Used in /flyto to swap the HUD between
        // "FLYING…" and "IDLE" while a flyTo animation is running. Counted via refs
        // so the increment is monotonic across cycles even if React batches setProps.
        let nMovestart = 0;
        let nMoveend = 0;
        map.on('movestart', () => {
            nMovestart += 1;
            setProps && setProps({ n_movestart: nMovestart });
        });
        map.on('moveend', () => {
            nMoveend += 1;
            setProps && setProps({ n_moveend: nMoveend });
        });

        setReady(true);
        pushView(); // emit initial viewport

        return () => {
            map.remove();
            mapRef.current = null;
            if (elRef.current) delete (elRef.current as any).__dl2_map;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Python -> map: re-center when center/zoom props change. `animate: false`
    // because for rAF-driven game loops (flight-sim, walking-sim) at 60fps,
    // Leaflet's default animated pan starts a new ~250ms animation every
    // frame; the animations chain, _pixelOrigin lags behind the requested
    // center, and Markers projected against that pixelOrigin are placed
    // wildly off-screen. Instant updates also avoid running 60 ease-curve
    // calculations per second to no visual benefit.
    //
    // Mount guard: the map was just constructed with these exact center/zoom
    // in the first useEffect, so the very first run of THIS effect (with the
    // same initial values) is a no-op that would only fire a spurious
    // `moveend` — that breaks the `n_movestart > n_moveend` "in-transit"
    // signal for the FIRST flyTo of the session.
    const centerZoomInitedRef = useRef(false);
    useEffect(() => {
        if (!mapRef.current || !center || typeof zoom !== 'number') return;
        if (!centerZoomInitedRef.current) {
            centerZoomInitedRef.current = true;
            return; // skip the redundant initial setView
        }
        (mapRef.current as any).setView(center, zoom, { animate: false });
    }, [center, zoom]);

    // Python -> map: react to minZoom/maxZoom/maxBounds/keyboard changes.
    useEffect(() => {
        const m: any = mapRef.current;
        if (!m) return;
        if (typeof minZoom === 'number' && typeof m.setMinZoom === 'function') m.setMinZoom(minZoom);
    }, [minZoom]);
    useEffect(() => {
        const m: any = mapRef.current;
        if (!m) return;
        if (typeof maxZoom === 'number' && typeof m.setMaxZoom === 'function') m.setMaxZoom(maxZoom);
    }, [maxZoom]);
    useEffect(() => {
        const m: any = mapRef.current;
        if (!m) return;
        if (typeof m.setMaxBounds === 'function') m.setMaxBounds(maxBounds || null);
    }, [maxBounds]);
    useEffect(() => {
        const m: any = mapRef.current;
        if (!m || !m.keyboard) return;
        if (keyboard) m.keyboard.enable(); else m.keyboard.disable();
    }, [keyboard]);

    // The remaining interaction handlers (dragging / scrollWheelZoom /
    // doubleClickZoom / boxZoom / pinchZoom / tapHold) all expose the same
    // `.enable() / .disable()` shape. Toggle them when the prop flips.
    const toggleHandler = (name: string, on: boolean | undefined) => {
        const m: any = mapRef.current;
        if (!m) return;
        const h = m[name];
        if (!h || typeof h.enable !== 'function') return;
        if (on === false) h.disable();
        else h.enable();
    };
    useEffect(() => toggleHandler('dragging', dragging), [dragging]);
    useEffect(() => toggleHandler('scrollWheelZoom', scrollWheelZoom), [scrollWheelZoom]);
    useEffect(() => toggleHandler('doubleClickZoom', doubleClickZoom), [doubleClickZoom]);
    useEffect(() => toggleHandler('boxZoom', boxZoom), [boxZoom]);
    // v2's handler property is `pinchZoom` — fall back to `touchZoom` for safety.
    useEffect(() => {
        toggleHandler('pinchZoom', pinchZoom);
        toggleHandler('touchZoom', pinchZoom);
    }, [pinchZoom]);
    useEffect(() => toggleHandler('tapHold', tapHold), [tapHold]);

    // Python -> map: bearing prop changed externally (slider, callback). Sync
    // it through the same setBearing path so context consumers re-render.
    useEffect(() => {
        if (typeof initialBearing === 'number' && initialBearing !== bearing) {
            setBearingState(((initialBearing % 360) + 360) % 360);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [initialBearing]);

    // Python -> map: smooth viewport transition (flyTo / panTo / fitBounds ...).
    // Same n_clicks-bump pattern as drawToolbar / editToolbar / featureUpdate so
    // consecutive identical payloads still trigger (a fresh n_clicks value is the
    // signal). Default transition is `flyTo` (or `flyToBounds` if `bounds` is given)
    // — those are the smooth ones the dash-leaflet viewport API is best known for.
    const lastFlyTriggerRef = useRef<number>(-1);
    useEffect(() => {
        if (!ready || !flyTo || flyTo.n_clicks === undefined) return;
        if (flyTo.n_clicks === lastFlyTriggerRef.current) return;
        lastFlyTriggerRef.current = flyTo.n_clicks;
        const m: any = mapRef.current;
        if (!m) return;
        const opts = flyTo.options || {};
        const t = flyTo.transition || (flyTo.bounds ? 'flyToBounds' : 'flyTo');
        // In v2, setView() and fitBounds() ANIMATE by default — that makes setView
        // visually indistinguishable from panTo (which is literally
        // `setView(c, zoom, {pan: options})`). To match dash-leaflet 1.x semantics
        // (where setView is instant), default `animate: false` for setView and
        // fitBounds unless the caller explicitly opts in. The user can still
        // pass `options: {animate: true}` to get the animated variant.
        const instantOpts = opts.animate === undefined ? { ...opts, animate: false } : opts;
        try {
            if (t === 'setView' && flyTo.center) {
                const targetZoom = typeof flyTo.zoom === 'number' ? flyTo.zoom : m.getZoom();
                m.setView(flyTo.center, targetZoom, instantOpts);
            } else if (t === 'flyTo' && flyTo.center) {
                const targetZoom = typeof flyTo.zoom === 'number' ? flyTo.zoom : m.getZoom();
                m.flyTo(flyTo.center, targetZoom, opts);
            } else if (t === 'panTo' && flyTo.center) {
                m.panTo(flyTo.center, opts);
            } else if (t === 'fitBounds' && flyTo.bounds) {
                m.fitBounds(flyTo.bounds, instantOpts);
            } else if (t === 'flyToBounds' && flyTo.bounds) {
                m.flyToBounds(flyTo.bounds, opts);
            } else if (t === 'panInsideBounds' && flyTo.bounds) {
                m.panInsideBounds(flyTo.bounds, opts);
            } else {
                // eslint-disable-next-line no-console
                console.warn('dl2.Map.flyTo: incompatible payload for transition=', t, flyTo);
            }
        } catch (e) {
            // eslint-disable-next-line no-console
            console.warn('dl2.Map.flyTo error:', e);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [flyTo, ready]);

    return (
        <div
            id={id}
            ref={elRef}
            className={className}
            style={{ height: '100%', width: '100%', ...style }}
        >
            <LeafletMapContext.Provider value={ready ? mapRef.current : null}>
                <LeafletBearingContext.Provider value={{ bearing, setBearing }}>
                    {ready ? children : null}
                </LeafletBearingContext.Provider>
            </LeafletMapContext.Provider>
        </div>
    );
};

export default Map;
