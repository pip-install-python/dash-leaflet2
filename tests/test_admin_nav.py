"""The Admin section's navigation entries, and what they are allowed to imply.

REWRITTEN for the navigation contract (template 1.6.38, sync item 16). The
mechanism this file used to pin is gone, and the replacement is strictly
stronger, so most of the old assertions could not simply be re-pointed:

    before: both shells always rendered an Admin section carrying the real
            `/admin/control-board` href, and a pattern-matching callback set
            `style={"display": "none"}` on it for everyone else. The link was
            in every anonymous visitor's DOM; only CSS hid it.

    now:    `create_content` emits an EMPTY `navbar-admin-{desktop,mobile}`
            box, and `render_admin_section` fills it per request only for an
            admin. An anonymous visitor's page contains no /admin/ href at
            all — the section does not exist for them rather than being
            hidden from them.

`tests/test_nav_contract.py` owns the structural half of that (no admin href
in the anonymous tree, every admin page in the admin tree, admin paths never
in a docs section or in search). What stays HERE is this fork's own share,
which the template's file does not assert: that the predicate really is the
one the pages themselves use, that the owner's address is an admin with
ADMIN_EMAILS unset, that the callback fires on FIRST load under this app's
global `prevent_initial_callbacks=True`, and that the board behind the link
still fails closed.
"""

from __future__ import annotations

import json

from components.navbar import admin_pages, create_content, render_admin_section


def _walk(component):
    """Every component in a layout tree, depth-first."""
    yield component
    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        if hasattr(child, "children") or hasattr(child, "id"):
            yield from _walk(child)


def _hrefs(tree):
    return [h for h in (getattr(c, "href", None) for c in _walk(tree)) if h]


# ------------------------------------------------------------- the placeholder --


def test_both_shells_get_their_own_admin_placeholder(pages):
    """Desktop and drawer need SEPARATE ids.

    They cannot share one: Dash raises a duplicate-id error at layout
    validation and the whole site fails to render, so this also guards the
    boot. The old dict-id existed for the same reason; the contract uses two
    plain ids and one callback with two Outputs instead.
    """
    entries = [entry for _p, _n, entry in pages]
    desktop = str(create_content(entries, variant="desktop"))
    mobile = str(create_content(entries, variant="mobile"))

    assert "navbar-admin-desktop" in desktop
    assert "navbar-admin-mobile" not in desktop
    assert "navbar-admin-mobile" in mobile
    assert "navbar-admin-desktop" not in mobile


def test_the_startup_tree_carries_no_admin_link_at_all(pages):
    """The rendered default, which is what an anonymous visitor is served.

    Stronger than the `style={"display": "none"}` this replaced: there is no
    href to reveal. A page load that beats the callback used to show the
    Control Board link permanently; now there is nothing to show.
    """
    entries = [entry for _p, _n, entry in pages]
    for variant in ("desktop", "mobile"):
        tree = create_content(entries, variant=variant)
        leaked = [h for h in _hrefs(tree) if h.startswith("/admin/")]
        assert leaked == [], f"{variant} ships admin links: {leaked}"


def test_every_admin_page_is_in_the_admin_set_and_none_are_docs(pages):
    """Both admin surfaces belong to the gated section, and only there."""
    entries = [entry for _p, _n, entry in pages]
    paths = {e["path"] for e in admin_pages(entries)}
    assert paths == {"/admin/control-board", "/admin/traffic"}


# ------------------------------------------------------------------ the reveal --


def test_it_stays_empty_with_no_clerk_and_no_override(monkeypatch):
    """The zero-secret default — the posture CI's container boots in.

    `admin_access_open()` is false unless ALLOW_UNGATED_ADMIN is set, so the
    section stays empty on a stock deploy with no Clerk keys. That matches the
    pages, which fail closed in exactly the same situation.
    """
    monkeypatch.delenv("ALLOW_UNGATED_ADMIN", raising=False)
    assert render_admin_section("navbar-admin-desktop") == (None, None)


def test_the_ungated_override_fills_it(app_module, monkeypatch):
    """Proves the predicate is consulted rather than the section hard-coded
    empty. Without this, a section that was simply never filled would pass
    every other test in this file."""
    monkeypatch.setenv("ALLOW_UNGATED_ADMIN", "1")
    desktop, mobile = render_admin_section("navbar-admin-desktop")
    assert desktop is not None and mobile is not None
    assert "/admin/control-board" in _hrefs(desktop)
    assert "/admin/traffic" in _hrefs(desktop)


def test_it_fills_for_an_admin_user_and_stays_empty_for_everyone_else(
    app_module, monkeypatch
):
    """The signed-in case, with Clerk reporting enabled.

    `is_admin_user` is patched rather than a Clerk session faked: the point
    being pinned is that the callback delegates to the SAME predicate the
    admin pages use, not that Clerk works.
    """
    import lib.auth as auth

    monkeypatch.setenv("ALLOW_UNGATED_ADMIN", "")
    monkeypatch.setattr(auth, "clerk_enabled", lambda: True)

    monkeypatch.setattr(auth, "is_admin_user", lambda user=None: True)
    assert render_admin_section("navbar-admin-desktop")[0] is not None

    monkeypatch.setattr(auth, "is_admin_user", lambda user=None: False)
    assert render_admin_section("navbar-admin-desktop") == (None, None)


def test_the_owner_email_is_always_an_admin():
    """`is_admin_user` folds OWNER_EMAIL in, so the nav is owner-only by default.

    With ADMIN_EMAILS unset — the state this deployment is in — the allowlist
    reduces to the owner's address alone, which is the requested behaviour.
    Using the pages' own predicate rather than a literal comparison means
    adding an ADMIN_EMAILS entry later updates the nav and the gate together,
    instead of leaving a link that lies about access.
    """
    from lib.auth import OWNER_EMAIL, is_admin_user

    class _User:
        def __init__(self, email):
            self.email = email
            self.user_id = ""

    assert is_admin_user(_User(OWNER_EMAIL)) is True
    assert is_admin_user(_User(OWNER_EMAIL.upper())) is True, "must be case-insensitive"
    assert is_admin_user(_User("someone-else@example.com")) is False
    assert is_admin_user(None) is False


def _admin_dependency(app):
    """The admin callback's entry in the serialised dependency list.

    `prevent_initial_call` is recorded on `app._callback_list`, NOT in
    `app.callback_map` — the map's values carry the handler and its I/O spec
    and have no such key, so reading it there returns None for every callback
    and an assertion against it can only ever fail. Both structures are also
    empty until `_setup_server()` runs, which is why this takes `client`:
    module-level `@callback` registers into Dash's global registry and only
    transfers to the app on the first request.
    """
    matches = [
        cb for cb in app._callback_list
        if "navbar-admin" in json.dumps(cb.get("output"))
    ]
    assert matches, "the admin section callback is not registered"
    assert len(matches) == 1, f"expected one admin callback, found {len(matches)}"
    return matches[0]


def test_the_admin_callback_fires_on_first_load(app, client):
    """This app sets `prevent_initial_callbacks=True` globally, and the
    callback's only Input is a component `id` — a property that never changes
    again. If the initial call were suppressed this callback would fire
    NEVER and the Admin section would be permanently empty, for the owner
    too. Measured False (i.e. it does fire); pinned so it stays that way.
    """
    client.get("/")  # force _setup_server() before inspecting the registry
    assert _admin_dependency(app).get("prevent_initial_call") is False, (
        "the admin section would never be filled on a page the owner loads "
        "directly — which is the page they signed in to"
    )


def test_one_callback_covers_both_shells(app, client):
    """One callback, two Outputs — not two callbacks that can drift apart."""
    client.get("/")
    output = json.dumps(_admin_dependency(app)["output"])
    assert "navbar-admin-desktop" in output and "navbar-admin-mobile" in output


# ------------------------------------------------------------- the real gate --


def test_the_board_itself_still_fails_closed(client):
    """The link is cosmetic; this is the check that actually protects anything.

    In the zero-secret suite Clerk is off and ALLOW_UNGATED_ADMIN is unset, so
    the board must not render its controls to an anonymous visitor.
    """
    response = client.get("/admin/control-board")
    assert response.ok, "the route should answer, then refuse"
    assert "cb-vis" not in response.text, (
        "the control board served its visibility switches to an anonymous "
        "visitor — the page is no longer failing closed"
    )


def test_the_admin_pages_are_still_hidden_from_agents(client):
    """Unchanged by this work, and worth re-asserting beside it."""
    assert client.get("/admin/control-board/llms.txt").status == 404
    assert client.get("/admin/traffic/llms.txt").status == 404
