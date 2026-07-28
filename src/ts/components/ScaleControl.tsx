import { useEffect, useRef } from 'react';
import { Control } from 'leaflet';
import { useLeafletMap } from '../context';
import { DashComponentProps } from '../props';

type Props = {
    /** "topleft" | "topright" | "bottomleft" | "bottomright". Default "bottomleft". [MUTABLE] */
    position?: 'topleft' | 'topright' | 'bottomleft' | 'bottomright';
    /** Show metric (km/m) bar. Default true. */
    metric?: boolean;
    /** Show imperial (mi/ft) bar. Default false. */
    imperial?: boolean;
    /** Maximum bar width in pixels. Default 100. */
    maxWidth?: number;
    /** Only redraw the bar when the map stops moving. Default false. */
    updateWhenIdle?: boolean;
} & DashComponentProps;

/**
 * ScaleControl shows a metric and/or imperial scale bar in a map corner.
 * Wraps Leaflet 2's built-in `Control.Scale` (lives on the Control namespace
 * but not exported by the ESM — we reach in through `Control.Scale`).
 */
const ScaleControl = ({
    position = 'bottomleft',
    metric = true,
    imperial = false,
    maxWidth = 100,
    updateWhenIdle = false,
}: Props) => {
    const map = useLeafletMap();
    const ctlRef = useRef<any>(null);

    useEffect(() => {
        if (!map) return;
        const Scale = (Control as any).Scale;
        if (!Scale) return;
        const ctl = new Scale({ position, metric, imperial, maxWidth, updateWhenIdle });
        ctl.addTo(map);
        ctlRef.current = ctl;
        return () => {
            try { ctl.remove(); } catch (e) {}
            ctlRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map, metric, imperial, maxWidth, updateWhenIdle]);

    useEffect(() => {
        if (ctlRef.current && position) ctlRef.current.setPosition(position);
    }, [position]);

    return null;
};

export default ScaleControl;
