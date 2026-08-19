# Deployment — leaflet.2plot.dev

The documentation site ships as a Docker web service on Render, fronted by
`leaflet.2plot.dev`, and runs as a **satellite** of the 2plot network. Four
integrations attach to it, and **every one is dormant without its environment
keys** — a plain `python run.py` is just the docs.

| Integration | Module | Talks to | Dormant unless |
|---|---|---|---|
| Ad network | `lib/ad_client.py` | `2plot.dev/api/ad-network/serve` | ad server reachable |
| Traffic analytics | `lib/analytics_tracker.py` + `lib/traffic_rollup.py` + `lib/satellite_reporter.py` | `2plot.ai/api/satellite/traffic` | `CROSS_APP_WEBHOOK_SECRET` |
| Authentication | `lib/auth.py` | Clerk, satellite of 2plot.ai | all three `CLERK_*` keys |
| Page control board | `lib/page_visibility.py`, `pages/control_board.py` | local JSON | always on; gate needs Clerk |

## Quick start

```bash
docker build -t dash-leaflet2-docs .
docker run --rm -p 8050:8050 -e PORT=8050 dash-leaflet2-docs
open http://localhost:8050
```

On Render: **New → Blueprint → this repo**. `render.yaml` declares the service,
the health check (`/healthz`) and every environment variable, with secrets
marked `sync: false` so you fill them in the dashboard.

## Environment variables

### Core

| Variable | Default | What it does |
|---|---|---|
| `DASH_BACKEND` | `flask` | `flask` \| `fastapi` \| `quart`. Keep `flask` under gunicorn — the ASGI backends need uvicorn. |
| `PORT` / `HOST` | `8050` / `0.0.0.0` | Bind address. Render injects `PORT`. |
| `WEB_CONCURRENCY` | `2` | gunicorn workers. Drop to 1 on a 512 MB free instance. |
| `APP_BASE_URL` | `https://leaflet.2plot.dev` | Canonical origin for `sitemap.xml`, `llms.txt` and every `<link rel="canonical">` / `og:url`. Network-standard name, **read first**. |
| `DASH_LEAFLET2_BASE_URL` | `https://leaflet.2plot.dev` | This repo's own spelling of the same thing, read second. An alias, never a rename — keep both set on a live service. |

> **Never carry `.env.example`'s values for those two into a hosted service.**
> They are `http://localhost:8050` for local development. On a hosted deploy
> `lib.constants.require_owned_base_url()` — the network's hard boot guard,
> which replaced the old warn-only check in the 1.3.x sync — REFUSES to boot
> when neither variable is set, when one is set to a loopback origin, or when
> the value is a platform-generated hostname (`*.onrender.com`). A site
> publishing the wrong origin renders fine and `/healthz` returns 200, so the
> symptom used to be invisible from inside; now the deploy log carries the
> refusal, and `/healthz`'s `base_url` field still shows the origin actually
> advertised. Render's blueprint declares the right values but does **not**
> overwrite a variable already edited in the dashboard, so fix it there.
| `MUI_PRO_API_KEY` | — | MUI X Pro licence for the TreeViewPro tile browser on `/tile-layers-pro`. Absent → that one control is watermarked. |

### Ad network → 2plot.dev

| Variable | Default | What it does |
|---|---|---|
| `AD_SERVER_URL` | `https://2plot.dev` | Ad server origin. Fetches are server-to-server, so ad blockers and CORS never see them. |
| `AD_APP_ID` | `dash-leaflet2` | This app's identity in the `/admin/ad-board` performance tables. |

The slot is injected into each page's table-of-contents aside
(`inject_ad_into_aside` in `pages/markdown.py`), so pages without a `.. toc::`
carry no ad. If the ad server is unreachable the slot stays hidden and a 60-second
circuit breaker stops retrying — an outage never adds latency to a page view.

### Traffic analytics → 2plot.ai

The boilerplate's tracker/reporter/rollup trio, adopted in the fleet's 1.3.x
instrumentation sync (it replaced the Gen-1 single-module tracker):
`lib/analytics_tracker.py` records every request into a JSON ledger,
`lib/traffic_rollup.py` computes the daily v2+v3 payload with the hub's own
definitions (its `_SKIP` tuple stays byte-identical to the boilerplate's — the
fleet's one-measurement rule), and `lib/satellite_reporter.py` POSTs it
hourly, HMAC-signed. `/healthz` itself now lives in `lib/health.py`.

| Variable | Default | What it does |
|---|---|---|
| `CROSS_APP_WEBHOOK_SECRET` | — | Shared HMAC secret. **Without it nothing is reported** (the boot log says so), though `/healthz` is still served. |
| `SATELLITE_APP_KEY` | `leaflet` | Series name on 2plot.ai's `/traffic`. This is the network-directory key. (The Gen-1 spelling `SATELLITE_APP_ID` is retired.) |
| `SATELLITE_TRAFFIC_URL` | `https://2plot.ai/api/satellite/traffic` | Hub endpoint override. |
| `TRAFFIC_ANALYTICS_FILE` | `visitor_analytics.json` (repo root) | Visit ledger. Production points it at the persistent disk (`/var/data/visitor_analytics.json` in render.yaml) — the hub keeps the LAST report per (app, date), so a ledger that dies with the container under-reports every deploy day. |
| `SATELLITE_REPORT_INTERVAL_S` | `3600` | Seconds between rollup POSTs. |
| `SATELLITE_REPORT_DELAY_S` | `90` | Delay before the first report after boot. |
| `ANALYTICS_GEO_LOOKUP` | `1` | `0` disables the ip-api.com fallback — behind Cloudflare the `CF-IPCountry` header already answers it. |

To exercise the payload without a secret: `python -m lib.satellite_reporter --dry-run`.

### Sign-in attribution → `POST /api/satellite/auth` (retired with Gen-1)

> **Retired in the 1.3.x instrumentation sync.** The Gen-1 analytics module
> carried a per-session sign-in beacon (deduped on the Clerk `session_id`,
> transmitting only `sha256(lowercased email)[:12]` — never an email or a
> Clerk id) that fed `/traffic` → *Where sign-ins happen*. The boilerplate's
> trio has no counterpart, so the retrofit dropped it rather than fork the
> measurement standard; the hub loses this satellite's sign-in signal until
> the trio grows one fleet-wide. The Gen-1 SPA page-view beacon
> (`/api/pageview`) went the same way — the trio counts server requests only,
> which is what makes this app's numbers comparable to every other
> satellite's.

To have the hub health-sweep this app hourly, add to **2plot.ai**:

```
PULSE_POLL_TARGETS=...,leaflet=https://leaflet.2plot.dev/healthz
```

Two things worth knowing about the numbers:

- **SPA navigations are counted.** A Dash multi-page app serves one HTML request
  per visit; every later page is a client-side route change. The browser beacons
  each one to `/api/pageview`, so sessions are not all reported as single-page.
  Bots don't run JS, so bot hits stay request-only — which is correct.
- **Definitions are copied from the hub**, not invented: the bot-UA list, the
  skip list, the `ip|md5(ua)[:8]` visitor key, the 30-minute session gap and the
  "median of multi-page sessions only" rule all mirror 2plot.ai's
  `lib/traffic_insights.py`. That is what makes this app comparable to the rest
  of the network.

### Clerk authentication (satellite of 2plot.ai)

Set **all three** of the first group to turn auth on. Anything less and the whole
auth plane stays off, every visibility tier falls open to public, and one warning
is logged.

| Variable | Example | Notes |
|---|---|---|
| `CLERK_SECRET_KEY` | `sk_live_…` | Backend SDK key. Never exposed to the client. |
| `CLERK_PUBLISHABLE_KEY` | `pk_live_…` | Embedded in the injected `<script>`. |
| `CLERK_SIGN_IN_URL` | `https://2plot.ai/sign-in` | The **primary** hosts sign-in. |
| `CLERK_SIGN_UP_URL` | `https://2plot.ai/sign-up` | |
| `CLERK_FRONTEND_API` | `https://<app>.clerk.accounts.dev` | **Required in satellite mode.** A production custom-domain instance cannot derive this from the sign-in URL. |
| `CLERK_SATELLITE_DOMAIN` | `2plot.dev` — the registered satellite, **not** the served host | Host only, no scheme. Must match the deployed domain exactly. |
| `CLERK_IS_SATELLITE` | `true` | Leave false locally — Clerk rejects satellites on `localhost`. |
| `CLERK_SATELLITE_SIGN_IN_REDIRECT` | (unset) | Optional, dash-clerk-auth ≥ 0.9.2. Absolute URL on the **primary** that Sign In navigates to, with this page in `?returnTo=`. Read by the package itself. Unset, sign-in falls back to `Clerk.redirectToSignIn()` forcing this page as the return — what this site ships today. Only set it once `2plot.ai` honours `?returnTo=`. |
| `SESSION_SECRET` | (generated) | Signs the session + `__dca_identity` cookies. Without it dash-clerk-auth uses a **public dev default**. |
| `ADMIN_EMAILS` | `a@b.com,c@d.com` | Allowlist for `/admin/control-board`. `OWNER_EMAIL` always counts. |
| `DISABLE_CLERK` | `1` | Dev kill switch — reads as "intentionally off" without touching the keys. Never set in production. |
| `ALLOW_UNGATED_ADMIN` | `1` | Lets `/admin/control-board` render without Clerk. **Never set in production.** |

> **`dash-clerk-auth` is not a dependency of this project.** The 1.0.2 build is
> not resolved from PyPI — it is vendored across the 2plot network — so a stock
> deploy has **no Clerk at all** and `clerk_enabled()` is `False` however many
> `CLERK_*` variables you set.
>
> That is safe for the documentation itself, which is public anyway. It is not
> safe for `/admin/control-board`, so that page fails **closed**: without Clerk
> it returns a 404-style response and its save callback refuses writes, rather
> than handing an open admin panel to anyone who guesses the URL.
>
> **Clerk is enabled** — `vendor/dash_clerk_auth-1.0.2.tar.gz` is committed and
> active in `requirements.txt`. One operational risk to know before debugging a
> dead site: the package registers a `[dash_hooks]` entry point that Dash
> auto-imports at **every** `Dash()` construction, so it sits in the boot path
> of the whole site whether or not Clerk is configured. Rollback is to comment
> those two lines and redeploy — `/admin/control-board` fails closed without
> Clerk, so nothing is left exposed.

**Values for this satellite** (2plot.ai on its **production** Clerk instance —
the custom domains, not the `*.accounts.dev` hosts, which belong to the dev
instance and cannot host satellites):

| Variable | Value |
|---|---|
| `CLERK_SIGN_IN_URL` | `https://accounts.2plot.ai/sign-in` |
| `CLERK_SIGN_UP_URL` | `https://accounts.2plot.ai/sign-up` |
| `CLERK_FRONTEND_API` | `https://clerk.2plot.ai` |
| `CLERK_SATELLITE_DOMAIN` | `2plot.dev` — the registered satellite, **not** the served host |
| `CLERK_IS_SATELLITE` | `true` |

All five are already literals in `render.yaml`; only `CLERK_SECRET_KEY` and
`CLERK_PUBLISHABLE_KEY` need entering in the dashboard.

### Registering the satellite on the primary — two separate lists

Easy to conflate, and each fails differently.

**1. Clerk's dashboard → Allowed subdomains.** `leaflet.2plot.dev` does NOT
need its own paid satellite domain. The dashboard's Allowed Subdomains section
accepts a subdomain belonging to *"your primary domain 2plot.ai **or satellite
domains 2plot.media, 2plot.dev, 2plot.xyz**"*, so `leaflet.2plot.dev` is covered
as a subdomain of the existing `2plot.dev` satellite.

(Clerk's published docs for this feature mention only the primary domain and
are incomplete — the dashboard text is authoritative.)

> **Enabling the toggle is restrictive.** *"Only these subdomains will be
> allowed to access the application. `www` is treated as a subdomain and must be
> added explicitly."* So every subdomain already in use must be listed, not just
> the new one. From this network's redirect whitelist that means at least
> `www.2plot.media`, `www.2plot.xyz`, `www.2plot.net` and `cast.2plot.net`
> alongside `leaflet.2plot.dev` — turning it on with only the new host listed
> would cut the others off.
>
> Note also that `2plot.net`, `2plot.me`, `2plot.world` and `2plot.shop` appear
> in `_DEFAULT_SATELLITE_ORIGINS` but not among the satellites the dashboard
> names. Either that message is abbreviated or those were never registered —
> in which case their subdomains cannot be allowlisted either.

**2. The primary's own redirect whitelist** (`CLERK_ALLOWED_REDIRECT_ORIGINS`,
read by `lib/auth.py` in the **2plotai** repo). This is *our* code, not Clerk's
dashboard, and it is applied to `Clerk.load()` on the primary. Without it the
primary refuses to redirect back here after sign-in.

> **The env var REPLACES the default list — it does not extend it.** Setting it
> to just the new origin would silently break every existing satellite. Use the
> full value:
>
> ```
> CLERK_ALLOWED_REDIRECT_ORIGINS=https://2plot.media,https://www.2plot.media,https://2plot.net,https://www.2plot.net,https://2plot.xyz,https://www.2plot.xyz,https://cast.2plot.net,https://2plot.dev,https://2plot.me,https://2plot.world,https://2plot.shop,https://leaflet.2plot.dev
> ```
>
> The alternative is a one-line addition to `_DEFAULT_SATELLITE_ORIGINS` in
> `2plotai/lib/auth.py` and a redeploy, which is less error-prone if you are not
> already overriding the list.

**Satellite fixes: now upstream.** `lib/auth.py` used to hand-apply two of them
against dash-clerk-auth 0.9.0. Both ship in the package as of 1.0.0 and the
local copies are gone:

1. clerk-js@5 reads `domain` as a **constructor** option, from the script tag's
   `data-clerk-domain` — not as a `load()` option. Without stamping it,
   `load({isSatellite: true})` throws *"a satellite application needs to specify
   a domain or a proxyUrl"*. **Fixed upstream in 0.9.1.**
2. The package bound sign-in to `Clerk.openSignIn()`, a modal on the current
   domain. On a satellite that POSTs to the satellite FAPI and 403s. **Fixed
   upstream in 0.9.2**, which navigates to the primary instead.

What `lib/auth.py` still installs is one **delegated** capture-phase listener on
`#clerk-login-button`. The package binds that id inside its `DOMContentLoaded`
handler, once — fine for the header control, which is part of the app shell, but
the sign-in card in `lib/page_visibility.py` is rendered by a page callback when
a visitor reaches an `auth`-tier page, well after that handler ran. Without
delegation its button has no listener and the click does nothing. The listener
defers to the package's own `window.dashClerkAuth.buildSatelliteRedirect()` when
`CLERK_SATELLITE_SIGN_IN_REDIRECT` is set, and otherwise makes the same
`redirectToSignIn()` call upstream does.

> Downgrading below 0.9.2 means restoring both fixes in `lib/auth.py`.

**Satellite registration is not automatic.** `leaflet.2plot.dev` must also appear
in the primary's `CLERK_ALLOWED_REDIRECT_ORIGINS` (see `lib/auth.py` in the
2plotai repo) *with a scheme* — a missing scheme silently strands users on the
primary's home page, which has bitten this network before.

### The interactive gate

| Variable | Default | What it does |
|---|---|---|
| `PAGE_DEFAULT_TIER` | `public` | Baseline tier for pages whose frontmatter sets none. **This is the flip.** |
| `PAGE_DEFAULT_VISIBILITY` | — | This service's older name for the same knob, still read. Set one, not both; `PAGE_DEFAULT_TIER` wins. |
| `LLMS_PUBLIC_DEFAULT` | unset (= open) | The second axis. `0` closes every gated page's machine twin — the phase-4 agent flip. |
| `LLMS_SMALL_TIER` / `LLMS_FULL_TIER` | `public` | Tiers for the two corpus documents, independent of the default above. |
| `PAGE_VISIBILITY_FILE` | `page_visibility.json` | Where control-board overrides persist. |

Four tiers, re-resolved on **every render and every machine fetch**, so a
toggle, a hub change or an env flip applies with no restart:

| Tier | Who gets in |
|---|---|
| `public` | Anyone. |
| `auth` | Any signed-in Clerk user. The sign-in card is the account-creation funnel. |
| `admin` | Signed in *and* allowlisted. Its `llms.txt` is never served anonymously. |
| `hidden` | Nobody. The page and its `llms.txt` return a 404-style response. |

#### Where a verdict comes from

Three inputs, resolved in `lib/access.py`:

1. **The control board's override** (`lib/page_visibility.py`, persisted to
   `/var/data`). Most local, and it wins — that is the point of a live toggle.
2. **The frontmatter registration** (`lib/page_tiers.py`), underneath it.
3. **The hub's ceiling** (`lib/hub_client.py` → `POST 2plot.dev/api/page-tiers`).
   Applied last and only ever *restricts*: this site may lock a page down
   further, never open one the network gated. Needs
   `CROSS_APP_WEBHOOK_SECRET`; without it the ceiling is simply absent.

Then, per request: `public`/`hidden` short-circuit → a local Clerk session
answers for a person in a browser → and only for a cookie-less fetch does a
`?key=` go to the hub for verification. **A signed-in reader never needs the
hub**, which is why a hub outage gates nobody who is signed in.

Two lanes, and they answer different questions. `resolve_page_access` is what a
BROWSER gets (`lib/gate_layouts.py` renders the card); `check` is what a MACHINE
fetch gets (`/<page>/llms.txt`, the crawler document, the prerender). Keys
unlock the machine lane only — a `?key=` that opened layouts would turn every
copied URL into a shareable session.

#### Fail postures — both deliberate

- **Docs fall OPEN without Clerk.** Every tier except `hidden` degrades to
  public. Documentation must never brick because a deploy forgot a credential.
- **Admin fails CLOSED.** `/admin/control-board` returns a 404-style response
  without Clerk, and its save callback refuses writes, rather than handing an
  open admin panel to whoever guesses the URL. `ALLOW_UNGATED_ADMIN=1` opens it
  for local work only.
- **A hub failure is `gated`.** Never `allow` (an outage must not publish
  restricted prose), never `deny` (an outage must not black-hole the site).

#### Per-page baselines, from the markdown frontmatter

```yaml
---
name: "Tile Selector"
endpoint: "/tile-selector"
tier: public            # optional; defaults to PAGE_DEFAULT_TIER
llms_public: true       # optional; defaults to LLMS_PUBLIC_DEFAULT
---
```

`tier:` is canonical. `visibility:` is accepted as an alias for the same four
values; setting both to different values logs a warning and `tier:` wins. One
declared value feeds both the control board's row and the network ledger, so
the board can never show a tier the site does not enforce.

#### Shipping dark, then flipping

The gate is wired unconditionally at boot (`run.py` calls
`_access.configure(force=True)`), so the verdict path runs in production while
every verdict still answers `allow`. Confirm the boot line:

```
[dash-leaflet2] interactive gate: default tier 'public', 0 non-public page(s),
machine surfaces open by default (LLMS_PUBLIC_DEFAULT), access wiring ON, hub …
```

`access wiring ON` with `default tier 'public'` is the dark launch. To flip:
set `PAGE_DEFAULT_TIER=auth` in the Render dashboard and restart. **Rollback is
the same edit in reverse** — back to `public`, restart, fully public site, no
code revert. Rehearse it once before relying on it.

`/`, `/llms-small.txt` and `/llms-full.txt` are pinned public in `run.py` and
do not move with the default: the funnel's front door and the corpus documents
are deliberate settings, never an ambient default.

#### The control board

Lives at **`/admin/control-board`**, excluded from `robots.txt` and from the
docs navbar, and gates itself twice — the layout re-checks on every render and
the save callback re-checks before writing, because a pattern-matching callback
stays callable by anyone who can POST a reconstructed component id. Without
Clerk it is hidden, not merely unstyled.

> **Persistence.** Overrides are a JSON file. `PAGE_VISIBILITY_FILE` points at
> the `/var/data` disk in production, so a toggle outlives a deploy; on an
> ephemeral filesystem it would reset with every one.

### The person→agent handoff

`GET /api/agent-key` (`lib/agent_key.py`) turns the browser's Clerk session
into a portable `?key=` for copied `llms.txt` URLs, so a link pasted into an
assistant still resolves a gated document — the assistant's fetch arrives with
no cookie. `assets/llms_copy.js` calls it lazily, on the first copy click.

- **204, no body** — anonymous, Clerk off, or the hub declined. The copy button
  falls back to the plain URL, which is what an anonymous reader gets anyway.
- **200 `{"key": "k2p_…"}`** with `Cache-Control: private, no-store`. The key is
  never embedded in page HTML, so nothing can cache it and hand it to the next
  visitor.

This satellite holds **no key material**: it cannot mint and cannot verify
offline. The hub verifies the Clerk token against Clerk's JWKS and pins
`scope=auth`, so a satellite can never mint an admin key.

## Post-deploy checklist

1. `GET /healthz` → `{"ok": true, "app": "leaflet", "version": "…",
   "base_url": "https://leaflet.2plot.dev", "reporting": true}`.
   `reporting: false` means `CROSS_APP_WEBHOOK_SECRET` is missing.
   **`base_url` coming back `http://localhost:8050` is a live incident**: the
   service has `APP_BASE_URL` or `DASH_LEAFLET2_BASE_URL` set to a loopback
   origin, so every canonical link, `og:url`, sitemap entry and llms.txt URL is
   unreachable — while the site itself renders perfectly. See the note under
   the environment table.
2. `GET /llms.txt`, `/robots.txt`, `/sitemap.xml` all 200, and the sitemap URLs
   use `leaflet.2plot.dev` (i.e. `APP_BASE_URL` is set correctly).
3. Sign in from the site — you should bounce to 2plot.ai and land **back here**,
   not on the primary's home page.
4. `/admin/control-board` shows the page table with **no** dev-mode banner.
4b. The gate's boot line reads `access wiring ON` (see "Shipping dark, then
   flipping"). With `PAGE_DEFAULT_TIER=public` that is the dark launch:
   `GET /pointer-events` serves docs, `GET /pointer-events/llms.txt` serves
   prose, `GET /api/agent-key` answers 204 signed out and 200 with
   `Cache-Control: private, no-store` signed in.
5. The 2plot.ai `/traffic` dashboard grows a `leaflet` series within one
   `SATELLITE_REPORT_INTERVAL_S`.
6. An ad slot appears in the aside on a page with a table of contents.
