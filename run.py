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
    register_page_metadata,
)

from lib import auth, satellite_analytics
from lib.backend import get_backend_info, resolve_backend
from lib.constants import APP_VERSION, BASE_URL, LEAFLET_VERSION, SITE_TITLE

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
app = Dash(
    __name__,
    use_pages=True,
    backend=BACKEND,
    suppress_callback_exceptions=True,
    prevent_initial_callbacks=True,
    update_title=None,
    title=SITE_TITLE,
    index_string=open("templates/index.html").read(),
)
app._backend_info = BACKEND_INFO

# Post-construction Clerk wiring (sessions, /api/auth/*, request identity).
auth.configure_app(app)

# ----------------------------------------------------------------------------
# AI/LLM & SEO configuration
# ----------------------------------------------------------------------------
app._base_url = BASE_URL
app._robots_config = RobotsConfig(
    block_ai_training=False,
    allow_ai_search=True,
    allow_traditional=True,
    crawl_delay=10,
    # The admin control board is not documentation — keep it out of the index.
    disallowed_paths=["/admin/"],
)

register_page_metadata(
    path="/",
    name="dash-leaflet2",
    description=(
        "Leaflet 2 (alpha) on Dash 4 — a generation-ahead mapping component "
        "library that wraps Leaflet 2 core directly, without react-leaflet."
    ),
)

# ----------------------------------------------------------------------------
# Pages: pages/markdown.py walks docs/**/*.md and calls dash.register_page
# on each. Dash's use_pages=True auto-imports anything under pages/ during
# Dash(...) construction, so we DON'T re-import it here — doing so caused
# every page to register twice (visible as DMC Select "Duplicate options
# are not supported" errors when the search dropdown re-rendered).
# ----------------------------------------------------------------------------

# Wire up /llms.txt, /<page>/llms.txt, /robots.txt, /sitemap.xml + bot
# middleware. dash-improve-my-llms 2.0 auto-detects the active backend
# (flask / fastapi / quart) and dispatches to the matching adapter, so we
# no longer have to gate this on the backend. Per-page prose is registered
# through lib.page_visibility.register_llms_doc (see pages/markdown.py) so the
# control board's llms.txt switch can swap a page's body for a stub.
add_llms_routes(app, LLMSConfig(warn_missing_llms_doc=False))

# ----------------------------------------------------------------------------
# 2plot.ai satellite analytics: /healthz for the hub's hourly health sweep,
# per-request + SPA page-view tracking, and the signed traffic rollup POSTed to
# https://2plot.ai/api/satellite/traffic. Dormant without
# CROSS_APP_WEBHOOK_SECRET — /healthz is served either way, which is what
# render.yaml's healthCheckPath points at.
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
