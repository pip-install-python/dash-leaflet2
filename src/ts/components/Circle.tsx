import React, { useEffect, useRef } from 'react';
import { Circle as LeafletCircle } from 'leaflet';
import { LeafletLayerContext } from '../context';
import { useLayer } from '../useLayer';
import { DashComponentProps } from '../props';

type Props = {
    /** Center as [lat, lng]. [MUTABLE] */
    center?: [number, number];
    /** Radius in METERS (geographic). [MUTABLE] */
    radius?: number;
    /** Stroke color. [MUTABLE] */
    color?: string;
    /** Stroke width in pixels. [MUTABLE] */
    weight?: number;
    /** Fill color (defaults to stroke color). [MUTABLE] */
    fillColor?: string;
    /** Fill opacity, 0..1. [MUTABLE] */
    fillOpacity?: number;
    /** Times the circle has been clicked. [READONLY] */
    n_clicks?: number;
    /** Popup / Tooltip children. */
    children?: React.ReactNode;
} & DashComponentProps;

/**
 * Circle draws a circle with a radius in meters (it grows/shrinks with zoom). For a
 * fixed-pixel circle use CircleMarker. Place it as a child of Map. Wraps Leaflet 2's Circle.
 */
const Circle = ({
    center = [51.505, -0.09],
    radius = 100,
    color = '#3388ff',
    weight = 3,
    fillColor,
    fillOpacity = 0.2,
    setProps,
    children,
}: Props) => {
    const clicks = useRef(0);
    const style = () => ({ color, weight, fillColor, fillOpacity });
    const { layer, ref } = useLayer<LeafletCircle>(() => {
        const l = new LeafletCircle(center, { radius, ...style() });
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

export default Circle;
