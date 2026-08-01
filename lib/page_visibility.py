"""Dynamic per-page visibility for the dash-leaflet2 documentation site.

Four tiers, checked server-side at layout render time (i.e. on every request),
so a toggle from ``/admin/control-board`` applies immediately — no restart, no
redeploy:

  - ``public``  — anyone
  - ``auth``    — any signed-in Clerk user
  - ``admin``   — signed in AND allowlisted via ``ADMIN_EMAILS`` / ``ADMIN_USER_IDS``
  - ``hidden``  — nobody; the page renders a 404-style card and its llms.txt 404s

Where the defaults come from
----------------------------
Each ``docs/<slug>/<slug>.md`` may declare ``visibility:`` in its frontmatter.
Absent that, :data:`DEFAULT_TIER` applies — ``public``, because this is a
component library's own documentation and the whole point is that people can
read it. Override the baseline per deployment with ``PAGE_DEFAULT_VISIBILITY``.

Persistence
-----------
Overrides live in ``page_visibility.json`` at the project root. This is a
deliberate simplification of the pip-docs+ original, which mirrors into
Postgres: a docs satellite has one writer and no shared database, so a JSON
file is the whole story. On an ephemeral container filesystem (Render's free
tier) an override survives until the next deploy — set
``PAGE_VISIBILITY_FILE`` to a path on a persistent disk if they must outlive it.

Auth degrades gracefully: with the Clerk env keys absent (local dev without
credentials) every tier except ``hidden`` falls open to public and one warning
is logged. The site must never brick because a dev forgot a key.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

from lib.auth import clerk_enabled, current_user, is_admin_user

logger = logging.getLogger(__name__)

TIERS = ("public", "auth", "admin", "hidden")
DEFAULT_TIER = (os.environ.get("PAGE_DEFAULT_VISIBILITY") or "public").strip().lower()
if DEFAULT_TIER not in TIERS:
    logger.warning("PAGE_DEFAULT_VISIBILITY=%r is not a tier — using 'public'", DEFAULT_TIER)
    DEFAULT_TIER = "public"

_STORE_PATH = Path(os.environ.get("PAGE_VISIBILITY_FILE") or "page_visibility.json")
_lock = threading.Lock()

# endpoint -> {"visibility": tier, "llms_public": bool, "name": str}
# _defaults is registered at import time from frontmatter; _overrides is what
# the control board wrote and always wins.
_defaults: dict[str, dict] = {}
_overrides: dict[str, dict] = {}
_warned_no_clerk = False


def _load_overrides() -> None:
    global _overrides
    try:
        if _STORE_PATH.exists():
            loaded = json.loads(_STORE_PATH.read_text())
            _overrides = loaded if isinstance(loaded, dict) else {}
    except Exception as exc:  # a corrupt file must not kill the app
        logger.error("%s unreadable (%s) — ignoring overrides", _STORE_PATH, exc)
        _overrides = {}


def _persist() -> None:
    """Write overrides to disk. Call while holding ``_lock``."""
    try:
        _STORE_PATH.write_text(json.dumps(_overrides, indent=2, sort_keys=True))
    except Exception as exc:
        logger.error("Could not persist %s: %s", _STORE_PATH, exc)


_load_overrides()


# ---------------------------------------------------------------------------
# Registration + lookup
# ---------------------------------------------------------------------------

def register_default(path: str, name: str, visibility: str | None = None,
                     llms_public: bool = True) -> None:
    """Called once per page at registration time (frontmatter defaults)."""
    tier = (visibility or DEFAULT_TIER).strip().lower()
    if tier not in TIERS:
        logger.warning("Page %s: unknown visibility %r — using %r", path, tier, DEFAULT_TIER)
        tier = DEFAULT_TIER
    _defaults[path] = {"visibility": tier, "llms_public": llms_public, "name": name}


def get_settings(path: str) -> dict:
    base = _defaults.get(path, {"visibility": "public", "llms_public": True, "name": path})
    merged = dict(base)
    merged.update(_overrides.get(path, {}))
    return merged


def get_visibility(path: str) -> str:
    return get_settings(path)["visibility"]


def get_llms_public(path: str) -> bool:
    return bool(get_settings(path)["llms_public"])


def set_visibility(path: str, tier: str) -> None:
    if tier not in TIERS:
        raise ValueError(f"unknown tier {tier!r}")
    with _lock:
        _overrides.setdefault(path, {})["visibility"] = tier
        _persist()
    apply_llms_state(path)


def set_llms_public(path: str, value: bool) -> None:
    with _lock:
        _overrides.setdefault(path, {})["llms_public"] = bool(value)
        _persist()
    apply_llms_state(path)


def controllable_pages() -> dict[str, dict]:
    """Every registered page with overrides applied — the control board's model."""
    return {path: get_settings(path) for path in sorted(_defaults)}


# ---------------------------------------------------------------------------
# Access resolution
# ---------------------------------------------------------------------------

def resolve_access(path: str) -> str:
    """Verdict for the current request: 'allow' | 'sign_in' | 'forbidden' | 'hidden'."""
    global _warned_no_clerk
    tier = get_visibility(path)
    if tier == "hidden":
        return "hidden"
    if tier == "public":
        return "allow"
    if not clerk_enabled():
        if not _warned_no_clerk:
            logger.warning(
                "Clerk env keys missing — visibility tier %r falls open to public. "
                "Set CLERK_SECRET_KEY / CLERK_PUBLISHABLE_KEY in production.", tier,
            )
            _warned_no_clerk = True
        return "allow"
    user = current_user()
    if user is None:
        return "sign_in"
    if tier == "admin" and not is_admin_user(user):
        return "forbidden"
    return "allow"


# ---------------------------------------------------------------------------
# llms.txt bridge
# ---------------------------------------------------------------------------
# dash-improve-my-llms stores each page's prose as a plain string in its own
# registry and reads it at request time, so a control-board toggle only takes
# effect if we push the new verdict back into that registry. We therefore keep
# the real prose here and re-register either it or a stub whenever the tier or
# the llms_public switch changes.

_llms_docs: dict[str, tuple[str, str, str]] = {}  # path -> (name, description, doc)


def register_llms_doc(path: str, name: str, description: str, doc: str) -> None:
    """Record a page's llms.txt prose and push the current verdict."""
    _llms_docs[path] = (name, description, doc)
    apply_llms_state(path)


def published_name(path: str, name: str) -> str:
    """The name this path publishes to agents — SITE_BRAND at the root.

    The home page's registered `name` is not a nav label to
    dash-improve-my-llms: 2.3.4 resolves it through `resolve_site_title` into
    the /llms.txt H1, og:title and the viewer's brand chip. This site's home
    page is registered as "Home", which `resolve_site_title` SKIPS as generic,
    so publishing it would drop the site's identity to whatever candidate is
    left.

    This function is why the substitution lives here rather than only in
    run.py. `apply_llms_state` re-registers the entry EVERY time a
    control-board toggle changes a verdict — so a single flip of "/" would
    otherwise overwrite run.py's SITE_BRAND with "Home" at runtime, with
    nothing logged and nothing visibly broken. The nav keeps "Home"; only the
    published identity changes.
    """
    from lib.constants import SITE_BRAND

    return SITE_BRAND if path == "/" else name


def apply_llms_state(path: str) -> None:
    """Re-register this page's llms.txt body to match the current verdict."""
    entry = _llms_docs.get(path)
    if entry is None:
        return
    name, description, doc = entry
    try:
        from dash_improve_my_llms import register_page_metadata
    except Exception:  # optional dependency — nothing to sync
        return
    name = published_name(path, name)
    body = doc if llms_accessible(path) else (
        f"# {name}\n\n> This page is not publicly available.\n"
    )
    register_page_metadata(path=path, name=name, description=description, llms_doc=body)


def llms_accessible(path: str) -> bool:
    """Whether ``/<page>/llms.txt`` may serve this page's content.

    llms.txt intentionally bypasses the sign-in gate when ``llms_public`` is on
    — AI/SEO friendliness is the site's premise. But ``hidden`` pages are always
    excluded, and ``admin`` pages are never served to anonymous LLM traffic.
    """
    tier = get_visibility(path)
    if tier == "hidden":
        return False
    if tier == "admin":
        return clerk_enabled() and is_admin_user()
    return get_llms_public(path)


# ---------------------------------------------------------------------------
# Gate layouts
# ---------------------------------------------------------------------------

def _card(icon: str, color: str, title: str, body: str, extra=None):
    import dash_mantine_components as dmc
    from dash_iconify import DashIconify

    children = [
        DashIconify(icon=icon, width=56, color=f"var(--mantine-color-{color}-5)"),
        dmc.Title(title, order=3, ta="center"),
        dmc.Text(body, c="dimmed", ta="center", maw=440),
    ]
    if extra is not None:
        children.append(extra)
    return dmc.Center(
        dmc.Paper(
            dmc.Stack(children, align="center", gap="md", p="xl"),
            withBorder=True, radius="lg", shadow="md", p="xl", mt="10vh", maw=560,
        )
    )


def sign_in_layout(page_name: str, path: str | None = None):
    """Sign-in card for a visitor hitting an ``auth``-tier page.

    The buttons carry the ids dash-clerk-auth's satellite click-interceptor
    looks for, so sign-in redirects to the 2plot.ai primary and lands the user
    back on this page.
    """
    import dash_mantine_components as dmc
    from dash_iconify import DashIconify

    return dmc.Center(
        dmc.Paper(
            dmc.Stack(
                [
                    dmc.ThemeIcon(
                        DashIconify(icon="tabler:lock", width=28),
                        size=54, radius="xl", variant="light", color="teal",
                    ),
                    dmc.Title("Sign in to continue", order=3, ta="center"),
                    dmc.Text(
                        f"“{page_name}” is available to signed-in readers. A free "
                        "2plot account unlocks it along with every other live "
                        "example in the network.",
                        c="dimmed", ta="center", maw=460,
                    ),
                    dmc.Group(
                        [
                            dmc.Button(
                                "Create free account",
                                id="clerk-login-button",
                                size="md",
                                variant="gradient",
                                gradient={"from": "teal", "to": "cyan"},
                                leftSection=DashIconify(icon="tabler:user-plus", width=18),
                            ),
                            dmc.Anchor(
                                dmc.Button(
                                    "Sign in",
                                    size="md",
                                    variant="default",
                                    leftSection=DashIconify(icon="tabler:login-2", width=18),
                                ),
                                href=os.getenv("CLERK_SIGN_IN_URL", "https://2plot.ai/sign-in"),
                            ),
                        ],
                        justify="center", gap="sm", mt="xs",
                    ),
                    dmc.Text(
                        "Free forever — you'll be redirected straight back to this page.",
                        size="xs", c="dimmed", ta="center",
                    ),
                ],
                align="center", gap="md", p="xl",
            ),
            withBorder=True, radius="lg", shadow="xl", mt="10vh", maw=560,
        ),
        px="md",
    )


def forbidden_layout(page_name: str):
    return _card(
        "tabler:shield-lock", "red", "Restricted documentation",
        f"“{page_name}” is limited to administrator accounts.",
    )


def hidden_layout():
    return _card(
        "tabler:eye-off", "gray", "404 — Page not available",
        "This page is not currently published.",
    )


def gated_layout(path: str, page_name: str, build_layout):
    """Wrap a page layout in the dynamic visibility gate.

    ``build_layout`` is a prebuilt component tree (or a zero-arg callable
    returning one). The returned function becomes the Dash page layout, so the
    check runs on every render and control-board toggles apply live.

    ``**kwargs`` is required: Dash Pages forwards query params — including
    Clerk's ``?__clerk_handshake=`` — into layout callables.
    """
    def layout(**kwargs):
        verdict = resolve_access(path)
        if verdict == "hidden":
            return hidden_layout()
        if verdict == "sign_in":
            return sign_in_layout(page_name, path)
        if verdict == "forbidden":
            return forbidden_layout(page_name)
        return build_layout() if callable(build_layout) else build_layout

    return layout
