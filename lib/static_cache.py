"""Cache lifetimes for the static files this app serves (1.6.44 item 6g).

MEASURED ON THIS HOST FIRST, because the item says to and because a fleet
finding is not a local fact until someone looks. leaflet.2plot.dev,
2026-09-05:

    GET https://leaflet.2plot.dev/assets/main.css
        cache-control: no-cache
        cf-cache-status: DYNAMIC
    GET https://leaflet.2plot.dev/assets/style.css
        cache-control: no-cache
        cf-cache-status: DYNAMIC

So the CDN in front of this host stored nothing, and every visitor
revalidated the stylesheets, the map JS and the logo on every page load.
`no-cache` does not mean "do not store" — it means "revalidate before use" —
but the effect through Cloudflare is the same: the edge declines to serve it
and the origin answers every request.

Only ``/assets/`` is given a lifetime here, and deliberately:

* Dash's own ``/_dash-component-suites/`` URLs are fingerprinted and the
  package already sets a long immutable lifetime on them — a second opinion
  from this app could only make that worse;
* documents must keep revalidating. A page, ``/llms.txt``, ``/healthz`` and
  anything under ``/admin`` or ``/api`` are answers about right now, and one
  hour of a stale one is a bug report nobody can reproduce.

The window is one hour with a day of ``stale-while-revalidate``: assets here
are NOT fingerprinted (``main.css`` keeps its name across deploys), so the
lifetime is the longest a CSS fix may take to reach a returning reader.

One module, two lanes. Flask's ``after_request`` and the ASGI middleware both
read ``cache_control_for`` rather than each carrying a prefix and a value, so
the two cannot drift into serving different lifetimes for the same file — the
class of divergence nothing on the wire would reveal, because a host serves
only one lane at a time.
"""
from __future__ import annotations

ASSET_PREFIX = "/assets/"
ASSET_CACHE_CONTROL = "public, max-age=3600, stale-while-revalidate=86400"


def cache_control_for(path: str) -> str | None:
    """The ``Cache-Control`` this app wants on ``path``, or None to leave it.

    None is the answer for everything that is not an unfingerprinted static
    asset — the caller must not invent a header for a document.
    """
    return ASSET_CACHE_CONTROL if (path or "").startswith(ASSET_PREFIX) else None
