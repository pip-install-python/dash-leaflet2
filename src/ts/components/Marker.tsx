import React, { useEffect, useRef } from 'react';
import { Marker as LeafletMarker } from 'leaflet';
import { LeafletLayerContext, useLeafletBearing, useLeafletMap } from '../context';
import { useLayer } from '../useLayer';
import { buildMarkerIcon } from '../icons';
import { DashComponentProps } from '../props';

type Props = {
    /** Marker position as [lat, lng]. Updating it moves the marker; dragging writes it back. [MUTABLE] */
    position?: [number, number];

    // --- icon: pick one mode (precedence: iconOptions > iconify > emoji > icon > default) ---
    /** Custom image icon as Leaflet Icon options, e.g. {iconUrl, iconSize:[w,h], iconAnchor:[x,y]}. */
    icon?: object;
    /** A single emoji to use as the marker, e.g. "🛥️". */
    emoji?: string;
    /** An Iconify icon name, e.g. "mdi:home" or "twemoji:sailboat" (loads from the Iconify API). */
    iconify?: string;
    /** Pixel size for emoji / iconify markers. Default 32. */
    iconSize?: number;
    /** CSS color for monochrome iconify icons. */
    iconColor?: string;
    /** [x, y] icon anchor for emoji / iconify / iconOptions markers. Default bottom-center. */
    iconAnchor?: [number, number];
    /** Full Leaflet DivIcon options escape hatch ({html, className, iconSize, iconAnchor}). */
    iconOptions?: object;

    /** Convenience popup text. For rich content, use a <Popup> child instead. */
    popup?: string;
    /** Convenience tooltip text. For rich content, use a <Tooltip> child instead. */
    tooltip?: string;
    /** Whether the marker can be dragged with the pointer. [MUTABLE] */
    draggable?: boolean;
    /** Marker opacity, 0..1. [MUTABLE] */
    opacity?: number;
    /** z-index offset relative to other markers. [MUTABLE] */
    zIndexOffset?: number;

    /**
     * Marker rotation in degrees (CW from north). Useful for vehicle / aircraft /
     * character sprites that need to point in a direction. Applied via a CSS
     * `rotate` on the icon DOM. [MUTABLE]
     */
    rotationAngle?: number;

    /**
     * When `true`, the marker icon rotates together with the map — useful for
     * vehicles, aircraft, walking characters, compass arrows, anything whose
     * orientation is tied to the world. The icon's visual screen rotation is
     * `bearing + rotationAngle`.
     *
     * When `false` (default), the icon stays in a fixed screen orientation
     * regardless of map bearing — useful for pins, labels, and the typical
     * "marker should always look upright" case. The icon's visual screen
     * rotation is just `rotationAngle`.
     *
     * Implementation: when `false` we apply `rotationAngle - bearing` to the
     * icon, which cancels the map pane's rotation contribution. When `true` we
     * apply `rotationAngle` and let the pane's CSS rotation carry the icon.
     */
    rotateWithMap?: boolean;

    /** Number of times the marker has been clicked. [READONLY] */
    n_clicks?: number;
    /** Number of times the marker has been dragged. [READONLY] */
    n_drags?: number;

    /** Popup / Tooltip children bound to this marker. */
    children?: React.ReactNode;
} & DashComponentProps;

/**
 * Marker displays an icon at a position and can host Popup/Tooltip children. The icon can
 * be the default pin, a custom image (`icon`), an `emoji`, or any Iconify icon (`iconify`,
 * e.g. "mdi:home"). Draggable markers write their new `position` back to Dash. Wraps
 * Leaflet 2's Marker. Place it as a child of Map.
 */
const Marker = ({
    position = [51.505, -0.09],
    icon,
    emoji,
    iconify,
    iconSize = 32,
    iconColor,
    iconAnchor,
    iconOptions,
    popup,
    tooltip,
    draggable = false,
    opacity = 1,
    zIndexOffset = 0,
    rotationAngle = 0,
    rotateWithMap = false,
    setProps,
    children,
}: Props) => {
    const clicks = useRef(0);
    const drags = useRef(0);
    const { bearing: mapBearing } = useLeafletBearing();
    const map = useLeafletMap();

    const { layer, ref } = useLayer<LeafletMarker>(() => {
        const marker = new LeafletMarker(position, {
            icon: buildMarkerIcon({ icon, emoji, iconify, iconSize, iconColor, iconAnchor, iconOptions }),
            draggable: !!draggable,
            opacity,
            zIndexOffset,
        });
        if (popup) marker.bindPopup(popup);
        // Open above the icon (matches the DivIcon's tooltipAnchor for emoji/iconify).
        if (tooltip) marker.bindTooltip(tooltip, { direction: 'top' });
        marker.on('click', () => {
            clicks.current += 1;
            setProps && setProps({ n_clicks: clicks.current });
        });
        // Dragging writes the new position back to Dash (two-way `position`).
        marker.on('dragend', () => {
            drags.current += 1;
            const ll = marker.getLatLng();
            setProps &&
                setProps({
                    n_drags: drags.current,
                    position: [+ll.lat.toFixed(6), +ll.lng.toFixed(6)],
                });
        });
        return marker;
    });

    // Python -> marker: move when position changes.
    useEffect(() => {
        if (ref.current) ref.current.setLatLng(position);
    }, [position]);

    // Rebuild the icon when any icon-determining prop changes.
    useEffect(() => {
        if (ref.current) {
            ref.current.setIcon(
                buildMarkerIcon({ icon, emoji, iconify, iconSize, iconColor, iconAnchor, iconOptions })
            );
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [icon, emoji, iconify, iconSize, iconColor, iconAnchor, iconOptions]);

    useEffect(() => {
        if (ref.current) ref.current.setOpacity(opacity);
    }, [opacity]);
    useEffect(() => {
        if (ref.current) ref.current.setZIndexOffset(zIndexOffset);
    }, [zIndexOffset]);

    // Apply marker rotation. The marker is inside the map's rotation wrapper,
    // so the icon's DOM is already visually rotated by the map's `bearing` via
    // CSS inheritance. The `effective` value is what we layer on top:
    //
    //   rotateWithMap=true  -> effective = rotationAngle
    //       Visual = wrapper_bearing + rotationAngle. The icon spins together
    //       with the map, plus any per-marker offset.
    //
    //   rotateWithMap=false -> effective = rotationAngle - mapBearing
    //       Visual = wrapper_bearing + (rotationAngle - bearing) =
    //       rotationAngle. The icon stays at a fixed screen orientation
    //       regardless of how the map is rotated — the upright-pin case.
    //
    // We compose the rotation into Leaflet's `transform: translate3d(...)`
    // string rather than using the standalone CSS `rotate` property. The
    // standalone `rotate` does NOT reliably honor `transform-origin` in current
    // browsers — it appears to rotate around the bottom-right corner of the
    // element's content box, which is exactly wrong for marker icons.
    //
    // Because Leaflet re-writes the icon's transform on marker.setLatLng (which
    // fires marker.'move') AND on map zoom (re-projection), we re-apply on both
    // events to keep our rotation alive.
    useEffect(() => {
        const marker: any = ref.current;
        if (!marker) return;
        const applyTransform = () => {
            const el: HTMLElement | undefined = marker._icon;
            if (!el || !map) return;
            const effective = rotateWithMap ? rotationAngle : rotationAngle - mapBearing;
            // Re-project the marker's current latlng to the CURRENT pane coords.
            // We do this rather than parsing Leaflet's last-written translate3d
            // because of a React effect-order race: in flight-sim, the rAF
            // loop sets fs-aircraft.position AND fs-map.center in the same
            // tick, and React fires Marker's effect (calling marker.setLatLng)
            // BEFORE Map's effect (calling map.setView). The setLatLng call
            // computes the marker's pane coords using the OLD pixelOrigin; the
            // subsequent same-zoom pan via setView re-translates the pane but
            // does NOT re-call _setPos on each marker, so the marker's
            // translate3d stays stale. Re-projecting here, after every map
            // 'move' event, snaps the marker back to where its latlng actually
            // is in the post-pan projection.
            const latlng = marker.getLatLng();
            const point = (map as any).latLngToLayerPoint(latlng);
            const w = parseFloat(el.style.width) || el.offsetWidth || 25;
            const h = parseFloat(el.style.height) || el.offsetHeight || 41;
            el.style.transformOrigin = `${w / 2}px ${h / 2}px`;
            el.style.transform =
                `translate3d(${Math.round(point.x)}px, ${Math.round(point.y)}px, 0) rotate(${effective}deg)`;
            // Clear any stale standalone `rotate` from earlier code paths.
            (el.style as any).rotate = '';
        };
        applyTransform();
        // marker.'move' fires after setLatLng → covers the marker being moved
        // independently of the map. map.'move' fires DURING pan (covers the
        // setLatLng/setView race in rAF loops). 'zoom'/'zoomend' covers re-
        // projections. 'viewreset' covers explicit view resets.
        marker.on('move', applyTransform);
        if (map) {
            try { (map as any).on('move zoom zoomend viewreset', applyTransform); } catch (e) {}
        }
        return () => {
            try { marker.off('move', applyTransform); } catch (e) {}
            if (map) {
                try { (map as any).off('move zoom zoomend viewreset', applyTransform); } catch (e) {}
            }
        };
    }, [rotationAngle, rotateWithMap, mapBearing, layer, map]);

    return (
        <LeafletLayerContext.Provider value={layer}>
            {layer ? children : null}
        </LeafletLayerContext.Provider>
    );
};

export default Marker;
