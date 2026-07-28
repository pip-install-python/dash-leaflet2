/* ============================================================================
 * dash-leaflet2 — Leaflet 2.0.0-alpha.1 mount engine for Dash 4
 * ============================================================================
 *
 * Why this file exists
 * --------------------
 * Leaflet 2 has no Dash component yet (react-leaflet is frozen on Leaflet 1.9),
 * so we drive the v2 core imperatively. This single file is the whole "runtime":
 *
 *   1. DEMOS  — a registry mapping a string id -> a builder function that takes
 *               (el, L) and returns a mounted `leaflet.Map`. Each example page
 *               just renders <div class="leaflet2-map" data-demo="<id>">; the
 *               builder for that id paints into it.
 *
 *   2. observer — a MutationObserver watching <body>. When Dash's page_container
 *               swaps in a new page, any unmounted .leaflet2-map divs get their
 *               builder run; when a page is swapped out, its map is .remove()'d
 *               so Leaflet event handlers / ResizeObservers don't leak.
 *
 * This is the "scale" story in miniature: adding a new example = add one DEMOS
 * entry + one thin Python page. No build step, no per-page boilerplate JS.
 *
 * v2 gotchas baked in here (learned the hard way):
 *   - The global is `window.leaflet`, NOT `window.L` (the L global was dropped).
 *   - Mouse events are gone; v2 fires POINTER events (`pointermove`,
 *     `pointerdown`, ...). The Leaflet event's `.originalEvent` is a native
 *     PointerEvent, so `.pointerType` / `.pressure` are first-class.
 *   - Default marker icons resolve automatically from the injected leaflet.css.
 * ========================================================================== */

(function () {
  "use strict";

  const DL2 = (window.DL2 = window.DL2 || { maps: {}, util: {} });

  // ---- shared helpers --------------------------------------------------------

  // Theme-aware basemaps. CARTO Positron (light) + Dark Matter, both backed by OSM data,
  // are the standard pair used for light/dark map UIs and don't require an API key. We
  // swap tile URLs in place on every map when the app's DMC color scheme changes (see the
  // MutationObserver near the bottom of this file).
  const TILES = {
    light: {
      url: "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
      attribution:
        '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> ' +
        '&copy; <a href="https://carto.com/attributions">CARTO</a>',
    },
    dark: {
      url: "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
      attribution:
        '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> ' +
        '&copy; <a href="https://carto.com/attributions">CARTO</a>',
    },
  };
  function currentScheme() {
    return document.documentElement.getAttribute("data-mantine-color-scheme") === "dark"
      ? "dark"
      : "light";
  }

  // Tile layers created here register themselves so `DL2.setMapTheme(scheme)` can swap
  // every basemap when the app theme flips.
  DL2.tileLayers = DL2.tileLayers || [];
  function osm(L) {
    const t = TILES[currentScheme()];
    const layer = new L.TileLayer(t.url, { maxZoom: 19, attribution: t.attribution });
    DL2.tileLayers.push(layer);
    return layer;
  }
  DL2.setMapTheme = function (scheme) {
    const t = TILES[scheme] || TILES.light;
    // Drop layers whose map has been removed (avoid leaking across nav).
    DL2.tileLayers = DL2.tileLayers.filter((l) => l._map);
    DL2.tileLayers.forEach((l) => {
      try { l.setUrl(t.url); } catch (e) {}
    });
  };

  // Push a value into a dcc.Store so a Python @callback can read it. This is the
  // JS -> Python bridge for the whole app (Dash 4's clientside set_props API).
  //
  // Hardened against a real race: on client-side page navigation the map's DOM
  // (and our MutationObserver mount) can run BEFORE Dash has indexed the new
  // page's component paths. Calling set_props in that window throws deep in
  // Dash's getComponentLayout ("Cannot read properties of undefined (reading
  // 'length')") because the target id has no registered path yet. An uncaught
  // throw here would abort the Leaflet event handler, leaving readouts blank
  // (the events-python symptom). So we swallow it and retry once on the next
  // tick, by which time the paths registry has settled.
  function toStore(id, data) {
    var dc = window.dash_clientside;
    if (!dc || !dc.set_props) return;
    try {
      dc.set_props(id, { data: data });
    } catch (e) {
      setTimeout(function () {
        try {
          dc.set_props(id, { data: data });
        } catch (e2) {
          /* target genuinely absent from this page — ignore */
        }
      }, 60);
    }
  }
  DL2.util.osm = osm;
  DL2.util.toStore = toStore;

  // Called by the Iconify catalogue grid buttons (emoji_iconify page). Updates the marker
  // and pushes the choice to the readout + DashIconify preview via set_props.
  DL2.iconifyPick = function (name) {
    if (DL2.emojiIconify) DL2.emojiIconify.setIconify(name);
    var dc = window.dash_clientside;
    if (dc && dc.set_props) {
      try { dc.set_props("ei-readout", { children: "iconify " + name }); } catch (e) {}
      try { dc.set_props("ei-preview", { icon: name }); } catch (e) {}
    }
  };

  // Throttle: pointermove/mousemove fire at screen refresh rate; we don't want
  // to flood the Dash callback graph, so coarse-grain the JS->Python pushes.
  function throttle(fn, ms) {
    let last = 0;
    return function () {
      const now = Date.now();
      if (now - last >= ms) {
        last = now;
        fn.apply(this, arguments);
      }
    };
  }

  // A round of N random points scattered in a lat/lng box around a center.
  function scatter(center, n, spread) {
    const pts = [];
    for (let i = 0; i < n; i++) {
      pts.push([
        center[0] + (Math.random() - 0.5) * spread,
        center[1] + (Math.random() - 0.5) * spread * 1.6,
      ]);
    }
    return pts;
  }

  // ===========================================================================
  // LOCATIONS
  //
  // Every demo used to open on the same patch of Rockport, TX, which made the
  // documentation read as one map shown a dozen times. Each demo now opens
  // somewhere different. This table is the JS half of the registry — the
  // Python half is dl2_locations.py, and the two must agree for pages whose
  // prose quotes coordinates (vector-layers, resize-observer, home).
  //
  // `at()` takes KILOMETRES, not degrees, and scales longitude by cos(lat).
  // A degree of longitude is ~98 km in Houston and ~73 km in Vancouver, so
  // reusing degree offsets across latitudes would visibly squash every shape.
  // ===========================================================================
  const CITY = {
    vancouver: [49.2860, -123.1200],
    portland: [45.5202, -122.6742],
    newYork: [40.7484, -73.9857],
    chicago: [41.8827, -87.6233],
    dallas: [32.7791, -96.8005],
    houston: [29.7589, -95.3677],
    seattle: [47.6062, -122.3321],
  };

  /** A point `nKm` north and `eKm` east of `city`, as [lat, lon]. */
  function at(city, nKm, eKm) {
    const [lat, lon] = city;
    return [
      lat + nKm / 111.32,
      lon + eKm / (111.32 * Math.cos((lat * Math.PI) / 180)),
    ];
  }

  // ===========================================================================
  // DEMO REGISTRY
  // ===========================================================================
  const DEMOS = {
    // -- 1. Basics: prove a v2 map + tiles + marker + popup render ------------
    home(el, L) {
      const map = new L.Map(el).setView(CITY.vancouver, 12);
      osm(L).addTo(map);
      new L.Marker(CITY.vancouver)
        .addTo(map)
        .bindPopup("<b>Leaflet 2.0.0-alpha.1</b><br>running inside Dash 4 🛰️")
        .openPopup();
      return map;
    },

    // -- 2. Pointer Events: v2's headline change ------------------------------
    // v1's separate mouse/touch paths are unified into PointerEvents. The
    // Leaflet event's originalEvent is a native PointerEvent, so pen pressure,
    // tilt and pointerType come for free. Live HUD is written straight to the
    // DOM (snappy); a throttled copy is pushed to Python to prove the round-trip.
    "pointer-events"(el, L) {
      const map = new L.Map(el).setView(CITY.portland, 12);
      osm(L).addTo(map);

      const hud = document.getElementById("pe-live");
      const paint = (e) => {
        const oe = e.originalEvent || {};
        if (hud) {
          hud.textContent =
            `type=${oe.pointerType || "?"}  ` +
            `pressure=${(oe.pressure ?? 0).toFixed(2)}  ` +
            `tilt=[${oe.tiltX || 0},${oe.tiltY || 0}]  ` +
            `lat=${e.latlng.lat.toFixed(5)}  lng=${e.latlng.lng.toFixed(5)}`;
        }
      };
      map.on("pointermove", paint);

      // Round-trip a coarse sample + every explicit pointerdown to Python.
      const push = throttle((e) => {
        const oe = e.originalEvent || {};
        toStore("pe-store", {
          event: e.type,
          pointerType: oe.pointerType || "mouse",
          pressure: +(oe.pressure ?? 0).toFixed(3),
          lat: +e.latlng.lat.toFixed(5),
          lng: +e.latlng.lng.toFixed(5),
        });
      }, 200);
      map.on("pointermove", push);
      map.on("pointerdown", (e) => {
        const oe = e.originalEvent || {};
        toStore("pe-store", {
          event: "pointerdown",
          pointerType: oe.pointerType || "mouse",
          pressure: +(oe.pressure ?? 0).toFixed(3),
          lat: +e.latlng.lat.toFixed(5),
          lng: +e.latlng.lng.toFixed(5),
        });
      });
      return map;
    },

    // -- 3. Vector layers: Polygon / Polyline / Circle / CircleMarker ---------
    // Clicking a shape round-trips its name to Python.
    "vector-layers"(el, L) {
      const c = CITY.newYork;
      const map = new L.Map(el).setView(c, 12);
      osm(L).addTo(map);

      const tag = (layer, name) =>
        layer.on("click", () => toStore("vec-store", { shape: name, t: Date.now() }));

      tag(
        new L.Polygon(
          [
            at(c, 3.3, -4.9),
            at(c, 4.5, 2.9),
            at(c, -1.1, 4.9),
            at(c, -2.2, -2.9),
          ],
          { color: "#2f9e44", weight: 2, fillOpacity: 0.25 }
        )
          .bindTooltip("Polygon (harbor zone)")
          .addTo(map),
        "polygon"
      );

      tag(
        new L.Polyline(
          [
            at(c, 1.1, -3.9),
            at(c, 0.6, -0.4),
            at(c, 2.2, 2.9),
          ],
          { color: "#1971c2", weight: 4 }
        )
          .bindTooltip("Polyline (route)")
          .addTo(map),
        "polyline"
      );

      tag(
        new L.Circle(at(c, -2.2, 1.0), { radius: 1500, color: "#e8590c", fillOpacity: 0.2 })
          .bindTooltip("Circle (1.5km geo radius)")
          .addTo(map),
        "circle"
      );

      tag(
        new L.CircleMarker(at(c, -0.6, -2.0), { radius: 10, color: "#9c36b5", fillOpacity: 0.6 })
          .bindTooltip("CircleMarker (fixed px)")
          .addTo(map),
        "circleMarker"
      );
      return map;
    },

    // -- 4. Canvas renderer: dense point clouds -------------------------------
    // `preferCanvas: true` routes all CircleMarkers through the Canvas renderer
    // (one <canvas>, not N SVG nodes). Drop ~8000 points and time it. This is
    // the substrate for live vessel positions / sensor swarms.
    "canvas-overlay"(el, L) {
      const center = CITY.chicago;
      // Hold an explicit Canvas renderer so we have a handle to repaint it.
      const renderer = new L.Canvas();
      const map = new L.Map(el, { renderer }).setView(center, 11);
      osm(L).addTo(map);

      const N = 8000;
      const hud = document.getElementById("canvas-hud");
      const group = new L.FeatureGroup().addTo(map);
      const t0 = performance.now();
      const pts = scatter(center, N, 0.5);
      for (let i = 0; i < N; i++) {
        new L.CircleMarker(pts[i], {
          renderer: renderer,
          radius: 3,
          stroke: false,
          fillColor: i % 7 === 0 ? "#e03131" : "#1971c2",
          fillOpacity: 0.6,
        }).addTo(group);
      }
      const ms = (performance.now() - t0).toFixed(0);
      if (hud) {
        hud.textContent = `Rendered ${N.toLocaleString()} CircleMarkers via Canvas in ${ms} ms — pan/zoom stays smooth.`;
      }

      // WORKAROUND (Leaflet 2.0.0-alpha.1): BlanketOverlay._onMoveEnd() draws
      // (_onSettled) and THEN calls _resizeContainer(), which sets canvas.width
      // and wipes the bitmap — so the canvas goes blank after every pan/zoom.
      // Re-issue the renderer update on the next frame to repaint onto the
      // freshly-sized canvas. (A real dash-leaflet2 build would patch this once
      // in the bundled renderer instead of per-map.)
      map.on("moveend zoomend", () =>
        requestAnimationFrame(() => map._loaded && renderer._update())
      );
      return map;
    },

    // -- 5. Subclassing: ES6 `extends` for a Control + a BlanketOverlay -------
    // v2 uses standard ES6 classes, so extending Leaflet types is idiomatic JS
    // (no L.Class.extend). We build (a) a custom Control showing live center,
    // and (b) a custom canvas layer on BlanketOverlay — the generalized renderer
    // base — that paints geo-anchored "sensor glow" blobs which re-project on
    // every pan/zoom settle.
    subclassing(el, L) {
      const center = CITY.dallas;
      const map = new L.Map(el).setView(center, 12);
      osm(L).addTo(map);

      // (a) Custom Control via ES6 class extension.
      class CenterControl extends L.Control {
        onAdd(m) {
          const div = L.DomUtil.create("div", "dl2-ctl");
          const render = () => {
            const ll = m.getCenter();
            div.innerHTML = `center<br><b>${ll.lat.toFixed(4)}, ${ll.lng.toFixed(4)}</b><br>zoom ${m.getZoom()}`;
          };
          render();
          m.on("move zoom", render);
          return div;
        }
      }
      new CenterControl({ position: "topright" }).addTo(map);

      // (b) Custom canvas layer on BlanketOverlay (the renderer superclass).
      // Subclass contract: _initContainer / _destroyContainer / _resizeContainer
      // / _onSettled. _onSettled is where rendering happens after the map settles.
      class GlowLayer extends L.BlanketOverlay {
        initialize(points, options) {
          super.initialize(options);
          this._points = points; // [{lat,lng,intensity}]
        }
        _initContainer() {
          this._container = L.DomUtil.create("canvas", "leaflet-zoom-animated");
          this._ctx = this._container.getContext("2d");
        }
        _destroyContainer() {
          this._container && this._container.remove();
          delete this._container;
        }
        _resizeContainer() {
          const size = super._resizeContainer();
          this._container.width = size.x;
          this._container.height = size.y;
          return size;
        }
        _onMoveEnd(ev) {
          // Same alpha.1 quirk as the Canvas renderer: the base _onMoveEnd
          // resizes (clearing our canvas) AFTER _onSettled draws. Draw once
          // more after the resize so glows survive pan/zoom.
          super._onMoveEnd(ev);
          this._onSettled(ev);
        }
        _onSettled() {
          const ctx = this._ctx;
          if (!ctx) return;
          ctx.clearRect(0, 0, this._container.width, this._container.height);
          // _bounds.min is the layer-point of the canvas top-left; convert each
          // geo point to a layer point and offset into canvas space.
          const origin = this._bounds.min;
          for (const p of this._points) {
            const lp = this._map.latLngToLayerPoint([p.lat, p.lng]);
            const x = lp.x - origin.x;
            const y = lp.y - origin.y;
            const r = 26 * p.intensity;
            const g = ctx.createRadialGradient(x, y, 0, x, y, r);
            g.addColorStop(0, "rgba(232,89,12,0.85)");
            g.addColorStop(1, "rgba(232,89,12,0)");
            ctx.fillStyle = g;
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
      const sensors = scatter(center, 40, 0.18).map((c, i) => ({
        lat: c[0],
        lng: c[1],
        intensity: 0.4 + (i % 5) * 0.15,
      }));
      new GlowLayer(sensors).addTo(map);
      return map;
    },

    // -- 6. ResizeObserver auto-sizing ----------------------------------------
    // v2 observes its container with a ResizeObserver (trackResize, default on),
    // so it re-renders when the container changes size — no more gray tiles and
    // no manual invalidateSize() inside collapsible/tab layouts. The "Toggle
    // side panel" button just shrinks the wrapper via CSS; the map fixes itself.
    "resize-observer"(el, L) {
      const map = new L.Map(el).setView(CITY.houston, 12);
      osm(L).addTo(map);
      new L.Marker(CITY.houston).addTo(map);
      return map;
    },

    // -- 8. Emoji & Iconify markers (DivIcon) ---------------------------------
    // Mirrors dash-leaflet's emoji_marker.py, and uses the exact DivIcon technique
    // baked into the compiled dl2.Marker (emoji / iconify modes). The DivIcon HTML
    // is swapped at runtime by clientside callbacks driven by a DashEmojiMart picker
    // and an Iconify select (see pages/emoji_iconify.py).
    "emoji-iconify"(el, L) {
      const map = new L.Map(el).setView([56, 10], 6);
      osm(L).addTo(map);

      const emojiHtml = (emoji, size) =>
        `<div style="font-size:${size}px;line-height:1;text-align:center;` +
        `filter:drop-shadow(0 2px 3px rgba(0,0,0,.35));">${emoji}</div>`;
      const iconifyHtml = (name, size, color) =>
        `<iconify-icon icon="${name}" width="${size}" height="${size}" ` +
        `style="display:block${color ? `;color:${color}` : ""}"></iconify-icon>`;
      // The marker's geo position is anchored at the icon's bottom-center (pin-style), so
      // tooltips/popups must open above the icon — set tooltipAnchor/popupAnchor to
      // [0, -size] (relative to iconAnchor) and bind with direction:'top' for the arrow.
      const makeIcon = (html, size) =>
        new L.DivIcon({
          className: "dl2-emoji-icon",
          html: html,
          iconSize: [size, size],
          iconAnchor: [size / 2, size],
          tooltipAnchor: [0, -size],
          popupAnchor: [0, -size],
        });

      const marker = new L.Marker([56, 10], {
        icon: makeIcon(emojiHtml("📍", 40), 40),
        draggable: true,
      }).addTo(map);
      marker.bindTooltip("Pick an emoji or an Iconify icon ↓", {
        direction: "top",
        offset: [0, -2],
      });

      // Exposed so the page's clientside callbacks (DashEmojiMart value, Iconify select,
      // size slider) can update the marker. Tracks current size + last selection so the
      // size slider can re-apply to whichever icon (emoji or iconify) is active.
      DL2.emojiIconify = {
        size: 40,
        last: { type: "emoji", val: "📍", color: undefined },
        setEmoji(emoji) {
          this.last = { type: "emoji", val: emoji };
          marker.setIcon(makeIcon(emojiHtml(emoji, this.size), this.size));
        },
        setIconify(name, color) {
          this.last = { type: "iconify", val: name, color: color };
          marker.setIcon(makeIcon(iconifyHtml(name, this.size, color), this.size));
        },
        setSize(s) {
          this.size = s;
          if (this.last.type === "iconify") this.setIconify(this.last.val, this.last.color);
          else this.setEmoji(this.last.val);
        },
      };

      return map;
    },

    // -- 9. Events -> Python: full round-trip ---------------------------------
    "events-python"(el, L) {
      const map = new L.Map(el).setView(CITY.seattle, 12);
      osm(L).addTo(map);

      const view = () => {
        const c = map.getCenter();
        toStore("ev-store", {
          lat: +c.lat.toFixed(5),
          lng: +c.lng.toFixed(5),
          zoom: map.getZoom(),
          bounds: (() => {
            const b = map.getBounds();
            return {
              n: +b.getNorth().toFixed(4),
              s: +b.getSouth().toFixed(4),
              e: +b.getEast().toFixed(4),
              w: +b.getWest().toFixed(4),
            };
          })(),
        });
      };
      map.on("moveend zoomend", view);
      map.on("click", (e) =>
        toStore("ev-click-store", {
          lat: +e.latlng.lat.toFixed(5),
          lng: +e.latlng.lng.toFixed(5),
        })
      );
      // Emit initial state after a frame so Dash has indexed the new page's
      // component paths (toStore is also retry-hardened as a backstop).
      requestAnimationFrame(view);
      return map;
    },
  };
  DL2.demos = DEMOS;

  // ===========================================================================
  // MOUNT / CLEANUP ENGINE
  // ===========================================================================
  function leaflet() {
    return window.leaflet || window.L || null; // v2 global is `leaflet`
  }

  function mountAll() {
    const L = leaflet();
    if (!L) return false; // global build not parsed yet
    document.querySelectorAll(".leaflet2-map").forEach((el) => {
      if (el._dl2_map || el._dl2_mounting) return;
      const id = el.dataset.demo;
      const build = DEMOS[id];
      if (!build) {
        console.warn("[DL2] no demo registered for", id);
        return;
      }
      el._dl2_mounting = true;
      try {
        const map = build(el, L);
        el._dl2_map = map;
        DL2.maps[id] = map;
      } catch (err) {
        console.error("[DL2] mount failed for", id, err);
      }
      el._dl2_mounting = false;
    });
    return true;
  }

  // Tear down maps inside a removed subtree so handlers/observers don't leak
  // when Dash swaps pages.
  function cleanup(node) {
    if (!node || node.nodeType !== 1) return;
    const els =
      node.classList && node.classList.contains("leaflet2-map")
        ? [node]
        : node.querySelectorAll
        ? Array.from(node.querySelectorAll(".leaflet2-map"))
        : [];
    els.forEach((el) => {
      if (el._dl2_map) {
        try {
          el._dl2_map.remove();
        } catch (e) {}
        delete DL2.maps[el.dataset.demo];
        el._dl2_map = null;
      }
    });
  }

  function start() {
    if (!mountAll()) {
      setTimeout(start, 50); // keep waiting for window.leaflet
      return;
    }
    const obs = new MutationObserver((muts) => {
      for (const m of muts) m.removedNodes.forEach(cleanup);
      mountAll();
    });
    obs.observe(document.body, { childList: true, subtree: true });

    // Watch the DMC color scheme on <html> and swap every basemap's tile URL when it
    // changes. The actual tooltip/popup/control colors flip via CSS (assets/style.css
    // uses --mantine-color-* vars), so nothing else needs JS.
    const themeObs = new MutationObserver(() => DL2.setMapTheme(currentScheme()));
    themeObs.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-mantine-color-scheme"],
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
