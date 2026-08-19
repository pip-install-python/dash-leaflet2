"""The access policy this site hands to dash-improve-my-llms.

Ported from the boilerplate and adapted for the one thing this repo has that
the template does not: a working, live control board. So the local half of
every verdict is resolved from THREE inputs, in this order (see
:func:`local_tier`):

    control-board override   lib.page_visibility, persisted to /var/data
    frontmatter registration lib.page_tiers, declared by `tier:`/`visibility:`
    the hub's ceiling        lib.hub_client, applied with `more_restrictive`

The override goes first because that is what the board is for: a toggle has to
apply on the next render, without a restart. The hub goes last and only ever
restricts — a satellite may lock a page down further, never loosen what the
network gated.

Two functions matter, and they answer different questions:

:func:`check` is the MACHINE lane — "may this fetch of a text file proceed?".
It honours ``?key=`` and the ``llms_public`` axis, and the package calls it for
``/<page>/llms.txt``, the crawler document and the prerender.

:func:`resolve_page_access` is the INTERACTIVE lane — "what does a browser get
instead of this page?". Keys never unlock layouts and ``llms_public`` says
nothing about the interactive experience, so it deliberately ignores both.

:func:`check`'s *ordering* is the rest of the design:

    tier -> short-circuit public/hidden
         -> local Clerk session          (a person in a browser)
         -> hub verification of ?key=    (an agent, later, elsewhere)

**Local session first, hub only as a fallback.** A signed-in visitor is
resolved entirely on this host, so the hub being down gates nothing for them.
Only the agent path — a fetch with no cookie, carrying a key in the URL —
needs the hub at all. Reversing this order would couple every satellite's
availability to one host for no benefit: it is the single most consequential
line in this file.

Two questions get asked of a documentation site, and only one has a session
attached. Clerk answers "who is this human?". It can never answer "may this
fetch of a text file proceed?", because when someone pastes
``https://host/guide/llms.txt`` into an assistant, the fetch arrives with no
cookie. That is why authority has to be able to travel in the URL, and why
both mechanisms exist rather than one.

Unwired by default in the template; wired unconditionally here.
:func:`configure` skips itself when every tier is public, which is the right
default for a fork — but this deployment flips its gate by environment
variable, and the verdict plumbing (including the prerender's use of it) has
to be live BEFORE the flip, not installed by it. run.py therefore passes
``force=True``. See its boot line for the resulting state.
"""

from __future__ import annotations

import logging
from typing import Optional

from lib import auth, hub_client, page_tiers, page_visibility

logger = logging.getLogger(__name__)

# Set by configure(). lib.page_visibility asks, because its legacy llms.txt
# stub swap is the fallback for a boot where nothing could be wired.
_CONFIGURED = False


def configured() -> bool:
    """True once the package holds this module's policy."""
    return _CONFIGURED


def _request_key() -> str:
    """The ``?key=`` on the current request, or "". Never raises, never logs."""
    try:
        from flask import request, has_request_context

        if not has_request_context():
            return ""
        return (request.args.get("key") or "").strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# The local half: one resolver, three inputs
# ---------------------------------------------------------------------------


def local_tier(path: str) -> str:
    """This page's tier before the hub ceiling — override, then frontmatter.

    ``page_visibility.tier_override`` answers None for a page the board never
    touched, which is the distinction that makes this work: an untouched page
    falls through to what its frontmatter declared, rather than to the
    override store's own unknown-path default. Both ledgers speak the same
    four-value vocabulary, so no mapping is needed.
    """
    override = page_visibility.tier_override(path)
    if override is not None:
        return override
    return page_tiers.local_tier(path)


def llms_public(path: str) -> bool:
    """The machine-surface axis, resolved the same way as the tier.

    Same precedence, same reason. ``LLMS_PUBLIC_DEFAULT`` still governs every
    page that neither the board nor the frontmatter pinned, so the phase-4
    agent flip stays one environment change.
    """
    override = page_visibility.llms_public_override(path)
    if override is not None:
        return override
    return page_tiers.get_llms_public(path)


def _raw_tier(path: str) -> str:
    """Local tier with the hub's ceiling applied, no degradation."""
    hub_tier = hub_client.hub_tiers().get(path)
    local = local_tier(path)
    return page_tiers.more_restrictive(local, hub_tier) if hub_tier else local


def effective_tier(path: str) -> str:
    """This page's tier, with the hub ceiling applied and degradation handled."""
    tier = _raw_tier(path)
    if not auth.clerk_enabled():
        # No way to identify anyone: everything except `hidden` falls open.
        # See lib/page_tiers.degraded_tier for why that is the right trade
        # for reading documentation, and why admin surfaces don't rely on it.
        return page_tiers.degraded_tier(tier)
    return tier


def check(path: str) -> str:
    """``allow`` | ``gated`` | ``deny`` for the current request.

    Runs inside the request, on every request, on paths that may be hot — so
    it stays cheap: a dict lookup, and at most one cached hub call for the
    agent path.
    """
    tier = effective_tier(path)

    if tier == "hidden":
        return "deny"
    if tier == "public":
        return "allow"

    # The second axis: an `auth` page whose machine twin stays open. This is
    # the window posture — humans meet the sign-in card (resolve_page_access,
    # the interactive lane) while llms.txt, crawler HTML and the prerender
    # keep serving prose so the crawl-demand dataset survives. The phase-4
    # agent flip is LLMS_PUBLIC_DEFAULT=0, which turns this branch off
    # everywhere at once; admin/hidden never reach it. The exemption applies
    # ONLY to a locally declared gate: when the hub's ceiling is what raised
    # this page above public, the machine lane must stay bound too — a
    # satellite's env default cannot loosen what the network restricted.
    if tier == "auth" and llms_public(path):
        hub_tier = hub_client.hub_tiers().get(path)
        if hub_tier not in ("auth", "admin", "hidden"):
            return "allow"

    # A signed-in reader in a browser. Resolved here, without the hub.
    user = auth.current_user()
    if user is not None:
        if tier == "admin":
            return "allow" if auth.is_admin_user(user) else "gated"
        return "allow"

    # No session: an agent, or an anonymous browser. Only a key can help now.
    key = _request_key()
    if not key:
        return "gated"
    return hub_client.verify(key, path, tier)


def resolve_page_access(path: str) -> str:
    """``allow`` | ``sign_in`` | ``forbidden`` | ``hidden`` — the INTERACTIVE
    verdict, for browser layouts (lib/gate_layouts wraps every docs page in
    it).

    Distinct from :func:`check` on purpose: the machine lane answers "may
    this fetch of a text file proceed" and honours ``?key=`` and
    ``llms_public``; a browser layout is a different question — keys never
    unlock layouts, and ``llms_public`` says nothing about the interactive
    experience.

    Fail postures are the boilerplate's, NOT the ones the retired
    ``page_visibility.resolve_access`` had: with Clerk unavailable, ``auth``
    pages fall OPEN (documentation must never brick on a missing credential)
    while ``admin`` pages stay CLOSED unless ``ALLOW_UNGATED_ADMIN`` says this
    is a local box. The old function fell open for both, which was survivable
    only because no admin surface ever went through it — ``/admin/control-board``
    has always gated itself. Do not restore that behaviour here.

    Uses the raw effective tier — not ``degraded_tier()``, which maps admin to
    public and would fall the wrong way.
    """
    tier = _raw_tier(path)

    if tier == "hidden":
        return "hidden"
    if tier == "public":
        return "allow"

    if not auth.clerk_enabled():
        if tier == "admin":
            return "allow" if auth.admin_access_open() else "forbidden"
        return "allow"

    user = auth.current_user()
    if user is None:
        return "sign_in"
    if tier == "admin" and not auth.is_admin_user(user):
        return "forbidden"
    return "allow"


def gate_doc(path: str) -> str:
    """The Markdown an unauthorised reader receives at 200.

    Deliberately useful rather than a wall: it names the page, says what would
    unlock it and where to sign in. An agent that fetches a gated document
    should come away knowing what it is and how its user gets access — that is
    the difference between a gate and a dead end, and it is why `gated` keeps
    the URL listed in the index and sitemap.
    """
    tier = effective_tier(path)
    name = _page_name(path) or path
    sign_in = _sign_in_url()

    lines = [
        f"# {name}",
        "",
        "> This document exists but is not public.",
        "",
        "---",
        "",
    ]
    if tier == "admin":
        lines += ["Reading it requires an administrator account on this site."]
    else:
        lines += ["Reading it requires a signed-in account."]
    lines += [
        "",
        "**If you are a person:** sign in"
        + (f" at {sign_in}" if sign_in else "")
        + ", then reload this page.",
        "",
        "**If you are an assistant:** ask whoever gave you this URL to copy it "
        "again while signed in. The copied link carries a key that authorises "
        "this document, and it will work when pasted here.",
        "",
        "The page's existence is public; only its content is restricted.",
        "",
    ]
    return "\n".join(lines)


def link_suffix() -> str:
    """Carry authority to the links generated in *this* response.

    An agent handed an authorised URL must be able to follow the site-index
    and per-page links inside it, or the catalogue is untraversable one hop
    from the document it was given. The package appends this to same-origin
    generated URLs only — never to canonical tags, the sitemap, or peer hosts,
    because a capability should not travel to another origin.
    """
    key = _request_key()
    return f"?key={key}" if key else ""


def _page_name(path: str) -> Optional[str]:
    try:
        import dash

        for entry in dash.page_registry.values():
            if page_tiers.normalize(entry.get("path", "")) == page_tiers.normalize(path):
                return entry.get("name")
    except Exception:
        pass
    return None


def sign_in_url() -> Optional[str]:
    """Where a reader signs in: the network bulletin's word first, env second.

    The bulletin travels with the hub's announcements, so a network-wide
    sign-in move is one hub edit instead of N satellite env changes; the env
    remains the local override and the offline fallback.
    """
    try:
        from dash_improve_my_llms.bulletin import get_bulletin

        url = ((get_bulletin() or {}).get("network") or {}).get("sign_in_url")
        if isinstance(url, str) and url.strip():
            return url.strip()
    except Exception:
        pass
    import os

    return (os.getenv("CLERK_SIGN_IN_URL") or "").strip() or None


# Old private name — gate_doc() predates the bulletin-aware lookup.
_sign_in_url = sign_in_url


def gating_configured() -> bool:
    """True when at least one page is not public.

    A site whose pages are all public gains nothing from a per-request check
    and pays for it on every hot path, so the wiring stays off until a tier
    says otherwise. Control-board overrides count: a board that gated a page
    on a previous boot has that override on disk before this is called.
    """
    if any(tier != "public" for tier in page_tiers.registered().values()):
        return True
    return any(
        page_visibility.tier_override(path) not in (None, "public")
        for path in page_visibility.controllable_pages()
    )


def configure(force: bool = False) -> bool:
    """Hand the policy to the package. Returns True when access control is on.

    Call after the pages are registered — the decision depends on their tiers.
    """
    global _CONFIGURED
    if not (force or gating_configured()):
        return False

    from dash_improve_my_llms import configure_access, configure_viewer_identity

    configure_access(check, gate_doc=gate_doc, link_suffix=link_suffix)
    configure_viewer_identity(auth.viewer_identity)
    _CONFIGURED = True
    logger.info(
        "access control ON (clerk=%s, hub=%s)",
        auth.clerk_enabled(),
        hub_client.enabled(),
    )
    return True
