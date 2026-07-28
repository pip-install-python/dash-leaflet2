import React, { useEffect, useRef } from 'react';
import { Polygon as LeafletPolygon } from 'leaflet';
import { LeafletLayerContext } from '../context';
import { useLayer } from '../useLayer';
import { DashComponentProps } from '../props';

type Props = {
    /** Ring vertices as a list of [lat, lng] points (auto-closed). [MUTABLE] */
    positions?: [number, number][];
    /** Stroke color. [MUTABLE] */
    color?: string;
    /** Stroke width in pixels. [MUTABLE] */
    weight?: number;
    /** Stroke opacity, 0..1. [MUTABLE] */
    opacity?: number;
    /** Fill color (defaults to stroke color). [MUTABLE] */
    fillColor?: string;
    /** Fill opacity, 0..1. [MUTABLE] */
    fillOpacity?: number;
    /** Times the polygon has been clicked. [READONLY] */
    n_clicks?: number;
    /** Popup / Tooltip children. */
    children?: React.ReactNode;
} & DashComponentProps;

/**
 * Polygon draws a filled, closed shape from a list of [lat, lng] points. Place it as a
 * child of Map. Wraps Leaflet 2's Polygon.
 */
const Polygon = ({
    positions = [],
    color = '#3388ff',
    weight = 3,
    opacity = 1,
    fillColor,
    fillOpacity = 0.2,
    setProps,
    children,
}: Props) => {
    const clicks = useRef(0);
    const style = () => ({ color, weight, opacity, fillColor, fillOpacity });
    const { layer, ref } = useLayer<LeafletPolygon>(() => {
        const l = new LeafletPolygon(positions, style());
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
        if (ref.current) ref.current.setStyle(style());
    }, [color, weight, opacity, fillColor, fillOpacity]);

    return (
        <LeafletLayerContext.Provider value={layer}>
            {layer ? children : null}
        </LeafletLayerContext.Provider>
    );
};

export default Polygon;
