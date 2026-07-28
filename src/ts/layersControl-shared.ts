import React from 'react';
import { Layer } from 'leaflet';

/**
 * Shared registration plumbing for LayersControl ↔ BaseLayer / Overlay.
 *
 * Children of LayersControl publish themselves through this context with their name + kind
 * (base or overlay) + layer instance. The control then manages which entries are on the
 * real map in response to user interaction (radios for bases, checkboxes for overlays).
 */
export type EntryKind = 'base' | 'overlay';

export type RegisterFn = (
    name: string,
    kind: EntryKind,
    layer: Layer,
    initialChecked: boolean
) => () => void;

export const RegisterContext = React.createContext<RegisterFn | null>(null);

/**
 * A minimal stand-in for a Leaflet Map that captures the single `addLayer` call a layer
 * component makes during its `addTo(map)`. Everything else is a no-op; the real map adopts
 * the layer later via realMap.addLayer(layer), at which point Leaflet sets layer._map.
 */
export function makeMapProxy(onAddLayer: (layer: Layer) => void): any {
    return {
        addLayer(layer: Layer) {
            onAddLayer(layer);
            return this;
        },
        removeLayer() {
            return this;
        },
        hasLayer: () => false,
        getPanes: () => ({}),
    };
}

/**
 * Like `makeMapProxy`, but for container components (LayerGroup / FeatureGroup) where
 * children also need to call methods on the actual map — `latLngToLayerPoint`,
 * `getCenter`, `on`, etc. The proxy intercepts `addLayer` / `removeLayer` to route
 * additions into our container, and forwards every other access to the real map
 * (looked up lazily so children that mount before the container is attached still
 * get a live reference once it is).
 */
export function makeForwardingMapProxy(
    onAddLayer: (layer: Layer) => void,
    onRemoveLayer: (layer: Layer) => void,
    getRealMap: () => any
): any {
    const intercepted: Record<string, any> = {
        addLayer(layer: Layer) {
            onAddLayer(layer);
            return this;
        },
        removeLayer(layer: Layer) {
            onRemoveLayer(layer);
            return this;
        },
    };
    return new Proxy(intercepted, {
        get(target, prop: any) {
            if (prop in target) return target[prop];
            const real = getRealMap();
            if (!real) return undefined;
            const val = real[prop];
            return typeof val === 'function' ? val.bind(real) : val;
        },
        has(target, prop) {
            if (prop in target) return true;
            const real = getRealMap();
            return real ? prop in real : false;
        },
    });
}
