import React, { useEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import { ImageOverlay as LeafletImageOverlay } from 'leaflet';
import { useLeafletMap } from '../context';
import { DashComponentProps } from '../props';
import { Anchor, anchorFx, anchorFy, anchorDotCss } from '../anchor';

type Bounds = [[number, number], [number, number]];

type Props = {
    /** URL of the image. [MUTABLE] */
    url?: string;
    /** Geographic bounds the image is stretched to, `[[south, west], [north, east]]`.
     * Two-way when `editable`: dragging / resizing writes it back. [MUTABLE] */
    bounds?: Bounds;
    /** Layer opacity, 0..1. [MUTABLE] */
    opacity?: number;
    /** Alt-text / title for the image element. */
    alt?: string;
    /** Adds the `crossOrigin` attribute to the img element. Pass "anonymous" to make
     * the image load CORS-mode so canvas captures (map screenshots / html2canvas) can
     * read the pixels. The host must answer with Access-Control-Allow-Origin or the
     * image fails to load entirely — leave unset for hosts you don't control.
     * "use-credentials" and "" are also valid. Construction-time only. */
    crossOrigin?: string;
    /** If true, the image is wrapped in an interactive layer that fires click events.
     * Forced on when `editable`. */
    interactive?: boolean;
    /** Explicit z-index for the overlay pane. [MUTABLE] */
    zIndex?: number;

    /** Enable the on-map transform controls: click to select, then drag to move, drag the
     * corner handle to resize, and the top handle to rotate. @default false. */
    editable?: boolean;
    /** Whether the transform chrome (outline + resize/rotate handles) is shown. Two-way:
     * clicking the image selects it, a map-background click clears it. Only meaningful when
     * `editable`. [MUTABLE] */
    selected?: boolean;
    /** Visual rotation in degrees, CW. Applied as a CSS transform pivoting at the `anchor`
     * (Leaflet's ImageOverlay has no native geographic rotation, so the image's `bounds` stay
     * axis-aligned and only the rendered pixels rotate). The rotate handle writes it back.
     * [MUTABLE] */
    rotation?: number;
    /** Which point of the image is the rotation pivot + resize anchor + where the white anchor
     * dot is drawn. One of center | top-left | top | top-right | left | right | bottom-left |
     * bottom | bottom-right. @default "center". [MUTABLE] */
    anchor?: Anchor;

    /** Number of times the image has been clicked. [READONLY] */
    n_clicks?: number;
    /** Bumped on each drag-move / resize commit. [READONLY] */
    n_transforms?: number;
} & DashComponentProps;

/**
 * ImageOverlay drapes a single static image over a geographic bounding box. With `editable`
 * it gains a TextMarker-style transform control system: click to select, drag to move, a corner
 * handle to resize (scaling the bounds about the `anchor`), and a top handle to rotate (a visual
 * CSS rotation pivoting at the `anchor`). The white anchor dot marks where the image is pinned.
 * `bounds`, `rotation`, and `selected` round-trip back to Dash. Wraps Leaflet 2's ImageOverlay.
 */
const ImageOverlay = ({
    url = '',
    bounds = [[0, 0], [0, 0]],
    opacity = 1,
    alt,
    crossOrigin,
    interactive = false,
    zIndex,
    editable = false,
    selected,
    rotation = 0,
    anchor = 'center',
    setProps,
}: Props) => {
    const map = useLeafletMap();
    const layerRef = useRef<LeafletImageOverlay | null>(null);
    const chromeRef = useRef<HTMLDivElement | null>(null);
    const clicksRef = useRef(0);
    const transformsRef = useRef(0);

    // Live state the imperative reprojection reads through refs (handlers bind once).
    const boundsRef = useRef<Bounds>(bounds);
    const rotationRef = useRef(rotation);
    const anchorRef = useRef<Anchor>(anchor);
    const editableRef = useRef(editable);
    const lastBounds = useRef<string>(JSON.stringify(bounds));
    rotationRef.current = rotation;
    anchorRef.current = anchor;
    editableRef.current = editable;

    const [selectedState, setSelectedState] = useState(!!selected);
    const selectedRef = useRef(selectedState);
    selectedRef.current = selectedState;
    const lastSelected = useRef<boolean | undefined>(selected);

    const reprojectRef = useRef<() => void>(() => {});

    const emit = (payload: Record<string, any>) => setProps && setProps(payload);

    const setSelectedLocal = (val: boolean) => {
        setSelectedState(val);
        lastSelected.current = val;
        // Single selection across the map: announce so any other selected TextMarker / editable
        // ImageOverlay deselects (shared `dl2:tm-select` bus — only one transform UI at a time).
        if (val && map) { try { (map as any).fire('dl2:tm-select', { source: layerRef.current }); } catch (e) {} }
        emit({ selected: val });
    };

    // ---- create the overlay once -------------------------------------------------------
    useEffect(() => {
        if (!map) return;
        const options: any = { opacity, interactive: interactive || editable };
        if (alt !== undefined) options.alt = alt;
        if (crossOrigin !== undefined) options.crossOrigin = crossOrigin;
        if (zIndex !== undefined) options.zIndex = zIndex;
        const overlay = new LeafletImageOverlay(url, bounds as any, options);
        overlay.addTo(map);
        layerRef.current = overlay;
        boundsRef.current = bounds;

        overlay.on('click', () => {
            clicksRef.current += 1;
            emit({ n_clicks: clicksRef.current });
            if (editableRef.current && !selectedRef.current) setSelectedLocal(true);
        });

        // Image position + visual rotation, re-applied whenever Leaflet repositions the image.
        const reproject = () => {
            const ov: any = layerRef.current;
            const img: HTMLElement | undefined = ov && ov._image;
            if (!img || !map) return;
            const b = boundsRef.current;
            const south = b[0][0], west = b[0][1], north = b[1][0], east = b[1][1];
            const nw = (map as any).latLngToLayerPoint([north, west]);
            const se = (map as any).latLngToLayerPoint([south, east]);
            const w = Math.abs(se.x - nw.x), h = Math.abs(se.y - nw.y);
            const ox = anchorFx(anchorRef.current) * w, oy = anchorFy(anchorRef.current) * h;
            img.style.transformOrigin = `${ox}px ${oy}px`;
            img.style.transform =
                `translate3d(${Math.round(nw.x)}px, ${Math.round(nw.y)}px, 0) rotate(${rotationRef.current}deg)`;

            // Position the selection chrome (container coords) over the image rect.
            const chrome = chromeRef.current;
            if (chrome) {
                const nwC = (map as any).latLngToContainerPoint([north, west]);
                const seC = (map as any).latLngToContainerPoint([south, east]);
                const cw = seC.x - nwC.x, ch = seC.y - nwC.y;
                chrome.style.left = `${nwC.x}px`;
                chrome.style.top = `${nwC.y}px`;
                chrome.style.width = `${cw}px`;
                chrome.style.height = `${ch}px`;
                chrome.style.transformOrigin = `${anchorFx(anchorRef.current) * cw}px ${anchorFy(anchorRef.current) * ch}px`;
                chrome.style.transform = `rotate(${rotationRef.current}deg)`;
            }
        };
        reprojectRef.current = reproject;
        reproject();
        requestAnimationFrame(reproject);
        (map as any).on('move zoom zoomend viewreset', reproject);

        return () => {
            try { (map as any).off('move zoom zoomend viewreset', reproject); } catch (e) {}
            try { overlay.remove(); } catch (e) {}
            layerRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map]);

    // ---- two-way prop reactions --------------------------------------------------------
    useEffect(() => {
        const l: any = layerRef.current;
        if (l && url && typeof l.setUrl === 'function') l.setUrl(url);
    }, [url]);
    useEffect(() => {
        const l: any = layerRef.current;
        if (!l) return;
        // Echo guard: ignore the bounds we just emitted ourselves.
        if (JSON.stringify(bounds) === lastBounds.current) return;
        lastBounds.current = JSON.stringify(bounds);
        boundsRef.current = bounds;
        if (typeof l.setBounds === 'function') l.setBounds(bounds);
        reprojectRef.current();
    }, [bounds]);
    useEffect(() => {
        const l: any = layerRef.current;
        if (l && typeof l.setOpacity === 'function') l.setOpacity(opacity);
    }, [opacity]);
    useEffect(() => {
        const l: any = layerRef.current;
        if (l && typeof l.setZIndex === 'function' && zIndex !== undefined) l.setZIndex(zIndex);
    }, [zIndex]);
    useEffect(() => {
        reprojectRef.current();
    }, [rotation, anchor, selectedState]);

    // External selected prop -> local (only when the host drives it).
    useEffect(() => {
        if (selected !== undefined && selected !== lastSelected.current) {
            lastSelected.current = selected;
            setSelectedState(selected);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selected]);

    // Map-background click deselects.
    useEffect(() => {
        if (!map) return;
        const onMapClick = () => { if (selectedRef.current) setSelectedLocal(false); };
        map.on('click', onMapClick);
        // Shared single-selection bus: deselect when another object becomes selected.
        const onOther = (e: any) => {
            if (e && e.source !== layerRef.current && selectedRef.current) setSelectedLocal(false);
        };
        (map as any).on('dl2:tm-select', onOther);
        return () => {
            map.off('click', onMapClick);
            try { (map as any).off('dl2:tm-select', onOther); } catch (err) {}
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map]);

    useEffect(() => {
        const ov: any = layerRef.current;
        const img: HTMLElement | undefined = ov && ov._image;
        if (!img) return;
        img.classList.toggle('dl2-img-editable-target', !!editable);
        img.style.cursor = editable ? 'move' : '';
    }, [editable, selectedState]);

    // Move is handled by dragging the chrome "body" (see handleDrag 'move' mode) rather than
    // the Leaflet image element — pointerdown on the interactive image disrupts the window
    // pointer stream (only the first pointermove arrives), whereas plain chrome elements drag
    // cleanly. Click the image (Leaflet click) to select, then drag the body to move.

    const commitBounds = () => {
        const b = boundsRef.current;
        const r: Bounds = [
            [+b[0][0].toFixed(6), +b[0][1].toFixed(6)],
            [+b[1][0].toFixed(6), +b[1][1].toFixed(6)],
        ];
        lastBounds.current = JSON.stringify(r);
        transformsRef.current += 1;
        emit({ bounds: r, n_transforms: transformsRef.current });
    };

    // A handle drag ends over the map → the synthesized click would deselect; swallow it.
    const swallowNextClick = () => {
        const swallow = (ev: Event) => { ev.stopPropagation(); document.removeEventListener('click', swallow, true); };
        document.addEventListener('click', swallow, true);
        setTimeout(() => document.removeEventListener('click', swallow, true), 80);
    };

    // ---- move / resize / rotate dragging (all via window listeners) ---------------------
    const handleDrag = (e: React.PointerEvent, mode: 'move' | 'resize' | 'rotate') => {
        e.stopPropagation();
        e.preventDefault();
        if (!map) return;
        try { (map as any).dragging?.disable(); } catch (err) {}
        const ov: any = layerRef.current;
        const rect = (map as any).getContainer().getBoundingClientRect();
        const b0 = boundsRef.current;
        const south0 = b0[0][0], west0 = b0[0][1], north0 = b0[1][0], east0 = b0[1][1];

        // MOVE: translate the whole bounds box by the pointer's latlng delta.
        if (mode === 'move') {
            const toLatLng = (cx: number, cy: number) =>
                (map as any).containerPointToLatLng([cx - rect.left, cy - rect.top]);
            const start = toLatLng(e.clientX, e.clientY);
            let moved = false;
            const onMove = (ev: PointerEvent) => {
                const cur = toLatLng(ev.clientX, ev.clientY);
                const dLat = cur.lat - start.lat, dLng = cur.lng - start.lng;
                if (Math.abs(dLat) + Math.abs(dLng) > 1e-9) moved = true;
                const nb: Bounds = [
                    [south0 + dLat, west0 + dLng],
                    [north0 + dLat, east0 + dLng],
                ];
                boundsRef.current = nb;
                try { ov.setBounds(nb); } catch (err) {}
                reprojectRef.current();
            };
            const onUp = () => {
                window.removeEventListener('pointermove', onMove);
                window.removeEventListener('pointerup', onUp);
                try { (map as any).dragging?.enable(); } catch (err) {}
                if (moved) { swallowNextClick(); commitBounds(); }
            };
            window.addEventListener('pointermove', onMove);
            window.addEventListener('pointerup', onUp);
            return;
        }
        // Anchor latlng (fixed pivot) + its screen point.
        const fx = anchorFx(anchorRef.current), fy = anchorFy(anchorRef.current);
        const latA = north0 - fy * (north0 - south0);
        const lngA = west0 + fx * (east0 - west0);
        const anchorC = (map as any).latLngToContainerPoint([latA, lngA]);
        const anchorClient = { x: rect.left + anchorC.x, y: rect.top + anchorC.y };
        // Box-center screen for the resize ratio (stable regardless of where the handle sits).
        const nwC = (map as any).latLngToContainerPoint([north0, west0]);
        const seC = (map as any).latLngToContainerPoint([south0, east0]);
        const centerClient = { x: rect.left + (nwC.x + seC.x) / 2, y: rect.top + (nwC.y + seC.y) / 2 };
        const startDist = Math.hypot(e.clientX - centerClient.x, e.clientY - centerClient.y) || 1;
        const angleAt = (cx: number, cy: number) =>
            (Math.atan2(cy - anchorClient.y, cx - anchorClient.x) * 180) / Math.PI + 90;
        const startAngle = angleAt(e.clientX, e.clientY);
        const startRotation = rotationRef.current;

        const onMove = (ev: PointerEvent) => {
            if (mode === 'resize') {
                const dist = Math.hypot(ev.clientX - centerClient.x, ev.clientY - centerClient.y);
                const scale = Math.max(0.05, Math.min(40, dist / startDist));
                // Scale the bounds box about the anchor latlng (anchor stays pinned).
                const nb: Bounds = [
                    [latA + (south0 - latA) * scale, lngA + (west0 - lngA) * scale],
                    [latA + (north0 - latA) * scale, lngA + (east0 - lngA) * scale],
                ];
                boundsRef.current = nb;
                try { ov.setBounds(nb); } catch (err) {}
                reprojectRef.current();
            } else {
                let next = Math.round(startRotation + (angleAt(ev.clientX, ev.clientY) - startAngle));
                if (ev.shiftKey) next = Math.round(next / 15) * 15;
                rotationRef.current = next;
                reprojectRef.current();
            }
        };
        const onUp = () => {
            window.removeEventListener('pointermove', onMove);
            window.removeEventListener('pointerup', onUp);
            try { (map as any).dragging?.enable(); } catch (err) {}
            swallowNextClick();
            if (mode === 'resize') commitBounds();
            else emit({ rotation: rotationRef.current });
        };
        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', onUp);
    };

    // ---- render the chrome (portal into the map container) -----------------------------
    if (!map || !editable || !selectedState) return null;
    return ReactDOM.createPortal(
        <div className="dl2-img-chrome" ref={chromeRef}>
            <div
                className="dl2-img-body"
                title="Drag to move"
                onPointerDown={(e) => handleDrag(e, 'move')}
            />
            <span className="dl2-img-rotate-line" />
            <span
                className="dl2-img-handle dl2-img-handle-rotate"
                title="Drag to rotate (hold Shift to snap 15°)"
                onPointerDown={(e) => handleDrag(e, 'rotate')}
            />
            <span
                className="dl2-img-handle dl2-img-handle-resize"
                title="Drag to resize — this dot also marks the anchor point"
                style={anchorDotCss(anchor)}
                onPointerDown={(e) => handleDrag(e, 'resize')}
            />
        </div>,
        (map as any).getContainer()
    );
};

export default ImageOverlay;
