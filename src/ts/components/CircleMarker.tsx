import React, { useEffect, useRef } from 'react';
import { CircleMarker as LeafletCircleMarker } from 'leaflet';
import { LeafletLayerContext } from '../context';
import { useLayer } from '../useLayer';
import { DashComponentProps } from '../props';

type Props = {
    /** Center as [lat, lng]. [MUTABLE] */
    center?: [number, number];
    /** Radius in PIXELS (fixed; does not scale with zoom). [MUTABLE] */
    radius?: number;
    /** Stroke color. [MUTABLE] */
    color?: string;
    /** Stroke width in pixels. [MUTABLE] */
    weight?: number;
    /** Fill color (defaults to stroke color). [MUTABLE] */
    fillColor?: string;
    /** Fill opacity, 0..1. [MUTABLE] */
    fillOpacity?: number;
    /** Whether the circle captures pointer events (fires clicks, blocks the map click
     *  underneath). Set false for a non-interactive decoration / context overlay so it
     *  never intercepts clicks meant for the map. Construction-only. @default true */
    interactive?: boolean;
    /** Times the marker has been clicked. [READONLY] */
    n_clicks?: number;
    /** Popup / Tooltip children. */
    children?: React.ReactNode;
} & DashComponentProps;

/**
 * CircleMarker draws a circle with a fixed pixel radius (it stays the same size at every
 * zoom). For a metric radius use Circle. Place it as a child of Map. Wraps Leaflet 2's
 * CircleMarker.
 */
const CircleMarker = ({
    center = [51.505, -0.09],
    radius = 10,
    color = '#3388ff',
    weight = 3,
    fillColor,
    fillOpacity = 0.2,
    interactive,
    setProps,
    children,
}: Props) => {
    const clicks = useRef(0);
    const style = () => ({ color, weight, fillColor, fillOpacity });
    const { layer, ref } = useLayer<LeafletCircleMarker>(() => {
        const l = new LeafletCircleMarker(center, { radius, interactive, ...style() });
        l.on('click', () => {
            clicks.current += 1;
            setProps && setProps({ n_clicks: clicks.current });
        });
        return l;
    });

    useEffect(() => {
        if (ref.current) ref.current.setLatLng(center);
    }, [center]);
    useEffect(() => {
        if (ref.current) ref.current.setRadius(radius);
    }, [radius]);
    useEffect(() => {
        if (ref.current) ref.current.setStyle(style());
    }, [color, weight, fillColor, fillOpacity]);

    return (
        <LeafletLayerContext.Provider value={layer}>
            {layer ? children : null}
        </LeafletLayerContext.Provider>
    );
};

export default CircleMarker;
