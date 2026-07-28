import React, { useEffect, useRef } from 'react';
import { Rectangle as LeafletRectangle } from 'leaflet';
import { LeafletLayerContext } from '../context';
import { useLayer } from '../useLayer';
import { DashComponentProps } from '../props';

type Props = {
    /** Geographic bounds as [[south, west], [north, east]]. [MUTABLE] */
    bounds?: [[number, number], [number, number]];
    /** Stroke color. [MUTABLE] */
    color?: string;
    /** Stroke width in pixels. [MUTABLE] */
    weight?: number;
    /** Fill color (defaults to stroke color). [MUTABLE] */
    fillColor?: string;
    /** Fill opacity, 0..1. [MUTABLE] */
    fillOpacity?: number;
    /** Times the rectangle has been clicked. [READONLY] */
    n_clicks?: number;
    /** Popup / Tooltip children. */
    children?: React.ReactNode;
} & DashComponentProps;

/**
 * Rectangle draws an axis-aligned box from geographic bounds. Place it as a child of Map.
 * Wraps Leaflet 2's Rectangle.
 */
const Rectangle = ({
    bounds = [[0, 0], [0, 0]],
    color = '#3388ff',
    weight = 3,
    fillColor,
    fillOpacity = 0.2,
    setProps,
    children,
}: Props) => {
    const clicks = useRef(0);
    const style = () => ({ color, weight, fillColor, fillOpacity });
    const { layer, ref } = useLayer<LeafletRectangle>(() => {
        const l = new LeafletRectangle(bounds as any, style());
        l.on('click', () => {
            clicks.current += 1;
            setProps && setProps({ n_clicks: clicks.current });
        });
        return l;
    });

    useEffect(() => {
        if (ref.current) ref.current.setBounds(bounds as any);
    }, [bounds]);
    useEffect(() => {
        if (ref.current) ref.current.setStyle(style());
    }, [color, weight, fillColor, fillOpacity]);

    return (
        <LeafletLayerContext.Provider value={layer}>
            {layer ? children : null}
        </LeafletLayerContext.Provider>
    );
};

export default Rectangle;
