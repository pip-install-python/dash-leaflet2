import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactDOM from 'react-dom';
import { Control, DomEvent, Layer, Map as LeafletMap } from 'leaflet';
import { useLeafletMap } from '../context';
import { RegisterContext, RegisterFn, EntryKind } from '../layersControl-shared';
import { DashComponentProps } from '../props';

// Leaflet 2's bundled `Layers` control class is NOT exported by the v2 ESM, so we extend
// the exported `Control` base and render the toggle UI through a React portal. Children
// <BaseLayer> / <Overlay> register themselves via context using a map-proxy trick that
// captures the layer without adding it to the real map; the control then manages adding /
// removing active layers as the user clicks or as Python changes props.
//
// State model:
//   • `entries`   — the catalogue (one item per registered child).
//   • `toggles`   — user/Python overrides on top of each entry's initialChecked.
//   • `active`    — DERIVED on every render from entries + toggles.
//   • Python props activeBase/activeOverlays sync INTO toggles, but only when they differ
//     from what we last emitted (otherwise our own setProps round-trips back as a prop and
//     wipes out the initialChecked-derived state — that race is what bit the first cut).

type Entry = {
    name: string;
    kind: EntryKind;
    layer: Layer;
    initialChecked: boolean;
};

type Toggles = {
    base?: string;
    overlays: Map<string, boolean>; // name -> isOn (only set when user/Python overrode)
};

type Props = {
    /** "topright" | "topleft" | "bottomright" | "bottomleft". */
    position?: string;
    /** If true, show only the toggle handle until the pointer enters. */
    collapsed?: boolean;
    /** Name of the active base layer. Two-way: reflects user choice + accepts callback. [MUTABLE] */
    activeBase?: string;
    /** Names of currently visible overlays. Two-way. [MUTABLE] */
    activeOverlays?: string[];
    /** BaseLayer + Overlay children. */
    children?: React.ReactNode;
} & DashComponentProps;

/**
 * LayersControl renders a Leaflet control that lets the user pick one of N base layers and
 * toggle M overlays. Place dl2.BaseLayer and dl2.Overlay as its children; LayersControl
 * itself must be a child of dl2.Map.
 */
const LayersControl = ({
    position = 'topright',
    collapsed = true,
    activeBase,
    activeOverlays,
    setProps,
    children,
}: Props) => {
    const map = useLeafletMap();
    const containerRef = useRef<HTMLDivElement | null>(null);
    if (!containerRef.current) containerRef.current = document.createElement('div');
    const controlRef = useRef<Control | null>(null);

    const [entries, setEntries] = useState<Entry[]>([]);
    const [toggles, setToggles] = useState<Toggles>({ overlays: new Map() });
    const [open, setOpen] = useState(!collapsed);

    // Track our own last emission so we can ignore round-tripped self-echo coming back as
    // activeBase / activeOverlays props.
    const lastEmitBaseRef = useRef<string | null | undefined>(undefined);
    const lastEmitOverlaysKeyRef = useRef<string | undefined>(undefined);

    // Create the Leaflet control once the map is available.
    useEffect(() => {
        if (!map) return;
        const C = Control as any;
        const ctl = new C({ position });
        ctl.onAdd = () => {
            const el = containerRef.current!;
            el.classList.add('leaflet-bar', 'dl2-layers-control');
            DomEvent.disableClickPropagation(el);
            DomEvent.disableScrollPropagation(el);
            return el;
        };
        ctl.addTo(map);
        controlRef.current = ctl;
        return () => {
            ctl.remove();
            controlRef.current = null;
        };
    }, [map, position]);

    const register: RegisterFn = useCallback((name, kind, layer, initialChecked) => {
        setEntries((prev) => {
            if (prev.some((e) => e.name === name && e.kind === kind)) return prev;
            return [...prev, { name, kind, layer, initialChecked }];
        });
        return () =>
            setEntries((prev) => prev.filter((e) => !(e.name === name && e.kind === kind)));
    }, []);
    /* (debug console.logs intentionally absent — this state model was iterated on; see
       lastEmit* refs above for the self-echo guard that closes the round-trip race.) */

    const bases = entries.filter((e) => e.kind === 'base');
    const overlayEntries = entries.filter((e) => e.kind === 'overlay');

    // --- Sync Python props INTO toggles (but never our own echo) -------------
    useEffect(() => {
        if (activeBase === undefined) return;
        if (activeBase === lastEmitBaseRef.current) return; // self-echo, skip
        setToggles((t) => ({ ...t, base: activeBase }));
    }, [activeBase]);

    useEffect(() => {
        if (!activeOverlays) return;
        const key = [...activeOverlays].sort().join(',');
        if (key === lastEmitOverlaysKeyRef.current) return; // self-echo, skip
        setToggles((t) => {
            const o = new Map<string, boolean>();
            overlayEntries.forEach((e) => o.set(e.name, activeOverlays.includes(e.name)));
            return { ...t, overlays: o };
        });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeOverlays]);

    // --- Derive `active` from entries + toggles ------------------------------
    const active = useMemo(() => {
        // Base: user-toggle wins; else first entry with initialChecked; else first entry.
        let baseName: string | null = null;
        if (toggles.base && bases.some((e) => e.name === toggles.base)) baseName = toggles.base;
        else {
            const checked = bases.find((e) => e.initialChecked);
            baseName = checked ? checked.name : bases.length ? bases[0].name : null;
        }
        // Overlay: per-entry, user override (if any) wins over initialChecked.
        const overlays = new Set<string>();
        overlayEntries.forEach((e) => {
            const userVal = toggles.overlays.get(e.name);
            const on = userVal === undefined ? e.initialChecked : userVal;
            if (on) overlays.add(e.name);
        });
        return { base: baseName, overlays };
    }, [entries, toggles, bases, overlayEntries]);

    // Sync the map's layers to match `active`. The only place we touch the real map.
    useEffect(() => {
        if (!map) return;
        entries.forEach((e) => {
            const shouldBeOn =
                e.kind === 'base' ? e.name === active.base : active.overlays.has(e.name);
            const isOn = !!(e.layer as any)._map;
            if (shouldBeOn && !isOn) (map as LeafletMap).addLayer(e.layer);
            else if (!shouldBeOn && isOn) (map as LeafletMap).removeLayer(e.layer);
        });
    }, [map, entries, active]);

    // --- Emit `active` to Dash whenever it changes ---------------------------
    // Guard: don't emit until at least one entry has registered (otherwise the initial
    // empty state would round-trip back and lock things out — see toggles-sync above).
    useEffect(() => {
        if (!setProps || entries.length === 0) return;
        const overlaysArr = Array.from(active.overlays).sort();
        const overlaysKey = overlaysArr.join(',');
        if (active.base === lastEmitBaseRef.current && overlaysKey === lastEmitOverlaysKeyRef.current) {
            return;
        }
        lastEmitBaseRef.current = active.base;
        lastEmitOverlaysKeyRef.current = overlaysKey;
        setProps({ activeBase: active.base, activeOverlays: overlaysArr });
    }, [active, setProps, entries.length]);

    const pickBase = (name: string) => setToggles((t) => ({ ...t, base: name }));
    const toggleOverlay = (name: string) =>
        setToggles((t) => {
            const o = new Map(t.overlays);
            const initial = overlayEntries.find((e) => e.name === name)?.initialChecked ?? false;
            const wasOn = o.has(name) ? o.get(name)! : initial;
            o.set(name, !wasOn);
            return { ...t, overlays: o };
        });

    return (
        <RegisterContext.Provider value={register}>
            {/* Hidden — children register via context; they render no DOM, and their
                useLeafletMap returns a proxy via BaseLayer/Overlay, not the real map. */}
            <div style={{ display: 'none' }}>{children}</div>
            {map && containerRef.current
                ? ReactDOM.createPortal(
                      <div
                          className={`dl2-layers-ui ${open ? 'open' : 'collapsed'}`}
                          onMouseEnter={() => collapsed && setOpen(true)}
                          onMouseLeave={() => collapsed && setOpen(false)}
                      >
                          <button className="dl2-layers-handle" aria-label="Layers">
                              ☰
                          </button>
                          <div className="dl2-layers-body">
                              {bases.length > 0 && (
                                  <section>
                                      {bases.map((e) => (
                                          <label key={e.name} className="dl2-layer-row">
                                              <input
                                                  type="radio"
                                                  name="dl2-base"
                                                  checked={active.base === e.name}
                                                  onChange={() => pickBase(e.name)}
                                              />
                                              <span>{e.name}</span>
                                          </label>
                                      ))}
                                  </section>
                              )}
                              {bases.length > 0 && overlayEntries.length > 0 && (
                                  <hr className="dl2-layers-sep" />
                              )}
                              {overlayEntries.length > 0 && (
                                  <section>
                                      {overlayEntries.map((e) => (
                                          <label key={e.name} className="dl2-layer-row">
                                              <input
                                                  type="checkbox"
                                                  checked={active.overlays.has(e.name)}
                                                  onChange={() => toggleOverlay(e.name)}
                                              />
                                              <span>{e.name}</span>
                                          </label>
                                      ))}
                                  </section>
                              )}
                          </div>
                      </div>,
                      containerRef.current
                  )
                : null}
        </RegisterContext.Provider>
    );
};

export default LayersControl;
