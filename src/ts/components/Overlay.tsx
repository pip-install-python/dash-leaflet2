import React, { useEffect, useMemo, useRef } from 'react';
import { LeafletMapContext } from '../context';
import { RegisterContext, makeMapProxy } from '../layersControl-shared';
import { DashComponentProps } from '../props';

type Props = {
    /** Display name shown in the LayersControl (also the checkbox's identity). */
    name?: string;
    /** Initially checked? Overlays are independent. */
    checked?: boolean;
    /** The Leaflet layer (TileLayer, GeoJSON, Marker, ...) controlled by this entry. */
    children?: React.ReactNode;
} & DashComponentProps;

/**
 * Overlay wraps any layer and registers it as a toggleable overlay in the parent
 * LayersControl (checkbox). Place it as a child of LayersControl, with a single layer
 * component as its own child.
 */
const Overlay = ({ name = 'Overlay', checked = false, children }: Props) => {
    const register = React.useContext(RegisterContext);
    const unregisterRef = useRef<(() => void) | null>(null);

    const proxy = useMemo(
        () =>
            makeMapProxy((layer) => {
                if (register && !unregisterRef.current) {
                    unregisterRef.current = register(name, 'overlay', layer, checked);
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

export default Overlay;
