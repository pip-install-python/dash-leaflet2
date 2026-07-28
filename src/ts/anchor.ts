import React from 'react';

// Shared 9-point anchor model used by TextMarker and the editable ImageOverlay. The anchor is
// the point of the box that sits on the geographic position AND the pivot that rotation turns
// around. The selection "anchor dot" is rendered at this point so the user can see where the
// object is pinned.

export type Anchor =
    | 'center'
    | 'top-left' | 'top' | 'top-right'
    | 'left' | 'right'
    | 'bottom-left' | 'bottom' | 'bottom-right';

// Sidebar / control ordering (3×3 grid, reading order).
export const ANCHORS: Anchor[] = [
    'top-left', 'top', 'top-right',
    'left', 'center', 'right',
    'bottom-left', 'bottom', 'bottom-right',
];

// Horizontal / vertical fraction (0 | 0.5 | 1) of the anchor within the box.
export const anchorFx = (a: Anchor): number =>
    a === 'left' || a === 'top-left' || a === 'bottom-left' ? 0 :
    a === 'right' || a === 'top-right' || a === 'bottom-right' ? 1 : 0.5;

export const anchorFy = (a: Anchor): number =>
    a === 'top' || a === 'top-left' || a === 'top-right' ? 0 :
    a === 'bottom' || a === 'bottom-left' || a === 'bottom-right' ? 1 : 0.5;

// Anchor -> pixel offset (from the box's top-left) of the named anchor point, for a box of
// measured size w×h. The object is positioned so this point sits on the latlng, and rotation
// pivots around it (transform-origin).
export const anchorOffset = (anchor: Anchor, w: number, h: number): [number, number] =>
    [w * anchorFx(anchor), h * anchorFy(anchor)];

// CSS to position the selection "anchor dot" at the anchor point of a `position:relative`
// box, outset by `outset` px so it straddles the border. `center` is special-cased to the
// bottom-right corner (the default resize-grip spot) so a dot never sits over the content.
export const anchorDotCss = (anchor: Anchor, outset = 7): React.CSSProperties => {
    const a: Anchor = anchor === 'center' ? 'bottom-right' : anchor;
    const fx = anchorFx(a);
    const fy = anchorFy(a);
    const css: React.CSSProperties = {};
    if (fx === 0) { css.left = -outset; css.right = 'auto'; }
    else if (fx === 1) { css.right = -outset; css.left = 'auto'; }
    else { css.left = '50%'; css.right = 'auto'; }
    if (fy === 0) { css.top = -outset; css.bottom = 'auto'; }
    else if (fy === 1) { css.bottom = -outset; css.top = 'auto'; }
    else { css.top = '50%'; css.bottom = 'auto'; }
    const tx = fx === 0.5 ? '-50%' : '0';
    const ty = fy === 0.5 ? '-50%' : '0';
    css.transform = `translate(${tx}, ${ty})`;
    return css;
};
