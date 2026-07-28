import { useEffect, useRef } from 'react';
import { TileLayer as LeafletTileLayer } from 'leaflet';
import { useLeafletMap } from '../context';
import { DashComponentProps } from '../props';

type Props = {
    /**
     * Tile URL template, e.g. "https://tile.openstreetmap.org/{z}/{x}/{y}.png".
     * Updating it swaps the basemap. [MUTABLE]
     */
    url?: string;

    /**
     * Attribution HTML shown in the bottom-right of the map.
     */
    attribution?: string;

    /**
     * Minimum zoom level at which this tile layer is visible. Below this zoom
     * Leaflet stops requesting tiles entirely (no 404 thrash on out-of-range
     * historical / harbor-cropped pyramids). Default 0.
     */
    minZoom?: number;

    /**
     * Maximum zoom level for this tile layer.
     */
    maxZoom?: number;

    /**
     * Maximum zoom level that the tile source actually has tiles for. Leaflet
     * upscales tiles from this zoom when the map zooms in past it (instead of
     * 404-ing). Useful for overlays whose cache caps below the map's max zoom —
     * e.g. USGS Hydro is only cached to z16; set `maxNativeZoom=16` and the
     * z16 tile will be shown at z17/z18.
     */
    maxNativeZoom?: number;

    /**
     * Geographic bounds outside of which no tiles are requested, as
     * `[[south, west], [north, east]]`. Same as Leaflet's `LatLngBounds`. Cheaper
     * than server-side 404s for out-of-area requests.
     */
    bounds?: [[number, number], [number, number]];

    /**
     * URL of an image shown in place of any tile that fails to load. A 1x1
     * transparent PNG data URL is the common "hide broken tiles" trick.
     */
    errorTileUrl?: string;

    /**
     * Explicit z-index for the tile layer's DOM pane. Higher = renders on top.
     * Useful when stacking multiple tile layers and DOM mount order alone is
     * insufficient. [MUTABLE]
     */
    zIndex?: number;

    /**
     * Subdomains substituted into the URL `{s}` placeholder. Accepts an array
     * like `['a','b','c']` or a string `'abc'` (each character is a subdomain).
     */
    subdomains?: string | string[];

    /**
     * If true, request tiles at 2x resolution on hi-DPI displays (loads twice
     * as many tiles but renders sharper).
     */
    detectRetina?: boolean;

    /**
     * If true, inverts Y coordinates so this layer works with TMS-shaped tile
     * pyramids (Leaflet defaults to XYZ).
     */
    tms?: boolean;

    /**
     * Layer opacity, 0..1. [MUTABLE]
     */
    opacity?: number;

    /**
     * Adds the `crossOrigin` attribute to every tile img element. Pass "anonymous"
     * to make tile loads CORS-mode so canvas captures (map screenshots /
     * html2canvas) can read the pixels. The tile host must answer with
     * Access-Control-Allow-Origin or the tiles fail to load entirely — leave
     * unset for hosts you don't control. "use-credentials" and "" are also
     * valid. Construction-time only.
     */
    crossOrigin?: string;
} & DashComponentProps;

/**
 * TileLayer loads and displays a raster tile basemap. Place it as a child of
 * Map. Wraps Leaflet 2's TileLayer.
 */
const TileLayer = ({
    url = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution = '&copy; OpenStreetMap contributors',
    minZoom = 0,
    maxZoom = 19,
    maxNativeZoom,
    bounds,
    errorTileUrl,
    zIndex,
    subdomains,
    detectRetina = false,
    tms = false,
    opacity = 1,
    crossOrigin,
}: Props) => {
    const map = useLeafletMap();
    const layerRef = useRef<LeafletTileLayer | null>(null);

    useEffect(() => {
        if (!map) return;
        const options: any = { attribution, minZoom, maxZoom, opacity, detectRetina, tms };
        if (maxNativeZoom !== undefined) options.maxNativeZoom = maxNativeZoom;
        if (bounds !== undefined) options.bounds = bounds;
        if (errorTileUrl !== undefined) options.errorTileUrl = errorTileUrl;
        if (zIndex !== undefined) options.zIndex = zIndex;
        if (subdomains !== undefined) options.subdomains = subdomains;
        if (crossOrigin !== undefined) options.crossOrigin = crossOrigin;
        const layer = new LeafletTileLayer(url as string, options);
        layer.addTo(map);
        layerRef.current = layer;
        return () => {
            layer.remove();
            layerRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map]);

    // React to mutable prop changes without recreating the layer.
    useEffect(() => {
        if (layerRef.current && url) layerRef.current.setUrl(url);
    }, [url]);

    useEffect(() => {
        const l: any = layerRef.current;
        if (l && typeof l.setOpacity === 'function') l.setOpacity(opacity);
    }, [opacity]);

    useEffect(() => {
        const l: any = layerRef.current;
        if (l && typeof l.setZIndex === 'function' && zIndex !== undefined) l.setZIndex(zIndex);
    }, [zIndex]);

    return null;
};

export default TileLayer;
