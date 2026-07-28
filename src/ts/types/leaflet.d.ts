/**
 * Minimal ambient declaration for Leaflet 2.0.0-alpha.1.
 *
 * Leaflet 2 alpha ships NO TypeScript types and its `exports` map points only
 * at the ESM source, so neither bundled types nor the (v1-shaped) @types/leaflet
 * apply cleanly. We declare just the surface the core-trio components touch,
 * loosely typed. As the component set grows, tighten these or replace with
 * upstream types once Leaflet 2 ships them.
 */
declare module 'leaflet' {
  export type LatLngTuple = [number, number];
  export interface LatLng { lat: number; lng: number; }

  export class Evented {
    on(type: string, fn: (e: any) => void, context?: any): this;
    off(type?: string, fn?: (e: any) => void, context?: any): this;
    fire(type: string, data?: any, propagate?: boolean): this;
  }

  export class Layer extends Evented {
    addTo(map: Map | LayerGroup): this;
    remove(): this;
    removeFrom(map: Map): this;
    bindPopup(content: string | HTMLElement, options?: any): this;
    unbindPopup(): this;
    bindTooltip(content: string | HTMLElement, options?: any): this;
    unbindTooltip(): this;
    openPopup(): this;
    closePopup(): this;
    setStyle(style: any): this;
  }

  // Path-family vector layers (all extend Layer transitively).
  export class Path extends Layer {
    constructor(options?: any);
    setStyle(style: any): this;
  }
  export class Polyline extends Path {
    constructor(latlngs: LatLngTuple[] | LatLng[], options?: any);
    setLatLngs(latlngs: any): this;
    getLatLngs(): any;
    addLatLng(latlng: LatLngTuple | LatLng): this;
    removeFrom(map: Map): this;
  }
  export class Polygon extends Polyline {}
  export class Rectangle extends Polygon {
    constructor(bounds: LatLngTuple[] | any, options?: any);
    setBounds(bounds: any): this;
  }
  export class CircleMarker extends Path {
    constructor(latlng: LatLngTuple | LatLng, options?: any);
    setLatLng(latlng: LatLngTuple | LatLng): this;
    setRadius(radius: number): this;
    getLatLng(): LatLng;
    getRadius(): number;
  }
  export class Circle extends CircleMarker {}

  export class FeatureGroup extends Layer {
    constructor(layers?: Layer[], options?: any);
    addLayer(layer: Layer): this;
    removeLayer(layer: Layer): this;
    clearLayers(): this;
    eachLayer(fn: (layer: Layer) => void): this;
    toGeoJSON(precision?: number): any;
    getLayers(): Layer[];
  }
  export class LatLngBounds {
    constructor(corner1: LatLngTuple | LatLng, corner2: LatLngTuple | LatLng);
    // Corner accessors — used by EditControl's rectangle-preview area calc
    // (geodesic width × height via map.distance(NW, NE/SW)).
    getNorthWest(): LatLng;
    getNorthEast(): LatLng;
    getSouthWest(): LatLng;
    getSouthEast(): LatLng;
    getNorth(): number;
    getSouth(): number;
    getEast(): number;
    getWest(): number;
  }
  export class GeoJSON extends FeatureGroup {
    constructor(geojson?: any, options?: any);
    addData(geojson: any): this;
  }

  export class Map extends Evented {
    constructor(el: string | HTMLElement, options?: any);
    setView(center: LatLngTuple | LatLng, zoom?: number, options?: any): this;
    flyTo(center: LatLngTuple | LatLng, zoom?: number, options?: any): this;
    // Pan / fit helpers used by the flyTo trigger in Map.tsx. v2 ships no
    // types — these mirror the live method signatures in
    // node_modules/leaflet/dist/leaflet-src.js (verified Nov 2025).
    panTo(center: LatLngTuple | LatLng, options?: any): this;
    panBy(offset: [number, number] | Point, options?: any): this;
    fitBounds(bounds: any, options?: any): this;
    flyToBounds(bounds: any, options?: any): this;
    panInsideBounds(bounds: any, options?: any): this;
    stop(): this;
    getCenter(): LatLng;
    getZoom(): number;
    getBounds(): any;
    addLayer(layer: Layer): this;
    removeLayer(layer: Layer): this;
    invalidateSize(options?: any): this;
    remove(): this;
    distance(a: LatLngTuple | LatLng, b: LatLngTuple | LatLng): number;
    project(latlng: LatLngTuple | LatLng, zoom?: number): Point;
    unproject(point: Point | [number, number], zoom?: number): LatLng;
    // Screen-space projection helpers used by TextMarker (rotation pivot + handle math).
    getContainer(): HTMLElement;
    latLngToLayerPoint(latlng: LatLngTuple | LatLng): Point;
    latLngToContainerPoint(latlng: LatLngTuple | LatLng): Point;
    containerPointToLatLng(point: Point | [number, number]): LatLng;
    dragging: { enable(): void; disable(): void; enabled(): boolean };
    doubleClickZoom: { enable(): void; disable(): void; enabled(): boolean };
    keyboard?: { enable(): void; disable(): void; enabled(): boolean };
    setMinZoom(zoom: number): this;
    setMaxZoom(zoom: number): this;
    setMaxBounds(bounds: any): this;
    getMinZoom(): number;
    getMaxZoom(): number;
  }

  export class Point {
    constructor(x: number, y: number);
    x: number;
    y: number;
  }

  export class ImageOverlay extends Layer {
    constructor(url: string, bounds: any, options?: any);
    setUrl(url: string): this;
    setBounds(bounds: any): this;
    setOpacity(opacity: number): this;
    setZIndex(zIndex: number): this;
  }

  export class TileLayer extends Layer {
    constructor(urlTemplate: string, options?: any);
    setUrl(url: string, noRedraw?: boolean): this;
    setOpacity(opacity: number): this;
    setZIndex(zIndex: number): this;
  }

  export class Marker extends Layer {
    constructor(latlng: LatLngTuple | LatLng, options?: any);
    setLatLng(latlng: LatLngTuple | LatLng): this;
    getLatLng(): LatLng;
    setOpacity(opacity: number): this;
    setZIndexOffset(offset: number): this;
    setIcon(icon: Icon | DivIcon): this;
    dragging?: { enable(): void; disable(): void; enabled(): boolean };
  }

  export class Icon {
    constructor(options: any);
    static Default: any;
  }
  export class DivIcon extends Icon {
    constructor(options?: any);
  }
  export function icon(options: any): Icon;

  export class LayerGroup extends Layer {
    constructor(layers?: Layer[], options?: any);
    addLayer(layer: Layer): this;
    removeLayer(layer: Layer): this;
  }

  export class Control {
    constructor(options?: any);
    addTo(map: Map): this;
    remove(): this;
    setPosition(position: string): this;
    getPosition(): string;
    getContainer(): HTMLElement | undefined;
    onAdd?: (map: Map) => HTMLElement;
    onRemove?: (map: Map) => void;
    options: any;
  }

  export const DomEvent: {
    disableClickPropagation(el: HTMLElement): any;
    disableScrollPropagation(el: HTMLElement): any;
    on(el: HTMLElement, types: string, fn: any, context?: any): any;
    off(el: HTMLElement, types: string, fn?: any, context?: any): any;
    stop(e: any): any;
  };

  export const DomUtil: {
    create(tag: string, className?: string, container?: HTMLElement): HTMLElement;
    addClass(el: HTMLElement, name: string): void;
    removeClass(el: HTMLElement, name: string): void;
    hasClass(el: HTMLElement, name: string): boolean;
  };

  const _default: any;
  export default _default;
}

// Allow `import 'leaflet/dist/leaflet.css'` and image imports.
declare module '*.css';
declare module '*.png';
declare module '*.svg';

// Minimal supercluster typing — used by GeoJSON's clustering mode. The npm package
// ships no types; these signatures match supercluster@8.
declare module 'supercluster' {
    export default class Supercluster {
        constructor(options?: any);
        load(features: any[]): this;
        getClusters(bbox: [number, number, number, number], zoom: number): any[];
        getChildren(clusterId: number): any[];
        getLeaves(clusterId: number, limit?: number, offset?: number): any[];
        getClusterExpansionZoom(clusterId: number): number;
        getTile(z: number, x: number, y: number): any;
    }
}

// Allow <iconify-icon> as a JSX intrinsic element (the iconify-icon web component is
// registered by importing `iconify-icon` in icons.ts).
declare namespace JSX {
    interface IntrinsicElements {
        'iconify-icon': any;
    }
}
