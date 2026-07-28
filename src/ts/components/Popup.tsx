import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { useLeafletLayer } from '../context';
import { DashComponentProps } from '../props';

type Props = {
    /** Popup content — any Dash/HTML children, rendered live via a React portal. */
    children?: React.ReactNode;
    /** Max width in pixels. */
    maxWidth?: number;
    /** Min width in pixels. */
    minWidth?: number;
    /** Show the close (×) button. */
    closeButton?: boolean;
    /**
     * If true, clicking the map closes the popup. Leaflet defaults to true; set False
     * for form popups that should stay open while the user is interacting.
     */
    closeOnClick?: boolean;
    /**
     * If true, opening a popup closes other popups. Leaflet defaults to true; set False
     * to allow multiple popups open simultaneously.
     */
    autoClose?: boolean;
    /**
     * Controlled open state — when set, the popup follows this prop (True → open,
     * False → closed) instead of waiting for a click on the parent layer. [MUTABLE]
     */
    opened?: boolean;
} & DashComponentProps;

/**
 * Popup shows content in a balloon bound to its parent layer (Marker, Polygon, ...).
 * Children are rendered through a React portal, so any Dash component works as popup
 * content. Wraps Leaflet 2's Popup.
 */
const Popup = ({
    children,
    maxWidth = 300,
    minWidth = 50,
    closeButton = true,
    closeOnClick,
    autoClose,
    opened,
}: Props) => {
    const layer = useLeafletLayer();
    // One detached div per Popup, created once; the portal renders children into it and
    // Leaflet displays it as the popup body.
    const [container] = useState(() => document.createElement('div'));

    // Bind the popup once per layer / option change. NOTE: `opened` is intentionally NOT
    // in this effect's deps — re-binding the popup just to toggle open/close would tear
    // down + re-create it on every state flip.
    useEffect(() => {
        if (!layer) return;
        const opts: any = { maxWidth, minWidth, closeButton };
        if (closeOnClick !== undefined) opts.closeOnClick = closeOnClick;
        if (autoClose !== undefined) opts.autoClose = autoClose;
        layer.bindPopup(container, opts);
        return () => {
            try {
                layer.unbindPopup();
            } catch (e) {
                /* layer already gone */
            }
        };
    }, [layer, maxWidth, minWidth, closeButton, closeOnClick, autoClose, container]);

    // Controlled open/close — independent of binding so we don't re-bind on every flip.
    useEffect(() => {
        if (!layer || opened === undefined) return;
        try {
            if (opened) (layer as any).openPopup?.();
            else (layer as any).closePopup?.();
        } catch (e) {
            /* layer not on map yet */
        }
    }, [layer, opened]);

    return ReactDOM.createPortal(children, container);
};

export default Popup;
