# Deployment — leaflet.2plot.dev

The documentation site ships as a Docker web service on Render, fronted by
`leaflet.2plot.dev`, and runs as a **satellite** of the 2plot network. Four
integrations attach to it, and **every one is dormant without its environment
keys** — a plain `python run.py` is just the docs.

| Integration | Module | Talks to | Dormant unless |
|---|---|---|---|
| Ad network | `lib/ad_client.py` | `2plot.dev/api/ad-network/serve` | ad server reachable |
| Traffic analytics | `lib/satellite_analytics.py` | `2plot.ai/api/satellite/traffic` | `CROSS_APP_WEBHOOK_SECRET` |
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
| `DASH_LEAFLET2_BASE_URL` | `https://leaflet.2plot.dev` | Canonical origin for `sitemap.xml` and `llms.txt`. |
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

| Variable | Default | What it does |
|---|---|---|
| `CROSS_APP_WEBHOOK_SECRET` | — | Shared HMAC secret. **Without it nothing is reported**, though `/healthz` is still served. |
| `SATELLITE_APP_ID` | `leaflet` | Series name on 2plot.ai's `/traffic`. This is the network-directory key. |
| `SATELLITE_HUB_URL` | `https://2plot.ai` | Hub origin. |
| `SATELLITE_ANALYTICS_FILE` | `satellite_traffic.jsonl` | Hit ledger. Put it on a persistent disk to survive evictions. |
| `SATELLITE_REPORT_INTERVAL_S` | `1800` | Minimum seconds between rollup POSTs. |
| `SATELLITE_ANALYTICS_DRY_RUN` | — | `1` → track and log rollups, never POST. The smoke test sets this. |

### Sign-in attribution → `POST /api/satellite/auth`

2plot.ai is the Clerk primary, so every account is created there — but on a
satellite domain the correct call is `Clerk.redirectToSignIn()`, which routes
the visitor through Clerk's hosted pages and back **without ever touching a hub
URL**. The hub therefore cannot tell that the sign-in happened here. This beacon
is the only signal that attributes it to this app, and `/traffic` → *Where
sign-ins happen* is what it feeds.

One beacon per session observed becoming authenticated — deduped on the Clerk
`session_id`, with an `O_EXCL` claim file so several gunicorn workers don't each
send one. Same HMAC headers as the traffic rollup, and best-effort throughout: a
failed beacon must never break a sign-in.

**Nothing identifying is ever transmitted.** `who` is
`sha256(lowercased email)[:12]` — the network convention, matching the wallet
provisioner. The email is hashed the moment it is read, and the `session_id` is
used only as a local dedupe key. Verified end-to-end against the hub's own
`verify_and_record_auth` (HTTP 200), with an explicit assertion that the email,
the Clerk user id and the session id appear nowhere in the request body:

```json
{"app":"leaflet","event":"sign_in","who":"85f85c0071e4",
 "path":"/tile-selector","domain":"leaflet.2plot.dev"}
```

It rides `clerk-auth-store`, so it is registered only when Clerk is actually
enabled — without Clerk that store never exists and the callback could not fire.

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

> **`dash-clerk-auth` is not a dependency of this project.** The 1.0.0 build is
> not resolved from PyPI — it is vendored across the 2plot network — so a stock
> deploy has **no Clerk at all** and `clerk_enabled()` is `False` however many
> `CLERK_*` variables you set.
>
> That is safe for the documentation itself, which is public anyway. It is not
> safe for `/admin/control-board`, so that page fails **closed**: without Clerk
> it returns a 404-style response and its save callback refuses writes, rather
> than handing an open admin panel to anyone who guesses the URL.
>
> **Clerk is enabled** — `vendor/dash_clerk_auth-1.0.0.tar.gz` is committed and
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

### Page visibility

| Variable | Default | What it does |
|---|---|---|
| `PAGE_DEFAULT_VISIBILITY` | `public` | Baseline tier for pages whose frontmatter sets none. |
| `PAGE_VISIBILITY_FILE` | `page_visibility.json` | Where control-board overrides persist. |

Four tiers, re-checked on **every page render** so a toggle applies with no
restart:

| Tier | Who gets in |
|---|---|
| `public` | Anyone. |
| `auth` | Any signed-in Clerk user. The sign-in card is the account-creation funnel. |
| `admin` | Signed in *and* allowlisted. Its `llms.txt` is never served anonymously. |
| `hidden` | Nobody. The page and its `llms.txt` return a 404-style response. |

Per-page baselines come from the markdown frontmatter:

```yaml
---
name: "Tile Selector"
endpoint: "/tile-selector"
visibility: public      # optional; defaults to PAGE_DEFAULT_VISIBILITY
llms_public: true       # optional; defaults to true
---
```

The board lives at **`/admin/control-board`**. It is excluded from `robots.txt`
and from the docs navbar. With Clerk off it renders ungated behind a dev-mode
warning banner — so **do not deploy publicly without the Clerk keys** if any page
is meant to be gated.

> **Persistence caveat.** Overrides are a JSON file on the container filesystem.
> On Render's free tier that is ephemeral: changes survive until the next deploy.
> Point `PAGE_VISIBILITY_FILE` at a persistent disk if they must outlive one.

## Post-deploy checklist

1. `GET /healthz` → `{"ok": true, "app": "leaflet", "version": "…", "reporting": true}`.
   `reporting: false` means `CROSS_APP_WEBHOOK_SECRET` is missing.
2. `GET /llms.txt`, `/robots.txt`, `/sitemap.xml` all 200, and the sitemap URLs
   use `leaflet.2plot.dev` (i.e. `DASH_LEAFLET2_BASE_URL` is set).
3. Sign in from the site — you should bounce to 2plot.ai and land **back here**,
   not on the primary's home page.
4. `/admin/control-board` shows the page table with **no** dev-mode banner.
5. The 2plot.ai `/traffic` dashboard grows a `leaflet` series within one
   `SATELLITE_REPORT_INTERVAL_S`.
6. An ad slot appears in the aside on a page with a table of contents.
