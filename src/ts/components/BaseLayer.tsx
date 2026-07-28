import React, { useEffect, useMemo, useRef } from 'react';
import { LeafletMapContext } from '../context';
import { RegisterContext, makeMapProxy } from '../layersControl-shared';
import { DashComponentProps } from '../props';

type Props = {
    /** Display name shown in the LayersControl (also the radio's identity). */
    name?: string;
    /** Initially selected base layer? Exactly one base is active at a time. */
    checked?: boolean;
    /** The Leaflet layer (typically a dl2.TileLayer) controlled by this entry. */
    children?: React.ReactNode;
} & DashComponentProps;

/**
 * BaseLayer wraps a layer (typically a TileLayer) and registers it as a base layer in the
 * parent LayersControl. Bases are mutually exclusive (radio). Place it as a child of
 * LayersControl, with a single layer component (e.g. TileLayer) as its own child.
 */
const BaseLayer = ({ name = 'Base', checked = false, children }: Props) => {
    const register = React.useContext(RegisterContext);
    const unregisterRef = useRef<(() => void) | null>(null);

    // Capture the child layer's addTo call (forwarded to the LayersControl's register).
    const proxy = useMemo(
        () =>
            makeMapProxy((layer) => {
                if (register && !unregisterRef.current) {
                    unregisterRef.current = register(name, 'base', layer, checked);
                }
            }),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [name]
    );

    useEffect(
        () => () => {
            if (unregisterRef.current) unregisterRef.current();
            unregisterRef.current = null;
        },
        []
    );

    return (
        <LeafletMapContext.Provider value={proxy as any}>{children}</LeafletMapContext.Provider>
    );
};

export default BaseLayer;
