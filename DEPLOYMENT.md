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
| `CLERK_SATELLITE_DOMAIN` | `leaflet.2plot.dev` | Host only, no scheme. Must match the deployed domain exactly. |
| `CLERK_IS_SATELLITE` | `true` | Leave false locally — Clerk rejects satellites on `localhost`. |
| `SESSION_SECRET` | (generated) | Signs the session + `__dca_identity` cookies. Without it dash-clerk-auth uses a **public dev default**. |
| `ADMIN_EMAILS` | `a@b.com,c@d.com` | Allowlist for `/admin/control-board`. `OWNER_EMAIL` always counts. |
| `DISABLE_CLERK` | `1` | Dev kill switch — reads as "intentionally off" without touching the keys. Never set in production. |
| `ALLOW_UNGATED_ADMIN` | `1` | Lets `/admin/control-board` render without Clerk. **Never set in production.** |

> **`dash-clerk-auth` is not a dependency of this project.** The 0.9.0 build
> carrying the satellite fixes is not on PyPI — it is vendored across the 2plot
> network — so a stock deploy has **no Clerk at all** and `clerk_enabled()` is
> `False` however many `CLERK_*` variables you set.
>
> That is safe for the documentation itself, which is public anyway. It is not
> safe for `/admin/control-board`, so that page fails **closed**: without Clerk
> it returns a 404-style response and its save callback refuses writes, rather
> than handing an open admin panel to anyone who guesses the URL.
>
> The tarball is already committed to `vendor/`; `requirements.txt` has the
> line **commented out**. Uncomment it (and `clerk-backend-api>=5.0.0,<6`) to
> enable Clerk. Two reasons it is off by default:
>
> 1. The package registers a `[dash_hooks]` entry point that Dash auto-imports
>    at **every** `Dash()` construction, so installing it puts Clerk in the boot
>    path of the whole site — a broken transitive dependency would take down the
>    documentation, not just sign-in.
> 2. **Clerk satellite domains need a production Clerk instance.** The 2plot.ai
>    primary is currently a *dev* instance — `pk_test` key, frontend API on
>    `fine-rhino-96.clerk.accounts.dev`. Dev instances do not support
>    multi-domain, so `CLERK_IS_SATELLITE=true` against it cannot work.
>
> **Values for this satellite, once the primary is on production Clerk:**
>
> | Variable | Value |
> |---|---|
> | `CLERK_SIGN_IN_URL` | the primary's sign-in URL (dev today: `https://fine-rhino-96.accounts.dev/sign-in`) |
> | `CLERK_FRONTEND_API` | the primary's frontend API (dev today: `https://fine-rhino-96.clerk.accounts.dev`) |
> | `CLERK_SATELLITE_DOMAIN` | `leaflet.2plot.dev` |
> | `CLERK_IS_SATELLITE` | `true` |
>
> `https://leaflet.2plot.dev` must also be added to the primary's
> `CLERK_ALLOWED_REDIRECT_ORIGINS`. It is **not** there today — the list has
> `https://2plot.dev`, and a subdomain is a different origin.

**Two satellite fixes** are applied in `lib/auth.py` for dash-clerk-auth 0.9.0.
They are the difference between a working satellite and a broken one:

1. clerk-js@5 reads `domain` as a **constructor** option, from the script tag's
   `data-clerk-domain` — not as a `load()` option. Without stamping it,
   `load({isSatellite: true})` throws *"a satellite application needs to specify
   a domain or a proxyUrl"*.
2. The package binds sign-in to `Clerk.openSignIn()`, a modal on the current
   domain. On a satellite that POSTs to the satellite FAPI and 403s. We intercept
   the click in the capture phase and call `redirectToSignIn()` with
   `signInForceRedirectUrl` set to this page, so the primary sends the user back
   here rather than to its own home.

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
