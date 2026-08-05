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
  * traffic  — lib/satellite_analytics.py → 2plot.ai/api/satellite/traffic
  * auth     — lib/auth.py              → Clerk satellite of the 2plot.ai primary
  * control  — pages/control_board.py   → /admin/control-board

Every one of those is dormant without its env keys, so a plain `python run.py`
gives you the same local docs site it always did.

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
    LLMSConfig,
    RobotsConfig,
    add_llms_routes,
    mark_hidden,
    register_page_metadata,
)

from lib import auth, bulletin, network_directory, satellite_analytics
from lib.backend import get_backend_info, resolve_backend
from lib.constants import (
    APP_VERSION,
    BASE_URL,
    LEAFLET_VERSION,
    SITE_BRAND,
    SITE_DESCRIPTION,
    base_url_misconfigured,
)

# ----------------------------------------------------------------------------
# Pluggable backend (Dash 4.1+). FastAPI default so WebSocket / background
# callbacks remain available for the sim pages.
# ----------------------------------------------------------------------------
BACKEND = resolve_backend()
BACKEND_INFO = get_backend_info(BACKEND)

# DMC 2.x targets React 18.2; Dash 4 ships 18.3.1 — pin to keep DMC happy.
_dash_renderer._set_react_version("18.2.0")

print(f"[dash-leaflet2] v{APP_VERSION} on Dash {dash.__version__} · backend='{BACKEND}'")

# ----------------------------------------------------------------------------
# Clerk satellite auth. MUST run BEFORE Dash(...) — register_clerk_auth installs
# @dash.hooks callbacks that fire during app construction, so calling it later
# silently does nothing. Fully dormant without the CLERK_* keys.
# ----------------------------------------------------------------------------
CLERK_ENABLED = auth.register()
if not CLERK_ENABLED:
    print("[auth] Clerk dormant — every visibility tier falls open to public.")

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

# A hosted deploy advertising http://localhost is invisible from inside the
# container — the site renders perfectly and every published URL is dead. Say
# so at boot, where the deploy log will carry it. See lib.constants.
_base_url_problem = base_url_misconfigured()
print(f"[dash-leaflet2] base url: {BASE_URL}")
if _base_url_problem:
    print(f"[dash-leaflet2] ⚠️  {_base_url_problem}")

# ----------------------------------------------------------------------------
# 2plot.ai satellite analytics: /healthz for the hub's hourly health sweep,
# per-request + SPA page-view tracking, and the signed traffic rollup POSTed to
# https://2plot.ai/api/satellite/traffic. Dormant without
# CROSS_APP_WEBHOOK_SECRET — /healthz is served either way, which is what
# render.yaml's healthCheckPath points at.
#
# THIS STAYS AFTER add_llms_routes, and the reason is worth keeping: on the
# FastAPI backend the tracker is a Starlette http middleware, and Starlette
# makes the LAST-added middleware the outermost one. Registered first, it
# would sit inside `_bot_middleware` — which answers every crawler with
# prerendered HTML — and no crawler request would ever be counted.
#
# Flask and Quart have the opposite rule (`before_request` handlers run in
# registration order, and the first to return a response wins), so no single
# ordering can be correct for all three. They are therefore wrapped at the
# WSGI/ASGI boundary instead and do not depend on this line's position at all
# — see `_wsgi_tracker` in lib/satellite_analytics.py, which is what fixed the
# structural `bot_hits: 0` this satellite had been reporting.
# ----------------------------------------------------------------------------
satellite_analytics.register(app, BACKEND)

# ----------------------------------------------------------------------------
# Layout
# ----------------------------------------------------------------------------
from components.appshell import create_appshell  # noqa: E402  (needs the registry)

app.layout = create_appshell(dash.page_registry.values())
server = app.server


if __name__ == "__main__":
    # Host/port are env-driven so the compat-matrix harness can run several
    # Dash versions side by side without editing this file.
    app.run(
        debug=os.getenv("DASH_DEBUG", "true").lower() not in ("0", "false", "no"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8050")),
    )
