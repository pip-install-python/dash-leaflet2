import { useEffect, useRef } from 'react';
import { Control, DomEvent } from 'leaflet';
import { useLeafletMap } from '../context';
import { DashComponentProps } from '../props';

// Leaflet 2's built-in `Attribution` extends `Control` but is NOT exported by the
// v2 ESM (the namespace lives on `map.attributionControl`). We port the ~20 lines
// of `_update` logic into a small Control subclass so dl2 owns the lifecycle
// (mount / move / unmount) the same way it owns LayersControl. Mirrors the
// dash-leaflet API: `position` + `prefix` (string | false), positions in any of
// the four corners, `prefix=False` hides the "Leaflet" link.
//
// If the host `dl2.Map` was created with `attributionControl=True` (default),
// Leaflet has already mounted its own bundled attribution. This component
// removes that one on mount so the two don't stack — the user opted into
// explicit control by adding us.

type Props = {
    /** Map control position. Default 'bottomright'. [MUTABLE] */
    position?: 'topleft' | 'topright' | 'bottomleft' | 'bottomright';
    /**
     * HTML shown before the layer attributions. Default Leaflet's "Leaflet"
     * link. Pass `False` (or empty string) to hide the prefix entirely. [MUTABLE]
     */
    prefix?: string | false;
} & DashComponentProps;

const DEFAULT_PREFIX =
    '<a target="_blank" href="https://leafletjs.com" title="A JavaScript library for interactive maps">Leaflet</a>';

class Dl2Attribution extends (Control as any) {
    constructor(options: any) {
        super(options);
        this._attributions = {} as Record<string, number>;
    }
    options!: any;
    _attributions!: Record<string, number>;
    _container!: HTMLDivElement;
    _map!: any;

    onAdd(map: any) {
        // Same wire-up as Leaflet's bundled Attribution.onAdd — read every
        // existing layer's getAttribution() string into our index, then
        // subscribe to subsequent layeradd events.
        const el = document.createElement('div');
        el.className = 'leaflet-control-attribution';
        DomEvent.disableClickPropagation(el);
        this._container = el;

        for (const layer of Object.values(map._layers || {})) {
            const a = (layer as any).getAttribution?.();
            if (a) this._addAttributionText(a);
        }
        map.on('layeradd', this._onLayerAdd, this);
        this._update();
        return el;
    }
    onRemove(map: any) {
        map.off('layeradd', this._onLayerAdd, this);
    }
    _onLayerAdd(ev: any) {
        const a = ev.layer?.getAttribution?.();
        if (a) {
            this._addAttributionText(a);
            ev.layer.once('remove', () => this._removeAttributionText(a));
        }
    }
    _addAttributionText(text: string) {
        if (!text) return;
        this._attributions[text] = (this._attributions[text] || 0) + 1;
        this._update();
    }
    _removeAttributionText(text: string) {
        if (!text || !this._attributions[text]) return;
        this._attributions[text]--;
        this._update();
    }
    setPrefix(prefix: string | false) {
        this.options.prefix = prefix;
        this._update();
        return this;
    }
    _update() {
        if (!this._map) return;
        const attribs = Object.keys(this._attributions).filter((k) => this._attributions[k]);
        const parts: string[] = [];
        if (this.options.prefix) parts.push(this.options.prefix as string);
        if (attribs.length) parts.push(attribs.join(', '));
        this._container.innerHTML = parts.join(' <span aria-hidden="true">|</span> ');
    }
}

/**
 * AttributionControl adds an explicitly-controlled attribution box to the map. Place
 * it as a child of `dl2.Map` with `attributionControl=False` to take over from the
 * bundled default; both `position` and `prefix` are two-way (mutable from Python
 * callbacks). Pass `prefix=False` to hide the "Leaflet" link.
 */
const AttributionControl = ({
    position = 'bottomright',
    prefix,
}: Props) => {
    const map = useLeafletMap();
    const controlRef = useRef<any>(null);

    // Resolve the effective prefix: undefined -> default 'Leaflet' link; `false`
    // -> no prefix; any string passed through verbatim (HTML allowed, same as
    // dash-leaflet's behavior).
    const effectivePrefix: string | false =
        prefix === undefined ? DEFAULT_PREFIX : prefix === false ? false : prefix;

    useEffect(() => {
        if (!map) return;
        // If the Map was created with attributionControl=true (default), Leaflet
        // already mounted its own bundled control. Remove it so ours can take
        // over without two boxes stacking on the same corner.
        const existing = (map as any).attributionControl;
        if (existing && typeof existing.remove === 'function') {
            try { existing.remove(); } catch (e) { /* ignore */ }
            (map as any).attributionControl = undefined;
        }
        const ctl = new Dl2Attribution({ position, prefix: effectivePrefix });
        ctl.addTo(map);
        controlRef.current = ctl;
        return () => {
            try { ctl.remove(); } catch (e) {}
            controlRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map]);

    // React to prop changes — both `position` and `prefix` are MUTABLE.
    useEffect(() => {
        const ctl = controlRef.current;
        if (ctl && position) ctl.setPosition(position);
    }, [position]);

    useEffect(() => {
        const ctl = controlRef.current;
        if (ctl) ctl.setPrefix(effectivePrefix);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [prefix]);

    return null;
};

export default AttributionControl;
