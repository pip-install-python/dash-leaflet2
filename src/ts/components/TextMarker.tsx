import React, { useEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import { DivIcon, DomEvent, Marker as LeafletMarker } from 'leaflet';
import { useLeafletBearing, useLeafletMap } from '../context';
import { useLayer } from '../useLayer';
import { DashComponentProps } from '../props';
import { Anchor, anchorOffset, anchorDotCss } from '../anchor';
import '../textMarker.css';

// A draggable, inline-editable, styleable text label anchored to a [lat, lng] — used
// exactly like a dl2.Marker. Under the hood it IS a Leaflet 2 Marker whose icon is a
// 0×0 anchor point with an absolutely-positioned text <div> rendered into it via a React
// portal (so any prop change / contentEditable edit is React-managed). We reuse Marker's
// drag lifecycle and its transform-reprojection trick (re-project on every map/marker move
// so rotation survives Leaflet's constant transform rewrites). When `selected`, on-canvas
// resize / rotate handles appear plus a contextual glass toolbar for typography & color —
// and every interactive edit round-trips back to Dash so a host can record it.

// Anchor type + anchorOffset live in ../anchor (shared with the editable ImageOverlay).

const FONT_OPTIONS = [
    { label: 'System', value: 'system-ui, sans-serif' },
    { label: 'Inter', value: 'Inter, system-ui, sans-serif' },
    { label: 'Helvetica', value: 'Helvetica, Arial, sans-serif' },
    { label: 'Georgia', value: 'Georgia, serif' },
    { label: 'Times', value: '"Times New Roman", Times, serif' },
    { label: 'Courier', value: '"Courier New", monospace' },
    { label: 'Verdana', value: 'Verdana, Geneva, sans-serif' },
    { label: 'Impact', value: 'Impact, Haettenschweiler, sans-serif' },
];

const MIN_FONT = 6;
const MAX_FONT = 400;

type Props = {
    /** Text anchor as [lat, lng]. Dragging the label writes it back. When omitted, the
     * label is created at the current center of the map viewport (and that position is
     * emitted back so Python has it). [MUTABLE] */
    position?: [number, number];

    /** The caption string. Double-click the label to edit it inline; the committed text
     * (on blur / Enter) is written back with `n_edits` bumped. [MUTABLE] */
    text?: string;

    /** Which point of the text box sits on `position`. One of center | top-left | top |
     * top-right | left | right | bottom-left | bottom | bottom-right. @default "center". */
    anchor?: Anchor;

    /** Text color (any CSS color / Mantine var). Editable from the toolbar. [MUTABLE] */
    color?: string;
    /** Box background behind the text ("transparent" for none). Editable from the toolbar. [MUTABLE] */
    backgroundColor?: string;
    /** Font family stack, e.g. "Inter, system-ui, sans-serif". [MUTABLE] */
    fontFamily?: string;
    /** Font size in screen px (the resize handle changes this). [MUTABLE] */
    fontSize?: number;
    /** Font weight (400 / 600 / 700 / "bold" …). [MUTABLE] */
    fontWeight?: number | string;
    /** Font style: "normal" | "italic". [MUTABLE] */
    fontStyle?: 'normal' | 'italic';
    /** Box padding in px (only visible when `backgroundColor` is set). [MUTABLE] */
    padding?: number;
    /** Corner radius of the background pill in px. @default 6. */
    borderRadius?: number;

    /** Rotation in degrees, CW from upright. The rotate handle changes this. [MUTABLE] */
    rotation?: number;
    /** Caption opacity, 0..1 — fade the whole label in/out (e.g. keyframed transitions).
     *  @default 1 [MUTABLE] */
    opacity?: number;
    /** When true the label rotates together with a rotated map (`Map.bearing`); when false
     * (default) it stays upright on screen regardless of map bearing — like a Marker. */
    rotateWithMap?: boolean;

    /** Geographic sizing. When false (default) the label is a constant screen-size HUD caption:
     * `fontSize` is literal screen px at every zoom (like a Tooltip). When true the label scales
     * with the map — its on-screen size grows/shrinks by 2^(zoom − referenceZoom) so it keeps a
     * fixed *ground* footprint as the camera flies (like a polygon's edge). [MUTABLE] */
    scaleWithZoom?: boolean;
    /** The zoom level at which `fontSize` is the literal screen px (only used when
     * `scaleWithZoom`). Defaults to the map's zoom when the label is created. [MUTABLE] */
    referenceZoom?: number;

    /** Whether the label can be dragged to a new position. @default true. */
    draggable?: boolean;
    /** Whether double-click enters inline text edit. @default true. */
    editable?: boolean;
    /** Show selection chrome (resize / rotate handles + the style toolbar). Two-way: clicking
     * the label sets it true and a map-background click clears it, so a host can also drive
     * selection from the outside. [MUTABLE] */
    selected?: boolean;
    /** Whether the contextual style toolbar is shown while selected. @default true. */
    showToolbar?: boolean;

    /** Number of times the label has been clicked. [READONLY] */
    n_clicks?: number;
    /** Number of times the label has been dragged. [READONLY] */
    n_drags?: number;
    /** Bumped on each committed text edit (fires a Dash Input even for identical text). [READONLY] */
    n_edits?: number;
} & DashComponentProps;

/**
 * TextMarker is editable, draggable, styleable text placed on the map like a Marker. Give it
 * a `position` and `text`; drag to move, double-click to edit, and (when `selected`) use the
 * on-canvas resize / rotate handles and the contextual toolbar to restyle it. Position, text,
 * rotation, font size, and color all round-trip back to Dash. When `position` is omitted the
 * label spawns at the center of the current viewport. Place it as a child of dl2.Map.
 */
const TextMarker = ({
    position,
    text = 'Text',
    anchor = 'center',
    color = '#111827',
    backgroundColor = 'transparent',
    fontFamily = 'system-ui, sans-serif',
    fontSize = 24,
    fontWeight = 600,
    fontStyle = 'normal',
    padding = 6,
    borderRadius = 6,
    rotation = 0,
    opacity = 1,
    rotateWithMap = false,
    scaleWithZoom = false,
    referenceZoom,
    draggable = true,
    editable = true,
    // `selected` is UNCONTROLLED when omitted (undefined): the marker self-manages
    // selection (click to select, map-click two-stage to deselect) and only ONE
    // TextMarker on a map is selected at a time. Pass an explicit true/false to drive
    // it from the host. [MUTABLE]
    selected,
    showToolbar = true,
    setProps,
}: Props) => {
    const map = useLeafletMap();
    const { bearing: mapBearing } = useLeafletBearing();

    // ---- local style state (instant feedback) mirrored back to Python -------------------
    // `style` is the source of truth for rendering. UI edits update it AND emit to Dash;
    // external prop changes are merged in via the echo-guarded effect below. `lastSynced`
    // tracks the value we've already reconciled with each prop so a round-tripped self-emit
    // doesn't bounce back in (the LayersControl pattern).
    const [style, setStyle] = useState({
        text, anchor, color, backgroundColor, fontFamily,
        fontSize, fontWeight, fontStyle, padding, borderRadius, rotation,
    });
    const styleRef = useRef(style);
    styleRef.current = style;
    const lastSynced = useRef<Record<string, any>>({ ...style });

    const [editing, setEditing] = useState(false);
    const editingRef = useRef(false);
    editingRef.current = editing;

    // Geographic sizing: the on-screen font is `style.fontSize * zoomScale`, where zoomScale is
    // 2^(zoom − referenceZoom) when `scaleWithZoom`, else 1 (constant screen size). referenceZoom
    // defaults to the zoom at which the label was created.
    const [zoomScale, setZoomScale] = useState(1);
    const scaleWithZoomRef = useRef(scaleWithZoom);
    scaleWithZoomRef.current = scaleWithZoom;
    const refZoomRef = useRef<number | null>(null);

    const boxRef = useRef<HTMLDivElement | null>(null);
    const clicks = useRef(0);
    const drags = useRef(0);
    const edits = useRef(0);
    const rotationRef = useRef(rotation);
    const rotateWithMapRef = useRef(rotateWithMap);
    const bearingRef = useRef(mapBearing);
    const anchorRef = useRef(anchor);
    rotationRef.current = style.rotation;
    rotateWithMapRef.current = rotateWithMap;
    bearingRef.current = mapBearing;
    anchorRef.current = style.anchor as Anchor;

    // Resolve the spawn position once: explicit prop, else the live viewport center.
    const resolvedPos = useRef<[number, number] | null>(null);
    const lastPos = useRef<[number, number] | null>(null);
    if (!resolvedPos.current) {
        if (position) resolvedPos.current = position;
        else if (map) {
            const c = map.getCenter();
            resolvedPos.current = [c.lat, c.lng];
        }
    }

    // ---- the Leaflet Marker (0×0 anchor-point icon) -------------------------------------
    const applyTransformRef = useRef<() => void>(() => {});
    const { layer, ref } = useLayer<LeafletMarker>(() => {
        const start = resolvedPos.current || [0, 0];
        const marker = new LeafletMarker(start, {
            icon: new DivIcon({
                className: 'dl2-text-marker-icon',
                html: '',
                iconSize: [0, 0],
                iconAnchor: [0, 0],
            } as any),
            draggable: !!draggable,
            // Don't bubble the click to the map, so a map-background click can mean "deselect"
            // without firing the moment you click the label itself.
            bubblingMouseEvents: false,
            keyboard: false,
        } as any);

        marker.on('click', () => {
            clicks.current += 1;
            emit({ n_clicks: clicks.current });
            if (!selectedRef.current) setSelectedLocal(true, /*emit*/ true);
        });
        marker.on('dblclick', () => {
            if (editableRef.current) startEditing();
        });
        marker.on('dragend', () => {
            drags.current += 1;
            const ll = marker.getLatLng();
            const p: [number, number] = [+ll.lat.toFixed(6), +ll.lng.toFixed(6)];
            lastPos.current = p;
            emit({ n_drags: drags.current, position: p });
        });
        return marker;
    });

    // Stable refs for values read inside once-bound Leaflet handlers.
    const selectedRef = useRef(selected);
    const editableRef = useRef(editable);
    editableRef.current = editable;

    // setProps wrapper that records what we emit so the prop echo doesn't re-enter `style`.
    const emit = (payload: Record<string, any>) => {
        Object.keys(payload).forEach((k) => {
            if (k in lastSynced.current) lastSynced.current[k] = payload[k];
        });
        setProps && setProps(payload);
    };

    // Mutate one or more style fields locally + emit them to Dash.
    const setStyleAndEmit = (patch: Partial<typeof style>) => {
        setStyle((s) => ({ ...s, ...patch }));
        emit(patch as Record<string, any>);
    };

    // ---- selection (two-way; uncontrolled when `selected` is undefined) -----------------
    const [selectedState, setSelectedState] = useState(!!selected);
    selectedRef.current = selectedState;
    const lastSelected = useRef<boolean | undefined>(selected);
    // Armed only for the single blur->map-click gesture (see the two-stage exit below);
    // reset on any OTHER way editing/selection ends so it can't get stuck (e.g. abandoning
    // an edit by clicking a different marker fires no map click to consume it).
    const exitedEditRef = useRef(false);
    const setSelectedLocal = (val: boolean, doEmit: boolean) => {
        if (!val) exitedEditRef.current = false;
        setSelectedState(val);
        // Single selection: announce so any OTHER selected TextMarker on this map
        // deselects (only one toolbar/handle set at a time).
        if (val && map) { try { (map as any).fire('dl2:tm-select', { source: ref.current }); } catch (e) {} }
        if (doEmit) {
            lastSelected.current = val;
            setProps && setProps({ selected: val });
        }
        if (!val && editingRef.current) commitEditing();
    };
    // External selected prop -> local (only when the host actually drives it).
    useEffect(() => {
        if (selected !== undefined && selected !== lastSelected.current) {
            lastSelected.current = selected;
            if (!selected) exitedEditRef.current = false;
            setSelectedState(selected);
            if (!selected && editingRef.current) commitEditing();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selected]);

    // Single-selection coordination: when ANOTHER TextMarker becomes selected, deselect
    // this one (clicking marker B doesn't fire a map click, so B can't deselect A via
    // onMapClick — this map-event bus does it).
    useEffect(() => {
        if (!map) return;
        const onOther = (e: any) => {
            if (e && e.source !== ref.current && selectedRef.current) setSelectedLocal(false, true);
        };
        (map as any).on('dl2:tm-select', onOther);
        return () => { try { (map as any).off('dl2:tm-select', onOther); } catch (err) {} };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map]);

    // Two-stage exit on a map-background click: while EDITING, the click just exits text
    // mode → "move" mode (the box blur commits; the marker stays selected); a SECOND
    // map click then deselects → back to normal map control. `exitedEditRef` swallows the
    // very click that blurred the editor so it doesn't deselect in the same gesture.
    useEffect(() => {
        if (!map) return;
        const onMapClick = () => {
            if (exitedEditRef.current) { exitedEditRef.current = false; return; }
            if (editingRef.current) { commitEditing(true); return; }  // safety: exit to move mode
            if (selectedRef.current) setSelectedLocal(false, true);   // move mode -> deselect
        };
        map.on('click', onMapClick);
        return () => { map.off('click', onMapClick); };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map]);

    // ---- Python -> local style reconciliation (echo-guarded) ----------------------------
    useEffect(() => {
        const incoming: Record<string, any> = {
            text, anchor, color, backgroundColor, fontFamily,
            fontSize, fontWeight, fontStyle, padding, borderRadius, rotation,
        };
        const patch: Record<string, any> = {};
        Object.keys(incoming).forEach((k) => {
            if (incoming[k] !== undefined && incoming[k] !== lastSynced.current[k]) {
                patch[k] = incoming[k];
                lastSynced.current[k] = incoming[k];
            }
        });
        if (Object.keys(patch).length) setStyle((s) => ({ ...s, ...patch }));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [text, anchor, color, backgroundColor, fontFamily, fontSize, fontWeight,
        fontStyle, padding, borderRadius, rotation]);

    // ---- Python -> marker position ------------------------------------------------------
    useEffect(() => {
        if (!ref.current || !position) return;
        if (lastPos.current && position[0] === lastPos.current[0] && position[1] === lastPos.current[1]) return;
        lastPos.current = position;
        ref.current.setLatLng(position);
        applyTransformRef.current();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [position]);

    // Emit the auto-spawned center position so Python records where the label landed.
    useEffect(() => {
        if (layer && !position && resolvedPos.current && !lastPos.current) {
            lastPos.current = resolvedPos.current;
            const [lat, lng] = resolvedPos.current;
            emit({ position: [+lat.toFixed(6), +lng.toFixed(6)] });
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [layer]);

    // ---- draggable toggle ---------------------------------------------------------------
    useEffect(() => {
        const m: any = ref.current;
        if (!m || !m.dragging) return;
        if (draggable && !editingRef.current) m.dragging.enable();
        else m.dragging.disable();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [draggable, layer]);

    // ---- transform: position + anchor + rotation, re-applied on every move/zoom ----------
    // The marker's icon element IS the (content-sized) text box — it must have real area so
    // Leaflet's drag picks up a pointerdown on it (a 0×0 icon never receives the drag). Leaflet
    // positions the icon's top-left at the latlng pixel; we offset it by the anchor point so the
    // requested `anchor` of the box sits on the latlng, set the rotation pivot (transform-origin)
    // to that same anchor point, and re-assert all of it on marker-move + zoom re-projection
    // (Leaflet rewrites this element's transform on those events — mirrors Marker.tsx).
    useEffect(() => {
        const marker: any = ref.current;
        if (!marker || !map) return;
        // Undo the inline width/height:0 that DivIcon's iconSize:[0,0] stamps on, so the box
        // sizes to its content (CSS sets width:max-content).
        if (marker._icon) {
            marker._icon.style.width = '';
            marker._icon.style.height = '';
        }
        const applyTransform = () => {
            const el: HTMLElement | undefined = marker._icon;
            if (!el) return;
            const eff = rotateWithMapRef.current
                ? rotationRef.current
                : rotationRef.current - bearingRef.current;
            const [ox, oy] = anchorOffset(anchorRef.current, el.offsetWidth, el.offsetHeight);
            // Anchor offset via MARGIN (not baked into translate3d): Leaflet's own drag rewrites
            // the icon transform to the raw latlng pixel with no offset, so if we subtracted the
            // offset in translate3d the two would disagree mid-drag. Margin is applied in layout,
            // untouched by Leaflet, so the box stays anchored correctly even on Leaflet's frames.
            el.style.marginLeft = `${-ox}px`;
            el.style.marginTop = `${-oy}px`;
            el.style.transformOrigin = `${ox}px ${oy}px`;
            const pt = (map as any).latLngToLayerPoint(marker.getLatLng());
            el.style.transform =
                `translate3d(${Math.round(pt.x)}px, ${Math.round(pt.y)}px, 0) rotate(${eff}deg)`;
            (el.style as any).rotate = '';
        };
        applyTransformRef.current = applyTransform;
        applyTransform();
        // The first synchronous call may measure an empty box (its text/handles are filled in
        // by sibling effects that run after this one). Re-measure on the next frame so the
        // anchor margin/offset reflect the laid-out content size — otherwise the visual anchor
        // is offset from the real latlng and a drag grabs the wrong point.
        requestAnimationFrame(applyTransform);
        marker.on('move', applyTransform);
        (map as any).on('move zoom zoomend viewreset', applyTransform);
        return () => {
            try { marker.off('move', applyTransform); } catch (e) {}
            try { (map as any).off('move zoom zoomend viewreset', applyTransform); } catch (e) {}
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [layer, map]);

    // Re-apply when rotation / bearing changes (spin) or when anything that changes the box's
    // measured size changes (text, font size, anchor, padding, geographic zoom-scale) — the
    // anchor offset depends on offsetWidth/Height, so a resize must re-center. rAF lets the DOM
    // lay out the new size first so offsetWidth/Height are current when we read them.
    useEffect(() => {
        requestAnimationFrame(() => applyTransformRef.current());
    }, [layer, style.rotation, mapBearing, rotateWithMap, style.text, style.fontSize, zoomScale,
        style.anchor, style.padding, style.fontFamily, style.fontWeight, style.backgroundColor]);

    // ---- geographic sizing: recompute the zoom scale on zoom ----------------------------
    useEffect(() => {
        if (!map) return;
        // referenceZoom prop wins; otherwise lock to the zoom at creation.
        if (typeof referenceZoom === 'number') refZoomRef.current = referenceZoom;
        else if (refZoomRef.current === null) refZoomRef.current = (map as any).getZoom();
        const recompute = () => {
            const factor = scaleWithZoomRef.current
                ? Math.pow(2, (map as any).getZoom() - (refZoomRef.current as number))
                : 1;
            setZoomScale(factor);
        };
        recompute();
        (map as any).on('zoomend', recompute);
        return () => { try { (map as any).off('zoomend', recompute); } catch (e) {} };
    }, [map, scaleWithZoom, referenceZoom]);

    // ---- inline text editing ------------------------------------------------------------
    // contentEditable is uncontrolled (React never owns its child text nodes — that would
    // jump the caret). We push `style.text` in via textContent when not editing, and read it
    // back on commit.
    useEffect(() => {
        if (boxRef.current && !editingRef.current) boxRef.current.textContent = style.text || '';
    }, [style.text, layer, selectedState]);

    const startEditing = () => {
        const m: any = ref.current;
        if (!m) return;
        exitedEditRef.current = false;
        setEditing(true);
        if (!selectedRef.current) setSelectedLocal(true, true);
        try { m.dragging?.disable(); } catch (e) {}
        // Focus + select-all on the next frame, once contentEditable is live.
        requestAnimationFrame(() => {
            const box = boxRef.current;
            if (!box) return;
            box.focus();
            const range = document.createRange();
            range.selectNodeContents(box);
            const sel = window.getSelection();
            sel?.removeAllRanges();
            sel?.addRange(range);
        });
    };

    // Exit inline edit → "move" mode (the marker stays SELECTED). `fromBlur` marks the
    // commit caused by clicking off the box onto the map, so the map-click handler
    // swallows that same click instead of also deselecting. Re-entry guarded so a
    // blur + map-click (or double Enter) don't double-commit.
    const commitEditing = (fromBlur = false) => {
        if (!editingRef.current) return;
        editingRef.current = false;
        if (fromBlur) exitedEditRef.current = true;
        const box = boxRef.current;
        setEditing(false);
        const m: any = ref.current;
        if (draggable && m?.dragging) { try { m.dragging.enable(); } catch (e) {} }
        if (!box) return;
        const newText = box.textContent || '';
        edits.current += 1;
        setStyle((s) => ({ ...s, text: newText }));
        lastSynced.current.text = newText;
        emit({ text: newText, n_edits: edits.current });
    };

    // While editing, keep pointer/dblclick/wheel from reaching the map (so selecting text or
    // scrolling doesn't pan / zoom / re-enter edit). Stop-propagation only — never prevent
    // default, or the caret stops working.
    useEffect(() => {
        const box = boxRef.current;
        if (!box || !editing) return;
        const stop = (e: Event) => e.stopPropagation();
        const types = ['pointerdown', 'mousedown', 'dblclick', 'wheel', 'touchstart'];
        types.forEach((t) => box.addEventListener(t, stop));
        return () => types.forEach((t) => box.removeEventListener(t, stop));
    }, [editing]);

    // ---- resize / rotate handle dragging ------------------------------------------------
    // Both pivot around the anchor's SCREEN point. Resize scales fontSize by the ratio of
    // the pointer's distance-from-anchor now vs. at grab; rotate sets the angle from the
    // anchor to the pointer. We listen on the window during the drag and stop the initiating
    // pointerdown so neither the marker drag nor a map pan kicks in.
    const handleDrag = (e: React.PointerEvent, mode: 'resize' | 'rotate') => {
        e.stopPropagation();
        e.preventDefault();
        const m: any = ref.current;
        if (!m || !map) return;
        try { m.dragging?.disable(); } catch (err) {}
        try { (map as any).dragging?.disable(); } catch (err) {}

        const anchorPt = (map as any).latLngToContainerPoint(m.getLatLng());
        const startVec = { x: e.clientX, y: e.clientY };
        const containerRect = (map as any).getContainer().getBoundingClientRect();
        const anchorClient = { x: containerRect.left + anchorPt.x, y: containerRect.top + anchorPt.y };
        const startFont = styleRef.current.fontSize;
        const startRotation = styleRef.current.rotation;

        // Resize scales fontSize by the ratio of the pointer's distance from the box CENTER
        // (now vs. at grab). The center — not the anchor — is the reference because the resize
        // dot now lives AT the anchor (so an anchor-referenced ratio would divide by ~0). The
        // center sits at `anchorClient + R(θ)·(boxCenter − anchorOffset)`.
        const el: HTMLElement | undefined = m._icon;
        const w = el ? el.offsetWidth : 0;
        const h = el ? el.offsetHeight : 0;
        const [aox, aoy] = anchorOffset(anchorRef.current, w, h);
        const effRad =
            ((rotateWithMapRef.current ? rotationRef.current : rotationRef.current - bearingRef.current) *
                Math.PI) / 180;
        const cosT = Math.cos(effRad), sinT = Math.sin(effRad);
        const dlx = w / 2 - aox, dly = h / 2 - aoy;
        const centerClient = {
            x: anchorClient.x + dlx * cosT - dly * sinT,
            y: anchorClient.y + dlx * sinT + dly * cosT,
        };
        const startDist = Math.hypot(startVec.x - centerClient.x, startVec.y - centerClient.y) || 1;
        // Rotation pivots around the ANCHOR (transform-origin), so its angle is measured there.
        const angleAt = (cx: number, cy: number) =>
            (Math.atan2(cy - anchorClient.y, cx - anchorClient.x) * 180) / Math.PI + 90;
        const startAngle = angleAt(startVec.x, startVec.y);

        const onMove = (ev: PointerEvent) => {
            if (mode === 'resize') {
                const dist = Math.hypot(ev.clientX - centerClient.x, ev.clientY - centerClient.y);
                const next = Math.round(Math.min(MAX_FONT, Math.max(MIN_FONT, startFont * (dist / startDist))));
                setStyle((s) => ({ ...s, fontSize: next }));
            } else {
                const delta = angleAt(ev.clientX, ev.clientY) - startAngle;
                let next = Math.round(startRotation + delta);
                // Snap to 15° increments while holding Shift.
                if (ev.shiftKey) next = Math.round(next / 15) * 15;
                setStyle((s) => ({ ...s, rotation: next }));
                rotationRef.current = next;
                applyTransformRef.current();
            }
        };
        const onUp = () => {
            window.removeEventListener('pointermove', onMove);
            window.removeEventListener('pointerup', onUp);
            const m2: any = ref.current;
            if (draggable && m2?.dragging && !editingRef.current) { try { m2.dragging.enable(); } catch (err) {} }
            try { (map as any).dragging?.enable(); } catch (err) {}
            // The pointer-up usually lands over the map, so the browser then synthesizes a
            // `click` on the common ancestor that bubbles to Leaflet → fires the map-click
            // deselect. Swallow that one click (capture phase) so a handle drag doesn't
            // deselect the label.
            const swallow = (ev: Event) => {
                ev.stopPropagation();
                document.removeEventListener('click', swallow, true);
            };
            document.addEventListener('click', swallow, true);
            setTimeout(() => document.removeEventListener('click', swallow, true), 80);
            const cur = styleRef.current;
            if (mode === 'resize') { lastSynced.current.fontSize = cur.fontSize; emit({ fontSize: cur.fontSize }); }
            else { lastSynced.current.rotation = cur.rotation; emit({ rotation: cur.rotation }); }
        };
        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', onUp);
    };

    // ===================================================================================
    // Render: the in-icon content (text box + handles) via a portal into marker._icon, and
    // the contextual toolbar via a portal into the map container.
    // ===================================================================================
    const iconEl: HTMLElement | undefined = layer ? (layer as any)._icon : undefined;
    const hasBg = style.backgroundColor && style.backgroundColor !== 'transparent';

    // Outer box = background pill + selection chrome + handles; it fills the content-sized icon
    // element (the icon carries the anchor offset + rotation via our transform). Inner text
    // element = the contentEditable typography (kept separate so writing its textContent never
    // wipes the React-rendered handle spans).
    const outerStyle: React.CSSProperties = {
        position: 'relative',
        opacity,
        background: hasBg ? style.backgroundColor : 'transparent',
        padding: hasBg ? `${style.padding}px ${style.padding * 1.6}px` : 0,
        borderRadius: hasBg ? `${style.borderRadius}px` : 0,
    };
    const textStyle: React.CSSProperties = {
        color: style.color,
        fontFamily: style.fontFamily,
        // `zoomScale` is 1 unless `scaleWithZoom` is on, in which case the on-screen size grows
        // with the map so the caption keeps a fixed ground footprint.
        fontSize: `${style.fontSize * zoomScale}px`,
        fontWeight: style.fontWeight as any,
        fontStyle: style.fontStyle,
        lineHeight: 1.15,
    };

    const content = iconEl
        ? ReactDOM.createPortal(
              <div
                  className={
                      'dl2-tm-box' +
                      (selectedState ? ' is-selected' : '') +
                      (editing ? ' is-editing' : '')
                  }
                  style={outerStyle}
              >
                  <div
                      ref={boxRef}
                      className={'dl2-tm-text' + (!editing && !style.text ? ' is-empty' : '')}
                      style={textStyle}
                      contentEditable={editing}
                      suppressContentEditableWarning
                      spellCheck={false}
                      onBlur={editing ? () => commitEditing(true) : undefined}
                      onKeyDown={
                          editing
                              ? (e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        commitEditing();
                                    } else if (e.key === 'Escape') {
                                        e.preventDefault();
                                        if (boxRef.current) boxRef.current.textContent = styleRef.current.text || '';
                                        commitEditing();
                                    }
                                }
                              : undefined
                      }
                  />
                  {selectedState && !editing && (
                      <>
                          <span className="dl2-tm-rotate-line" />
                          <span
                              className="dl2-tm-handle dl2-tm-handle-rotate"
                              title="Drag to rotate (hold Shift to snap 15°)"
                              onPointerDown={(e) => handleDrag(e, 'rotate')}
                          />
                          <span
                              className="dl2-tm-handle dl2-tm-handle-resize"
                              title="Drag to resize — this dot also marks the anchor point"
                              style={anchorDotCss(style.anchor as Anchor)}
                              onPointerDown={(e) => handleDrag(e, 'resize')}
                          />
                      </>
                  )}
              </div>,
              iconEl
          )
        : null;

    const toolbar =
        selectedState && showToolbar && map
            ? ReactDOM.createPortal(
                  <Toolbar
                      style={style}
                      editing={editing}
                      onChange={setStyleAndEmit}
                      onEdit={startEditing}
                  />,
                  (map as any).getContainer()
              )
            : null;

    return (
        <>
            {content}
            {toolbar}
        </>
    );
};

// ---- the contextual style toolbar (portaled into the map container) ----------------------
type ToolbarProps = {
    style: any;
    editing: boolean;
    onChange: (patch: Record<string, any>) => void;
    onEdit: () => void;
};

const Toolbar = ({ style, editing, onChange, onEdit }: ToolbarProps) => {
    const ref = useRef<HTMLDivElement | null>(null);
    // Keep map drag / scroll / click from leaking through the toolbar.
    useEffect(() => {
        const el = ref.current;
        if (!el) return;
        DomEvent.disableClickPropagation(el);
        DomEvent.disableScrollPropagation(el);
    }, []);

    const isBold = Number(style.fontWeight) >= 600 || style.fontWeight === 'bold';
    const isItalic = style.fontStyle === 'italic';
    const hasBg = style.backgroundColor && style.backgroundColor !== 'transparent';

    return (
        <div className="dl2-tm-toolbar" ref={ref}>
            <select
                className="dl2-tm-tb-select"
                title="Font family"
                value={style.fontFamily}
                onChange={(e) => onChange({ fontFamily: e.target.value })}
            >
                {FONT_OPTIONS.map((f) => (
                    <option key={f.label} value={f.value}>{f.label}</option>
                ))}
            </select>

            <div className="dl2-tm-tb-num">
                <button
                    className="dl2-tm-tb-step"
                    title="Smaller"
                    onClick={() => onChange({ fontSize: Math.max(MIN_FONT, Math.round(style.fontSize - 2)) })}
                >−</button>
                <input
                    className="dl2-tm-tb-size"
                    type="number"
                    min={MIN_FONT}
                    max={MAX_FONT}
                    value={style.fontSize}
                    onChange={(e) => {
                        const v = parseInt(e.target.value, 10);
                        if (!isNaN(v)) onChange({ fontSize: Math.min(MAX_FONT, Math.max(MIN_FONT, v)) });
                    }}
                />
                <button
                    className="dl2-tm-tb-step"
                    title="Larger"
                    onClick={() => onChange({ fontSize: Math.min(MAX_FONT, Math.round(style.fontSize + 2)) })}
                >+</button>
            </div>

            <span className="dl2-tm-tb-sep" />

            <button
                className={'dl2-tm-tb-btn' + (isBold ? ' active' : '')}
                title="Bold"
                style={{ fontWeight: 800 }}
                onClick={() => onChange({ fontWeight: isBold ? 400 : 700 })}
            >B</button>
            <button
                className={'dl2-tm-tb-btn' + (isItalic ? ' active' : '')}
                title="Italic"
                style={{ fontStyle: 'italic', fontFamily: 'Georgia, serif' }}
                onClick={() => onChange({ fontStyle: isItalic ? 'normal' : 'italic' })}
            >I</button>

            <span className="dl2-tm-tb-sep" />

            <label className="dl2-tm-tb-swatch" title="Text color">
                <span className="dl2-tm-tb-swatch-ink" style={{ background: style.color }} />
                <input
                    type="color"
                    value={toHex(style.color)}
                    onChange={(e) => onChange({ color: e.target.value })}
                />
                <span className="dl2-tm-tb-swatch-label">A</span>
            </label>

            <label className={'dl2-tm-tb-swatch' + (hasBg ? '' : ' is-off')} title="Background color">
                <span
                    className="dl2-tm-tb-swatch-ink dl2-tm-tb-swatch-bg"
                    style={{ background: hasBg ? style.backgroundColor : 'transparent' }}
                />
                <input
                    type="color"
                    value={toHex(hasBg ? style.backgroundColor : '#000000')}
                    onChange={(e) => onChange({ backgroundColor: e.target.value })}
                />
                <span className="dl2-tm-tb-swatch-label">▣</span>
            </label>
            <button
                className="dl2-tm-tb-btn"
                title={hasBg ? 'Remove background' : 'Add background'}
                onClick={() => onChange({ backgroundColor: hasBg ? 'transparent' : 'rgba(0,0,0,0.55)' })}
            >{hasBg ? '⌫' : '▢'}</button>

            <span className="dl2-tm-tb-sep" />

            <div className="dl2-tm-tb-num" title="Rotation (degrees)">
                <span className="dl2-tm-tb-rot-ico">⟳</span>
                <input
                    className="dl2-tm-tb-size"
                    type="number"
                    value={Math.round(style.rotation)}
                    onChange={(e) => {
                        const v = parseInt(e.target.value, 10);
                        if (!isNaN(v)) onChange({ rotation: v });
                    }}
                />
            </div>

            <span className="dl2-tm-tb-sep" />

            <button
                className={'dl2-tm-tb-btn' + (editing ? ' active' : '')}
                title="Edit text"
                onClick={onEdit}
            >✎</button>
        </div>
    );
};

// Coerce an arbitrary CSS color to a #rrggbb hex an <input type="color"> accepts (it rejects
// named colors / rgba). Falls back to black when it can't be resolved.
const toHex = (c: string): string => {
    if (!c) return '#000000';
    if (/^#[0-9a-fA-F]{6}$/.test(c)) return c;
    if (/^#[0-9a-fA-F]{3}$/.test(c)) {
        return '#' + c.slice(1).split('').map((ch) => ch + ch).join('');
    }
    try {
        const ctx = document.createElement('canvas').getContext('2d');
        if (ctx) {
            ctx.fillStyle = c;
            const v = ctx.fillStyle;
            if (/^#[0-9a-fA-F]{6}$/.test(v)) return v;
        }
    } catch (e) { /* fall through */ }
    return '#000000';
};

export default TextMarker;
