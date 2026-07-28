import { useEffect, useRef } from 'react';
import { Control, DomEvent } from 'leaflet';
import { useLeafletMap } from '../context';
import { DashComponentProps } from '../props';

type Props = {
    /** "topleft" | "topright" | "bottomleft" | "bottomright". Default "topleft". [MUTABLE] */
    position?: 'topleft' | 'topright' | 'bottomleft' | 'bottomright';
    /** Tooltip text when entering fullscreen. Default "Full Screen". */
    title?: string;
    /** Tooltip text when leaving fullscreen. Default "Exit Full Screen". */
    titleCancel?: string;
    /** Number of times the button has been clicked. [READONLY] */
    n_clicks?: number;
    /** Whether the map is currently in fullscreen mode. [READONLY] */
    fullscreen?: boolean;
} & DashComponentProps;

/**
 * FullScreenControl adds a single button to the map that toggles the map
 * container in/out of the browser's native fullscreen mode. Leaflet 2 doesn't
 * ship a fullscreen control — this maps the browser's `requestFullscreen()`
 * API onto a small `Control` subclass, matching the dash-leaflet (and
 * `Leaflet.fullscreen` plugin) API shape.
 */
const FullScreenControl = ({
    position = 'topleft',
    title = 'Full Screen',
    titleCancel = 'Exit Full Screen',
    setProps,
}: Props) => {
    const map = useLeafletMap();
    const ctlRef = useRef<any>(null);
    const clicksRef = useRef<number>(0);

    useEffect(() => {
        if (!map) return;
        const C = Control as any;
        const ctl = new C({ position });

        let buttonEl: HTMLAnchorElement | null = null;

        const isFullscreen = () => !!document.fullscreenElement;

        const updateTitle = () => {
            if (!buttonEl) return;
            buttonEl.title = isFullscreen() ? titleCancel : title;
            buttonEl.setAttribute('aria-label', buttonEl.title);
            buttonEl.classList.toggle('dl2-fs-active', isFullscreen());
        };

        const onChange = () => {
            updateTitle();
            setProps && setProps({ fullscreen: isFullscreen() });
        };

        ctl.onAdd = (m: any) => {
            const wrap = document.createElement('div');
            wrap.className = 'leaflet-bar dl2-fullscreen-control';
            const a = document.createElement('a');
            a.href = '#';
            a.className = 'dl2-fullscreen-button';
            a.innerHTML =
                '<svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" '
                + 'stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" '
                + 'aria-hidden="true">'
                + '<path d="M4 9V4h5"/><path d="M20 9V4h-5"/>'
                + '<path d="M4 15v5h5"/><path d="M20 15v5h-5"/>'
                + '</svg>';
            buttonEl = a;
            wrap.appendChild(a);
            DomEvent.disableClickPropagation(wrap);
            DomEvent.on(a, 'click', (e: any) => {
                DomEvent.stop(e);
                clicksRef.current += 1;
                setProps && setProps({ n_clicks: clicksRef.current });
                const container: HTMLElement | undefined = m._container;
                if (!container) return;
                if (!document.fullscreenElement) {
                    container.requestFullscreen?.().catch(() => {});
                } else {
                    document.exitFullscreen?.().catch(() => {});
                }
            });
            document.addEventListener('fullscreenchange', onChange);
            updateTitle();
            return wrap;
        };
        ctl.onRemove = () => {
            document.removeEventListener('fullscreenchange', onChange);
        };

        ctl.addTo(map);
        ctlRef.current = ctl;
        return () => {
            try { ctl.remove(); } catch (e) {}
            ctlRef.current = null;
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [map]);

    useEffect(() => {
        if (ctlRef.current && position) ctlRef.current.setPosition(position);
    }, [position]);

    return null;
};

export default FullScreenControl;
