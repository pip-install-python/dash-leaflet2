import React, { useEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import {
    Circle as LeafletCircle,
    CircleMarker as LeafletCircleMarker,
    Control,
    DivIcon,
    DomEvent,
    FeatureGroup,
    GeoJSON as LeafletGeoJSON,
    LatLngBounds,
    Marker as LeafletMarker,
    Polygon as LeafletPolygon,
    Polyline as LeafletPolyline,
    Rectangle as LeafletRectangle,
} from 'leaflet';
// Tooltip is used purely via layer.bindTooltip(...) — no value import needed.
import { useLeafletMap } from '../context';
import { DEFAULT_ICON } from '../icons';
import { DashComponentProps } from '../props';

// leaflet-draw is Leaflet 1-only (L.Class.extend, lowercase factories, mousedown events —
// none of which exist in v2 alpha). This is a native v2 replacement modeled on the dash-
// leaflet EditControl prop API: a toolbar Control with a Draw section, an Edit section
// (visible only when shapes exist), and a contextual sub-toolbar (Finish / Delete last
// point / Cancel during draw; Save / Cancel during edit; Clear all / Cancel during remove).
// All actions round-trip to Python via `geojson`, `n_drawn`, `lastAction`, and `action`
// (dash-leaflet-shaped {layer_type, type, n_actions}).

type Tool = 'marker' | 'polyline' | 'polygon' | 'rectangle' | 'circle' | 'circlemarker' | 'text';
type EditMode = 'edit' | 'remove';

const TOOL_ICONS: Record<Tool, { icon: string; label: string }> = {
    marker:       { icon: 'mdi:map-marker-plus',  label: 'Draw a marker (1 click)' },
    polyline:     { icon: 'mdi:vector-polyline',  label: 'Draw a polyline (click vertices, double-click to finish)' },
    polygon:      { icon: 'mdi:vector-polygon',   label: 'Draw a polygon (click vertices, double-click to close)' },
    rectangle:    { icon: 'mdi:vector-rectangle', label: 'Draw a rectangle (2 corner clicks)' },
    circle:       { icon: 'mdi:vector-circle',    label: 'Draw a circle (center, then radius)' },
    circlemarker: { icon: 'mdi:circle-medium',    label: 'Draw a circle marker (1 click, fixed radius)' },
    text:         { icon: 'mdi:format-text',      label: 'Add a text caption (click, then type)' },
};

const EDIT_ICONS: Record<EditMode, { icon: string; label: string }> = {
    edit:   { icon: 'mdi:vector-square-edit', label: 'Edit layers (drag vertices / markers)' },
    remove: { icon: 'mdi:delete-outline',     label: 'Delete layers (click to remove)' },
};

const ALL_TOOLS: Tool[] = ['marker', 'polyline', 'polygon', 'rectangle', 'circle', 'circlemarker', 'text'];

// Default style for a text caption dropped by the `text` tool. `shapeOptions.color` (if a
// readable color) overrides the text color so the EditControl color picker drives it too.
const TEXT_DEFAULTS = { color: '#111827', fontSize: 18, fontFamily: 'system-ui, sans-serif', fontWeight: 600 };

type Props = {
    /** Control position: "topleft" | "topright" | "bottomleft" | "bottomright". */
    position?: string;

    /**
     * Per-tool enable/disable for the Draw section, e.g. {rectangle: False, marker: True}.
     * Tools not listed default to enabled.
     */
    draw?: Record<string, boolean>;

    /**
     * Per-mode enable/disable for the Edit section, e.g. {remove: False}. Modes not listed
     * default to enabled. The Edit section only appears once at least one shape exists.
     */
    edit?: Record<string, boolean>;

    /** Path style applied to drawn vectors (color, weight, fillOpacity, ...). */
    shapeOptions?: object;

    /**
     * Unit system for the live drawing previews — drives the radius readout in the
     * circle tool and the area readout in the rectangle tool.
     *
     * - 'metric' (default): meters / kilometers for distance; m² / hectares / km² for area.
     * - 'imperial' (US customary): feet / miles for distance; ft² / acres / mi² for area.
     *
     * Each formatter auto-picks the largest readable unit for the current magnitude
     * (e.g. a 5 km radius reads "5.00 km"; a 50 m radius reads "50 m"). [MUTABLE]
     */
    measurementSystem?: 'metric' | 'imperial';

    /**
     * Python -> control: setting this prop activates a draw tool or dispatches an action on
     * the currently active tool. Bump `n_clicks` to ensure the prop registers as changed.
     * Shape: {mode?: tool name, action?: 'finish'|'cancel'|'delete last point', n_clicks: int}.
     * [MUTABLE]
     */
    drawToolbar?: { mode?: Tool; action?: string; n_clicks?: number };

    /**
     * Python -> control: enter edit/remove mode or dispatch save/cancel/clear-all. Bump
     * `n_clicks` to ensure the prop changes. Shape:
     * {mode?: 'edit'|'remove', action?: 'save'|'cancel'|'clear all', n_clicks: int}. [MUTABLE]
     */
    editToolbar?: { mode?: EditMode; action?: string; n_clicks?: number };

    /** All currently drawn shapes as a GeoJSON FeatureCollection. [READONLY] */
    geojson?: object;

    /** Total shapes drawn since mount (decrements on delete). [READONLY] */
    n_drawn?: number;

    /** Brief metadata for the most recent draw / delete event (legacy shape). [READONLY] */
    lastAction?: object;

    /**
     * The most recent action, dash-leaflet-shaped:
     *   {layer_type: 'polygon', type: 'created'|'edited'|'deleted', n_actions: int}
     * Bumps every time something happens — useful as a sole Input for "anything changed". [READONLY]
     */
    action?: { layer_type?: string; type?: string; n_actions: number };

    /**
     * The currently active draw tool, or null. Emitted whenever a tool is activated or
     * cleared — pages can use this to open a popover when the user clicks a draw icon
     * (mirrors the `/easy-button` popover-on-button-click pattern). [READONLY]
     */
    activeTool?: Tool | null;

    /**
     * The currently active edit/remove mode, or null. [READONLY]
     */
    activeMode?: EditMode | null;

    /**
     * The most recent feature click. Only fires while `editMode === 'edit'` — clicks on
     * features in normal view mode do NOT emit this. The click is NOT propagated to the
     * map (we set `bubblingMouseEvents: false`) so a Map.clickData callback only fires
     * on empty-map clicks. Shape: {id, layerType, n_clicks}. [READONLY]
     */
    featureClick?: { id: string; layerType: string; n_clicks: number };

    /**
     * Python -> control: update or remove a single feature by its _dl2_id. Bump
     * `n_clicks` each call to ensure the prop registers as changed. Shape:
     *   {id, style?, properties?, remove?, n_clicks}
     *   - style:      Leaflet path style options to apply via setStyle (color, weight, fillOpacity, ...)
     *   - properties: merged into the feature's properties (e.g. {name: "Lighthouse"})
     *   - remove:     drop the feature from the FeatureGroup
     * [MUTABLE]
     */
    featureUpdate?: {
        id: string;
        style?: object;
        properties?: object;
        remove?: boolean;
        n_clicks: number;
    };

    /**
     * When true, every committed shape gets a permanent Leaflet tooltip showing its
     * measured area (rectangle / circle / polygon) or length (polyline), formatted with
     * the configured `measurementSystem`. [READONLY]
     */
    showMeasurementTooltips?: boolean;
} & DashComponentProps;

/**
 * EditControl renders a Leaflet draw/edit toolbar (native v2 — leaflet-draw is Leaflet
 * 1-only). Place it as a child of dl2.Map. Shapes are kept in an internal FeatureGroup and
 * surfaced via the `geojson` prop. The Edit section appears only when at least one shape
 * exists. A contextual sub-toolbar appears while a tool is active (Finish / Delete last
 * point / Cancel during draw; Save / Cancel during edit; Clear all / Cancel during remove).
 */
const EditControl = ({
    position = 'topleft',
    draw,
    edit,
    shapeOptions = { color: '#2f9e44', weight: 3, fillOpacity: 0.2 },
    measurementSystem = 'metric',
    showMeasurementTooltips = false,
    drawToolbar,
    editToolbar,
    featureUpdate,
    setProps,
}: Props) => {
    const map = useLeafletMap();
    const containerRef = useRef<HTMLDivElement | null>(null);
    if (!containerRef.current) containerRef.current = document.createElement('div');
    const groupRef = useRef<FeatureGroup | null>(null);
    const [tool, setTool] = useState<Tool | null>(null);
    const [editMode, setEditMode] = useState<EditMode | null>(null);
    // Count of shapes (drives Edit-section visibility); kept in sync with the FeatureGroup.
    const [shapeCount, setShapeCount] = useState(0);
    const nActionsRef = useRef(0);
    // Action dispatcher exposed by the currently active draw-tool driver (Finish/Cancel/…).
    const toolActionRef = useRef<((a: string) => void) | null>(null);
    // Snapshot for edit-mode cancel/revert.
    const editSnapshotRef = useRef<any>(null);
    // Cleanup function for the currently active edit/remove driver.
    const editCleanupRef = useRef<(() => void) | null>(null);

    // Per-tool enable lookup with sensible defaults (everything on).
    const drawEnabled = (t: Tool) => (draw ? draw[t] !== false : true);
    const editEnabled = (m: EditMode) => (edit ? edit[m] !== false : true);

    // Read measurementSystem through a ref so a live preview reacts to the latest
    // value — driveTool() captures props once at tool-start; without this, flipping
    // metric ↔ imperial mid-draw wouldn't update the tooltip text until you restart.
    const unitsRef = useRef(measurementSystem);
    useEffect(() => {
        unitsRef.current = measurementSystem;
    }, [measurementSystem]);

    // Same pattern for shapeOptions and showMeasurementTooltips — a color picker
    // in /edit-control-measurement updates shapeOptions.color live; the running
    // draw tool needs to see the new color on the NEXT click without reactivating.
    const shapeOptionsRef = useRef(shapeOptions);
    useEffect(() => {
        shapeOptionsRef.current = shapeOptions || {};
    }, [shapeOptions]);
    const showMeasurementTooltipsRef = useRef(showMeasurementTooltips);
    useEffect(() => {
        showMeasurementTooltipsRef.current = !!showMeasurementTooltips;
    }, [showMeasurementTooltips]);

    // Per-feature counter used to bump featureClick.n_clicks so Python @callback
    // (Input("ec", "featureClick")) fires every click even on the same shape.
    const featureClickCountRef = useRef(0);
    // Used by edit-mode click handlers to know the current feature set without
    // re-binding each time the group changes (we re-bind in startEdit anyway).

    // Create the FeatureGroup + Leaflet control once the map is available.
    useEffect(() => {
        if (!map) return;
        const group = new FeatureGroup().addTo(map);
        groupRef.current = group;

        const C = Control as any;
        const ctl = new C({ position });
        ctl.onAdd = () => {
            const el = containerRef.current!;
            el.classList.add('leaflet-bar', 'dl2-edit-control');
            DomEvent.disableClickPropagation(el);
            DomEvent.disableScrollPropagation(el);
            return el;
        };
        ctl.addTo(map);

        // Zoom-gate tooltip visibility — hide labels when the user zooms
        // further out than the level a shape was drawn at (the label would
        // otherwise sprawl across the whole map at low zoom).
        const onZoomEnd = () => applyZoomTooltipVisibility();
        map.on('zoomend', onZoomEnd);

        return () => {
            map.off('zoomend', onZoomEnd);
            ctl.remove();
            group.remove();
            groupRef.current = null;
        };
    }, [map, position]);

    // When measurementSystem flips (metric ↔ imperial), rebind every existing
    // tooltip so the displayed unit updates without redrawing the shape.
    useEffect(() => {
        if (!groupRef.current) return;
        groupRef.current.eachLayer((layer: any) => {
            const layerType = layer.feature?.properties?._dl2_type;
            if (layerType) bindMeasurementTooltip(layer, layerType);
        });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [measurementSystem]);

    // When showMeasurementTooltips flips on, bind tooltips to every existing
    // layer; when it flips off, unbind them.
    useEffect(() => {
        if (!groupRef.current) return;
        groupRef.current.eachLayer((layer: any) => {
            const layerType = layer.feature?.properties?._dl2_type;
            if (!layerType) return;
            if (showMeasurementTooltips) bindMeasurementTooltip(layer, layerType);
            else { try { layer.unbindTooltip(); } catch (e) {} }
        });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [showMeasurementTooltips]);

    // Stamp a stable id + a feature container onto a freshly created layer so
    // toGeoJSON() carries it through, and so we can look the layer back up by id
    // when Python sends featureUpdate. Also captures the zoom AT DRAW TIME so
    // tooltips can hide themselves when the user zooms further out than the
    // level the shape was authored at (labels otherwise overtake the map).
    const tagFeature = (layer: any, layerType: string, extraProps?: object) => {
        const id = 'f_' + Math.random().toString(36).slice(2, 11);
        layer.feature = layer.feature || { type: 'Feature', properties: {} };
        layer.feature.properties = {
            ...(layer.feature.properties || {}),
            _dl2_id: id,
            _dl2_type: layerType,
            _dl2_zoom: map ? map.getZoom() : undefined,
            ...(extraProps || {}),
        };
        return id;
    };

    // Compute the layer's measurements in raw SI units (m² and m). Returned as
    // an object so a single emit can carry both — Python formats per-units in
    // the right rail / total row, and a measurement-change can be detected by
    // comparing area_m2 directly. Polylines have length only; markers / circle-
    // markers have neither (return zeros).
    const layerMeasurements = (layer: any, layerType: string) => {
        try {
            if (layerType === 'circle') {
                const r = layer.getRadius();
                return { area_m2: Math.PI * r * r, length_m: 0 };
            }
            if (layerType === 'rectangle' || layerType === 'polygon') {
                const ring = (layer.getLatLngs() as any[])[0];
                return { area_m2: polygonAreaM2(ring), length_m: 0 };
            }
            if (layerType === 'polyline' && map) {
                const pts = layer.getLatLngs() as any[];
                let total = 0;
                for (let i = 1; i < pts.length; i++) total += (map as any).distance(pts[i - 1], pts[i]);
                return { area_m2: 0, length_m: total };
            }
        } catch (e) { /* fall through */ }
        return { area_m2: 0, length_m: 0 };
    };

    // Toggle every layer's permanent tooltip based on the current map zoom vs
    // the zoom it was drawn at. Layers without `_dl2_zoom` (e.g. legacy /
    // imported GeoJSON) are treated as "always show".
    const applyZoomTooltipVisibility = () => {
        if (!showMeasurementTooltipsRef.current || !map || !groupRef.current) return;
        const cur = map.getZoom();
        groupRef.current.eachLayer((layer: any) => {
            if (!layer.getTooltip || !layer.getTooltip()) return;
            const drawZoom = layer.feature?.properties?._dl2_zoom;
            if (drawZoom === undefined) {
                try { layer.openTooltip(); } catch (e) {}
                return;
            }
            try {
                if (cur >= drawZoom) layer.openTooltip();
                else layer.closeTooltip();
            } catch (e) {}
        });
    };

    // Look up a layer in the FeatureGroup by its _dl2_id (returns null if none).
    const findById = (id: string) => {
        const g = groupRef.current;
        if (!g) return null;
        let found: any = null;
        g.eachLayer((layer: any) => {
            if (layer.feature?.properties?._dl2_id === id) found = layer;
        });
        return found;
    };

    // Bind a permanent Leaflet Tooltip with the measured area / length to a
    // committed shape, if the showMeasurementTooltips prop is on. Used both for
    // freshly drawn shapes and to refresh after a vertex edit changes geometry
    // or after the units / name change. Honors zoom-gating: if the current map
    // zoom is BELOW the layer's draw zoom, the tooltip stays bound but closed.
    const bindMeasurementTooltip = (layer: any, layerType: string) => {
        if (!showMeasurementTooltipsRef.current || !map) return;
        const text = measurementLabel(map, layer, layerType, unitsRef.current);
        if (!text) return;
        layer.unbindTooltip();
        layer.bindTooltip(text, {
            permanent: true,
            direction: 'center',
            className: 'dl2-measurement-tooltip',
            interactive: false,
        } as any);
        // Respect zoom-gating immediately — the bindTooltip call above opens
        // the tooltip by default since permanent:true; close it if the map
        // is currently zoomed out below the layer's draw zoom.
        const drawZoom = layer.feature?.properties?._dl2_zoom;
        if (drawZoom !== undefined && map.getZoom() < drawZoom) {
            try { layer.closeTooltip(); } catch (e) {}
        }
    };

    // Push current state to Python after every change to the FeatureGroup.
    const emit = (action: string, layerType: string, extra?: object) => {
        const g = groupRef.current;
        if (!g || !setProps) return;
        const fc = g.toGeoJSON();
        const n = (fc.features || []).length;
        setShapeCount(n);
        nActionsRef.current += 1;
        setProps({
            geojson: fc,
            n_drawn: n,
            lastAction: { type: layerType, action, ...(extra || {}) },
            action: {
                layer_type: layerType,
                type: action,
                n_actions: nActionsRef.current,
                ...(extra || {}),
            },
        });
    };

    // -------- DRAW drivers ----------------------------------------------------
    // Each driver returns { cleanup, action } where action(name) handles 'finish' /
    // 'delete last point' / 'cancel' from the sub-toolbar or from drawToolbar.
    const driveTool = (t: Tool, g: FeatureGroup) => {
        if (!map) return { cleanup: () => {}, action: () => {} };
        // Read live shapeOptions on each construction — picks up color picker
        // changes in /edit-control-measurement without restarting the tool.
        const getOpts = () => shapeOptionsRef.current as any;

        // Common post-creation hook: tag the layer with a stable id (+ draw
        // zoom), bind a measurement tooltip if enabled, and emit `created`
        // with that id AND the raw measurements (so the Features panel can
        // show & total areas without re-deriving them on the Python side).
        const onCreated = (layer: any, layerType: string) => {
            const id = tagFeature(layer, layerType);
            bindMeasurementTooltip(layer, layerType);
            const m = layerMeasurements(layer, layerType);
            emit('created', layerType, { id, ...m });
        };

        if (t === 'marker') {
            const onClick = (e: any) => {
                const m = new LeafletMarker(e.latlng, { icon: DEFAULT_ICON });
                m.addTo(g);
                onCreated(m, 'marker');
                setTool(null); // single-shot
            };
            map.on('click', onClick);
            return {
                cleanup: () => map.off('click', onClick),
                action: (a: string) => a === 'cancel' && setTool(null),
            };
        }

        if (t === 'text') {
            // Click drops a centered, inline-editable text caption and enters edit mode. It
            // round-trips through the same `geojson` channel as every other shape — a Point
            // feature carrying `kind:"text"` + the caption style in `properties`.
            const onClick = (e: any) => {
                const opts = getOpts();
                const st = { ...TEXT_DEFAULTS };
                // Use the toolbar color for the text unless it's a vector-ish green default.
                if (opts.color && opts.color !== '#2f9e44') st.color = opts.color;
                const m = new LeafletMarker(e.latlng, {
                    icon: makeTextIcon('', st),
                    bubblingMouseEvents: false,
                } as any);
                m.addTo(g);
                tagFeature(m, 'text', { kind: 'text', text: '', ...st });
                beginTextEdit(map, m, /* isNew */ true, emit);
                setTool(null); // single-shot
            };
            map.on('click', onClick);
            return {
                cleanup: () => map.off('click', onClick),
                action: (a: string) => a === 'cancel' && setTool(null),
            };
        }

        if (t === 'circlemarker') {
            const onClick = (e: any) => {
                const cm = new LeafletCircleMarker(e.latlng, { ...getOpts(), radius: 10 });
                cm.addTo(g);
                onCreated(cm, 'circlemarker');
                setTool(null);
            };
            map.on('click', onClick);
            return {
                cleanup: () => map.off('click', onClick),
                action: (a: string) => a === 'cancel' && setTool(null),
            };
        }

        if (t === 'polyline' || t === 'polygon') {
            const closed = t === 'polygon';
            const opts = getOpts();   // captured at first click below; rubber band reuses
            let working: LeafletPolyline | null = null;
            // Live visuals during drawing: small square handles at each clicked vertex,
            // a dashed rubber-band line from the last vertex to the cursor, and a tooltip
            // that follows the cursor with state-dependent guidance.
            const vertexHandles: LeafletMarker[] = [];
            let rubberBand: LeafletPolyline | null = null;
            const mapContainer = (map as any)._container as HTMLElement;
            const tip = document.createElement('div');
            tip.className = 'dl2-draw-tooltip';
            tip.style.display = 'none';
            mapContainer.appendChild(tip);

            const vertexCount = () =>
                !working
                    ? 0
                    : closed
                    ? (working.getLatLngs() as any[])[0]?.length || 0
                    : (working.getLatLngs() as any[])?.length || 0;

            const lastVertex = () =>
                !working
                    ? null
                    : closed
                    ? (working.getLatLngs() as any[])[0]?.slice(-1)[0]
                    : (working.getLatLngs() as any[])?.slice(-1)[0];

            const updateTipText = () => {
                const n = vertexCount();
                if (n === 0) tip.textContent = closed
                    ? 'Click to start drawing the polygon'
                    : 'Click to start drawing';
                else if (n < 2) tip.textContent = 'Click for next point';
                else tip.textContent = closed
                    ? 'Click first point or double-click to close this shape'
                    : 'Click for next point — double-click to finish';
            };
            updateTipText();

            const addVertexHandle = (latlng: any) => {
                const m = new LeafletMarker(latlng, {
                    icon: VERTEX_PREVIEW_ICON,
                    interactive: false,
                    keyboard: false,
                } as any);
                m.addTo(map);
                vertexHandles.push(m);
            };

            const onPointerMove = (e: any) => {
                // Position the cursor-following guide tooltip in container space.
                const cp = e.containerPoint;
                if (cp) {
                    tip.style.left = cp.x + 'px';
                    tip.style.top = cp.y + 'px';
                    tip.style.display = '';
                }
                // Update the rubber-band preview line.
                if (rubberBand) {
                    const last = lastVertex();
                    if (last) rubberBand.setLatLngs([last, e.latlng]);
                }
            };
            const onPointerOut = () => {
                tip.style.display = 'none';
            };

            const teardownVisuals = () => {
                if (rubberBand) {
                    rubberBand.removeFrom(map);
                    rubberBand = null;
                }
                vertexHandles.forEach((h) => h.remove());
                vertexHandles.length = 0;
                if (tip.parentNode) tip.parentNode.removeChild(tip);
            };

            const finish = () => {
                if (!working) {
                    setTool(null);
                    return;
                }
                const committed = working;
                working = null;
                committed.removeFrom(map); // detach the preview…
                teardownVisuals();
                g.addLayer(committed); // …then commit into the FeatureGroup.
                onCreated(committed, t);
                setTool(null);
            };
            const cancel = () => {
                if (working) {
                    working.removeFrom(map);
                    working = null;
                }
                teardownVisuals();
                setTool(null);
            };
            const deleteLast = () => {
                if (!working) return;
                if (closed) {
                    const rings = working.getLatLngs() as any[];
                    if (rings[0] && rings[0].length > 0) {
                        rings[0].pop();
                        working.setLatLngs(rings);
                    }
                } else {
                    const arr = working.getLatLngs() as any[];
                    if (arr.length > 0) {
                        arr.pop();
                        working.setLatLngs(arr);
                    }
                }
                const last = vertexHandles.pop();
                if (last) last.remove();
                updateTipText();
                // Re-anchor the rubber-band's start (or remove it if no vertices remain).
                if (rubberBand) {
                    const lv = lastVertex();
                    if (lv) rubberBand.setLatLngs([lv, lv]);
                    else {
                        rubberBand.removeFrom(map);
                        rubberBand = null;
                    }
                }
                if (vertexCount() === 0 && working) {
                    working.removeFrom(map);
                    working = null;
                }
            };

            const onClick = (e: any) => {
                if (!working) {
                    working = closed
                        ? new LeafletPolygon([[e.latlng] as any], opts)
                        : new LeafletPolyline([e.latlng], opts);
                    (working as any).addTo(map);
                    rubberBand = new LeafletPolyline([e.latlng, e.latlng], {
                        color: opts.color || '#2f9e44',
                        weight: 2,
                        dashArray: '5,7',
                        interactive: false,
                        opacity: 0.7,
                    } as any);
                    rubberBand.addTo(map);
                } else if (closed) {
                    const rings = working.getLatLngs() as any[];
                    rings[0].push(e.latlng);
                    working.setLatLngs(rings);
                } else {
                    working.addLatLng(e.latlng);
                }
                addVertexHandle(e.latlng);
                updateTipText();
            };
            const onDbl = () => finish();
            (map as any).doubleClickZoom.disable();
            map.on('click', onClick);
            map.on('dblclick', onDbl);
            map.on('pointermove', onPointerMove);
            map.on('pointerout', onPointerOut);
            return {
                cleanup: () => {
                    map.off('click', onClick);
                    map.off('dblclick', onDbl);
                    map.off('pointermove', onPointerMove);
                    map.off('pointerout', onPointerOut);
                    (map as any).doubleClickZoom.enable();
                    if (working) {
                        working.removeFrom(map);
                        working = null;
                    }
                    teardownVisuals();
                },
                action: (a: string) => {
                    if (a === 'finish') finish();
                    else if (a === 'cancel') cancel();
                    else if (a === 'delete last point') deleteLast();
                },
            };
        }

        if (t === 'rectangle') {
            // Live preview: after the first corner click, draw a dashed Rectangle that
            // tracks the cursor on every pointermove so the user sees the shape they're
            // about to commit. Same UX shape as the polyline/polygon rubber-band — a
            // cursor-following tooltip narrates each step and reads out the live area
            // in the configured unit system.
            let firstCorner: any = null;
            let preview: LeafletRectangle | null = null;
            let currentAreaM2 = 0;
            const mapContainer = (map as any)._container as HTMLElement;
            const tip = document.createElement('div');
            tip.className = 'dl2-draw-tooltip';
            tip.style.display = 'none';
            mapContainer.appendChild(tip);

            const updateTipText = () => {
                if (!firstCorner) tip.textContent = 'Click to set the first corner';
                else if (currentAreaM2 > 0)
                    tip.textContent = `Area ${formatArea(currentAreaM2, unitsRef.current)} — click to finish`;
                else tip.textContent = 'Click to set the opposite corner';
            };
            updateTipText();

            const onPointerMove = (e: any) => {
                const cp = e.containerPoint;
                if (cp) {
                    tip.style.left = cp.x + 'px';
                    tip.style.top = cp.y + 'px';
                    tip.style.display = '';
                }
                if (!firstCorner) return;
                const bounds = new LatLngBounds(firstCorner, e.latlng);
                if (!preview) {
                    preview = new LeafletRectangle(bounds as any, {
                        color: getOpts().color || '#2f9e44',
                        weight: 2,
                        dashArray: '5,7',
                        fill: true,
                        fillOpacity: 0.1,
                        interactive: false,
                    } as any);
                    preview.addTo(map);
                } else {
                    preview.setBounds(bounds);
                }
                // Geodesic width × height — approximate but close enough for small to
                // moderate rectangles. `map.distance` uses Leaflet's CRS (spherical
                // earth), so the readout matches what other tools report.
                const nw = bounds.getNorthWest();
                const ne = bounds.getNorthEast();
                const sw = bounds.getSouthWest();
                const widthM = (map as any).distance(nw, ne);
                const heightM = (map as any).distance(nw, sw);
                currentAreaM2 = widthM * heightM;
                updateTipText();
            };
            const onPointerOut = () => {
                tip.style.display = 'none';
            };

            const teardownVisuals = () => {
                if (preview) {
                    preview.removeFrom(map);
                    preview = null;
                }
                if (tip.parentNode) tip.parentNode.removeChild(tip);
            };

            const cancel = () => {
                firstCorner = null;
                currentAreaM2 = 0;
                teardownVisuals();
                setTool(null);
            };

            const onClick = (e: any) => {
                if (!firstCorner) {
                    firstCorner = e.latlng;
                    updateTipText();
                    return;
                }
                const bounds = new LatLngBounds(firstCorner, e.latlng);
                const r = new LeafletRectangle(bounds as any, getOpts());
                r.addTo(g);
                onCreated(r, 'rectangle');
                firstCorner = null;
                currentAreaM2 = 0;
                teardownVisuals();
                setTool(null);
            };
            map.on('click', onClick);
            map.on('pointermove', onPointerMove);
            map.on('pointerout', onPointerOut);
            return {
                cleanup: () => {
                    map.off('click', onClick);
                    map.off('pointermove', onPointerMove);
                    map.off('pointerout', onPointerOut);
                    teardownVisuals();
                },
                action: (a: string) => a === 'cancel' && cancel(),
            };
        }

        if (t === 'circle') {
            // Live preview: after the center click, draw a dashed Circle whose radius
            // tracks the cursor, plus a thin dashed line from center to cursor. The
            // tooltip reads out the live radius in the configured unit system (m/km
            // or ft/mi) so the user knows the scale before committing.
            let center: any = null;
            let preview: LeafletCircle | null = null;
            let radiusLine: LeafletPolyline | null = null;
            let currentRadius = 0;
            const mapContainer = (map as any)._container as HTMLElement;
            const tip = document.createElement('div');
            tip.className = 'dl2-draw-tooltip';
            tip.style.display = 'none';
            mapContainer.appendChild(tip);

            const updateTipText = () => {
                if (!center) tip.textContent = 'Click to set the center';
                else if (currentRadius > 0)
                    tip.textContent = `Radius ${formatDistance(currentRadius, unitsRef.current)} — click to finish`;
                else tip.textContent = 'Click to set the radius';
            };
            updateTipText();

            const onPointerMove = (e: any) => {
                const cp = e.containerPoint;
                if (cp) {
                    tip.style.left = cp.x + 'px';
                    tip.style.top = cp.y + 'px';
                    tip.style.display = '';
                }
                if (!center) return;
                currentRadius = (map as any).distance(center, e.latlng);
                if (!preview) {
                    preview = new LeafletCircle(center, {
                        radius: currentRadius,
                        color: getOpts().color || '#2f9e44',
                        weight: 2,
                        dashArray: '5,7',
                        fill: true,
                        fillOpacity: 0.1,
                        interactive: false,
                    } as any);
                    preview.addTo(map);
                } else {
                    preview.setRadius(currentRadius);
                }
                if (!radiusLine) {
                    radiusLine = new LeafletPolyline([center, e.latlng], {
                        color: getOpts().color || '#2f9e44',
                        weight: 1,
                        dashArray: '3,5',
                        opacity: 0.55,
                        interactive: false,
                    } as any);
                    radiusLine.addTo(map);
                } else {
                    radiusLine.setLatLngs([center, e.latlng]);
                }
                updateTipText();
            };
            const onPointerOut = () => {
                tip.style.display = 'none';
            };

            const teardownVisuals = () => {
                if (preview) {
                    preview.removeFrom(map);
                    preview = null;
                }
                if (radiusLine) {
                    radiusLine.removeFrom(map);
                    radiusLine = null;
                }
                if (tip.parentNode) tip.parentNode.removeChild(tip);
            };

            const cancel = () => {
                center = null;
                currentRadius = 0;
                teardownVisuals();
                setTool(null);
            };

            const onClick = (e: any) => {
                if (!center) {
                    center = e.latlng;
                    updateTipText();
                    return;
                }
                const radius = (map as any).distance(center, e.latlng);
                const c = new LeafletCircle(center, { ...getOpts(), radius });
                c.addTo(g);
                onCreated(c, 'circle');
                center = null;
                currentRadius = 0;
                teardownVisuals();
                setTool(null);
            };
            map.on('click', onClick);
            map.on('pointermove', onPointerMove);
            map.on('pointerout', onPointerOut);
            return {
                cleanup: () => {
                    map.off('click', onClick);
                    map.off('pointermove', onPointerMove);
                    map.off('pointerout', onPointerOut);
                    teardownVisuals();
                },
                action: (a: string) => a === 'cancel' && cancel(),
            };
        }

        return { cleanup: () => {}, action: () => {} };
    };

    // Drive the currently active tool; cleanup when it changes / clears.
    useEffect(() => {
        const g = groupRef.current;
        if (!map || !g) return;
        const mapEl = (map as any)._container as HTMLElement | undefined;
        if (mapEl) mapEl.style.cursor = tool ? 'crosshair' : '';
        // Emit the externally visible activeTool so /edit-control-measurement can
        // open its popover when a draw icon is clicked.
        if (setProps) setProps({ activeTool: tool });
        if (!tool) {
            toolActionRef.current = null;
            return;
        }
        // Activating a draw tool cancels any in-progress edit/remove.
        if (editMode) setEditMode(null);
        const driver = driveTool(tool, g);
        toolActionRef.current = driver.action;
        return () => {
            driver.cleanup();
            toolActionRef.current = null;
            if (mapEl) mapEl.style.cursor = '';
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [tool]);

    // -------- EDIT / REMOVE drivers ------------------------------------------
    const startEdit = () => {
        const g = groupRef.current;
        if (!g) return;
        editSnapshotRef.current = g.toGeoJSON();
        // While in edit mode, layers also become click-selectable so a page-level
        // popover can react. We stop event bubbling so the map's click doesn't fire
        // when the user clicks a feature (the map click is reserved for "deselect").
        const wiredClicks: { layer: any; h: (e: any) => void }[] = [];
        const wireClick = (layer: any) => {
            const id = layer.feature?.properties?._dl2_id;
            const layerType = layer.feature?.properties?._dl2_type || 'shape';
            if (!id) return;
            const originalBubbling = layer.options.bubblingMouseEvents;
            layer.options.bubblingMouseEvents = false;
            const h = (e: any) => {
                // DomEvent.stop = stopPropagation + preventDefault (close enough; click
                // has no default action on shape SVG that we care about preserving).
                if (e?.originalEvent) DomEvent.stop(e.originalEvent);
                featureClickCountRef.current += 1;
                setProps && setProps({
                    featureClick: {
                        id,
                        layerType,
                        n_clicks: featureClickCountRef.current,
                    },
                });
            };
            layer.on('click', h);
            wiredClicks.push({ layer, h });
            (layer as any)._dl2_origBubbling = originalBubbling;
        };
        // Attach handles per layer: markers become draggable; polylines/polygons get a
        // small DivIcon marker at each vertex that updates the underlying latlngs on drag.
        const handles: LeafletMarker[] = [];
        // After a vertex / center / edge handle drag ends, rebind the layer's
        // measurement tooltip (area changed) and emit a `geometry-changed`
        // action so the Python features list updates without waiting for Save.
        const onGeometryChanged = (layer: any) => {
            const layerType = layer.feature?.properties?._dl2_type || 'shape';
            const id = layer.feature?.properties?._dl2_id;
            bindMeasurementTooltip(layer, layerType);
            const m = layerMeasurements(layer, layerType);
            emit('geometry-changed', layerType, { id, ...m });
        };

        g.eachLayer((layer: any) => {
            wireClick(layer);
            if (layer instanceof LeafletMarker) {
                try { (layer as any).dragging?.enable(); } catch (e) {}
                // Markers don't have area, but their position is significant —
                // emit on dragend so consumers can react. No tooltip rebind
                // needed (markers don't carry a measurement label).
                const onMarkerDragEnd = () => {
                    const props = (layer as any).feature?.properties || {};
                    const layerType = props._dl2_type || 'marker';
                    const id = props._dl2_id;
                    if (id) emit('geometry-changed', layerType, { id, area_m2: 0, length_m: 0 });
                };
                layer.on('dragend', onMarkerDragEnd);
                (layer as any)._dl2_onDragEnd = onMarkerDragEnd;
                // Text captions: double-click in edit mode re-opens the inline editor.
                if ((layer as any).feature?.properties?.kind === 'text') {
                    const onTextDbl = () => beginTextEdit(map, layer, /* isNew */ false, emit);
                    layer.on('dblclick', onTextDbl);
                    (layer as any)._dl2_onTextDbl = onTextDbl;
                }
            } else if (layer instanceof LeafletCircle) {
                // Circles need bespoke handles — vertex handles wouldn't work
                // (they're round, with no vertices). We give them two:
                //   1. center handle: drag MOVES the whole circle (the edge
                //      handle follows so the radius stays constant);
                //   2. edge handle: drag RESIZES via setRadius(distance(
                //      center, edgeHandle.latlng)).
                const ch = new LeafletMarker(layer.getLatLng(), {
                    icon: VERTEX_ICON, draggable: true,
                } as any);
                const eh = new LeafletMarker(
                    pointEastOf(layer.getLatLng(), layer.getRadius()),
                    { icon: VERTEX_ICON, draggable: true } as any
                );
                ch.on('drag', () => {
                    const newC = ch.getLatLng();
                    const oldC = layer.getLatLng();
                    const dLat = newC.lat - oldC.lat;
                    const dLng = newC.lng - oldC.lng;
                    layer.setLatLng(newC);
                    const e = eh.getLatLng();
                    eh.setLatLng([e.lat + dLat, e.lng + dLng] as any);
                });
                eh.on('drag', () => {
                    const newR = (map as any).distance(layer.getLatLng(), eh.getLatLng());
                    if (newR > 0) layer.setRadius(newR);
                });
                ch.on('dragend', () => onGeometryChanged(layer));
                eh.on('dragend', () => onGeometryChanged(layer));
                ch.addTo(map!);
                eh.addTo(map!);
                handles.push(ch, eh);
            } else if (layer instanceof LeafletPolyline) {
                const isPoly = layer instanceof LeafletPolygon;
                const latlngs = (
                    isPoly ? (layer.getLatLngs() as any[])[0] : (layer.getLatLngs() as any[])
                ) as any[];
                latlngs.forEach((ll: any, i: number) => {
                    const h = new LeafletMarker(ll, {
                        icon: VERTEX_ICON,
                        draggable: true,
                    } as any);
                    (h as any)._dl2Layer = layer;
                    (h as any)._dl2Index = i;
                    h.on('drag', () => {
                        const pos = h.getLatLng();
                        if (isPoly) {
                            const rings = (layer.getLatLngs() as any[]).map((r: any[]) => r.slice());
                            rings[0][i] = pos;
                            layer.setLatLngs(rings);
                        } else {
                            const arr = (layer.getLatLngs() as any[]).slice();
                            arr[i] = pos;
                            layer.setLatLngs(arr);
                        }
                    });
                    h.on('dragend', () => onGeometryChanged(layer));
                    h.addTo(map!);
                    handles.push(h);
                });
            }
        });
        editCleanupRef.current = () => {
            handles.forEach((h) => h.remove());
            wiredClicks.forEach(({ layer, h }) => {
                try { layer.off('click', h); } catch (e) {}
                // restore Leaflet's default click-bubbles-to-map behavior.
                layer.options.bubblingMouseEvents = (layer as any)._dl2_origBubbling ?? true;
                delete (layer as any)._dl2_origBubbling;
            });
            g.eachLayer((layer: any) => {
                if (layer instanceof LeafletMarker) {
                    try { layer.dragging?.disable(); } catch (e) {}
                    const dh = (layer as any)._dl2_onDragEnd;
                    if (dh) { try { layer.off('dragend', dh); } catch (e) {} }
                    delete (layer as any)._dl2_onDragEnd;
                    const td = (layer as any)._dl2_onTextDbl;
                    if (td) { try { layer.off('dblclick', td); } catch (e) {} }
                    delete (layer as any)._dl2_onTextDbl;
                }
            });
        };
    };

    const startRemove = () => {
        const g = groupRef.current;
        if (!g) return;
        const wired: { layer: any; h: () => void }[] = [];
        const wire = (layer: any) => {
            const h = () => {
                g.removeLayer(layer);
                emit('deleted', 'shape');
            };
            layer.on('click', h);
            wired.push({ layer, h });
        };
        g.eachLayer(wire);
        const onAdd = (e: any) => wire(e.layer);
        g.on('layeradd', onAdd);
        editCleanupRef.current = () => {
            g.off('layeradd', onAdd);
            wired.forEach(({ layer, h }) => {
                try { layer.off('click', h); } catch (e) {}
            });
        };
    };

    const exitEdit = (saved: boolean) => {
        const g = groupRef.current;
        if (editCleanupRef.current) {
            editCleanupRef.current();
            editCleanupRef.current = null;
        }
        if (!saved && editSnapshotRef.current && g) {
            // Revert to snapshot — clear & re-add layers from the GeoJSON. Force the
            // working DEFAULT_ICON for any Point features; otherwise GeoJSON's auto-created
            // markers fall back to Leaflet's stale shared Icon.Default (created at module-
            // load time before our base64 config) and 404 with broken "Mark" alt-text.
            g.clearLayers();
            new LeafletGeoJSON(editSnapshotRef.current, {
                pointToLayer: (f: any, latlng: any) => {
                    // Rebuild text captions as text icons (not pins); everything else as the
                    // working DEFAULT_ICON (avoids Leaflet's stale shared Icon.Default 404).
                    const p = f?.properties || {};
                    if (p.kind === 'text') {
                        const st = {
                            color: p.color || TEXT_DEFAULTS.color,
                            fontSize: p.fontSize || TEXT_DEFAULTS.fontSize,
                            fontFamily: p.fontFamily || TEXT_DEFAULTS.fontFamily,
                            fontWeight: p.fontWeight || TEXT_DEFAULTS.fontWeight,
                        };
                        const m = new LeafletMarker(latlng, {
                            icon: makeTextIcon(p.text || '', st), bubblingMouseEvents: false,
                        } as any);
                        requestAnimationFrame(() => centerTextIcon(m));
                        return m;
                    }
                    return new LeafletMarker(latlng, { icon: DEFAULT_ICON });
                },
            } as any).eachLayer((l: any) => g.addLayer(l));
            emit('cancelled', 'all');
        } else if (saved) {
            emit('edited', 'all');
        }
        editSnapshotRef.current = null;
        setEditMode(null);
    };

    // Drive edit/remove mode.
    useEffect(() => {
        if (!map || !groupRef.current) return;
        // Emit the externally visible activeMode for pages that need to react.
        if (setProps) setProps({ activeMode: editMode });
        if (!editMode) return;
        // Entering edit/remove cancels any active draw tool.
        if (tool) setTool(null);
        if (editMode === 'edit') startEdit();
        else if (editMode === 'remove') startRemove();
        // No cleanup on dep change here — exitEdit handles teardown explicitly via the
        // sub-toolbar buttons or Python action; switching directly between edit/remove
        // (rare) would just leak — guarded against here:
        return () => {
            if (editCleanupRef.current) {
                editCleanupRef.current();
                editCleanupRef.current = null;
                editSnapshotRef.current = null;
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [editMode]);

    // -------- Python -> control triggers --------------------------------------
    const lastDrawTriggerRef = useRef<number>(-1);
    useEffect(() => {
        if (!drawToolbar || drawToolbar.n_clicks === undefined) return;
        if (drawToolbar.n_clicks === lastDrawTriggerRef.current) return;
        lastDrawTriggerRef.current = drawToolbar.n_clicks;
        if (drawToolbar.mode) setTool(drawToolbar.mode);
        if (drawToolbar.action && toolActionRef.current) {
            toolActionRef.current(drawToolbar.action);
        }
    }, [drawToolbar]);

    // Python -> control: per-feature update (recolor / rename / remove). Bumping
    // n_clicks guarantees the prop registers as changed across consecutive identical
    // payloads (e.g. setting the same color twice).
    const lastFeatureUpdateRef = useRef<number>(-1);
    useEffect(() => {
        if (!featureUpdate || featureUpdate.n_clicks === undefined) return;
        if (featureUpdate.n_clicks === lastFeatureUpdateRef.current) return;
        lastFeatureUpdateRef.current = featureUpdate.n_clicks;

        const layer = findById(featureUpdate.id);
        const g = groupRef.current;
        if (!layer || !g) return;
        const layerType = layer.feature?.properties?._dl2_type || 'shape';

        if (featureUpdate.remove) {
            g.removeLayer(layer);
            emit('deleted', layerType, { id: featureUpdate.id });
            return;
        }
        if (featureUpdate.style && typeof layer.setStyle === 'function') {
            try { layer.setStyle(featureUpdate.style); } catch (e) {}
        }
        if (featureUpdate.properties) {
            layer.feature.properties = {
                ...(layer.feature.properties || {}),
                ...featureUpdate.properties,
            };
            // Rebind tooltip so a name change is reflected immediately in the
            // permanent label (and a name-clear hides the label cleanly).
            bindMeasurementTooltip(layer, layerType);
        }
        const m = layerMeasurements(layer, layerType);
        emit('restyled', layerType, { id: featureUpdate.id, ...m });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [featureUpdate]);

    const lastEditTriggerRef = useRef<number>(-1);
    useEffect(() => {
        if (!editToolbar || editToolbar.n_clicks === undefined) return;
        if (editToolbar.n_clicks === lastEditTriggerRef.current) return;
        lastEditTriggerRef.current = editToolbar.n_clicks;
        if (editToolbar.mode) setEditMode(editToolbar.mode);
        if (editToolbar.action) {
            if (editToolbar.action === 'clear all') {
                const g = groupRef.current;
                if (g) {
                    g.clearLayers();
                    emit('cleared', 'all');
                }
                setEditMode(null);
            } else if (editToolbar.action === 'save') exitEdit(true);
            else if (editToolbar.action === 'cancel') exitEdit(false);
        }
    }, [editToolbar]);

    // -------- UI --------------------------------------------------------------
    const tools = ALL_TOOLS.filter(drawEnabled);
    const showEditSection = shapeCount > 0 && (editEnabled('edit') || editEnabled('remove'));

    return map && containerRef.current
        ? ReactDOM.createPortal(
              <div className="dl2-edit-ui">
                  {/* DRAW section */}
                  <div className="dl2-edit-section">
                      {tools.map((t) => (
                          <button
                              key={t}
                              className={`dl2-edit-btn ${tool === t ? 'active' : ''}`}
                              title={TOOL_ICONS[t].label}
                              aria-pressed={tool === t}
                              onClick={() => setTool(tool === t ? null : t)}
                          >
                              <iconify-icon icon={TOOL_ICONS[t].icon} width="18"></iconify-icon>
                          </button>
                      ))}
                  </div>

                  {/* EDIT section — only when shapes exist */}
                  {showEditSection && (
                      <div className="dl2-edit-section dl2-edit-section-modify">
                          {editEnabled('edit') && (
                              <button
                                  className={`dl2-edit-btn ${editMode === 'edit' ? 'active' : ''}`}
                                  title={EDIT_ICONS.edit.label}
                                  aria-pressed={editMode === 'edit'}
                                  onClick={() => setEditMode(editMode === 'edit' ? null : 'edit')}
                              >
                                  <iconify-icon icon={EDIT_ICONS.edit.icon} width="18"></iconify-icon>
                              </button>
                          )}
                          {editEnabled('remove') && (
                              <button
                                  className={`dl2-edit-btn danger ${editMode === 'remove' ? 'active' : ''}`}
                                  title={EDIT_ICONS.remove.label}
                                  aria-pressed={editMode === 'remove'}
                                  onClick={() => setEditMode(editMode === 'remove' ? null : 'remove')}
                              >
                                  <iconify-icon icon={EDIT_ICONS.remove.icon} width="18"></iconify-icon>
                              </button>
                          )}
                      </div>
                  )}

                  {/* Contextual sub-toolbar — appears alongside the icon strip while a tool/mode is active */}
                  {(tool || editMode) && (
                      <div className="dl2-edit-actions">
                          {tool && (tool === 'polyline' || tool === 'polygon') && (
                              <>
                                  <button
                                      className="dl2-edit-action-btn primary"
                                      onClick={() => toolActionRef.current?.('finish')}
                                  >
                                      Finish
                                  </button>
                                  <button
                                      className="dl2-edit-action-btn"
                                      onClick={() => toolActionRef.current?.('delete last point')}
                                  >
                                      Delete last point
                                  </button>
                              </>
                          )}
                          {tool && (
                              <button
                                  className="dl2-edit-action-btn"
                                  onClick={() => toolActionRef.current?.('cancel')}
                              >
                                  Cancel
                              </button>
                          )}
                          {editMode === 'edit' && (
                              <>
                                  <button className="dl2-edit-action-btn primary" onClick={() => exitEdit(true)}>
                                      Save
                                  </button>
                                  <button className="dl2-edit-action-btn" onClick={() => exitEdit(false)}>
                                      Cancel
                                  </button>
                              </>
                          )}
                          {editMode === 'remove' && (
                              <>
                                  <button
                                      className="dl2-edit-action-btn danger"
                                      onClick={() => {
                                          const g = groupRef.current;
                                          if (g) {
                                              g.clearLayers();
                                              emit('cleared', 'all');
                                          }
                                          setEditMode(null);
                                      }}
                                  >
                                      Clear all
                                  </button>
                                  <button className="dl2-edit-action-btn" onClick={() => exitEdit(false)}>
                                      Cancel
                                  </button>
                              </>
                          )}
                      </div>
                  )}
              </div>,
              containerRef.current
          )
        : null;
};

// Unit-aware formatters used by the rectangle (area) and circle (radius) live previews.
// Each auto-picks the largest readable unit for the magnitude — so a 50 m radius reads
// "50 m" (not "0.05 km") and 50,000 m² reads "5.00 ha" (not "50,000 m²").
const M_TO_FT = 3.28084;            // 1 m
const MI_IN_M = 1609.344;           // 1 mile
const M2_TO_FT2 = 10.7639104;       // 1 m²
const ACRE_IN_M2 = 4046.8564224;    // 1 acre = 43,560 ft²
const MI2_IN_M2 = 2_589_988.110336; // 1 mi²  = 640 acres
const HA_IN_M2 = 10_000;            // 1 hectare
const KM2_IN_M2 = 1_000_000;        // 1 km²

type UnitSystem = 'metric' | 'imperial';

const formatDistance = (m: number, units: UnitSystem): string => {
    if (units === 'imperial') {
        const ft = m * M_TO_FT;
        return m >= MI_IN_M ? `${(m / MI_IN_M).toFixed(2)} mi` : `${Math.round(ft)} ft`;
    }
    return m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${Math.round(m)} m`;
};

const formatArea = (m2: number, units: UnitSystem): string => {
    if (units === 'imperial') {
        if (m2 >= MI2_IN_M2) return `${(m2 / MI2_IN_M2).toFixed(2)} mi²`;
        if (m2 >= ACRE_IN_M2) return `${(m2 / ACRE_IN_M2).toFixed(2)} acres`;
        return `${Math.round(m2 * M2_TO_FT2).toLocaleString()} ft²`;
    }
    if (m2 >= KM2_IN_M2) return `${(m2 / KM2_IN_M2).toFixed(2)} km²`;
    if (m2 >= HA_IN_M2) return `${(m2 / HA_IN_M2).toFixed(2)} ha`;
    return `${Math.round(m2).toLocaleString()} m²`;
};

// Initial position for the circle's edge handle in edit mode: a point `meters`
// east of `center`. After the user starts dragging, the handle's angular offset
// changes naturally — only the initial placement is east-by-default.
const pointEastOf = (center: any, meters: number) => {
    const metersPerLngDeg = 111_320 * Math.cos((center.lat * Math.PI) / 180);
    if (!isFinite(metersPerLngDeg) || metersPerLngDeg === 0) return center;
    return { lat: center.lat, lng: center.lng + meters / metersPerLngDeg };
};

// Spherical polygon area on the WGS84 reference sphere — approximate but good
// enough for showcase scales (sub-km error at 1000 km polygons). Used to label
// drawn polygons in the showMeasurementTooltips=true mode. Source: the standard
// spherical-excess formula via lng-shifted trapezoidal sum.
const polygonAreaM2 = (latlngs: any[], R: number = 6378137): number => {
    if (!latlngs || latlngs.length < 3) return 0;
    const toRad = (d: number) => (d * Math.PI) / 180;
    let total = 0;
    for (let i = 0; i < latlngs.length; i++) {
        const a = latlngs[i];
        const b = latlngs[(i + 1) % latlngs.length];
        total +=
            toRad(b.lng - a.lng) *
            (2 + Math.sin(toRad(a.lat)) + Math.sin(toRad(b.lat)));
    }
    return Math.abs((total * R * R) / 2);
};

// Minimal HTML-escape for the optional name we render inside the tooltip text
// (Leaflet's bindTooltip treats string content as HTML).
const escHtml = (s: string) =>
    String(s).replace(/[&<>"']/g, (c) =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' } as any)[c]);

// ---- `text` tool: a content-sized, inline-editable caption DivIcon ----------------------
type TextStyle = { color: string; fontSize: number; fontFamily: string; fontWeight: number | string };

const textStyleStr = (st: TextStyle) =>
    `color:${st.color};font-size:${st.fontSize}px;font-family:${st.fontFamily};font-weight:${st.fontWeight};`;

const makeTextIcon = (text: string, st: TextStyle) =>
    new DivIcon({
        className: 'dl2-edit-text-icon',
        html: `<div class="dl2-edit-text" style="${textStyleStr(st)}">${escHtml(text)}</div>`,
        iconSize: [0, 0],
        iconAnchor: [0, 0],
    } as any);

// Centre the (content-sized) text icon on its latlng by undoing the iconSize:[0,0] inline
// width/height and applying a half-size negative margin (Leaflet leaves margins alone).
const centerTextIcon = (marker: any) => {
    const el = marker._icon;
    if (!el) return;
    el.style.width = '';
    el.style.height = '';
    el.style.marginLeft = `${-(el.offsetWidth || 0) / 2}px`;
    el.style.marginTop = `${-(el.offsetHeight || 0) / 2}px`;
};

// Enter inline edit on a text caption marker: focus its contentEditable div, swallow map
// interactions while editing, and on blur / Enter commit the text into feature.properties
// and emit through the geojson channel. A brand-new empty caption is discarded on blur.
const beginTextEdit = (
    map: any,
    marker: any,
    isNew: boolean,
    emit: (action: string, layerType: string, extra?: object) => void
) => {
    const icon = marker._icon;
    if (!icon) {
        // _icon not attached yet (freshly added) — retry next frame.
        requestAnimationFrame(() => beginTextEdit(map, marker, isNew, emit));
        return;
    }
    const div = icon.querySelector('.dl2-edit-text') as HTMLElement | null;
    if (!div) return;
    centerTextIcon(marker);
    const wasDraggable = !!marker.dragging?.enabled?.();
    try { marker.dragging?.disable(); } catch (e) {}
    try { map.doubleClickZoom.disable(); } catch (e) {}
    div.classList.add('is-editing');
    div.setAttribute('contenteditable', 'true');

    const stop = (ev: Event) => ev.stopPropagation();
    const swallowTypes = ['pointerdown', 'mousedown', 'dblclick', 'wheel', 'touchstart', 'click'];
    swallowTypes.forEach((tp) => div.addEventListener(tp, stop));

    let done = false;
    const commit = () => {
        if (done) return;
        done = true;
        swallowTypes.forEach((tp) => div.removeEventListener(tp, stop));
        div.removeEventListener('keydown', onKey);
        div.removeEventListener('blur', commit);
        div.classList.remove('is-editing');
        div.removeAttribute('contenteditable');
        try { map.doubleClickZoom.enable(); } catch (e) {}
        if (wasDraggable) { try { marker.dragging?.enable(); } catch (e) {} }
        const text = (div.textContent || '').trim();
        if (isNew && !text) {
            marker.remove(); // discard an empty brand-new caption
            return;
        }
        marker.feature = marker.feature || { type: 'Feature', properties: {} };
        marker.feature.properties = { ...(marker.feature.properties || {}), text };
        centerTextIcon(marker);
        emit(isNew ? 'created' : 'edited', 'text', { id: marker.feature.properties._dl2_id });
    };
    const onKey = (ev: KeyboardEvent) => {
        ev.stopPropagation();
        if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); div.blur(); }
        else if (ev.key === 'Escape') { ev.preventDefault(); div.blur(); }
    };
    div.addEventListener('keydown', onKey);
    div.addEventListener('blur', commit);
    requestAnimationFrame(() => {
        div.focus();
        const range = document.createRange();
        range.selectNodeContents(div);
        const sel = window.getSelection();
        sel?.removeAllRanges();
        sel?.addRange(range);
    });
};

// Build the tooltip text shown on a committed shape. Returns "" for things that
// don't have a sensible measurement AND no name (markers, circlemarkers without
// a user-supplied name). If a name is present in feature.properties it's
// prepended on its own line so the user sees "Lighthouse / Area 5 acres".
const measurementLabel = (
    map: any,
    layer: any,
    layerType: string,
    units: UnitSystem
): string => {
    let measure = '';
    try {
        if (layerType === 'rectangle' || layerType === 'polygon') {
            const ring = (layer.getLatLngs() as any[])[0];
            measure = `Area ${formatArea(polygonAreaM2(ring), units)}`;
        } else if (layerType === 'circle') {
            const r = layer.getRadius();
            measure = `Radius ${formatDistance(r, units)} · Area ${formatArea(Math.PI * r * r, units)}`;
        } else if (layerType === 'polyline') {
            const pts = layer.getLatLngs() as any[];
            let total = 0;
            for (let i = 1; i < pts.length; i++) total += map.distance(pts[i - 1], pts[i]);
            measure = `Length ${formatDistance(total, units)}`;
        }
    } catch (e) { /* fall through */ }
    const name: string = layer.feature?.properties?.name || '';
    if (name && measure) return `<b>${escHtml(name)}</b><br>${measure}`;
    if (name) return `<b>${escHtml(name)}</b>`;
    return measure;
};

// Round handle used to mark vertices when in EDIT mode (draggable).
const VERTEX_ICON = new DivIcon({
    className: 'dl2-vertex-handle',
    html: '',
    iconSize: [10, 10],
    iconAnchor: [5, 5],
} as any);

// Smaller square handle used to mark each placed vertex while ACTIVELY DRAWING
// a polyline/polygon (non-draggable, just visual feedback).
const VERTEX_PREVIEW_ICON = new DivIcon({
    className: 'dl2-vertex-preview',
    html: '',
    iconSize: [8, 8],
    iconAnchor: [4, 4],
} as any);

export default EditControl;
