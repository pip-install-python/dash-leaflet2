import os

PAGE_TITLE_PREFIX = "dash-leaflet2 | "
PRIMARY_COLOR = "green"

# Keep in step with pyproject.toml and package.json when cutting a release.
APP_VERSION = "0.2.1"
LEAFLET_VERSION = "2.0.0-alpha.1"

# ---------------------------------------------------------------------------
# Site identity — one string, every surface
# ---------------------------------------------------------------------------
# The network standard (2plot.ai, 2plot.dev and the documentation boilerplate
# all ship it): a site states what it is, in the same words, on every surface
# an agent or a reader can reach. The surfaces this brand has to reach, and
# what serves each:
#
#   Dash(title=SITE_BRAND)              -> <title>, and the fallback identity
#   register_page_metadata(path="/",    -> the /llms.txt H1 and the llms
#       name=SITE_BRAND)                   viewer's brand chip, both via
#                                          dash-improve-my-llms 2.3.4's
#                                          `resolve_site_title`
#   docs/home/home.md's opening `# `     -> the home page's own prose
#
# tests/test_site_identity.py pins all of them to this constant, because the
# failure is silent: `resolve_site_title` SKIPS generic candidates ("Home",
# "Index", Dash's default "Dash") rather than publishing them, so a site that
# never states its identity falls through to whatever is left and nothing
# looks broken. This host was one candidate away from that — docs/home/home.md
# is registered as "Home", which is on the generic list.
#
# Naming rules, from the network standard:
#   - the PACKAGE NAME belongs in the description, not in the brand;
#   - "Pip Install Python" is the byline (who made it), never the site name.
SITE_BRAND = "dash-leaflet2 — Leaflet 2 maps for Dash"

SITE_DESCRIPTION = (
    "dash-leaflet2 — Leaflet 2 (alpha) mapping components for Plotly Dash 4. "
    "Wraps Leaflet 2 core directly instead of react-leaflet, exposing unified "
    "Pointer Events, BlanketOverlay canvas/WebGL layers, ES6-class "
    "subclassing, ResizeObserver sizing and map rotation as Dash components. "
    "By Pip Install Python."
)

# Public origin, used for canonical URLs, the sitemap and llms.txt. Override per
# deployment; the default is the 2plot network subdomain this site ships to.
BASE_URL = os.environ.get("DASH_LEAFLET2_BASE_URL", "https://leaflet.2plot.dev").rstrip("/")

# ---------------------------------------------------------------------------
# The social card
# ---------------------------------------------------------------------------
# Served from the 2plot CDN rather than this app's own /assets, deliberately:
# a link preview is fetched by Facebook, Twitter/X, Slack, Discord and
# LinkedIn — none of which wait for a free-tier container to wake from sleep.
# The CDN answers immediately whether or not this site is cold.
#
# THE BUG THIS FIXES: Dash builds `og:image` and `twitter:image` for every page
# from `register_page(image=...)` / `image_url=...`, and emits `content=""`
# when it finds neither (dash/_pages.py). This site had no brand image, so
# every page shipped an EMPTY og:image — which unfurls worse than having no
# tag at all, because scrapers treat the empty value as the declared image and
# render a blank card. `image_url` takes an absolute URL and wins over the
# assets-derived one, so passing it at `register_page` time fixes every page at
# the source instead of fighting tag order inside templates/index.html.
#
# 1280x515 (2.49:1) rather than the 1.91:1 the card specs ask for, so previews
# centre-crop roughly 100px off the top and bottom. The wordmark sits in the
# middle band and survives the crop.
OG_IMAGE_URL = "https://cdn.2plot.ai/github_assets/leaflet.2plot.dev.png"
OG_IMAGE_WIDTH = 1280
OG_IMAGE_HEIGHT = 515
OG_IMAGE_ALT = "dash-leaflet2 — Leaflet 2 maps for Dash, at leaflet.2plot.dev"

# ---------------------------------------------------------------------------
# The network's internal-traffic contract
# ---------------------------------------------------------------------------
# The analytics point of truth is https://2plot.ai/docs/satellite-analytics
# ("Internal traffic"): any request whose User-Agent contains
# INTERNAL_UA_TOKEN is 2plot network machinery talking to itself — the hub's
# hourly health sweep, CI smoke batteries, the 4x-daily heartbeat, this app's
# own server-to-server calls to the hub. It is counted NOWHERE.
#
# Two halves, and both are required for the contract to hold:
#
#   inbound  — every tracker drops a token-carrying request at WRITE time,
#              before device detection and before bot classification, so it
#              never reaches the ledger the rollup is built from;
#   outbound — every call this host makes to another network host sends
#              INTERNAL_UA, so the far side can apply the same rule.
#
# The outbound half is the one that was missing here. lib/ad_client.py fetched
# a campaign from 2plot.dev on EVERY docs page view, arriving as
# `python-requests/2.x` — which the hub's own tracker classifies as a bot, so
# this satellite's readers were inflating 2plot.dev's bot_hits. The signed
# rollup POST in lib/satellite_analytics.py had the same shape.
#
# The token string must stay byte-identical across the network; it mirrors
# 2plotai/lib/constants.py, pip-docs+/lib/constants.py and the boilerplate's.
INTERNAL_UA_TOKEN = "2plot-internal"
INTERNAL_UA = "2plot-internal/1.0 (+https://2plot.ai/docs/satellite-analytics)"


def internal_ua(caller: str = "") -> str:
    """``INTERNAL_UA`` with a caller suffix, e.g. ``"ad-client"``.

    The suffix is for reading logs on the far side; only the token matters to
    the contract, and it stays intact whatever the suffix says.
    """
    caller = (caller or "").strip()
    return f"{INTERNAL_UA} {caller}" if caller else INTERNAL_UA


# 2plot network links, surfaced in the README and the docs footer/header.
GITHUB_URL = "https://github.com/pip-install-python/dash-leaflet2"
DISCORD_URL = "https://discord.gg/WEnZR35mrK"
YOUTUBE_URL = "https://www.youtube.com/channel/UC6Bmo0t0ZUpU_xKBYW0bJuQ"

# This will be populated by pages/markdown.py when loading documentation files
NAME_CONTENT_MAP = {}
PROPS_TO_EXCLUDE = [
    "unstyled",
    "m",
    "my",
    "mx",
    "mt",
    "mb",
    "ms",
    "me",
    "ml",
    "mr",
    "p",
    "py",
    "px",
    "pt",
    "pb",
    "ps",
    "pe",
    "pl",
    "pr",
    "bg",
    "c",
    "opacity",
    "ff",
    "fz",
    "fw",
    "lts",
    "ta",
    "lh",
    "fs",
    "tt",
    "td",
    "w",
    "miw",
    "maw",
    "h",
    "mih",
    "mah",
    "bgsz",
    "bgp",
    "bgr",
    "bga",
    "pos",
    "top",
    "left",
    "bottom",
    "right",
    "inset",
    "display",
    "flex",
]
