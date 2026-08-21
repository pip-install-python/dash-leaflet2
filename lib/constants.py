import os

PRIMARY_COLOR = "green"

# The fixed AppShell header height (components/appshell.py header={"height"}).
# The mobile drawer docks beneath it — one number, two files, keep in sync.
HEADER_HEIGHT = 70

# Keep in step with pyproject.toml and package.json when cutting a release.
APP_VERSION = "0.2.2"
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

# The short form, for places a full brand line does not fit: the installed
# app's home-screen label and the per-page <title> prefix. Derived rather than
# typed twice — PAGE_TITLE_PREFIX used to be its own literal, which is one
# rename away from a site whose tab titles disagree with its brand.
SITE_SHORT_NAME = "dash-leaflet2"
PAGE_TITLE_PREFIX = f"{SITE_SHORT_NAME} | "

SITE_DESCRIPTION = (
    "dash-leaflet2 — Leaflet 2 (alpha) mapping components for Plotly Dash 4. "
    "Wraps Leaflet 2 core directly instead of react-leaflet, exposing unified "
    "Pointer Events, BlanketOverlay canvas/WebGL layers, ES6-class "
    "subclassing, ResizeObserver sizing and map rotation as Dash components. "
    "By Pip Install Python."
)

# Public origin, used for canonical URLs, the sitemap and llms.txt. Override per
# deployment; the default is the 2plot network subdomain this site ships to.
# APP_BASE_URL first, this repo's own spelling second. `BASE_URL` is a REQUIRED
# NAME, not a preference: the shared scripts/ and tests/ import it on every
# host in the network. The env var behind it is where hosts differ, and the
# rule from the email pass is an ALIAS, never a rename — render.yaml sets the
# legacy name on a live service, and removing one of two env names from a
# running host is how it starts advertising the wrong canonical origin, which
# deindexes it silently.
BASE_URL = (
    os.environ.get("APP_BASE_URL")
    or os.environ.get("DASH_LEAFLET2_BASE_URL")
    or "https://leaflet.2plot.dev"
).rstrip("/")

_LOOPBACK = ("localhost", "127.0.0.1", "0.0.0.0", "[::1]")


def require_owned_base_url(base_url: str = None) -> None:
    """Fail fast in production when BASE_URL isn't this app's real origin.

    The boilerplate's hard boot guard (its ``lib/constants.py``), replacing the
    warn-only ``base_url_misconfigured()`` this repo used to ship: a hosted
    deploy advertising the wrong origin logged one line into a wall of boot
    output and then served a whole site of wrong canonical URLs. Now it
    refuses to boot, where the deploy log carries the reason.

    Only enforced when a hosting platform is detected (Render sets ``RENDER``;
    ``APP_ENV=production`` works anywhere else), so local development and the
    test suite are unaffected.

    Three failures are caught:

    1. **No base-URL variable set in production.** The default above happens
       to be the right origin for THIS deployment, but an explicit value is
       the contract the fleet's guard enforces — a fork of this mirror that
       relies on the default deindexes itself, and a dashboard wipe should be
       loud, not silently absorbed. Either spelling satisfies the guard:
       ``APP_BASE_URL`` (network-standard, read first) or
       ``DASH_LEAFLET2_BASE_URL`` (this repo's legacy alias — an alias, never
       a rename; render.yaml sets both on the live service).
    2. **A platform-generated hostname.** ``*.onrender.com`` /
       ``*.herokuapp.com`` still resolve after a custom domain is attached, so
       canonicals pointing there split link equity across two hostnames for as
       long as nobody notices.
    3. **A loopback origin.** `.env.example`'s local values reaching a
       dashboard is how a hosted service ends up publishing
       ``http://localhost:8050`` in every canonical link, og:url,
       /sitemap.xml entry and /llms.txt URL — while looking perfectly healthy
       from inside the container. (This was the warn-only check's whole job;
       /healthz still advertises ``base_url`` so the sweep can see it too.)
    """
    base_url = base_url if base_url is not None else BASE_URL
    in_production = bool(os.environ.get("RENDER") or os.environ.get("APP_ENV") == "production")
    if not in_production:
        return

    if not (os.environ.get("APP_BASE_URL") or os.environ.get("DASH_LEAFLET2_BASE_URL")):
        raise RuntimeError(
            "APP_BASE_URL is not set. Canonical links, sitemap.xml and "
            "llms.txt all derive from it, and a production host must state "
            "its origin explicitly rather than lean on a code default. Set "
            "APP_BASE_URL to this deployment's real origin "
            "(https://leaflet.2plot.dev — render.yaml declares it; a "
            "blueprint sync restores a variable wiped in the dashboard)."
        )

    for platform_host in ("onrender.com", "herokuapp.com", "railway.app", "fly.dev"):
        if platform_host in base_url:
            raise RuntimeError(
                f"APP_BASE_URL={base_url!r} is a platform-generated hostname. "
                "Canonical tags, sitemap.xml and llms.txt would all point at it "
                "instead of the custom domain, splitting link equity across two "
                "hosts. Set APP_BASE_URL to the public domain."
            )

    host = base_url.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0]
    if host in _LOOPBACK:
        which = "APP_BASE_URL" if os.environ.get("APP_BASE_URL") else "DASH_LEAFLET2_BASE_URL"
        raise RuntimeError(
            f"BASE_URL is {base_url!r} on a HOSTED deploy — every canonical "
            f"URL, og:url, /sitemap.xml entry and /llms.txt link would point "
            f"at localhost. {which} is set to a loopback origin in this "
            f"service's environment; set BOTH it and its alias to "
            f"https://leaflet.2plot.dev and redeploy."
        )


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
# 1200x630 = exactly 1.91:1, the Open Graph documented ideal, which also
# degrades cleanly into Twitter's 2:1 `summary_large_image` slot. The file that
# lived at this URL until 0.2.2 was 1280x515 (2.49:1) — wider than both, so
# every platform cropped roughly 100px off the top and bottom — and it was the
# 2plot network wordmark rather than a card for this site at all. Regenerate
# with `python scripts/make_social_card.py`, then upload BY HAND; the values
# below must match the file's real IHDR, and
# `scripts/network_smoke.py::social_card_real_pixels` reads those bytes after
# every deploy precisely so a re-upload at a different size cannot pass.
OG_IMAGE_URL = "https://cdn.2plot.ai/github_assets/leaflet.2plot.dev.png"
OG_IMAGE_WIDTH = 1200
OG_IMAGE_HEIGHT = 630
OG_IMAGE_TYPE = "image/png"
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
# rollup POST (now lib/satellite_reporter.py) had the same shape.
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
