import React, { useMemo, useRef } from 'react';
import { FeatureGroup as LeafletFeatureGroup, Layer } from 'leaflet';
import { LeafletMapContext } from '../context';
import { useLayer } from '../useLayer';
import { makeForwardingMapProxy } from '../layersControl-shared';
import { DashComponentProps } from '../props';

type Props = {
    /** Any number of layer children (Marker, Polygon, Circle, ...). */
    children?: React.ReactNode;
    /** Number of times any child layer has been clicked. [READONLY] */
    n_clicks?: number;
    /** Combined GeoJSON FeatureCollection of all children (vectors only). [READONLY] */
    geojson?: object;
    /** Number of times the group's children were modified. [READONLY] */
    n_layers?: number;
} & DashComponentProps;

/**
 * FeatureGroup is like LayerGroup but extends `leaflet.FeatureGroup` — it can
 * emit a combined GeoJSON of its vector children and broadcasts a single
 * `click` event no matter which child was clicked. Use it when grouping
 * shapes you want to treat as one unit (typical companion for `EditControl`).
 * Wraps Leaflet 2's FeatureGroup.
 */
const FeatureGroup = ({ setProps, children }: Props) => {
    const groupRef = useRef<LeafletFeatureGroup | null>(null);
    const clicksRef = useRef<number>(0);
    const nLayersRef = useRef<number>(0);

    const { layer } = useLayer<LeafletFeatureGroup>(() => {
        const g = new LeafletFeatureGroup();
        groupRef.current = g;

        const emitGeoJSON = () => {
            if (!setProps) return;
            try {
                const gj = (g as any).toGeoJSON();
                nLayersRef.current += 1;
                setProps({ geojson: gj, n_layers: nLayersRef.current });
            } catch (_e) {
                /* non-geo children — skip */
            }
        };

        g.on('click', () => {
            clicksRef.current += 1;
            setProps && setProps({ n_clicks: clicksRef.current });
        });
        g.on('layeradd layerremove', emitGeoJSON);

        return g;
    });

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

export default FeatureGroup;
