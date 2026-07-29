"""Optional Clerk authentication — dash-leaflet2 docs as a 2plot satellite.

FULLY OPTIONAL. With no ``CLERK_*`` keys in the environment (or the package
missing) the site runs exactly as it does today: no script injection, no
session machinery, no routes, and every visibility tier in
:mod:`lib.page_visibility` falls open to public. That is deliberate — a
component library's documentation must never brick because a dev forgot a
key. The single source of truth for "is auth on" is :func:`clerk_enabled`.

``leaflet.2plot.dev`` runs as a Clerk **satellite** of the 2plot.ai primary,
so the same human is recognised across the galaxy. The cross-app join key is
the user's **email** — separate Clerk apps mean ``user_id`` does NOT map
across domains.

Env vars (set all three to enable):
    CLERK_SECRET_KEY       sk_...  backend SDK key, never exposed to the client
    CLERK_PUBLISHABLE_KEY  pk_...  embedded in the injected <script>
    CLERK_SIGN_IN_URL      https://2plot.ai/sign-in   (the primary hosts sign-in)

Required in production (we warn loudly when missing):
    SESSION_SECRET         signs the session + __dca_identity cookies. Without
                           it dash-clerk-auth falls back to a PUBLIC dev default.
    CLERK_FRONTEND_API     https://<app>.clerk.accounts.dev — REQUIRED in
                           satellite mode. Production custom-domain instances
                           CANNOT derive it from CLERK_SIGN_IN_URL.

Satellite config:
    CLERK_IS_SATELLITE     "true" in prod. Leave false locally — Clerk rejects
                           satellites on localhost.
    CLERK_SATELLITE_DOMAIN "leaflet.2plot.dev"  (host only, no scheme)
    CLERK_SIGN_UP_URL      https://2plot.ai/sign-up

Admin allowlist (drives /admin/control-board):
    ADMIN_EMAILS           comma-separated, case-insensitive
    ADMIN_USER_IDS         comma-separated, case-insensitive

Dev kill switch:
    DISABLE_CLERK=1        reads as "intentionally off" without touching the
                           CLERK_* values — the reliable way to run an auth-off
                           session when shell env prefixes don't survive an IDE
                           run config. Never set in production.

NOTE: read keys at CALL time, not import time — ``lib.backend``'s ``load_dotenv``
must have run first, and tests blank env vars per process.
"""
from __future__ import annotations

import os

# The app owner's Clerk account. Gates owner-only surfaces; env-overridable.
OWNER_EMAIL = os.getenv("OWNER_EMAIL", "pipinstallpython@gmail.com")

# This satellite's own host. Used as the satellite domain default and as the
# redirect target the primary sends the user back to after sign-in.
SATELLITE_HOST = "leaflet.2plot.dev"


def clerk_keys() -> tuple[str | None, str | None, str | None]:
    """(secret, publishable, sign_in_url) — or all None when disabled."""
    if (os.getenv("DISABLE_CLERK") or "").strip() == "1":
        return (None, None, None)
    return (
        os.getenv("CLERK_SECRET_KEY"),
        os.getenv("CLERK_PUBLISHABLE_KEY"),
        os.getenv("CLERK_SIGN_IN_URL"),
    )


def clerk_enabled() -> bool:
    """True only when all three CLERK_* vars are set AND the package imports."""
    if not all(clerk_keys()):
        return False
    try:
        import dash_clerk_auth  # noqa: F401

        return True
    except Exception:
        return False


def current_user():
    """The signed-in Clerk user, or None. Never raises."""
    if not clerk_enabled():
        return None
    try:
        from dash_clerk_auth import current_user as _cu

        return _cu()
    except Exception:
        return None


def current_user_email() -> str | None:
    user = current_user()
    return (getattr(user, "email", None) or None) if user else None


def _split_csv(raw: str | None) -> set[str]:
    return {item.strip().lower() for item in (raw or "").split(",") if item.strip()}


def admin_access_open() -> bool:
    """May admin surfaces render and act while Clerk is unavailable?

    Default **False** — admin surfaces fail CLOSED.

    The rest of this module fails open by design: with no Clerk keys every
    visibility tier degrades to public, because a documentation site must never
    brick over a missing credential. That is the right trade for *reading*
    docs. It is the wrong trade for `/admin/control-board`, which can hide or
    unhide any page on the site: falling open there means anyone who guesses
    the URL gets a working admin panel.

    `dash-clerk-auth` is not on PyPI (the 0.9.0 build with the satellite fixes
    is vendored across the 2plot network), so it is NOT a dependency here and
    `clerk_enabled()` is False on a default deploy. Without this gate the board
    would have shipped wide open.

    Set ``ALLOW_UNGATED_ADMIN=1`` to work on the board locally.
    """
    return (os.getenv("ALLOW_UNGATED_ADMIN") or "").strip() == "1"


def is_admin_user(user=None) -> bool:
    """Email / user-id allowlist via ADMIN_EMAILS / ADMIN_USER_IDS (case-insensitive).

    The owner's email always counts, so a fresh deploy that set the Clerk keys
    but forgot ADMIN_EMAILS still lets the owner reach the control board.
    """
    if user is None:
        user = current_user()
    if not user:
        return False
    admin_emails = _split_csv(os.environ.get("ADMIN_EMAILS")) | {OWNER_EMAIL.lower()}
    admin_ids = _split_csv(os.environ.get("ADMIN_USER_IDS"))
    email = (getattr(user, "email", None) or "").lower()
    if email and email in admin_emails:
        return True
    user_id = (getattr(user, "user_id", None) or "").lower()
    return bool(user_id and user_id in admin_ids)


# ---------------------------------------------------------------------------
# Registration — MUST run BEFORE Dash() is constructed
# ---------------------------------------------------------------------------

def register() -> bool:
    """Register Clerk with Dash. Call this *before* ``Dash(...)``.

    ``register_clerk_auth`` installs ``@dash.hooks`` callbacks that fire during
    app construction, so calling it afterwards silently does nothing.

    Returns True when auth was actually wired up.
    """
    if not clerk_enabled():
        return False

    from dash_clerk_auth import register_clerk_auth

    secret, publishable, sign_in = clerk_keys()
    sat_domain = (os.getenv("CLERK_SATELLITE_DOMAIN") or "").strip() or None
    sat_env = (os.getenv("CLERK_IS_SATELLITE", "false").strip().lower() == "true")
    pk_live = (publishable or "").startswith("pk_live_")

    # A production (pk_live) instance served on a configured satellite domain
    # MUST init ClerkJS with isSatellite+domain or ClerkJS throws "a satellite
    # application needs to specify a domain". Auto-enable it there even when
    # CLERK_IS_SATELLITE was missed in the deploy env, so prod cannot silently
    # boot in primary mode. Local dev uses a pk_test key and stays primary —
    # Clerk rejects satellites on localhost.
    is_satellite = sat_env or (pk_live and bool(sat_domain))
    if is_satellite and not sat_domain:
        # Satellite mode without a domain crashes register_clerk_auth and could
        # not work anyway. Degrade to primary with an actionable message rather
        # than failing the boot.
        print(
            "[auth] ⚠️  Clerk satellite mode needs CLERK_SATELLITE_DOMAIN "
            f"(e.g. {SATELLITE_HOST}). It is unset — booting in PRIMARY mode; "
            "client sign-in will fail until it is set."
        )
        is_satellite = False

    register_clerk_auth(
        clerk_secret_key=secret,
        clerk_publishable_key=publishable,
        clerk_sign_in_url=sign_in,
        session_secret=os.getenv("SESSION_SECRET"),
        backend="auto",
        headless=True,  # the avatar chip lives in components/header.py
        is_satellite=is_satellite,
        satellite_domain=sat_domain,
        clerk_frontend_api=(os.getenv("CLERK_FRONTEND_API") or None),
        sign_up_url=(os.getenv("CLERK_SIGN_UP_URL") or None),
    )

    if not os.getenv("SESSION_SECRET"):
        print(
            "[auth] ⚠️  Clerk ENABLED but SESSION_SECRET unset — cookies would use "
            "dash-clerk-auth's PUBLIC dev default. Set it before deploying."
        )
    if pk_live and not is_satellite:
        print(
            "[auth] ⚠️  pk_live key but NOT satellite mode — set "
            f"CLERK_SATELLITE_DOMAIN={SATELLITE_HOST} (and CLERK_IS_SATELLITE=true) "
            "or ClerkJS will fail with 'satellite needs a domain'."
        )

    if is_satellite and sat_domain:
        _install_satellite_fixups(sat_domain)

    print(
        f"[auth] Clerk ENABLED (headless; satellite={is_satellite}, "
        f"domain={sat_domain or '-'}, key={'live' if pk_live else 'test'})."
    )
    return True


def _install_satellite_fixups(sat_domain: str) -> None:
    """Two satellite fixes for dash-clerk-auth 0.9.0, applied via an index hook.

    1) clerk-js@5 reads ``domain`` as a CONSTRUCTOR option, from the script
       tag's ``data-clerk-domain`` — NOT as a ``load()`` option. The package
       passes the domain only to ``Clerk.load({domain})``, so the hosted loader
       builds the Clerk singleton with no domain and ``load({isSatellite:true})``
       throws "a satellite application needs to specify a domain or a proxyUrl".
       Fix: stamp ``data-clerk-domain`` onto the script tag. This hook runs
       AFTER the package's, so the tag already exists.

    2) The package binds the sign-in button to ``Clerk.openSignIn()`` — a modal
       on the CURRENT domain. On a satellite that POSTs to the satellite FAPI's
       ``/sign_ins`` and 403s ("This operation is not allowed on a satellite
       domain"). Sign-in must redirect to the primary instead. Fix: intercept
       the ``#clerk-login-button`` click in the CAPTURE phase (fires before the
       package's bubble-phase listener, and ``stopImmediatePropagation``
       prevents it) and call ``redirectToSignIn()``.

       ``signInForceRedirectUrl`` / ``signUpForceRedirectUrl`` are set to THIS
       page so the primary returns the user here. The deprecated ``redirectUrl``
       prop is ignored by clerk-js@5, so without these the primary would fall
       back to its own default and strand the user on 2plot.ai. Use
       origin+pathname (no query) so stale ``__clerk_*`` handshake params are
       not carried into the next sign-in.
    """
    from dash import hooks as _dash_hooks

    signin_js = (
        "<script>(function(){"
        "document.addEventListener('click',function(e){"
        "var b=e.target&&e.target.closest?e.target.closest('#clerk-login-button'):null;"
        "if(b&&window.Clerk&&typeof window.Clerk.redirectToSignIn==='function'){"
        "e.stopImmediatePropagation();e.preventDefault();"
        "var u=window.location.origin+window.location.pathname;"
        "window.Clerk.redirectToSignIn({signInForceRedirectUrl:u,signUpForceRedirectUrl:u});}"
        "},true);})();</script>"
    )

    @_dash_hooks.index()
    def _clerk_satellite_fixups(index_string):
        needle = "data-clerk-publishable-key="
        if needle in index_string and "data-clerk-domain=" not in index_string:
            index_string = index_string.replace(
                needle, f'data-clerk-domain="{sat_domain}" {needle}', 1
            )
        if "redirectToSignIn" not in index_string and "</body>" in index_string:
            index_string = index_string.replace("</body>", signin_js + "</body>", 1)
        return index_string


def configure_app(app) -> None:
    """Post-construction Clerk wiring (sessions, /api/auth/*, request identity).

    Separate from :func:`register` because dash-clerk-auth splits its setup
    either side of ``Dash(...)``. No-ops when auth is off or the package does
    not expose ``configure_app`` (older builds wired everything in register).
    """
    if not clerk_enabled():
        return
    try:
        from dash_clerk_auth import configure_app as _configure

        _configure(app)
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001 — never break the boot on auth wiring
        print(f"[auth] ⚠️  configure_app failed: {exc}")
