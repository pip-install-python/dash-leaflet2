import { Icon, DivIcon } from 'leaflet';
import './icons.css';

// Registers the <iconify-icon> custom element. Icons themselves lazy-load from the
// Iconify API (api.iconify.design) on first use — same model as dash-iconify, so the
// bundle stays small and you can use any of 200k+ icons by name (e.g. "mdi:home").
import 'iconify-icon';

// Marker images, inlined as base64 by webpack (asset/inline). Bundling them sidesteps
// Leaflet 2's CSS-based icon-path detection, which produces a bare/relative filename
// (and a 404) when Leaflet is bundled instead of served from a CDN with a <link>.
import iconUrl from 'leaflet/dist/images/marker-icon.png';
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png';
import shadowUrl from 'leaflet/dist/images/marker-shadow.png';

// --- Fix the DEFAULT icon globally -----------------------------------------------
// Anything that doesn't pass an explicit icon uses Icon.Default — most importantly
// GeoJSON point features (they create their own markers). Point Icon.Default at the
// inlined base64 images, and remove its imagePath-prepending `_getIconUrl` override so
// the base implementation returns those URLs verbatim.
const DefaultProto = Icon.Default.prototype as any;
DefaultProto.options = {
    ...DefaultProto.options,
    iconUrl,
    iconRetinaUrl,
    shadowUrl,
};
delete DefaultProto._getIconUrl;

export const DEFAULT_ICON = new Icon.Default();

const DEFAULT_IMAGE_ICON = {
    iconUrl,
    iconRetinaUrl,
    shadowUrl,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    tooltipAnchor: [16, -28],
    shadowSize: [41, 41],
};

export interface MarkerIconProps {
    /** Full Leaflet Icon options for a custom image icon (iconUrl, iconSize, ...). */
    icon?: any;
    /** A single emoji to render as the marker, e.g. "🛥️". */
    emoji?: string;
    /** An Iconify icon name to render, e.g. "mdi:home" or "twemoji:sailboat". */
    iconify?: string;
    /** Pixel size for emoji / iconify markers. Default 32. */
    iconSize?: number;
    /** CSS color for iconify markers (monochrome icon sets only). */
    iconColor?: string;
    /** [x, y] anchor for emoji / iconify / divIcon markers. Default bottom-center. */
    iconAnchor?: [number, number];
    /** Full Leaflet DivIcon options escape hatch (html/className/iconSize/iconAnchor). */
    iconOptions?: any;
}

const emojiHtml = (emoji: string, size: number) =>
    `<div style="font-size:${size}px;line-height:1;text-align:center;` +
    `filter:drop-shadow(0 2px 3px rgba(0,0,0,.35));">${emoji}</div>`;

const iconifyHtml = (icon: string, size: number, color?: string) =>
    `<iconify-icon icon="${icon}" width="${size}" height="${size}" ` +
    `style="display:block${color ? `;color:${color}` : ''}"></iconify-icon>`;

/**
 * Resolve the right Leaflet icon for a Marker from its props. Precedence:
 * iconOptions (full DivIcon) > iconify > emoji > icon (image) > the default pin.
 */
export function buildMarkerIcon(p: MarkerIconProps): Icon | DivIcon {
    const size = p.iconSize || 32;
    const anchor: [number, number] = p.iconAnchor || [size / 2, size];
    // Place tooltips/popups above the icon so they don't overlap a bottom-anchored pin.
    const aboveAnchor: [number, number] = [0, -size];

    if (p.iconOptions) return new DivIcon(p.iconOptions);

    if (p.iconify) {
        return new DivIcon({
            className: 'dl2-div-icon',
            html: iconifyHtml(p.iconify, size, p.iconColor),
            iconSize: [size, size],
            iconAnchor: anchor,
            tooltipAnchor: aboveAnchor,
            popupAnchor: aboveAnchor,
        });
    }

    if (p.emoji) {
        return new DivIcon({
            className: 'dl2-div-icon',
            html: emojiHtml(p.emoji, size),
            iconSize: [size, size],
            iconAnchor: anchor,
            tooltipAnchor: aboveAnchor,
            popupAnchor: aboveAnchor,
        });
    }

    if (p.icon) return new Icon({ ...DEFAULT_IMAGE_ICON, ...p.icon });

    return DEFAULT_ICON;
}
