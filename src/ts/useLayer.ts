import React, { useEffect, useRef, useState } from 'react';
import { Layer } from 'leaflet';
import { useLeafletMap } from './context';

/**
 * Shared lifecycle for every layer component (vectors, GeoJSON, ...).
 *
 * - waits for the map from context,
 * - calls `build()` once to create the Leaflet layer, adds it,
 * - exposes the instance both as state (so the component can publish it via
 *   LeafletLayerContext to Popup/Tooltip children, re-rendering when ready) and
 *   as a ref (for imperative [MUTABLE]-prop updates),
 * - removes it on unmount so handlers don't leak across Dash page changes.
 *
 * `build` is invoked once; bind any event handlers inside it (closures over the
 * stable `setProps` and component refs are fine — see the components for the
 * ref-based counter pattern).
 */
export function useLayer<T extends Layer>(build: () => T): {
    layer: T | null;
    ref: React.MutableRefObject<T | null>;
} {
    const map = useLeafletMap();
    const ref = useRef<T | null>(null);
    const [layer, setLayer] = useState<T | null>(null);

    useEffect(() => {
        if (!map) return;
        const instance = build();
        instance.addTo(map);
        ref.current = instance;
        setLayer(instance);
        return () => {
            instance.remove();
            ref.current = null;
            setLayer(null);
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map]);

    return { layer, ref };
}
