import React, { useEffect, useRef } from 'react';
import ReactDOM from 'react-dom';
import { Control, DomEvent } from 'leaflet';
import { useLeafletMap } from '../context';
import { DashComponentProps } from '../props';

type Props = {
    /** "topleft" | "topright" | "bottomleft" | "bottomright". */
    position?: string;
    /** Iconify icon name, e.g. "mdi:emoticon-happy-outline" or "mdi:crosshairs-gps". */
    icon?: string;
    /** Icon size in pixels. */
    iconSize?: number;
    /** Tooltip text shown on hover. */
    title?: string;
    /** Number of times the button has been clicked. [READONLY] */
    n_clicks?: number;
    /** Number of times the button has been double-clicked. [READONLY] */
    n_dblclicks?: number;
} & DashComponentProps;

/**
 * EasyButton adds a single-icon control to the map. Use it for quick map-level actions
 * (open a panel, locate, zoom-home, etc.); the click is reported back to Dash as n_clicks.
 * Icons come from Iconify (any of the 200k+ icons), e.g. "mdi:emoticon-happy-outline".
 * Place it as a child of dl2.Map.
 */
const EasyButton = ({
    position = 'topleft',
    icon = 'mdi:circle-medium',
    iconSize = 18,
    title,
    n_clicks = 0,
    n_dblclicks = 0,
    setProps,
}: Props) => {
    const map = useLeafletMap();
    const containerRef = useRef<HTMLDivElement | null>(null);
    if (!containerRef.current) containerRef.current = document.createElement('div');
    const clicksRef = useRef<number>(n_clicks || 0);
    const dblsRef = useRef<number>(n_dblclicks || 0);

    useEffect(() => {
        if (!map) return;
        const C = Control as any;
        const ctl = new C({ position });
        ctl.onAdd = () => {
            const el = containerRef.current!;
            el.classList.add('leaflet-bar', 'dl2-easy-button-container');
            DomEvent.disableClickPropagation(el);
            DomEvent.disableScrollPropagation(el);
            return el;
        };
        ctl.addTo(map);
        return () => ctl.remove();
    }, [map, position]);

    const onClick = () => {
        clicksRef.current += 1;
        setProps && setProps({ n_clicks: clicksRef.current });
    };
    const onDblClick = (e: React.MouseEvent) => {
        e.stopPropagation();
        dblsRef.current += 1;
        setProps && setProps({ n_dblclicks: dblsRef.current });
    };

    return map && containerRef.current
        ? ReactDOM.createPortal(
              <button
                  className="dl2-easy-button"
                  title={title}
                  onClick={onClick}
                  onDoubleClick={onDblClick}
              >
                  <iconify-icon icon={icon} width={iconSize}></iconify-icon>
              </button>,
              containerRef.current
          )
        : null;
};

export default EasyButton;
