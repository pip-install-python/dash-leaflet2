import React, { useEffect, useRef } from 'react';
import L, {
    DivIcon,
    FeatureGroup,
    GeoJSON as LeafletGeoJSON,
    Marker,
} from 'leaflet';
import { LeafletLayerContext } from '../context';
import { useLayer } from '../useLayer';
import { DEFAULT_ICON } from '../icons';
import { DashComponentProps } from '../props';
import Supercluster from 'supercluster';

type Props = {
    /** A GeoJSON FeatureCollection / Feature / geometry object. [MUTABLE] */
    data?: object;
    /** Path style applied to all vector features, e.g. {color, weight, fillOpacity}. [MUTABLE] */
    style?: object;

    /**
     * Turn on supercluster-based point clustering. Markers within `superClusterOptions.radius`
     * pixels collapse into a single cluster bubble; zooming in expands them. Only point
     * geometries cluster; vector features (LineString, Polygon) are passed through unchanged.
     */
    cluster?: boolean;

    /**
     * Tuning for the underlying SuperCluster index: `{ radius, minPoints, maxZoom, minZoom, extent }`.
     * Defaults: `{ radius: 80, minPoints: 2, maxZoom: 16, minZoom: 0, extent: 512 }`.
     * See https://github.com/mapbox/supercluster#options for the full list.
     */
    superClusterOptions?: Record<string, any>;

    /**
     * JavaScript source for a function that converts an individual point feature into a layer.
     * Signature: `(feature, latlng, ctx) => Layer`, where `ctx = { hideout, leaflet, map }`.
     * Pass the function body as a string; it is wrapped in `new Function(...)` at construction
     * time. The default uses the bundled DEFAULT_ICON.
     */
    pointToLayer?: string;

    /**
     * JavaScript source for a function that builds the layer shown in place of a SuperCluster
     * cluster. Signature: `(feature, latlng, index, ctx) => Layer`. The default is a small
     * DivIcon with the cluster's point count.
     */
    clusterToLayer?: string;

    /**
     * Arbitrary pass-through data made available to `pointToLayer` / `clusterToLayer` as
     * `ctx.hideout`. Use it to ship colour maps, label dictionaries, or threshold values
     * from Python without re-evaluating the JS function. [MUTABLE]
     */
    hideout?: Record<string, any>;

    /**
     * If true, clicking a cluster fits the map to that cluster's children's bounds.
     * Default true.
     */
    zoomToBoundsOnClick?: boolean;

    /**
     * Reserved for future support — at max zoom, "spiderfy" overlapping markers into a
     * ring so each is individually selectable. Currently a no-op (clicking the cluster
     * at maxZoom still triggers zoomToBoundsOnClick).
     */
    spiderfyOnMaxZoom?: boolean;

    /** Number of times any feature has been clicked. [READONLY] */
    n_clicks?: number;
    /** `properties` of the most recently clicked feature. [READONLY] */
    clickFeature?: object;
    /** Popup / Tooltip children bound to the whole layer. */
    children?: React.ReactNode;
} & DashComponentProps;

// Default DivIcon for a SuperCluster cluster: a soft glass bubble with the count.
function defaultClusterIcon(count: number): DivIcon {
    let size = 32;
    if (count >= 1000) size = 56;
    else if (count >= 100) size = 48;
    else if (count >= 10) size = 40;
    return new DivIcon({
        html: `<div class="dl2-cluster-bubble dl2-cluster-${size}">${count}</div>`,
        className: '',
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
    });
}

function compileFn(source: string | undefined): Function | null {
    if (!source) return null;
    try {
        // The user passes a function expression as a string. Wrap it so the
        // expression evaluates to a function value we can invoke.
        // eslint-disable-next-line no-new-func
        const factory = new Function('return (' + source + ')');
        const fn = factory();
        return typeof fn === 'function' ? fn : null;
    } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('dl2.GeoJSON: failed to compile user function', err);
        return null;
    }
}

/**
 * GeoJSON renders a GeoJSON object — typically fed from a Python callback via the `data`
 * prop. Set `cluster=True` to collapse dense point sets via SuperCluster (the same backend
 * dash-leaflet 1's clustering uses). Custom `pointToLayer` / `clusterToLayer` JS strings
 * plus a `hideout` passthrough let you style features without round-tripping through Python.
 * Place it as a child of Map. Wraps Leaflet 2's GeoJSON layer.
 */
const GeoJSON = ({
    data,
    style,
    cluster = false,
    superClusterOptions,
    pointToLayer,
    clusterToLayer,
    hideout,
    zoomToBoundsOnClick = true,
    spiderfyOnMaxZoom = false,
    setProps,
    children,
}: Props) => {
    const clicks = useRef(0);
    const styleRef = useRef<object | undefined>(style);
    styleRef.current = style;
    const hideoutRef = useRef<Record<string, any> | undefined>(hideout);
    hideoutRef.current = hideout;

    // Compile the user-supplied function strings once per source change.
    const pointFnRef = useRef<Function | null>(compileFn(pointToLayer));
    const clusterFnRef = useRef<Function | null>(compileFn(clusterToLayer));
    useEffect(() => { pointFnRef.current = compileFn(pointToLayer); }, [pointToLayer]);
    useEffect(() => { clusterFnRef.current = compileFn(clusterToLayer); }, [clusterToLayer]);

    // The shared FeatureGroup acts as the container layer. We attach our cluster /
    // non-cluster sub-layers into this group; LayersControl / Map see one layer.
    const indexRef = useRef<any>(null);
    const clusterContainerRef = useRef<FeatureGroup | null>(null);

    const buildCtx = () => ({
        hideout: hideoutRef.current || {},
        leaflet: L,
        map: (layerRef as any).current?._map,
    });

    const renderPoint = (feature: any, latlng: any) => {
        const fn = pointFnRef.current;
        if (fn) {
            try {
                return fn(feature, latlng, buildCtx());
            } catch (err) {
                // eslint-disable-next-line no-console
                console.warn('dl2.GeoJSON.pointToLayer threw', err);
            }
        }
        return new Marker(latlng, { icon: DEFAULT_ICON });
    };

    const renderCluster = (feature: any, latlng: any, index: any) => {
        const fn = clusterFnRef.current;
        if (fn) {
            try {
                return fn(feature, latlng, index, buildCtx());
            } catch (err) {
                // eslint-disable-next-line no-console
                console.warn('dl2.GeoJSON.clusterToLayer threw', err);
            }
        }
        const count = feature.properties.point_count || 0;
        return new Marker(latlng, { icon: defaultClusterIcon(count) });
    };

    const wireClick = (lyr: any, feature: any) => {
        lyr.on('click', () => {
            clicks.current += 1;
            setProps &&
                setProps({
                    n_clicks: clicks.current,
                    clickFeature: (feature && feature.properties) || {},
                });
        });
    };

    const { layer, ref: layerRef } = useLayer<FeatureGroup>(() => {
        // Whether or not cluster is on, we render into a FeatureGroup so popups /
        // tooltips bound to the layer cover all features.
        return new FeatureGroup();
    });

    // (Re)compute features on data / cluster-mode change.
    const rerender = () => {
        const fg = layerRef.current as any;
        if (!fg) return;
        const map: any = fg._map;
        if (!map) return;

        fg.clearLayers();

        if (cluster) {
            // Build/refresh the supercluster index and render visible clusters/points.
            const features = (data as any)?.features || [];
            const points = features.filter(
                (f: any) => f && f.geometry && f.geometry.type === 'Point'
            );
            const nonPoints = features.filter(
                (f: any) => f && f.geometry && f.geometry.type !== 'Point'
            );
            const opts = {
                radius: 80,
                minPoints: 2,
                maxZoom: 16,
                minZoom: 0,
                extent: 512,
                ...(superClusterOptions || {}),
            };
            const idx = new Supercluster(opts as any);
            idx.load(points as any);
            indexRef.current = idx;
            clusterContainerRef.current = fg;

            // Pass non-point features through unclustered.
            if (nonPoints.length) {
                const gj = new LeafletGeoJSON(
                    { type: 'FeatureCollection', features: nonPoints },
                    {
                        style: () => styleRef.current || {},
                        onEachFeature: (feature: any, lyr: any) => wireClick(lyr, feature),
                    } as any
                );
                fg.addLayer(gj as any);
            }

            const draw = () => {
                if (!fg._map) return;
                // Remove just the cluster-rendered sub-layers (keep the non-point GeoJSON).
                fg.eachLayer((l: any) => {
                    if (l && l.__dl2_cluster) fg.removeLayer(l);
                });

                const bounds = (map as any).getBounds();
                const bbox = [
                    bounds.getWest(),
                    bounds.getSouth(),
                    bounds.getEast(),
                    bounds.getNorth(),
                ] as [number, number, number, number];
                const zoom = Math.round(map.getZoom());
                const clusters = idx.getClusters(bbox, zoom);

                for (const f of clusters) {
                    const [lng, lat] = f.geometry.coordinates;
                    let lyr: any;
                    if (f.properties && f.properties.cluster) {
                        lyr = renderCluster(f, [lat, lng], idx);
                        lyr.__dl2_cluster = true;
                        lyr.on('click', () => {
                            const id = f.properties.cluster_id;
                            if (zoomToBoundsOnClick) {
                                try {
                                    const expansionZoom = Math.min(
                                        idx.getClusterExpansionZoom(id),
                                        opts.maxZoom + 2
                                    );
                                    map.flyTo([lat, lng], expansionZoom, { duration: 0.4 });
                                } catch (e) {
                                    map.flyTo([lat, lng], map.getZoom() + 2);
                                }
                            }
                            setProps &&
                                setProps({
                                    n_clicks: ++clicks.current,
                                    clickFeature: f.properties,
                                });
                        });
                    } else {
                        // Re-wrap as a feature shape compatible with the user pointToLayer.
                        const origFeature = {
                            type: 'Feature',
                            geometry: f.geometry,
                            properties: f.properties,
                        };
                        lyr = renderPoint(origFeature, [lat, lng]);
                        lyr.__dl2_cluster = true;
                        wireClick(lyr, origFeature);
                    }
                    fg.addLayer(lyr);
                }
            };

            // Bind once.
            if (!(fg as any).__dl2_clusterListenersBound) {
                (fg as any).__dl2_clusterListenersBound = true;
                map.on('moveend zoomend', draw);
                (fg as any).__dl2_clusterRedraw = draw;
            }
            draw();
        } else {
            // Non-cluster path: render features through LeafletGeoJSON, same as before.
            if (!data) return;
            const gj = new LeafletGeoJSON(data, {
                style: () => styleRef.current || {},
                pointToLayer: (feature: any, latlng: any) => renderPoint(feature, latlng),
                onEachFeature: (feature: any, lyr: any) => wireClick(lyr, feature),
            } as any);
            fg.addLayer(gj as any);
        }
    };

    // Initial render and on data / style / cluster / superClusterOptions change.
    useEffect(() => {
        rerender();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [layer, data, style, cluster, JSON.stringify(superClusterOptions)]);

    // hideout updates re-render so user functions read the latest passthrough.
    useEffect(() => {
        if (cluster) {
            const fg = layerRef.current as any;
            const draw = fg && fg.__dl2_clusterRedraw;
            if (draw) draw();
        } else {
            rerender();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [hideout]);

    return (
        <LeafletLayerContext.Provider value={layer}>
            {layer ? children : null}
        </LeafletLayerContext.Provider>
    );
};

export default GeoJSON;
