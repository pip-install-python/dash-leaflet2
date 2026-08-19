# Changelog

All notable changes to **dash-leaflet2** are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Because
the project tracks `leaflet@2.0.0-alpha.1`, the **0.x** line is itself alpha — APIs
will move until v2 leaves alpha upstream.

---

## [Unreleased]

The fleet's x402 instrumentation sync (1.3.x) — measurement only, no payment
or gating code, per the network's "instrument first, price later" rule.
Documentation site and network wiring only; no `dl2.*` component changed.

### Changed

- **Analytics: Gen-1 single-module tracker retired for the boilerplate's
  trio.** `lib/analytics_tracker.py` (per-request JSON ledger),
  `lib/traffic_rollup.py` (the hub's own daily v2+v3 definitions — its
  `_SKIP` tuple stays byte-identical to the boilerplate's, the fleet's
  one-measurement rule) and `lib/satellite_reporter.py` (hourly signed POST
  to 2plot.ai). The ledger moves from a JSONL file to
  `TRAFFIC_ANALYTICS_FILE` (JSON, `visitor_analytics.json`); the old ledger
  is left on disk untouched — the data window starts fresh. The Gen-1 SPA
  page-view beacon (`/api/pageview`) and per-session sign-in beacon
  (`POST /api/satellite/auth`) had no trio counterpart and were dropped:
  request-only counting is what makes this app's numbers comparable
  fleet-wide. `/healthz` now lives in `lib/health.py` (all three backends)
  and keeps its deployed payload shape. `SATELLITE_APP_ID` is retired;
  the trio reads `SATELLITE_APP_KEY` only.
- **Hard boot guard.** `lib.constants.require_owned_base_url()` replaces the
  warn-only `base_url_misconfigured()`: on Render (or `APP_ENV=production`)
  the app now REFUSES to boot without an owned base URL — unset, a
  platform-generated hostname, or a loopback origin all raise instead of
  logging one line into a wall of boot output.
- **dash-improve-my-llms floor 2.3.4 → 2.5.1** (the Tier-B SEO standard +
  tiered corpus documents), and `run.py` now registers `/llms-small.txt` /
  `/llms-full.txt` tiers from `LLMS_SMALL_TIER` / `LLMS_FULL_TIER` via the
  ported `lib/page_tiers.py`.
- **dash-clerk-auth 1.0.0 → 1.0.2, and a cryptography security floor.** This
  site renders the Clerk menu (`components/header.py`), so it was directly
  exposed to the avatar race 1.0.2 fixes: the injected script resolved the menu
  with `getElementById` the moment `Clerk.load()` resolved, but Dash mounts that
  menu from a separate `/_dash-layout` fetch — so whenever Clerk won the race a
  signed-in user sat behind a placeholder avatar and a "Sign In" menu for the
  life of the page, while `current_user()` and `clerk-auth-store` were both
  correct. Separately, `clerk-backend-api` moves `>=5.0.0,<6` → `>=7.0.0,<8`
  with a new `cryptography>=50.0.0` floor: SDK 5.x caps `cryptography` at
  `<47.0.0`, holding it on 46.0.7, below the fix for GHSA-537c-gmf6-5ccf,
  PYSEC-2026-3552, PYSEC-2026-3553 and PYSEC-2026-3554. Pinning `cryptography`
  alone returns `ResolutionImpossible`, which is why dash-clerk-auth 1.0.1 had
  to widen its own cap to `<8` first — the library carries the compatibility
  range, `requirements.txt` carries the security floor.
- **Version claims are derived, never written**: `lib/versions.py` ported and
  wired into `pages/markdown.py`, so docs prose can state
  `{{VERSION:dash-leaflet2}}` and always publish the installed version.
- **render.yaml matches the dashboard**: `plan: starter` (upgraded
  2026-08-16), a 1 GB disk at `/var/data` holding the analytics ledger and
  the control board's visibility overrides (both now survive deploys), and
  the corpus-tier knobs.

### Added

- `tests/test_traffic_rollup.py` — the boilerplate's 15-test suite over the
  v3 rollup semantics, copied verbatim.

---

## [0.2.2] — 2026-08-05

The rest of the 2plot network standard, from the checklist's "found on the
email pass" — the items that each bit a satellite which already looked
finished. Documentation site and network wiring only; no `dl2.*` component
changed.

> **Deploy note.** `og:image` now declares 1200×630, and the battery reads the
> CDN file's real pixels after every deploy. The new card
> (`scripts/make_social_card.py`) must be uploaded to
> `cdn.2plot.ai/github_assets/leaflet.2plot.dev.png` **before** this ships, or
> `social_card_real_pixels` fails the deploy — deliberately.

### Fixed

- **The network bulletin was never wired.** The hub publishes announcements and
  tips at `2plot.dev/api/network/bulletin`, and every satellite renders them in
  its llms.txt viewer header. This host had no `lib/bulletin.py` at all, so it
  showed "No announcements." and one generic tip where the hub publishes two —
  and an unwired host still renders both panels, which is why nobody noticed.
  Note that `dash_improve_my_llms/bulletin.py` never reads
  `NETWORK_BULLETIN_URL`: setting that variable without this code does nothing,
  silently. `run.py` now prints which of the two states it booted in.
- **The social card was the wrong shape, and the wrong image.** 1280×515
  (2.49:1) is wider than both the Open Graph ideal and Twitter's 2:1 slot, so
  every platform cropped it — and the file was the 2plot network wordmark
  rather than a card for this site. Replaced with a generated 1200×630 card,
  and the battery now reads the served PNG's IHDR so a re-upload at a different
  size cannot pass while every offline test stays green.
- **`dash-clerk-auth` 0.9.0 renders a dead avatar on satellites** — the header
  control appears and never resolves the signed-in user. This host is a
  satellite of the 2plot.ai primary, so it is exactly the affected shape.
  Vendored 0.9.1.
- **`markdown2dash` was installed without `--no-deps` in two places** —
  `scripts/compat_matrix.py` and the README quickstart. In the matrix that
  meant every per-Dash-version venv booted an app with no documentation pages,
  so the compatibility run measured nothing.
- **`AD_APP_ID` was the package name, not the directory key.** The hub lists
  `dash-leaflet2` under `legacy_ids` and folds it in at ingest specifically
  "until leaflet's own network-standard pass sets `AD_APP_ID=leaflet`". It now
  does, and `SATELLITE_APP_KEY` is set alongside `SATELLITE_APP_ID`.

### Added

- **The Control Board appears in the nav, to admins only** — its own section in
  both the desktop navbar and the mobile drawer, hidden by default and revealed
  server-side by the same predicate the page itself uses. The link is cosmetic:
  `/admin/control-board` gates itself on every render and again in its mutating
  callback, and fails closed without Clerk.
- `lib/bulletin.py`, `scripts/make_social_card.py`, `tests/test_bulletin.py`,
  `tests/test_admin_nav.py`, and `social_card_real_pixels` in the battery.
- `SITE_SHORT_NAME` (with `PAGE_TITLE_PREFIX` derived from it rather than typed
  twice) and `OG_IMAGE_TYPE`.

### Changed

- **A hosted deploy advertising `http://localhost` now says so, loudly.**
  Production was serving `/llms.txt`, `/sitemap.xml` and every canonical link
  pointing at `http://localhost:8050`, and nothing looked wrong: the site
  rendered, `/healthz` returned 200, and `tests/test_network_surfaces.py`
  passed because it asserts sitemap URLs start with `BASE_URL` — comparing the
  deployed value against itself, which is just as true when both sides are
  localhost. The code default was never the problem (it is already
  `https://leaflet.2plot.dev`); a loopback value can only come from
  `APP_BASE_URL` or `DASH_LEAFLET2_BASE_URL` being *explicitly* set to one, and
  `.env.example` ships exactly those values uncommented for local use.
  Three changes, none of which self-heal — auto-filling Render's
  `RENDER_EXTERNAL_URL` would just swap one wrong canonical origin
  (`*.onrender.com`) for another: `lib.constants.base_url_misconfigured()`
  returns an actionable message when a hosted service resolves BASE_URL to a
  loopback origin, naming which of the two variables is at fault; `run.py`
  prints the resolved base URL at boot and that warning after it; and
  `/healthz` now reports `base_url`, so the origin a satellite *advertises* is
  checkable from outside it with one curl. `.env.example` says plainly that its
  values are local-only.
- **`BASE_URL` accepts `APP_BASE_URL` first**, falling back to this repo's
  `DASH_LEAFLET2_BASE_URL`. An alias, never a rename — both are set in
  `render.yaml`, because removing one of two env names from a live service is
  how a host starts advertising the wrong canonical origin and deindexes
  itself quietly.
- **`dash-emoji-mart` and `flexlayout-dash` install from PyPI**, replacing the
  vendored tarballs now that their working builds are published. Both keep a
  load-bearing floor — `dash-emoji-mart>=0.0.5` (0.0.3 errors on init) and
  `flexlayout-dash>=1.1.0` (1.1.0 renamed the import to `flexlayout_dash`, which
  `docs/walking-sim/example.py` imports directly) — so a too-old resolve fails
  at install rather than at page render. They also re-enter CI's `pip-audit`
  job, which skips `./vendor/` lines because pip-audit can only assess PyPI
  dists. `vendor/` is down to the single Clerk tarball.
- **`dash-clerk-auth` 0.9.1 → 1.0.0**, and `lib/auth.py` stops hand-patching the
  satellite. Both fixes it used to inject are upstream: 0.9.1 stamps
  `data-clerk-domain` onto the ClerkJS script tag, and 0.9.2 replaced the
  `Clerk.openSignIn()` modal — which ClerkJS forbids on a satellite — with a
  navigation to the primary. What stays is one *delegated* capture-phase
  listener on `#clerk-login-button`: the package binds that id inside its
  `DOMContentLoaded` handler, so the header control is covered but the sign-in
  card in `lib/page_visibility.py`, which a page callback renders later, would
  otherwise have no listener at all. It now defers to the package's own
  `window.dashClerkAuth.buildSatelliteRedirect()` (0.9.2's page-JS surface,
  opt-in via `CLERK_SATELLITE_SIGN_IN_REDIRECT`) and falls back to the same
  `redirectToSignIn()` call upstream makes.

  1.0.0 raises `requires-python` to `>=3.10` — `clerk-backend-api` 5.x
  publishes no 3.9 build, so the old `>=3.9` claim was never installable. That
  binds the **docs site** only: Docker is 3.12 and the CI docs matrix is
  3.10/3.12/3.13. The `dash_leaflet2` package keeps `requires-python >=3.9`,
  which the `package-python-range` CI job proves against the built wheel.

---

## [0.2.1] — 2026-07-31

Brings this satellite onto the **2plot network standard** that 2plot.ai (root),
2plot.dev (hub) and `dash-documentation-boilerplate` (the template) now ship.
No `dl2.*` component changed; everything here is the documentation site, its
analytics and its CI.

### Fixed

- **Every page shipped an empty `og:image`.** Dash emits `og:image` and
  `twitter:image` for each page and leaves them `content=""` when it can find
  no image, which unfurls as a *blank* preview card on Facebook, Twitter/X,
  Slack, Discord and LinkedIn — strictly worse than declaring no image at all.
  `register_page(image_url=...)` now supplies the real absolute URL, served
  from the 2plot CDN so a sleeping free-tier container never costs a preview.
  `templates/index.html` deliberately declares only the auxiliaries Dash omits
  (`og:image:width` / `height` / `alt` / `type` / `secure_url`,
  `twitter:image:alt`), so it cannot duplicate the URL.
- **The web app manifest could never have offered an install.** Its `name` and
  `short_name` were empty strings — which disqualifies a manifest outright —
  and its icon `src` paths pointed at `/android-chrome-192x192.png` at the site
  root, where nothing is served; the files live under `/assets/favicon_io/`.
  Nothing linked to it either. Fixed, linked, and joined by
  `apple-touch-icon` (iOS ignores the manifest and uses that for Add to Home
  Screen) and the `msapplication-*` tiles.
- **Crawler traffic was never counted.** The per-request tracker was a Flask
  `before_request` handler registered *after* `add_llms_routes`, and
  dash-improve-my-llms' bot middleware answers every crawler with prerendered
  HTML — which short-circuits the remaining `before_request` handlers. No
  crawler request ever reached the ledger, so this site reported
  `bot_hits: 0` to 2plot.ai structurally, for every day it has been live,
  with nothing visibly broken. The tracker now wraps the WSGI/ASGI callable
  instead (`_wsgi_tracker` / `_asgi_tracker`), which sits outside the whole
  application and cannot be short-circuited. Registration order was not a
  usable fix: Flask runs `before_request` handlers first-registered-first,
  while Starlette makes the last-added middleware outermost, so no single
  ordering is correct on all three backends.
- **The ad fetch and the traffic rollup polluted the hub's ledgers.** Both
  server-to-server calls left as `python-requests/2.x`, which 2plot.dev and
  2plot.ai classify as a bot — so every docs page view here inflated the
  hub's `bot_hits`. Both now send the network's internal-traffic User-Agent.
- **A control-board toggle could rename the site.** `apply_llms_state`
  re-registers a page's metadata whenever a visibility verdict changes, using
  the name the markdown loader recorded — `"Home"` for this site's root. One
  flip of the home page's llms.txt switch would have overwritten the site
  brand at runtime, silently degrading the published identity to a generic
  word. `lib.page_visibility.published_name` now pins the root to
  `SITE_BRAND`.
- **gunicorn was pinned under a security floor.** `gunicorn>=21.2,<22` was
  holding the production server on a line carrying two HTTP request-smuggling
  CVEs (CVE-2024-6827, CVE-2024-1135), because `markdown2dash` 0.1.2 declares
  `gunicorn<22`. markdown2dash is now installed with `--no-deps` (its real
  dependencies moved into `requirements.txt`, carrying its own version ranges)
  and the floor is `gunicorn>=23.0.0`, asserted inside the built image by CI.

### Added

- **Explicit site identity.** `lib.constants.SITE_BRAND` —
  *"dash-leaflet2 — Leaflet 2 maps for Dash"* — is now the one string on every
  surface: `Dash(title=)`, `register_page_metadata(path="/")`, the home
  markdown's H1 and the README. This matters because the home page is
  registered as `"Home"`, which `resolve_site_title` skips as generic; without
  the explicit registration the site published a framework fallback.
- **An introduction video** on the home page and in the README —
  [*Dash Leaflet 2.0: Drone Tracking, Image Overlays & Map Packages in
  Python*](https://youtu.be/Wlmw98JrJZI). Embedded from
  `youtube-nocookie.com`, so the player sets no visitor-tracking cookies on a
  site that otherwise counts nothing beyond an anonymised page view, and
  accompanied by a plain link — an agent reading `/llms.txt` never sees an
  iframe, and neither does anyone whose browser blocks the embed.
- **`scripts/network_smoke.py`** — the network's named-check battery, run
  against the CI container and against production with identical check names.
  Proves identity, the agent-facing document surfaces, the robots fingerprint,
  hidden-page 404s and content negotiation.
- **`scripts/smoke_live.py`** — post-deploy checks: every canonical, every
  crawler body, and every peer `llms.txt` in the directory. Peer failures warn
  rather than fail, because gating a deploy on somebody else's certificate is
  shared fate.
- **`tests/`** — a secretless in-process suite (80 tests) covering site
  identity, the internal-traffic contract in both directions, the agent and
  crawler surfaces, the social card and manifest, and *the smoke scripts
  themselves*, so a battery that has rotted into a silent pass fails here
  first.
- Two live battery checks for the surfaces above — `social_card_is_shareable`
  (the image is declared once, is not empty, and actually resolves) and
  `installable_as_an_app` (the manifest is linked, named, and its icons
  resolve). Both fail invisibly in production otherwise: nobody sees their own
  link previews, and no browser explains why it declined to offer an install.
- **`.github/workflows/cd.yml`** — deploy plus live verification, waiting for
  five consecutive healthy responses after a 120s settle rather than a single
  200 (Render swaps instances, so the old build answers throughout).
- **`.github/dependabot.yml`** — weekly pip with a `dash-network` group,
  weekly npm, monthly actions and Docker.

### Changed

- **`dash-improve-my-llms>=2.3.4`** (from 2.3.3), the network floor: 2.3.4 adds
  `resolve_site_title`, without which the `/llms.txt` H1 and the llms viewer's
  brand chip fall back to `app.title`.
- **CI on the network baseline**: `permissions: contents: read`,
  `timeout-minutes` on every job, an `actionlint` step (an invalid workflow
  file is the one defect CI structurally cannot report), a real Docker
  build → boot → battery job with buildx GHA caching, version fingerprints
  asserted inside the image, and an advisory `pip-audit`. CI now runs on
  pull requests and `workflow_call` only — `main` belongs to CD, which calls
  it. The existing wheel and Dash-compatibility jobs are unchanged.
- **The home page** is no longer the generated scaffold: it opens with the site
  brand and describes what the library actually is.
- `templates/index.html` no longer publishes `pip-install-python.com` as this
  site's Organization URL, author URL or footer link — it is not a 2plot
  network host. Those now point at https://github.com/2plotai.
- The README's assets are served from `cdn.2plot.ai` rather than
  `raw.githubusercontent.com`, so they render on PyPI (where the README is the
  long description) as well as on GitHub.

---

## [0.2.0] — 2026-07-28

First public release: the project splits into a private R&D checkout and this
public mirror, which is what ships to PyPI and to https://leaflet.2plot.dev.

### Added — public release preparation

The project is split into a private R&D checkout and this **public mirror**, which
is what ships to PyPI and to https://leaflet.2plot.dev.

- **`/tile-selector` rewritten** as a lean, self-contained page documenting the
  `dl2.TileSelector` component — click / shift-drag selection, the
  `{z, x, y, url, bounds}` data boundary, and the `[MUTABLE]` round-trip that lets
  a Clear button write `selectedTiles` back from Python. The previous 3,700-line
  AI tile-generation lab stays internal.
- **`scripts/smoke_test.py`** — headless suite driving the app through the backend's
  test client (no socket, no browser): page registration with duplicate-path
  detection, layout construction plus JSON serialisation of every example, and an
  HTTP sweep of every route, `/_dash-layout`, `/_dash-dependencies`, `/healthz`,
  `/llms.txt`, `/robots.txt` and `/sitemap.xml`.
- **`scripts/compat_matrix.py`** — builds a throwaway virtualenv per Dash version
  (4.1.0 / 4.2.0 / 4.3.0 / 4.4.1 by default), installs the docs site into each, runs
  the smoke suite, and writes `COMPATIBILITY.md`. Optional `--browser` leg boots each
  venv for real and collects console errors with Playwright. This is what turns the
  `dash>=4.1` claim into evidence.
- **`scripts/sync_from_rnd.py`** — pulls R&D work forward into the mirror behind an
  explicit denylist. Pull, not push: a new R&D docs page surfaces as NEW for approval
  rather than leaking by being forgotten upstream.
- **2plot network integration**, all dormant without environment keys:
  `lib/ad_client.py` (2plot.dev ad slots in the docs aside), the Gen-1
  satellite traffic module — since retired for the analytics trio, see the
  Unreleased entry — (signed traffic rollups to 2plot.ai, `/healthz`, SPA
  page-view beacon),
  `lib/auth.py` (Clerk satellite of the 2plot.ai primary, including the two
  dash-clerk-auth 0.9.0 satellite fixes), and `lib/page_visibility.py` +
  `pages/control_board.py` (four-tier page visibility re-checked on every render,
  editable live at `/admin/control-board`).
- **Deployment**: `Dockerfile`, `.dockerignore`, `render.yaml` and `DEPLOYMENT.md`
  for `leaflet.2plot.dev`.
- **`vendor/`** — the two docs-only packages that are not on PyPI
  (`dash_emoji_mart` 0.0.5, `flexlayout_dash` 1.1.0) are committed here so
  `pip install -r requirements.txt` works from a clean clone. Neither is needed by
  the `dash_leaflet2` package, which still requires only `dash>=4.1`.

### Changed

- `app.py` → **`run.py`**, with `HOST` / `PORT` / `DASH_DEBUG` read from the
  environment so the compatibility matrix can run several Dash versions side by side.
- `requirements.txt` rewritten: the vendored packages install from relative
  `./vendor/` paths instead of absolute `file:///Users/...` URLs, and the Dash pin
  carries a `# COMPAT-MATRIX: dash` tag the matrix script strips per run.
- README rebuilt for the public release; `pyproject.toml` gained full trove
  classifiers and project URLs pointing at the documentation site.

---

## [0.1.0] — 2026-07-04

### Added — `crossOrigin` on TileLayer + ImageOverlay

`dl2.TileLayer` and `dl2.ImageOverlay` surface Leaflet's `crossOrigin` option
(`"anonymous" | "use-credentials" | ""`). Setting it makes the underlying `<img>`
loads CORS-mode so canvas captures (map screenshots / html2canvas thumbnails) can
read the pixels without tainting the canvas — requested by SailsBoard's
save-time-thumbnail pipeline. **Opt-in with no default**: a CORS-mode img fails to
load entirely against a host that doesn't answer `Access-Control-Allow-Origin`, so
leave it unset for tile providers you don't control. Construction-time only (for
`ImageOverlay`, `setUrl` and the editable drag/resize/rotate transforms reuse the
same img element, so the attribute set at construction persists).

### Added — dash-leaflet 1.x parity work (compiled `dl2.*` package)

Closes the surface gap downstream projects (SailsBoard's harbor map being the
canonical one) hit when migrating off `dash-leaflet` 1.x. Every item below is
verified end-to-end in a new live showcase page under `/docs/<slug>/`.

**TileLayer pro props** — `dl2.TileLayer` gains `minZoom`, `bounds`, `errorTileUrl`,
`zIndex`, `subdomains`, `detectRetina`, `tms`. `opacity` + `zIndex` are `[MUTABLE]`
via `setOpacity` / `setZIndex`. Lets downstream apps clip tile requests to a
geographic box, hide 404 tiles with a transparent PNG, stack multiple tile layers
explicitly, and shard CDN load across `{s}` subdomains. Showcase: `/tilelayer-pro-props`.

**Map pro props** — `dl2.Map` gains `minZoom`, `maxZoom`, `maxBounds`, `zoomControl`,
`keyboard`, plus the 6 interaction-disable handlers: `dragging`, `scrollWheelZoom`,
`doubleClickZoom`, `boxZoom`, `pinchZoom` (v2's name for v1's `touchZoom`), and
`tapHold`. All of zoom/bounds/keyboard/the 5 user-flippable handlers are `[MUTABLE]`
— a callback can lock dragging while a walkthrough plays, kill scroll-wheel zoom in a
detail-preview panel, etc. `pinchZoom` writes through to both `pinchZoom` (v2) and
`touchZoom` (v1 alias) so the prop name stays stable as Leaflet 2 evolves. Showcase:
`/map-pro-props`.

**GeoJSON clustering** — `dl2.GeoJSON` adds the dash-leaflet 1.x clustering surface
backed by [SuperCluster v8](https://github.com/mapbox/supercluster): `cluster`,
`superClusterOptions`, `pointToLayer`, `clusterToLayer`, `hideout`,
`zoomToBoundsOnClick`, `spiderfyOnMaxZoom`. `pointToLayer` / `clusterToLayer` accept
a JS source string compiled via `new Function(...)` at construction time; both
receive a `ctx = { hideout, leaflet, map }` argument so user code can build any
Leaflet 2 layer without depending on a global. Non-point features (LineString,
Polygon) pass through unclustered. Showcase: `/geojson-cluster`.

**LayerGroup + FeatureGroup** — new `dl2.LayerGroup` and `dl2.FeatureGroup`
components. Children of either attach to the group instead of the map via a
forwarding `LeafletMapContext` proxy (`makeForwardingMapProxy` in
`layersControl-shared.ts`) that intercepts `addLayer`/`removeLayer` but transparently
forwards every other map method (`latLngToLayerPoint`, `on`, `getCenter`, ...) to the
real map — required for layers like Marker whose rotation effect needs the real
projection. FeatureGroup additionally emits a combined `geojson` of its vector
children plus an aggregate `n_clicks` and `n_layers` counter. Showcase: `/layer-group`.

**ScaleControl** — `dl2.ScaleControl` wraps Leaflet 2's `Control.Scale` (lives on the
`Control` namespace but is not ESM-exported by `leaflet@2.0.0-alpha.1`, so we reach
through `(Control as any).Scale`). Props: `position` (mutable), `metric`, `imperial`,
`maxWidth`, `updateWhenIdle`. Showcase: `/scale-fullscreen-image`.

**FullScreenControl** — `dl2.FullScreenControl` is a thin custom `Control` that wraps
the browser's native `requestFullscreen()` / `exitFullscreen()` API around the map
container (Leaflet 2 itself does not ship a fullscreen control). Round-trips
`fullscreen` (boolean) and `n_clicks` to Dash so a callback can react when the user
enters or leaves fullscreen. Showcase: `/scale-fullscreen-image`.

**ImageOverlay** — `dl2.ImageOverlay` wraps `leaflet.ImageOverlay`. Mutable `url`,
`bounds`, `opacity`, `zIndex`; optional `interactive=True` lets the image fire
`n_clicks`. Useful for previewing a raster scan before slicing it into tiles, draping
a single static image onto a geographic box, or showing a non-tiled overlay. Showcase:
`/scale-fullscreen-image`.

- **Editable transform controls** — set `editable=True` for a TextMarker-style control
  system: click to select, drag the body to **move** (translates `bounds`), drag the corner
  dot to **resize** (scales `bounds` about the `anchor`, which stays pinned), and the top dot
  to **rotate** (a CSS-transform visual rotation pivoting at the `anchor` — `bounds` stay
  axis-aligned since Leaflet's ImageOverlay has no native geo-rotation). The white anchor dot
  sits at the chosen `anchor`. New props `editable`, `selected` (two-way), `rotation`
  (two-way), `anchor`; `bounds` becomes two-way and `n_transforms` counts move/resize commits.

**TextMarker** — new `dl2.TextMarker`: editable, draggable, styleable text placed on
the map like a Marker (implements Route A of the `text-caption-marker-proposal`). It is
a Leaflet 2 `Marker` whose icon is a content-sized, optionally-`contentEditable` text box
rendered into the icon via a React portal, reusing Marker's drag lifecycle + the
transform-reprojection trick (so rotation survives Leaflet's constant transform rewrites).
- **Placement**: anchored to `[lat, lng]`; when `position` is omitted it spawns at the
  **center of the current viewport** and writes that position back. `anchor` (9 positions)
  picks which point of the box sits on the latlng — that point is also the rotation pivot.
- **Direct manipulation**: drag to move (writes `position` + `n_drags`), double-click to
  edit inline (writes `text` + `n_edits`), and when `selected` a corner **resize** handle
  (→ `fontSize`) and a **rotate** handle (→ `rotation`, Shift-snaps to 15°) appear.
- **Style**: `color`, `backgroundColor`, `fontFamily`, `fontSize`, `fontWeight`,
  `fontStyle`, `padding`, `borderRadius`, `rotation`, `rotateWithMap` — all `[MUTABLE]`
  two-way (the contextual glass toolbar that shows while selected edits them and round-trips
  every change to Dash, so a host can also drive style from props). `selected` is two-way
  (clicking the label selects it; a map-background click deselects); `showToolbar` hides the
  built-in toolbar for hosts that supply their own.
- **Two size models** via `scaleWithZoom` (+ `referenceZoom`): `false` (default) is a
  constant screen-size HUD caption (`fontSize` is literal px at every zoom); `true` is
  geographic sizing — the on-screen size scales by `2^(zoom − referenceZoom)` so the caption
  keeps a fixed ground footprint as the camera flies. `referenceZoom` defaults to the zoom at
  which the label was created.
- Anchor offset is applied via the icon's **margin** (not baked into the transform) so
  Leaflet's own mid-drag positioning and ours never disagree; a post-handle-drag `click` is
  swallowed so resize/rotate don't deselect.
- The white selection dot (which doubles as the resize grip) is drawn at the chosen `anchor`
  point — `bottom` → bottom-center, `top-left` → top-left, … (`center` → bottom-right so it
  never covers the text) — so you can see where the label is pinned. Resize now references the
  box center (the dot sits at the anchor, so an anchor-referenced ratio would divide by ~0).
- `selected` is **uncontrolled when omitted**: the marker self-manages selection (click to
  select, two-stage map-click to deselect) and a map-event bus keeps only one TextMarker
  selected at a time. Pass an explicit `selected` to drive it from the host. The anchor model
  + dot positioning now live in the shared `src/ts/anchor.ts` (used by the editable ImageOverlay too).

**EditControl `text` tool (proposal Route B)** — `dl2.EditControl` gains a `text` tool
alongside `marker` / `polyline` / `polygon` / …. Picking it and clicking the map drops an
inline-editable caption that round-trips through the **same `geojson` channel** as every other
shape — a GeoJSON `Point` carrying `kind:"text"` + the caption style (`text`, `color`,
`fontSize`, `fontFamily`, `fontWeight`) in `properties`. In edit mode the caption is draggable
and double-click re-opens the inline editor; cancel/revert rebuilds captions as text icons (not
pins). Enable per-tool with `draw={"text": True}`. Showcase: `/text-marker`.

### Added — docs site (`docs/<slug>/`)

Five new markdown-driven showcase pages, each with a focused "limited working
example" `example.py` next to the markdown:

- `/tilelayer-pro-props` — two stacked tile layers (OSM base with `subdomains` +
  `detectRetina`; CARTO labels-only overlay clipped to a Rockport, TX `bounds` box
  with a transparent `errorTileUrl`). Sliders drive `opacity` + `zIndex` live.
- `/map-pro-props` — 6-handler Switch panel + zoom RangeSlider + `maxBounds` toggle
  + live viewport readback. Flipping a Switch immediately disables the matching
  Leaflet handler on the live map.
- `/geojson-cluster` — 200 synthetic vessel positions colored by category via a JS
  `pointToLayer` reading a Python-shipped `hideout` color map; cluster bubbles take
  the dominant category's color. Cluster-radius slider tunes
  `superClusterOptions.radius` live.
- `/layer-group` — two maps: one `LayerGroup` of three markers behind a single
  Switch (the whole group toggles together), one `FeatureGroup` wrapping four shapes
  and emitting combined `geojson` + bumping `n_clicks` on any child click.
- `/scale-fullscreen-image` — one map with the scale bar (position + metric/imperial
  Switches), the fullscreen button (reports `fullscreen` + `n_clicks`), and a
  swappable `ImageOverlay` with opacity slider.
- `/text-marker` — a selected `TextMarker` you drag / edit / resize / rotate / restyle
  on the map (or drive from the right column: text, color, font size, rotation, anchor,
  `scaleWithZoom`), a second caption with `scaleWithZoom=True` that holds its ground size,
  and the `EditControl` `text` tool wired in (click the T, click the map, type — the
  caption shows up in `EditControl.geojson` as a `kind:"text"` Point). Live readback panel.

### Added — supporting work

- New runtime dependency: `supercluster@^8.0.1` (bundled into `dash_leaflet2.js`).
  The 0.0.1 wheel sat at ~261 KiB; with clustering + the four new components the
  bundle is now ~263 KiB.
- `src/ts/types/leaflet.d.ts` — extended for `Map.setMinZoom` / `setMaxZoom` /
  `setMaxBounds` / `getMinZoom` / `getMaxZoom`, `Map.keyboard`, `TileLayer.setOpacity`
  / `setZIndex`, `ImageOverlay`, plus a minimal ambient `supercluster` module.
- `src/ts/layersControl-shared.ts` — new `makeForwardingMapProxy(onAdd, onRemove,
  getRealMap)` builds a JS-`Proxy`-based map stand-in that intercepts
  `addLayer`/`removeLayer` but forwards every other property access to the real map.
  Used by `LayerGroup` and `FeatureGroup`; the existing thin `makeMapProxy` is kept
  for `BaseLayer`/`Overlay` where forwarding is unwanted.
- `src/ts/theme.css` — cluster-bubble glass styling (`.dl2-cluster-bubble` and
  `.dl2-cluster-{32,40,48,56}` sizes) + fullscreen-button styling
  (`.dl2-fullscreen-control`, `.dl2-fullscreen-button`).

### Added — earlier in Unreleased

- **`dl2.TileSelector`** — a map control that turns the map into a tile picker:
  click or shift-drag to select tiles, which round-trip to Python as
  `{z, x, y, url, bounds}`, keyed by `z/x/y` so selections survive pan and zoom.
- **Compare Lab** (`/compare-lab`) — tileset comparison surface: an `EasyButton` +
  Popover + `dash_mui_charts.TreeViewPro` driving a clientside reconciler over a
  stack of `TileLayer` overlays (visibility, opacity, z-order, deletion), seeded
  with synthetic SVG overlays so every interaction responds in under a second.
- **Walking Sim** (`/walking-sim`) — Esri Imagery + NatGeo layered basemaps with a
  street-tile minimap; flyTo between WALK / EXPLORE modes.
- **Sub-toolbar + live drawing feedback** in `dl2.EditControl` — vertex-handle previews,
  cursor-following guide tooltip, dashed rubber-band, context-sensitive fly-out actions
  (Finish / Delete-last-point / Cancel during draw; Save / Cancel during edit).

### Fixed
- **Cross-zoom prompt engineering** — the AI was pasting descendant references as
  visible rectangular insets with duplicated features and a seam. Rewrote SOURCE +
  CROSS-ZOOM REFERENCE labels and the addendum to forbid pasting/insets and to assert
  the source tile as the geometric ground truth for all four quadrants.
- **Tileset comparison overlay layering** — z15 (later-added, larger) was covering z16
  at every viewport zoom. Added zoom-meets-tile filtering: among overlapping tree-checked
  tiles, only the deepest zoom the viewport has met shows (`z15` at vz=13–15, `z16` at
  vz=16, `z17` at vz=17+). Standalone tiles unaffected. Set `zIndex = 400 + tileZ` so
  any transient overlap keeps the finer tile on top.
- **EasyButton popover toggle** — `dmc.Popover.opened` is not pushed through `setProps`
  after internal state changes; switched to a DOM-read clientside pattern reading
  `.mantine-Popover-dropdown` `offsetParent`.
- **`MUI TreeView` overlay flicker** — refactored to "mount-everything-hide-via-opacity"
  with `transition: opacity 120ms ease`; checkbox-row double-click bounces no longer
  tear overlays off the map.

---

## [0.0.1] — 2026-05-22

First **alpha** release. Build a wheel from source (`python -m build`); not yet on PyPI.

### Added — components shipped in the wheel

| Component | Wraps | Notes |
|---|---|---|
| `dl2.Map` | `leaflet.Map` | `viewport` + `clickData` round-trip; React-context bridge replaces react-leaflet |
| `dl2.TileLayer` | `leaflet.TileLayer` | `url`, `attribution`, `maxZoom`, `opacity` |
| `dl2.Marker` | `leaflet.Marker` | default / `icon` / `emoji` / `iconify` / full `iconOptions` icon modes; bundled marker images (base64) |
| `dl2.Polyline`, `dl2.Polygon`, `dl2.Rectangle`, `dl2.Circle`, `dl2.CircleMarker` | corresponding `leaflet.*` | vector path props + click round-trip |
| `dl2.GeoJSON` | `leaflet.GeoJSON` | `data`, `style`, `clickFeature`; `pointToLayer` sets the bundled default icon to dodge v2's stale `Icon.Default()` trap |
| `dl2.Popup`, `dl2.Tooltip` | `leaflet.Popup`, `leaflet.Tooltip` | render arbitrary Dash content through React portals |
| `dl2.LayersControl` + `dl2.BaseLayer` + `dl2.Overlay` | custom (`Control` subclass) | v2's `Layers` class is not ESM-exported; ships our own with `RegisterContext` |
| `dl2.EditControl` | native v2 toolbar `Control` | leaflet-draw is v1-only; our native replacement draws marker / polyline / polygon / rectangle / circle + delete with GeoJSON round-trip |
| `dl2.EasyButton` | `leaflet.Control` | Iconify icon, `n_clicks` / `n_dblclicks` |
| `dl2.AttributionControl` | `leaflet.Control.Attribution` | `prefix`, custom `attribution` |
| `dl2.KeyboardControl` | custom (`Control`) | DOM key listeners → `lastKey` / `n_events` |
| `dl2.MiniMap` | custom (`Control`) | second `leaflet.Map` instance pinned to a corner |
| `dl2.TileSelector` | custom (`Control`) | hover-highlight, click-toggle, shift+drag box-select; `selectedTiles` round-trip with `{z, x, y, url, bounds}` |
| `dl2.Tooltip`, `dl2.Popup` | (see above) | bind to any layer via React portal |

### Added — hooks/CDN showcase (`run.py`)
- 20+ pages under `docs/` demonstrating v2 features through the `dash.hooks` API with
  no build step: pointer events, canvas overlay, ES6 subclassing, `ResizeObserver`
  sizing, vector layers, emoji/iconify markers, layers control, draw + edit + measure,
  easy button, MiniMap, basic rotation, flight sim, walking sim, events→Python, flyTo,
  attribution control, tile-layers-pro, tile-selector, compare-lab.
- DMC AppShell + sidebar + dark-mode toggle; FastAPI backend by default
  (`DASH_BACKEND=flask python run.py` to fall back).

### Added — developer tooling
- `.claude/` directory: 1 subagent (`leaflet2-component-author`), 2 skills
  (`build-and-verify`, `new-component`), 3 path-scoped rules
  (`leaflet2-v2-api.md`, `dash-components.md`, `showcase-pages.md`).
- Webpack + `dash-generate-components` build pipeline; Python classes generated from TS
  JSDoc; default marker icons inlined as base64 to dodge v2's CSS-path detection.

### Known gotchas
- v2's UMD global is **`window.leaflet`** (not `window.L`).
- No lowercase factories — `new Marker(...)`, not `L.marker(...)`.
- v2 fires **pointer events** (`pointermove`/`pointerdown`), not mouse events.
- `BlanketOverlay._onMoveEnd()` clears the canvas after drawing — Canvas renderer
  workaround: `requestAnimationFrame(() => renderer._update())` after `moveend`/`zoomend`.
- v2 ships no TypeScript types — minimal ambient declarations at
  `src/ts/types/leaflet.d.ts`.

[Unreleased]: https://github.com/pip-install-python/dash-leaflet2/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pip-install-python/dash-leaflet2/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/pip-install-python/dash-leaflet2/releases/tag/v0.0.1
