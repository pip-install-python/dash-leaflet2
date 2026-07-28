import React from 'react';
import { Map as LeafletMap, Layer } from 'leaflet';

/**
 * The bridge that replaces react-leaflet's context. <Map> creates the Leaflet 2 map
 * instance imperatively and publishes it here; layer components (TileLayer, Marker,
 * Polygon, ...) read it and add themselves via useEffect.
 */
export const LeafletMapContext = React.createContext<LeafletMap | null>(null);

export const useLeafletMap = (): LeafletMap | null =>
    React.useContext(LeafletMapContext);

/**
 * A second context published by interactive layers (Marker, Polygon, ...) so their
 * children — Popup and Tooltip — can bind to the parent layer instead of the map.
 * Null when a Popup/Tooltip is placed directly under <Map>.
 */
export const LeafletLayerContext = React.createContext<Layer | null>(null);

export const useLeafletLayer = (): Layer | null =>
    React.useContext(LeafletLayerContext);

/**
 * Bearing (rotation) bridge. <Map> publishes the current bearing and a setter;
 * child components like <Marker> (counter-rotation when rotateWithMap=true) and
 * <KeyboardControl> (arrow-key rotation) consume / mutate it.
 *
 * The bearing live on the Map's React state, NOT inside Leaflet — Leaflet 2
 * has no native rotation. The visual rotation is implemented as a CSS
 * transform on the map pane (see src/ts/components/Map.tsx).
 */
export interface LeafletBearingState {
    bearing: number;
    setBearing: (b: number) => void;
}

export const LeafletBearingContext = React.createContext<LeafletBearingState>({
    bearing: 0,
    setBearing: () => {},
});

export const useLeafletBearing = (): LeafletBearingState =>
    React.useContext(LeafletBearingContext);
