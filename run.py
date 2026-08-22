"""
dash-leaflet2 documentation site — Leaflet 2 on Dash 4, markdown-driven.

Shell is the dash-documentation-boilerplate's AppShell (DMC header + navbar +
markdown-loaded docs). Each `docs/<slug>/<slug>.md` registers as a Dash page;
the body is rendered by markdown2dash and its `.. exec::docs.<slug>.example`
directive imports the corresponding `example.py` to embed the live demo.

The showcase pages live in `docs/<slug>/example.py` with their
`dash.register_page(...)` stripped — the markdown loader is the single source
of routing. The hooks-driven Leaflet 2 CDN delivery lives here at the app level
so the JS showcase pages and the compiled `dl2.*` pages both work.

This is the PUBLIC mirror of the dash-leaflet2 project, deployed at
https://leaflet.2plot.dev as a 2plot network satellite:

  * ads      — lib/ad_client.py         → 2plot.dev/api/ad-network/serve
  * traffic  — lib/analytics_tracker.py (per-request ledger) +
               lib/traffic_rollup.py (the hub's own daily definitions) +
               lib/satellite_reporter.py → 2plot.ai/api/satellite/traffic
  * auth     — lib/auth.py              → Clerk satellite of the 2plot.ai primary
  * gate     — lib/access.py (+ page_tiers / hub_client / gate_layouts)
                                        → who may read which page
  * control  — pages/control_board.py   → /admin/control-board

Every one of those is dormant without its env keys, so a plain `python run.py`
gives you the same local docs site it always did.

The gate is wired unconditionally (`_access.configure(force=True)` below) and
ships DARK: with PAGE_DEFAULT_TIER=public every verdict answers `allow`, so the
whole verdict path — including the prerender's use of it — is exercised in
production before the flip that turns it on. Flipping that one environment
variable to `auth` gates the site; flipping it back is the rollback. Read
lib/access.py for the policy and DEPLOYMENT.md for the operational half.

Run:
    python run.py                          # FastAPI backend (default)
    DASH_BACKEND=flask python run.py       # Flask fallback
    # open http://127.0.0.1:8050
"""

import os

from dotenv import load_dotenv

# .env loads MUI_PRO_API_KEY (TreeViewPro on the /tile-layers-pro page), the
# CLERK_* satellite keys, CROSS_APP_WEBHOOK_SECRET and anything else env-driven
# before Dash imports run.
load_dotenv()

import dash
from dash import Dash, _dash_renderer, hooks

# AI/LLM Integration & SEO via dash-improve-my-llms.
from dash_improve_my_llms import (
    __version__ as LLMS_PKG_VERSION,
    LLMSConfig,
    RobotsConfig,
    add_llms_routes,
    mark_hidden,
    register_page_metadata,
)

from lib import auth, bulletin, network_directory
from lib import hub_client as _hub_client
from lib.analytics_tracker import tracker
from lib.backend import get_backend_info, resolve_backend
from lib.constants import (
    APP_VERSION,
    BASE_URL,
    LEAFLET_VERSION,
    SITE_BRAND,
    SITE_DESCRIPTION,
    require_owned_base_url,
)

# ----------------------------------------------------------------------------
# Pluggable backend (Dash 4.1+). FastAPI default so WebSocket / background
# callbacks remain available for the sim pages.
# ----------------------------------------------------------------------------
BACKEND = resolve_backend()
BACKEND_INFO = get_backend_info(BACKEND)

# DMC 2.x targets React 18.2; Dash 4 ships 18.3.1 — pin to keep DMC happy.
_dash_renderer._set_react_version("18.2.0")

# The dash-improve-my-llms version is on this line because a deploy once
# silently kept an old one. The Dockerfile caches the dependency layer on
# requirements.txt's bytes, so a commit touching only lib/ never re-resolves
# the floor — the container came up on 2.6.0 with the pin already saying it
# was fine, and the only way anyone found out was by fetching the live HTML
# and noticing the prerender still carried `hidden`. A version the boot log
# states is a version a deploy check can read in one glance.
print(
    f"[dash-leaflet2] v{APP_VERSION} on Dash {dash.__version__} "
    f"(dash-improve-my-llms {LLMS_PKG_VERSION}) · backend='{BACKEND}'"
)

# ----------------------------------------------------------------------------
# Clerk satellite auth. MUST run BEFORE Dash(...) — register_clerk_auth installs
# @dash.hooks callbacks that fire during app construction, so calling it later
# silently does nothing. Fully dormant without the CLERK_* keys.
# ----------------------------------------------------------------------------
CLERK_ENABLED = auth.register()
if not CLERK_ENABLED:
    # Precisely: every DOCS tier falls open, because documentation must not
    # brick over a missing credential. Admin surfaces do not — they gate on
    # `auth.admin_access_open()` and stay closed. See lib/access.py.
    print("[auth] Clerk dormant — docs tiers fall open to public; admin stays closed.")

# ----------------------------------------------------------------------------
# Leaflet 2 alpha delivery via dash.hooks — the same no-build-step contract
# the showcase pages rely on. The compiled `dl2.*` components bundle their
# own Leaflet 2 in UMD scope, so these hooks don't conflict with them.
#
# Note: the version string MUST be "2.0.0-alpha.1" WITH the dot — the
# dotless form 404s on unpkg. window.leaflet (NOT window.L) is the global.
# ----------------------------------------------------------------------------
hooks.stylesheet([
    {
        "external_url": f"https://unpkg.com/leaflet@{LEAFLET_VERSION}/dist/leaflet.css",
        "external_only": True,
    }
])
hooks.script([
    {
        "external_url": f"https://unpkg.com/leaflet@{LEAFLET_VERSION}/dist/leaflet-global.js",
        "external_only": True,
    }
])
# Iconify web component for the Emoji/Iconify markers page.
hooks.script([
    {
        "external_url": "https://unpkg.com/iconify-icon@3.0.2/dist/iconify-icon.min.js",
        "external_only": True,
    }
])

# ----------------------------------------------------------------------------
# Dash app
# ----------------------------------------------------------------------------
_dash_kwargs = dict(
    use_pages=True,
    suppress_callback_exceptions=True,
    prevent_initial_callbacks=True,
    update_title=None,
    title=SITE_BRAND,
    index_string=open("templates/index.html").read(),
)

# `backend=` is Dash 4.2+, NOT 4.1 as its own release notes imply — verified
# against two separate 4.1.0 installs, where `Dash()` has no such parameter and
# raises TypeError. The dash_leaflet2 PACKAGE never touches it (it needs only
# `dash>=4.1`), so this fallback is what lets the documentation site keep
# running on the package's own support floor instead of quietly raising it.
try:
    app = Dash(__name__, backend=BACKEND, **_dash_kwargs)
except TypeError:
    print(
        f"[dash-leaflet2] Dash {dash.__version__} has no `backend=` parameter "
        "(added in 4.2) — falling back to the bundled Flask backend. The async "
        "backends need Dash 4.2 or newer."
    )
    BACKEND = "flask"
    BACKEND_INFO = get_backend_info(BACKEND)
    app = Dash(__name__, **_dash_kwargs)

app._backend_info = BACKEND_INFO

# Post-construction Clerk wiring (sessions, /api/auth/*, request identity).
auth.configure_app(app)

# ----------------------------------------------------------------------------
# AI/LLM & SEO configuration
# ----------------------------------------------------------------------------
app._base_url = BASE_URL
app._robots_config = RobotsConfig(
    # DELIBERATE open posture, reviewed against dash-improve-my-llms 2.3.3.
    #
    # 2.3.3 makes `True` safe — it blocks the real training crawlers (GPTBot,
    # ClaudeBot, CCBot) while still allowing Claude-User, Claude-SearchBot and
    # ChatGPT-User, so the old reason to run `False` (blocking broke claude.ai
    # fetches through the legacy aliases) is gone. We stay `False` anyway,
    # because for MIT-licensed component documentation being in the training
    # corpus is the point: it is how a model recommends this library to someone
    # who never visits the site. Flip to `True` if that calculus changes.
    #
    # Note this diverges from the fleet fingerprint in
    # handoff/existing_subdomains.md, whose verification expects
    # `ClaudeBot -> Disallow`. The divergence is intentional, not drift.
    block_ai_training=False,
    allow_ai_search=True,
    allow_traditional=True,
    crawl_delay=10,
    # The admin control board is not documentation — keep it out of the index.
    disallowed_paths=["/admin/"],
)

# The home page's registered `name` is this site's published identity, not a
# nav label: dash-improve-my-llms 2.3.4 resolves it through `resolve_site_title`
# into the /llms.txt H1, og:title and the llms viewer's brand chip. It must be
# SITE_BRAND and nothing else — docs/home/home.md registers the page as "Home",
# which `resolve_site_title` SKIPS as generic, so without this call the site
# would fall through to `app.title` and, on a pre-2.3.4 artifact, to a bare
# "Dash". `register_page_metadata` MERGES (2.2.0+), so this refines the entry
# the markdown loader created without touching the prose it registered.
register_page_metadata(
    path="/",
    name=SITE_BRAND,
    description=SITE_DESCRIPTION,
)

# ----------------------------------------------------------------------------
# Pages: pages/markdown.py walks docs/**/*.md and calls dash.register_page
# on each. Dash's use_pages=True auto-imports anything under pages/ during
# Dash(...) construction, so we DON'T re-import it here — doing so caused
# every page to register twice (visible as DMC Select "Duplicate options
# are not supported" errors when the search dropdown re-rendered).
# ----------------------------------------------------------------------------

# Cross-host network directory. A sitemap is scoped to its own origin by
# design, so nothing in this site's markup would otherwise say the other 2plot
# hosts exist — an agent landing here sees one library and no ecosystem. This
# emits <link rel="related"> tags, a "## Network" section in /llms.txt, and
# followed links in the prerendered body. Must run BEFORE add_llms_routes.
#
# The peer list is kept in one place (copied verbatim from the boilerplate) and
# self-excludes by URL, so there is nothing app-specific to edit here — editing
# it per repo is how twelve copies drift apart.
network_directory.apply(BASE_URL)

# /admin/control-board is an admin surface, not documentation. It is the one
# registered page with no llms.txt prose, so it must be marked hidden BEFORE
# add_llms_routes — otherwise it is the sole reason the missing-prose warning
# below can never reach zero. mark_hidden also keeps it out of the sitemap and
# out of /llms.txt, which matches the robots `disallowed_paths` above.
mark_hidden("/admin/control-board")

# /healthz for the hub's hourly health sweep and render.yaml's
# healthCheckPath. Registered BEFORE add_llms_routes so the package's
# catch-all routing can never shadow it on the ASGI backends; served with or
# without a webhook secret, which is what makes it a valid liveness probe.
from lib.health import register_health_route  # noqa: E402

register_health_route(app, BACKEND)

# ============================================================================
# Analytics tracking (Flask / Quart) — MUST be registered BEFORE
# add_llms_routes. (Mirrors the boilerplate's run.py.)
#
# `before_request` hooks run in registration order, and the package's
# `_bot_middleware` short-circuits AI-search crawlers (ClaudeBot, ChatGPT-User,
# PerplexityBot, ...) with its own response. Registered after it, this hook
# never runs for exactly the bot traffic a docs site most wants counted, and
# the `bot_hits` we report to 2plot.ai would be quietly too low — the
# structural `bot_hits: 0` this satellite once shipped.
#
# FastAPI is the mirror image and is wired further down: Starlette runs the
# LAST-added middleware outermost, so ours goes on after add_llms_routes.
# ============================================================================

if BACKEND == "flask":
    from flask import request as _flask_request

    @app.server.before_request
    def track_visitor():
        """Track visitor analytics before each request."""
        try:
            # Headers are passed so the tracker can read the REAL client IP
            # and country from the proxy/CDN (behind Render or Cloudflare,
            # remote_addr is the proxy — every visitor would look like one).
            tracker.track_visit(
                _flask_request.path,
                _flask_request.headers.get('User-Agent', ''),
                _flask_request.remote_addr,
                headers=dict(_flask_request.headers),
            )
        except Exception:
            pass

elif BACKEND == "quart":
    from quart import request as _quart_request

    @app.server.before_request
    async def track_visitor():
        """Track visitor analytics before each request (Quart)."""
        try:
            tracker.track_visit(
                _quart_request.path,
                _quart_request.headers.get('User-Agent', ''),
                _quart_request.remote_addr,
                headers=dict(_quart_request.headers),
            )
        except Exception:
            pass

# ============================================================================
# Access control. Reads the tiers the pages just declared, so it runs after
# they are registered and before the routes are attached. The policy and its
# reasoning live in lib/access.py; lib/page_visibility.py keeps the live
# control-board overrides it reads first.
# ============================================================================

from lib import access as _access  # noqa: E402
from lib import page_tiers as _page_tiers  # noqa: E402
from lib import page_visibility as _page_visibility  # noqa: E402

# Tiered corpus documents (dash-improve-my-llms >= 2.4.0). Pseudo-paths:
# they never enter dash.page_registry, so they cannot leak into listings —
# registering them here lets this satellite tier its compact briefing and
# full corpus via env (LLMS_SMALL_TIER / LLMS_FULL_TIER), and the hub can
# tighten either network-wide through its page-tier ceilings with no redeploy
# here. The explicit `or "public"` matters: unset, these would inherit
# PAGE_DEFAULT_TIER, so flipping that env to gate the *interactive* site would
# silently gate the corpus documents too. Their tier is always a deliberate
# setting, never an ambient default.
_page_tiers.register("/llms-small.txt",
                     os.environ.get("LLMS_SMALL_TIER") or "public")
_page_tiers.register("/llms-full.txt",
                     os.environ.get("LLMS_FULL_TIER") or "public")

# The funnel's front door stays public, always. docs/home/home.md declares no
# tier, so under PAGE_DEFAULT_TIER=auth the landing page would inherit the
# gate and a signed-out visitor would meet a sign-in card before they had any
# reason to want an account. Pinned on BOTH ledgers so the control board shows
# what the site enforces; an operator can still override it from the board.
_page_tiers.register("/", "public")
_page_visibility.pin_default("/", "public")

# force=True, unconditionally — the deviation from the boilerplate, and the
# whole point of shipping dark. With every tier still public the auto-detect
# would skip the wiring entirely, so the gate would go live in the same change
# that first exercises it. Wiring it now means the verdict path, the gate
# document and the prerender's use of the check are all running (and
# answering `allow`) before PAGE_DEFAULT_TIER flips, and the flip is then an
# environment change against code that has been serving for a week.
ACCESS_ENABLED = _access.configure(force=True)

# Wire up /llms.txt, /<page>/llms.txt, /robots.txt, /sitemap.xml + bot
# middleware. dash-improve-my-llms auto-detects the active backend
# (flask / fastapi / quart) and dispatches to the matching adapter, so we
# no longer have to gate this on the backend. Per-page prose is registered
# through lib.page_visibility.register_llms_doc (see pages/markdown.py) so the
# control board's llms.txt switch can swap a page's body for a stub.
#
# warn_missing_llms_doc is deliberately TRUE. It was silenced while the home
# page still lost its prose to the assign-semantics bug in 2.0; 2.2.0 made
# register_page_metadata MERGE, so every page now keeps the llms_doc the
# markdown loader gave it and the warning should stay at zero. If it starts
# firing, a page has genuinely lost its prose — which is worth hearing about.
add_llms_routes(app, LLMSConfig(warn_missing_llms_doc=True))

# The hub's announcement feed, rendered in the header of this site's llms.txt
# viewer. Opt-in: with NETWORK_BULLETIN_URL unset the feature is simply off and
# the viewer still renders, so the failure mode is an announcement that never
# appears — which nobody notices.
#
# Hence a function that RETURNS whether it wired, and a boot line that says so.
# The boilerplate shipped four commented-out lines here for weeks, against a
# hub endpoint that was already serving, and the only symptom was silence. An
# unwired host still renders both banner panels; the tell is one generic tip
# where the hub publishes two.
print(
    "[dash-leaflet2] network bulletin: "
    + (f"wired -> {bulletin.url()}" if bulletin.configure()
       else "off (NETWORK_BULLETIN_URL unset)")
)

# A hosted deploy advertising the wrong origin is invisible from inside the
# container — the site renders perfectly and every published URL is dead or
# points at another host. The old check here only WARNED, one line into a wall
# of boot output; the fleet standard is the boilerplate's hard guard, which
# refuses to boot on Render without an owned APP_BASE_URL. See lib.constants.
require_owned_base_url()
print(f"[dash-leaflet2] base url: {BASE_URL}")

# ----------------------------------------------------------------------------
# Layout
# ----------------------------------------------------------------------------
from components.appshell import create_appshell  # noqa: E402  (needs the registry)

app.layout = create_appshell(dash.page_registry.values())
server = app.server

# ============================================================================
# The person->agent handoff: /api/agent-key turns the browser's Clerk session
# into a portable ?key= for copied llms.txt URLs (lib/agent_key.py, consumed
# by assets/llms_copy.js on the first copy click). 204 for everyone until
# Clerk AND the hub are both configured, so it is safe to mount always.
# ============================================================================

from lib.agent_key import register_agent_key_route  # noqa: E402

register_agent_key_route(app, BACKEND)

# One line, because every part of this is env-driven and invisible from
# inside the container. A dark launch that quietly failed to wire looks
# exactly like a dark launch that worked.
_non_public = sum(1 for t in _page_tiers.registered().values() if t != "public")
print(
    "[dash-leaflet2] interactive gate: default tier "
    f"'{_page_tiers._default_tier()}', {_non_public} non-public page(s), "
    "machine surfaces "
    f"{'GATED' if not _page_tiers.get_llms_public('/__probe__') else 'open'} "
    f"by default (LLMS_PUBLIC_DEFAULT), access wiring "
    f"{'ON' if ACCESS_ENABLED else 'off'}, hub "
    f"{'reachable' if _hub_client.enabled() else 'off (no CROSS_APP_WEBHOOK_SECRET)'}."
)

# ============================================================================
# Analytics tracking (FastAPI) — added LAST on purpose.
# Starlette runs the most recently added middleware outermost, so registering
# here (after add_llms_routes) puts the tracker in front of the package's bot
# middleware and every request gets counted — including the crawler traffic
# `_bot_middleware` answers itself, which is exactly the traffic a docs site
# most wants counted (the structural `bot_hits: 0` this satellite once
# reported). The Flask/Quart hooks are the mirror image and live above,
# BEFORE add_llms_routes.
# ============================================================================

if BACKEND == "fastapi":
    from lib.asgi_middleware import register_asgi_middleware  # noqa: E402

    register_asgi_middleware(app)

# ============================================================================
# Network analytics — hourly signed rollup POSTed to 2plot.ai so the hub's
# owner-only /traffic dashboard can chart this app alongside the network.
# Contract: 2plotai/docs/network/satellite-analytics.md.
# No-op unless CROSS_APP_WEBHOOK_SECRET is set — and it SAYS so at boot,
# which is the line the fleet's acceptance check reads.
# ============================================================================

from lib.satellite_reporter import start_reporter  # noqa: E402

start_reporter()


if __name__ == "__main__":
    # Host/port are env-driven so the compat-matrix harness can run several
    # Dash versions side by side without editing this file.
    app.run(
        debug=os.getenv("DASH_DEBUG", "true").lower() not in ("0", "false", "no"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8050")),
    )
