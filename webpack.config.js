const path = require('path');
const packagejson = require('./package.json');
const WebpackDashDynamicImport = require('@plotly/webpack-dash-dynamic-import');

const dashLibraryName = packagejson.name.replace(/-/g, '_'); // dash_leaflet2

module.exports = function (env, argv) {
    const mode = (argv && argv.mode) || 'production';

    return {
        mode,
        entry: [path.join(__dirname, 'src/ts/index.ts')],
        target: 'web',
        output: {
            path: path.join(__dirname, dashLibraryName),
            chunkFilename: '[name].js',
            filename: `${dashLibraryName}.js`,
            library: dashLibraryName,
            libraryTarget: 'umd',
        },
        // React/ReactDOM are provided by Dash's renderer at runtime — don't bundle
        // them. Leaflet 2 IS bundled (this is where v2's ESM-only build resolves
        // cleanly via webpack and tree-shaking pays off).
        externals: {
            react: {
                commonjs: 'react', commonjs2: 'react', amd: 'react', umd: 'react', root: 'React',
            },
            'react-dom': {
                commonjs: 'react-dom', commonjs2: 'react-dom', amd: 'react-dom', umd: 'react-dom', root: 'ReactDOM',
            },
        },
        resolve: {
            extensions: ['.ts', '.tsx', '.js', '.jsx', '.json'],
        },
        module: {
            rules: [
                {
                    test: /\.tsx?$/,
                    use: 'ts-loader',
                    exclude: /node_modules/,
                },
                {
                    test: /\.css$/,
                    use: [
                        {
                            loader: 'style-loader',
                            options: {
                                // Insert Leaflet's CSS at the top of <head> so app
                                // styles can override it.
                                insert: function insertAtTop(element) {
                                    var parent = document.querySelector('head');
                                    var last = window._lastElementInsertedByStyleLoader;
                                    if (!last) {
                                        parent.insertBefore(element, parent.firstChild);
                                    } else if (last.nextSibling) {
                                        parent.insertBefore(element, last.nextSibling);
                                    } else {
                                        parent.appendChild(element);
                                    }
                                    window._lastElementInsertedByStyleLoader = element;
                                },
                            },
                        },
                        { loader: 'css-loader' },
                    ],
                },
                {
                    // Inline Leaflet's marker images as base64 so default markers
                    // work without serving image files.
                    test: /\.(png|jpe?g|gif|svg)$/i,
                    type: 'asset/inline',
                },
            ],
        },
        optimization: {
            splitChunks: {
                name: '[name].js',
                cacheGroups: {
                    async: {
                        chunks: 'async',
                        minSize: 0,
                        name(module, chunks, cacheGroupKey) {
                            return `${cacheGroupKey}-${chunks[0].name}`;
                        },
                    },
                    shared: {
                        chunks: 'all',
                        minSize: 0,
                        minChunks: 2,
                        name: 'dash_leaflet2-shared',
                    },
                },
            },
        },
        plugins: [new WebpackDashDynamicImport()],
    };
};
