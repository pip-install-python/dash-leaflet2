import React, { useMemo, useRef } from 'react';
import { LayerGroup as LeafletLayerGroup, Layer } from 'leaflet';
import { LeafletMapContext } from '../context';
import { useLayer } from '../useLayer';
import { makeForwardingMapProxy } from '../layersControl-shared';
import { DashComponentProps } from '../props';

type Props = {
    /** Any number of layer children (Marker, Polygon, Circle, GeoJSON, ...). */
    children?: React.ReactNode;
} & DashComponentProps;

/**
 * LayerGroup bundles N layers so they can be added/removed together. Drop child
 * layers (Marker, Polygon, Circle, GeoJSON, ...) inside it; each is added to a
 * shared `leaflet.LayerGroup` instead of the map directly. Place it as a child
 * of `dl2.Map` — or of `dl2.Overlay` inside a LayersControl, to toggle the
 * whole group as one entry. Wraps Leaflet 2's LayerGroup.
 */
const LayerGroup = ({ children }: Props) => {
    const groupRef = useRef<LeafletLayerGroup | null>(null);

    const { layer } = useLayer<LeafletLayerGroup>(() => {
        const g = new LeafletLayerGroup();
        groupRef.current = g;
        return g;
    });

    // Forward map methods (latLngToLayerPoint, getCenter, on, ...) through to
    // the real map so children like Marker's rotation effect — which needs the
    // real map's projection — work unchanged. Intercept addLayer/removeLayer
    // to route the child layers into OUR group instead of the map directly.
    const proxy = useMemo(
        () =>
            makeForwardingMapProxy(
                (child) => {
                    const g = groupRef.current;
                    if (g) (g as any).addLayer(child as Layer);
                },
                (child) => {
                    const g = groupRef.current;
                    if (g) (g as any).removeLayer(child as Layer);
                },
                () => (groupRef.current as any)?._map || null
            ),
        []
    );

    return (
        <LeafletMapContext.Provider value={proxy as any}>
            {layer ? children : null}
        </LeafletMapContext.Provider>
    );
};

export default LayerGroup;
