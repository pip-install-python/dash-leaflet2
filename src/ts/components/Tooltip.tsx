import React, { useEffect, useState } from 'react';
import ReactDOM from 'react-dom';
import { useLeafletLayer } from '../context';
import { DashComponentProps } from '../props';

type Props = {
    /** Tooltip content — any Dash/HTML children, rendered live via a React portal. */
    children?: React.ReactNode;
    /** If true, the tooltip stays open instead of showing only on hover. */
    permanent?: boolean;
    /** Placement: "right" | "left" | "top" | "bottom" | "center" | "auto". */
    direction?: string;
    /** Tooltip opacity, 0..1. */
    opacity?: number;
} & DashComponentProps;

/**
 * Tooltip shows a small label on hover (or permanently), bound to its parent layer
 * (Marker, Polygon, ...). Children render through a React portal, so any Dash component
 * works as content. Wraps Leaflet 2's Tooltip.
 */
const Tooltip = ({ children, permanent = false, direction = 'auto', opacity = 0.9 }: Props) => {
    const layer = useLeafletLayer();
    const [container] = useState(() => document.createElement('div'));

    useEffect(() => {
        if (!layer) return;
        layer.bindTooltip(container, { permanent, direction, opacity });
        return () => {
            try {
                layer.unbindTooltip();
            } catch (e) {
                /* layer already gone */
            }
        };
    }, [layer, permanent, direction, opacity, container]);

    return ReactDOM.createPortal(children, container);
};

export default Tooltip;
