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
    CLERK_SATELLITE_SIGN_IN_REDIRECT
                           REQUIRED in production, despite reading as optional.
                           An absolute URL on the PRIMARY that the Sign In
                           button navigates to, with this page carried in
                           ?returnTo=. Read by dash-clerk-auth from the
                           environment itself, so we do not pass it through.
                           Set to https://2plot.ai/onboarding (render.yaml).

                           It was left unset here while the note below said
                           "only set it once 2plot.ai has a page that honours
                           ?returnTo=". 2plot.ai gained exactly that page —
                           /onboarding, which validates returnTo against its
                           own satellite whitelist and force-redirects home —
                           and nobody came back to set it. The result, live on
                           2026-08-20: sign-in succeeded on the primary and
                           stranded the user there.

                           Unset, the fallback is Clerk.redirectToSignIn(),
                           which hops to CLERK_SIGN_IN_URL — the Clerk-HOSTED
                           Account Portal. The hub's Dash app never sees that
                           request, so none of its returnTo handling runs and
                           the return depends solely on the Clerk dashboard's
                           own allowed-redirect list. That failure is silent
                           on both sides. See the boot warning in register().

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

    `dash-clerk-auth` is vendored across the 2plot network rather than resolved
    from PyPI (1.0.0 is the current build), so it is NOT a dependency here and
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
# Viewer identity for the llms.txt banner
# ---------------------------------------------------------------------------

# session_id -> first ISO timestamp this process saw it. Deliberately NOT the
# Clerk token's `iat`: the session token is refreshed roughly every 60 seconds,
# so `iat` is the age of the *token*, not of the sign-in — wiring it renders a
# "signed in since" clock that resets every minute.
#
# Process-local and unbounded-by-design is wrong, so it is capped. Losing an
# entry costs a slightly-late timestamp, nothing more.
_SESSION_FIRST_SEEN: dict[str, str] = {}
_SESSION_CACHE_MAX = 2048


def _first_seen(session_id: str) -> str:
    from datetime import datetime, timezone

    stamp = _SESSION_FIRST_SEEN.get(session_id)
    if stamp is None:
        if len(_SESSION_FIRST_SEEN) >= _SESSION_CACHE_MAX:
            _SESSION_FIRST_SEEN.clear()
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        _SESSION_FIRST_SEEN[session_id] = stamp
    return stamp


def viewer_identity() -> dict | None:
    """For ``configure_viewer_identity``. None when nobody is signed in.

    Rendered in the HTML viewer's banner only — the Markdown variant of the
    same URL is byte-identical with and without it, so this can never reach an
    agent, a crawler or an index.
    """
    user = current_user()
    if not user:
        return None
    try:
        identity = {"name": getattr(user, "email", None) or getattr(user, "user_id", "")}
        session_id = getattr(user, "session_id", None)
        if session_id:
            identity["since"] = _first_seen(session_id)
        plan = getattr(user, "plan", None)
        if plan:
            identity["plan"] = plan
        return identity if identity.get("name") else None
    except Exception:
        return None


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
        # THE REPLAY WINDOW, stated rather than inherited. dash-clerk-auth
        # 1.0.3 made this an explicit re-vendor decision, because it is the
        # only knob an application controls here: `__dca_identity` is a
        # STATELESS signed token, so a value captured before sign-out keeps
        # verifying until its max-age expires — the server holds no
        # revocation list, and closing that would mean giving up the fast
        # path the cookie exists to provide.
        #
        # 7 (the package default) is the choice for THIS host. What it gates
        # is documentation: a captured cookie buys read access to pages a
        # free account also unlocks, and the gate exists to drive account
        # creation, so re-authenticating readers every day would tax the
        # funnel for almost nothing. Shortening it is the whole mitigation
        # if that calculus changes — and the one thing that would change it
        # is /admin/control-board, which trusts the identity in this cookie
        # and can hide or unhide any page on the site. If an admin account
        # is ever used from a shared machine, drop this well below a week.
        session_lifetime_days=7,
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
    sat_redirect = (os.getenv("CLERK_SATELLITE_SIGN_IN_REDIRECT") or "").strip()
    if is_satellite and not sat_redirect:
        # The one Clerk misconfiguration with NO error on either side: the
        # user signs in successfully and is simply left on the primary. It
        # shipped that way here for weeks because nothing said so. Now
        # something does.
        print(
            "[auth] ⚠️  Satellite mode with CLERK_SATELLITE_SIGN_IN_REDIRECT "
            "unset — sign-in will hop to the Clerk Account Portal instead of "
            "the hub, and users may not be returned to this site at all. "
            "Set it to https://2plot.ai/onboarding (see render.yaml)."
        )
    elif is_satellite and not sat_redirect.startswith(("http://", "https://")):
        # It is a URL, not a flag, and the package does not reject a bad one:
        # it logs a warning and uses the value anyway. `buildSatelliteRedirect`
        # concatenates `<value>?returnTo=<here>`, so a non-absolute value is
        # resolved against THIS host — CLERK_SATELLITE_SIGN_IN_REDIRECT=true
        # sends the Sign In button to https://<this host>/true?returnTo=...,
        # which is strictly worse than leaving it unset. The package's own
        # warning goes to `logger`, several screens up in the boot output;
        # this one prints where the rest of the [auth] diagnostics are.
        print(
            f"[auth] ⚠️  CLERK_SATELLITE_SIGN_IN_REDIRECT={sat_redirect!r} is not "
            "an absolute http(s) URL. It is a DESTINATION, not a flag — the "
            "Sign In button will navigate to a path on THIS host and 404. "
            "Set it to https://2plot.ai/onboarding."
        )

    if is_satellite and sat_domain:
        _install_satellite_signin_delegation()
    _install_signout_delegation()

    print(
        f"[auth] Clerk ENABLED (headless; satellite={is_satellite}, "
        f"domain={sat_domain or '-'}, key={'live' if pk_live else 'test'})."
    )
    return True


def _install_satellite_signin_delegation() -> None:
    """Delegate ``#clerk-login-button`` clicks, for buttons Dash renders LATE.

    This used to be two hand-rolled satellite fixes for dash-clerk-auth 0.9.0.
    Both are upstream now and the local copies are gone:

    * stamping ``data-clerk-domain`` onto the ClerkJS script tag (clerk-js@5
      reads ``domain`` as a CONSTRUCTOR option, not a ``load()`` option) —
      fixed in **0.9.1**;
    * replacing ``Clerk.openSignIn()`` on a satellite, which POSTs to the
      satellite FAPI and 403s with "This operation is not allowed on a
      satellite domain" — fixed in **0.9.2**, which branches to
      ``buildSatelliteRedirect()`` / ``redirectToSignIn()`` instead.

    What is NOT upstream is *delegation*. The package binds the button by id
    inside its ``DOMContentLoaded`` handler, once. The header control exists by
    then (``components.header``, part of the app shell) and works. The sign-in
    card in :func:`lib.page_visibility.sign_in_layout` does NOT — it is rendered
    by a page callback when a visitor reaches an ``auth``-tier page, long after
    that handler ran, so its button would have no listener at all and the click
    would do nothing.

    So we keep one delegated CAPTURE-phase listener, which catches the button
    however late it appears. ``stopImmediatePropagation`` means exactly one
    handler runs even on the header button, where the package's own listener is
    also attached — deterministic rather than order-dependent.

    The action itself defers to the package: ``buildSatelliteRedirect()`` (its
    0.9.2 page-JS surface, which carries the current page in ``?returnTo=``)
    when a ``satellite_sign_in_redirect`` is configured, else the same
    ``redirectToSignIn`` call upstream makes. Set
    ``CLERK_SATELLITE_SIGN_IN_REDIRECT`` to switch this satellite onto the
    first path; unset, the fallback is the behaviour this site already shipped.
    """
    from dash import hooks as _dash_hooks

    # Unique marker: the guard below keys off it so a second registration (or a
    # future second index hook) cannot inject this script twice.
    marker = "dl2-clerk-signin-delegate"

    signin_js = (
        f"<script data-{marker}>(function(){{"
        "document.addEventListener('click',function(e){"
        "var b=e.target&&e.target.closest?e.target.closest('#clerk-login-button'):null;"
        "if(!b||!window.Clerk)return;"
        "var dca=window.dashClerkAuth;"
        "var dest=dca&&dca.buildSatelliteRedirect?dca.buildSatelliteRedirect():null;"
        "if(dest){e.stopImmediatePropagation();e.preventDefault();"
        "window.location.assign(dest);return;}"
        "if(typeof window.Clerk.redirectToSignIn==='function'){"
        "e.stopImmediatePropagation();e.preventDefault();"
        "var u=window.location.href;"
        "window.Clerk.redirectToSignIn({signInForceRedirectUrl:u,signUpForceRedirectUrl:u});}"
        "},true);})();</script>"
    )

    @_dash_hooks.index()
    def _clerk_satellite_signin(index_string):
        if marker not in index_string and "</body>" in index_string:
            index_string = index_string.replace("</body>", signin_js + "</body>", 1)
        return index_string


def _install_signout_delegation() -> None:
    """Make Sign Out actually revoke the SERVER's idea of who you are.

    FIXED UPSTREAM IN 1.0.3 — this shim is now a deliberate duplicate, kept
    for one release and retiring in 1.0.4. The package's POST is idempotent
    (its changelog says so explicitly, so an app may keep its own handler
    through the upgrade), and both handlers cannot both run on one click
    anyway: this delegate takes the capture phase and calls
    ``stopImmediatePropagation``. Retiring it early would be the riskier
    move, because it is what actually shipped the fix to this host.

    The defect, for the record. dash-clerk-auth 1.0.2's logout handler ran
    ``window.Clerk.signOut()`` and reloaded — client-side only. The server keeps trusting the signed
    ``__dca_identity`` cookie (and the Flask session) it minted at sign-in
    for the rest of ``session_lifetime_days`` (default **7 days**): a
    signed-out browser still renders every auth-gated page — the pilot's
    live defect of 2026-08-21. The package ships the endpoint that fixes
    this — ``POST /api/auth/signout`` clears the session and the identity
    cookie — but nothing ever calls it.

    This capture-phase delegate owns the click (``stopImmediatePropagation``,
    the sign-in delegation's proven pattern) and sequences what the package
    should have: Clerk sign-out FIRST (kills ``__session``, so the slow path
    cannot re-verify and re-mint identity), then the server signout (kills
    the Flask session + ``__dca_identity``), then the reload — awaited, so
    the reload can never race the cookie clears. Every failure still ends in
    a reload, and the server POST runs even when ClerkJS never loaded —
    which is exactly the stale-ghost case that needs it most.

    1.0.3 sequences exactly this upstream — Clerk sign-out, then the revoke
    POST, then the reload, awaited — and additionally fires the POST on a
    signed-in -> signed-out transition, which covers a sign-out performed in
    another tab or on another host of the same Clerk instance. That last
    part this shim does NOT do, which is the second reason to keep the
    package's handler rather than replace it.
    """
    from dash import hooks as _dash_hooks

    marker = "dl2-clerk-signout-delegate"

    signout_js = (
        f"<script data-{marker}>(function(){{"
        "document.addEventListener('click',function(e){"
        "var b=e.target&&e.target.closest?e.target.closest('#clerk-logout-menu-item'):null;"
        "if(!b)return;"
        "e.stopImmediatePropagation();e.preventDefault();"
        "var done=function(){window.location.reload();};"
        "var server=function(){return fetch('/api/auth/signout',"
        "{method:'POST',credentials:'same-origin'}).catch(function(){});};"
        "var clerk=(window.Clerk&&typeof window.Clerk.signOut==='function')"
        "?window.Clerk.signOut().catch(function(){}):Promise.resolve();"
        "clerk.then(server).then(done,done);"
        "},true);})();</script>"
    )

    @_dash_hooks.index()
    def _clerk_signout(index_string):
        if marker not in index_string and "</body>" in index_string:
            index_string = index_string.replace("</body>", signout_js + "</body>", 1)
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
