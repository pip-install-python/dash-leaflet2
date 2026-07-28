import os

PAGE_TITLE_PREFIX = "dash-leaflet2 | "
PRIMARY_COLOR = "green"

# Keep in step with pyproject.toml and package.json when cutting a release.
APP_VERSION = "0.1.0"
LEAFLET_VERSION = "2.0.0-alpha.1"

SITE_TITLE = "dash-leaflet2 — Leaflet 2 on Dash 4"

# Public origin, used for canonical URLs, the sitemap and llms.txt. Override per
# deployment; the default is the 2plot network subdomain this site ships to.
BASE_URL = os.environ.get("DASH_LEAFLET2_BASE_URL", "https://leaflet.2plot.dev").rstrip("/")

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
