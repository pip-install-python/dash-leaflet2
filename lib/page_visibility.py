"""The control board's override store — live per-page tiers, persisted.

**Demoted, deliberately.** This module used to be the whole access system:
frontmatter defaults, verdicts, gate layouts and the llms.txt bridge. The
network stack now owns enforcement — :mod:`lib.page_tiers` holds the declared
baseline, :mod:`lib.access` resolves the verdict (adding the hub ceiling, the
``?key=`` agent lane and the ``llms_public`` axis), and
:mod:`lib.gate_layouts` renders the interactive gate. What stayed here is the
half that had no counterpart in the network stack and is working production
UX: the ``/admin/control-board`` model, its live toggles, and their JSON
persistence.

So the reading order is: an override written here beats everything local (see
:func:`lib.access.local_tier`), because the point of the board is that a
toggle applies on the next render with no restart and no redeploy. Underneath
it sits the frontmatter registration in :mod:`lib.page_tiers`, and above both
sits the hub's ceiling, which only ever restricts.

The four tiers are the network's, unchanged — they were always the same
vocabulary:

  - ``public``  — anyone
  - ``auth``    — any signed-in Clerk user
  - ``admin``   — signed in AND allowlisted via ``ADMIN_EMAILS`` / ``ADMIN_USER_IDS``
  - ``hidden``  — nobody; the page renders a 404-style card and its llms.txt 404s

Where the defaults come from
----------------------------
Each ``docs/<slug>/<slug>.md`` declares ``tier:`` (or its older spelling
``visibility:``) in frontmatter, and ``pages/markdown.py`` feeds that one value
to both this store's board rows and ``lib.page_tiers``. Absent a declaration
the baseline comes from :func:`lib.page_tiers._default_tier`, i.e.
``PAGE_DEFAULT_TIER`` / ``PAGE_DEFAULT_VISIBILITY`` — read through that
function rather than re-derived here, so the board can never display a
different default from the one enforced.

Persistence
-----------
Overrides live in ``page_visibility.json`` at the project root, or wherever
``PAGE_VISIBILITY_FILE`` points — in production that is the persistent
``/var/data`` disk, so a board toggle outlives a deploy. This is a deliberate
simplification of the pip-docs+ original, which mirrors into Postgres: a docs
satellite has one writer and no shared database, so a JSON file is the whole
story.

What this module no longer does: resolve access (that is
``lib.access.resolve_page_access`` for browsers and ``lib.access.check`` for
machine surfaces, and their fail postures differ from the old
``resolve_access``'s — admin fails CLOSED now), and wrap page layouts (that is
``lib.gate_layouts.gated_layout``). The gate cards below are kept for
``/admin/control-board``, which gates itself.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

from lib import page_tiers
from lib.auth import clerk_enabled, is_admin_user

logger = logging.getLogger(__name__)

TIERS = page_tiers.TIERS


def default_tier() -> str:
    """The baseline for a page that declares nothing.

    Delegated to :mod:`lib.page_tiers` rather than re-read here. It used to be
    a module constant computed from ``PAGE_DEFAULT_VISIBILITY`` at import time,
    which meant two things this pilot cannot afford: the board's rows and the
    enforced tier resolved the default independently (so they could disagree
    once ``PAGE_DEFAULT_TIER`` was introduced), and a value read at import
    could not be flipped by a test or a reload.
    """
    return page_tiers._default_tier()


_STORE_PATH = Path(os.environ.get("PAGE_VISIBILITY_FILE") or "page_visibility.json")
_lock = threading.Lock()

# endpoint -> {"visibility": tier, "llms_public": bool, "name": str}
# _defaults is registered at import time from frontmatter; _overrides is what
# the control board wrote and always wins.
_defaults: dict[str, dict] = {}
_overrides: dict[str, dict] = {}

# Cross-worker reconciliation. gunicorn runs this app with more than one
# worker process (Dockerfile: --workers ${WEB_CONCURRENCY:-2}), and a board
# toggle mutates _overrides only in the worker that served the POST. Every
# other worker kept its import-time copy — so an anonymous refresh became a
# coin flip between the new verdict and the stale one, decided by which
# worker answered. The store file is the one thing all workers share;
# re-reading it when its mtime moves is what makes a toggle land everywhere.
# The stat is throttled so hot paths pay at most one os.stat per second.
_store_mtime_ns: int | None = None
_next_stat_at = 0.0
_STAT_INTERVAL_S = 1.0


def _load_overrides() -> None:
    global _overrides, _store_mtime_ns
    try:
        if _STORE_PATH.exists():
            # stat BEFORE read: a write that lands between the two is picked
            # up by the next mtime check instead of being masked forever.
            stamp = _STORE_PATH.stat().st_mtime_ns
            loaded = json.loads(_STORE_PATH.read_text())
            _overrides = loaded if isinstance(loaded, dict) else {}
            _store_mtime_ns = stamp
    except Exception as exc:  # a corrupt file must not kill the app
        logger.error("%s unreadable (%s) — ignoring overrides", _STORE_PATH, exc)
        _overrides = {}


def _persist() -> None:
    """Write overrides to disk. Call while holding ``_lock``."""
    global _store_mtime_ns
    try:
        _STORE_PATH.write_text(json.dumps(_overrides, indent=2, sort_keys=True))
        # Record our own write's stamp so this worker doesn't re-read it.
        _store_mtime_ns = _STORE_PATH.stat().st_mtime_ns
    except Exception as exc:
        logger.error("Could not persist %s: %s", _STORE_PATH, exc)


def _persistence_warning() -> None:
    """Loud when the store lives on the container filesystem.

    render.yaml declares ``PAGE_VISIBILITY_FILE=/var/data/...``, but a
    Blueprint env row reaches the live service only on a sync — the exact
    drift that had every control-board toggle silently resetting on every
    redeploy (stage-3 env diff found the var absent; owner re-observed the
    resets 2026-08-22). With the variable unset, ``_STORE_PATH`` falls back
    to ``page_visibility.json`` in the app directory, which a Docker deploy
    replaces wholesale. The absence of this line in a deploy log is the
    acceptance check that the variable actually landed on the service.
    """
    configured = os.environ.get("PAGE_VISIBILITY_FILE")
    if not configured:
        print(
            "[visibility] WARNING: PAGE_VISIBILITY_FILE unset — control-board "
            "toggles are writing to the app directory and will NOT survive a "
            "redeploy. Set PAGE_VISIBILITY_FILE=/var/data/page_visibility.json "
            "on the Render service (render.yaml declares it, but only a "
            "Blueprint sync or a dashboard add makes it live)."
        )
        return
    # The env being right is only HALF the persistence story: render.yaml
    # also declares the disk, and disks materialize only via a Blueprint
    # sync or a dashboard add. An app can mkdir /var/data on the container
    # filesystem and everything works — until the next deploy wipes it,
    # which is indistinguishable from the unset case without this check.
    path = Path(configured)
    if str(path).startswith("/var/"):
        anchor = Path("/") / path.parts[1] / path.parts[2] \
            if len(path.parts) > 2 else path.parent
        if not os.path.ismount(str(anchor)):
            print(
                f"[visibility] WARNING: {anchor} is not a mounted disk on "
                "this instance — the control-board store will vanish on the "
                "next deploy. Attach the render.yaml disk (Blueprint sync, "
                "or add it in the dashboard)."
            )


def _maybe_reload() -> None:
    """Pick up another worker's board writes; no-op when nothing changed.

    Reload triggers ONLY on an observed mtime change of the store file:
    a missing file, a stat error, or an unchanged stamp all leave the
    in-memory dict alone — which is also what keeps tests that inject
    straight into ``_overrides`` (without touching the file) valid.
    """
    global _next_stat_at
    if time.monotonic() < _next_stat_at:
        return
    with _lock:
        if time.monotonic() < _next_stat_at:  # another thread just checked
            return
        _next_stat_at = time.monotonic() + _STAT_INTERVAL_S
        try:
            stamp = _STORE_PATH.stat().st_mtime_ns
        except OSError:
            return
        if stamp == _store_mtime_ns:
            return
        _load_overrides()


_load_overrides()
_persistence_warning()


# ---------------------------------------------------------------------------
# Registration + lookup
# ---------------------------------------------------------------------------

def register_default(path: str, name: str, visibility: str | None = None,
                     llms_public: bool | None = None) -> None:
    """Called once per page at registration time (frontmatter defaults).

    ``llms_public=None`` means "this page did not pin the axis" and is stored
    as None rather than resolved here, so ``LLMS_PUBLIC_DEFAULT`` keeps
    governing it — including in the board's own switches, which then show what
    the site is actually doing rather than what it was doing at boot.
    """
    fallback = default_tier()
    tier = (visibility or fallback).strip().lower()
    if tier not in TIERS:
        logger.warning("Page %s: unknown visibility %r — using %r", path, tier, fallback)
        tier = fallback
    _defaults[path] = {"visibility": tier, "llms_public": llms_public, "name": name}


def get_settings(path: str) -> dict:
    """Baseline + override, with the unpinned machine axis resolved live.

    The board's model, not the resolver's — lib.access reads the override
    accessors below instead, because a merged value cannot say whether an
    operator chose it.
    """
    _maybe_reload()
    base = _defaults.get(path)
    if base is None:
        base = {"visibility": default_tier(), "llms_public": None, "name": path}
    merged = dict(base)
    merged.update(_overrides.get(path, {}))
    if merged.get("llms_public") is None:
        merged["llms_public"] = page_tiers.get_llms_public(path)
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


def pin_default(path: str, visibility: str) -> None:
    """Force a page's baseline tier after it registered. Board rows follow.

    run.py pins the funnel's front door public so ``PAGE_DEFAULT_TIER=auth``
    cannot gate it. That pin has to land on BOTH ledgers or the board would
    display a tier the site does not enforce — the exact drift this pilot
    unified the two systems to remove. An operator can still override the pin
    from the board; that is the point of an override.
    """
    if visibility not in TIERS:
        raise ValueError(f"unknown tier {visibility!r}")
    entry = _defaults.get(path)
    if entry is None:
        return
    entry["visibility"] = visibility


# ---------------------------------------------------------------------------
# Overrides, read by lib.access
# ---------------------------------------------------------------------------
# `get_settings` merges defaults and overrides, which is right for the board's
# table and wrong for the resolver: a merged read cannot tell "the operator
# set this page to public" from "nobody ever touched it". The resolver needs
# that difference, because an untouched page has to fall through to the
# frontmatter registration in lib.page_tiers rather than to this store's
# unknown-path default. Hence two accessors that answer None for "no override".


def tier_override(path: str) -> str | None:
    """The tier the control board wrote for ``path``, or None."""
    _maybe_reload()
    tier = (_overrides.get(path) or {}).get("visibility")
    return tier if tier in TIERS else None


def llms_public_override(path: str) -> bool | None:
    """The machine-surface switch the control board wrote, or None."""
    _maybe_reload()
    value = (_overrides.get(path) or {}).get("llms_public")
    return None if value is None else bool(value)


# ---------------------------------------------------------------------------
# llms.txt bridge
# ---------------------------------------------------------------------------
# dash-improve-my-llms stores each page's prose as a plain string in its own
# registry and reads it at request time. This module used to swap that string
# for a stub whenever a page's verdict said "not public" — a second, parallel
# enforcement path.
#
# lib.access is the enforcement engine now, and it is strictly better at this
# job: the package asks it per request, so the answer can honour the hub
# ceiling, an agent's `?key=`, and the llms_public axis, and an unauthorised
# fetch gets `gate_doc()` (which names the page and says how to unlock it)
# instead of a bare stub. Registering the real prose once and letting the
# check decide is therefore the whole design — a stub swapped in underneath a
# working check would only mean a reader who IS authorised gets the stub.
#
# The stub swap survives as the fallback for one case: a boot where the
# package could not be handed a policy at all (`lib.access.configured()` is
# False). Then nothing else is standing between a hidden page and its prose.

# path -> {"name", "description", "doc", "extra"}. `extra` is whatever else
# the page declares for dash-improve-my-llms — `lastmod`, `image_url`,
# `schema_type`. It has to be REMEMBERED rather than passed once, because
# `apply_llms_state` re-registers the whole record on every control-board
# toggle, and register_page_metadata MERGES: a re-registration that omitted
# these would leave the earlier values in place today and silently drop them
# the day the package's merge semantics change. Remembering them is the
# version of this that cannot rot.
_llms_docs: dict[str, dict] = {}


def register_llms_doc(path: str, name: str, description: str, doc: str,
                      **extra) -> None:
    """Record a page's llms.txt prose (and its metadata) and push it."""
    _llms_docs[path] = {
        "name": name, "description": description, "doc": doc, "extra": extra,
    }
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
    """Register this page's llms.txt body. Real prose whenever a check is wired.

    Still called on every control-board toggle, and still worth calling: it is
    what re-asserts :func:`published_name` for "/" (see that docstring — a
    board flip of the home page would otherwise republish the site's identity
    as "Home").
    """
    entry = _llms_docs.get(path)
    if entry is None:
        return
    try:
        from dash_improve_my_llms import register_page_metadata
    except Exception:  # optional dependency — nothing to sync
        return
    name = published_name(path, entry["name"])
    body = entry["doc"]
    if not _enforcement_wired() and not llms_accessible(path):
        body = f"# {name}\n\n> This page is not publicly available.\n"
    register_page_metadata(
        path=path,
        name=name,
        description=entry["description"],
        llms_doc=body,
        **entry["extra"],
    )


def _enforcement_wired() -> bool:
    """Whether lib.access handed the package a policy. Imported lazily —
    lib.access imports this module, so a top-level import would be a cycle."""
    try:
        from lib import access

        return access.configured()
    except Exception:
        return False


def llms_accessible(path: str) -> bool:
    """The legacy machine-surface verdict — the degraded-boot fallback only.

    :func:`lib.access.check` is the real answer; this stays for the case where
    no policy could be wired at all, so a hidden or admin page still cannot
    publish prose on a boot with the package misconfigured. It knows nothing
    about the hub ceiling or `?key=`, which is exactly why it is not the
    engine any more.
    """
    tier = get_visibility(path)
    if tier == "hidden":
        return False
    if tier == "admin":
        return clerk_enabled() and is_admin_user()
    return get_llms_public(path)


# ---------------------------------------------------------------------------
# Gate layouts — the CONTROL BOARD's cards only
# ---------------------------------------------------------------------------
# Docs pages moved to lib/gate_layouts.py, whose sign-in card carries the
# `#auth-gate-*` ids that assets/auth_gate.js handles. These three stay
# because /admin/control-board gates itself in `pages/control_board.layout`
# and needs something to render; one admin page is not worth a second
# dependency on the docs funnel's copy.
#
# Note the button here is `#clerk-login-button`, handled by lib/auth.py's
# capture-phase delegation. Deliberately the OTHER selector: the two handlers
# must stay disjoint or a single click runs both.

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
    """Sign-in card for a signed-out visitor. Used by the control board.

    The primary button carries `#clerk-login-button`, the id lib/auth.py's
    satellite click-interceptor looks for, so sign-in redirects to the
    2plot.ai primary and lands the user back on this page.

    The secondary "Sign in" anchor still points straight at
    ``CLERK_SIGN_IN_URL`` with no ``returnTo``, which strands the visitor on
    the primary after they authenticate. lib/gate_layouts.sign_in_layout is
    the fixed version and is what every docs page renders; this copy is left
    as-is because an administrator who lands here knows the board's URL. Fix
    it here too if this card ever gets a second caller.
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
