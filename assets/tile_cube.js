/**
 * Tile-cube renderOption — a tiny rotating CSS cube that previews
 * each tile provider in the MultiSelect dropdown on /tile-layers-pro.
 *
 * Ported from SailsBoard's assets/map_layers.js (renderTilesetCubeFace).
 * Same idea: each option's value is a provider slug; the Python layout
 * writes a `tilesets` map (slug -> {name, attribution, tileUrls})
 * into the renderOption options payload. We pluck the 6 tile URLs and
 * paint each cube face with one of them as a background image.
 *
 * Falls back to a Mantine-tinted gradient (see assets/tile_cube.css
 * .tlp-cube-face::before) when a face has no URL, so the chip never
 * reads empty.
 */
var dmcfuncs = window.dashMantineFunctions = window.dashMantineFunctions || {};
var dmc = window.dash_mantine_components;

dmcfuncs.renderTileCubeFace = function ({ option }, opts) {
    var registry = (opts && opts.tilesets) || {};
    var meta = registry[option.value] || {};
    var tileUrls = meta.tileUrls || [];

    var faceClasses = [
        'tlp-cube-face tlp-cube-front',
        'tlp-cube-face tlp-cube-back',
        'tlp-cube-face tlp-cube-right',
        'tlp-cube-face tlp-cube-left',
        'tlp-cube-face tlp-cube-top',
        'tlp-cube-face tlp-cube-bottom',
    ];
    var faces = faceClasses.map(function (cls, i) {
        var style = {};
        var hasTile = !!tileUrls[i];
        if (hasTile) {
            style.backgroundImage = 'url(' + tileUrls[i] + ')';
        }
        // The `has-tile` marker lets CSS strip the background-color tint and the
        // fallback gradient ONLY when a tile is actually painted — otherwise the
        // blue/green tint that's meant as a fallback bleeds through the image.
        return React.createElement('div', {
            key:       'face-' + i,
            className: cls + (hasTile ? ' has-tile' : ''),
            style:     style,
        });
    });

    var stage = React.createElement(
        'div',
        { className: 'tlp-cube-stage' },
        React.createElement('div', { className: 'tlp-cube' }, faces)
    );

    var labelParts = [
        React.createElement(
            dmc.Text,
            { size: 'sm', fw: 600, lh: 1.15, key: 'name' },
            meta.name || option.value
        ),
    ];
    var sublineBits = [];
    if (meta.group)   sublineBits.push(meta.group);
    if (meta.maxZoom) sublineBits.push('z ≤ ' + meta.maxZoom);
    if (meta.kind === 'overlay') sublineBits.push('overlay');
    if (sublineBits.length) {
        labelParts.push(
            React.createElement(
                dmc.Text,
                { size: 'xs', c: 'dimmed', lh: 1.15, ff: 'monospace', key: 'meta' },
                sublineBits.join(' · ')
            )
        );
    }

    return React.createElement(
        dmc.Group,
        { gap: 'sm', wrap: 'nowrap', align: 'center' },
        stage,
        React.createElement(
            dmc.Stack,
            { gap: 1, key: 'label-block' },
            labelParts
        )
    );
};
