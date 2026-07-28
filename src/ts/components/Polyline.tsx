import React, { useEffect, useRef } from 'react';
import { Polyline as LeafletPolyline } from 'leaflet';
import { LeafletLayerContext } from '../context';
import { useLayer } from '../useLayer';
import { DashComponentProps } from '../props';

type Props = {
    /** Vertices as a list of [lat, lng] points. [MUTABLE] */
    positions?: [number, number][];
    /** Stroke color. [MUTABLE] */
    color?: string;
    /** Stroke width in pixels. [MUTABLE] */
    weight?: number;
    /** Stroke opacity, 0..1. [MUTABLE] */
    opacity?: number;
    /** Dash pattern, e.g. "5,10". [MUTABLE] */
    dashArray?: string;
    /** Whether the line captures pointer events (fires clicks, blocks the map click
     *  underneath). Set false for a non-interactive decoration / context overlay so it
     *  never intercepts clicks meant for the map. Construction-only. @default true */
    interactive?: boolean;
    /** Times the line has been clicked. [READONLY] */
    n_clicks?: number;
    /** Popup / Tooltip children. */
    children?: React.ReactNode;
} & DashComponentProps;

/**
 * Polyline draws a multi-segment line from a list of [lat, lng] points. Place it as a
 * child of Map. Wraps Leaflet 2's Polyline.
 */
const Polyline = ({
    positions = [],
    color = '#3388ff',
    weight = 3,
    opacity = 1,
    dashArray,
    interactive,
    setProps,
    children,
}: Props) => {
    const clicks = useRef(0);
    const { layer, ref } = useLayer<LeafletPolyline>(() => {
        const l = new LeafletPolyline(positions, { color, weight, opacity, dashArray, interactive });
        l.on('click', () => {
            clicks.current += 1;
            setProps && setProps({ n_clicks: clicks.current });
        });
        return l;
    });

    useEffect(() => {
        if (ref.current) ref.current.setLatLngs(positions);
    }, [positions]);
    useEffect(() => {
        if (ref.current) ref.current.setStyle({ color, weight, opacity, dashArray });
    }, [color, weight, opacity, dashArray]);

    return (
        <LeafletLayerContext.Provider value={layer}>
            {layer ? children : null}
        </LeafletLayerContext.Provider>
    );
};

export default Polyline;
