"""The Control Board's navigation entry, and what it is allowed to imply.

The link is cosmetic and must stay that way. `/admin/control-board` gates
itself twice — `pages/control_board.layout()` re-checks on every render and the
mutating callback re-checks before changing anything — and it fails CLOSED when
Clerk is unavailable. So these tests are not about access control; they are
about a link that would otherwise either advertise an admin surface to every
reader, or hide it from someone who can legitimately open it.

The default asserted here is HIDDEN, in the same zero-secret posture CI's
container runs: no Clerk, `admin_access_open()` false. A test that only checked
the visible case would pass just as happily against a section hard-coded open.
"""

from __future__ import annotations

import json

from components.navbar import ADMIN_NAV_ID, _reveal_admin_nav, create_content


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


def _admin_nodes(tree):
    return [
        c for c in _walk(tree)
        if isinstance(getattr(c, "id", None), dict)
        and c.id.get("type") == ADMIN_NAV_ID
    ]


def _hrefs(tree):
    return [h for h in (getattr(c, "href", None) for c in _walk(tree)) if h]


# --------------------------------------------------------------- the section --


def test_the_admin_section_exists_in_both_shells(pages):
    """The desktop navbar and the mobile drawer each render their own copy.

    They cannot share a plain string id, which is why the id is a dict. If the
    two ever collide, Dash raises a duplicate-id error at layout validation and
    the whole site fails to render — so this also guards the boot.
    """
    entries = [entry for _p, _n, entry in pages]
    navbar_nodes = _admin_nodes(create_content(entries, loc="navbar"))
    drawer_nodes = _admin_nodes(create_content(entries, loc="drawer"))

    assert len(navbar_nodes) == 1, "the navbar has no Admin section"
    assert len(drawer_nodes) == 1, "the drawer has no Admin section"
    assert navbar_nodes[0].id != drawer_nodes[0].id, "both shells share one id"


def test_the_admin_section_is_hidden_before_any_callback_runs(pages):
    """The rendered default, which is what an anonymous visitor is served.

    If this were ever `{}`, every reader would see a Control Board link until
    the reveal callback happened to run — and on a page load that beats the
    callback, they would see it permanently.
    """
    entries = [entry for _p, _n, entry in pages]
    for loc in ("navbar", "drawer"):
        node = _admin_nodes(create_content(entries, loc=loc))[0]
        assert node.style == {"display": "none"}, f"{loc} ships the link visible"


def test_the_control_board_is_not_in_the_documentation_sections(pages):
    """It must appear once, in its own gated section — never among the docs."""
    entries = [entry for _p, _n, entry in pages]
    content = create_content(entries, loc="navbar")
    admin_node = _admin_nodes(content)[0]

    everywhere = _hrefs(content).count("/admin/control-board")
    inside_gate = _hrefs(admin_node).count("/admin/control-board")
    assert everywhere == 1, f"the board is linked {everywhere} times"
    assert inside_gate == 1, "the board's link is outside the gated section"


# --------------------------------------------------------------- the reveal --


def _run_reveal(monkeypatch, *, n_outputs=2):
    """Invoke the callback with a stubbed `ctx.outputs_list`.

    The callback returns one style per matched component, and outside a real
    request `ctx.outputs_list` is empty — which would make it return `[]` and
    every assertion below vacuous.
    """
    import components.navbar as navbar

    class _Ctx:
        outputs_list = [
            {"id": {"type": ADMIN_NAV_ID, "loc": loc}, "property": "style"}
            for loc in ("navbar", "drawer")[:n_outputs]
        ]

    monkeypatch.setattr(navbar, "ctx", _Ctx)
    return _reveal_admin_nav("/")


def test_it_stays_hidden_with_no_clerk_and_no_override(monkeypatch):
    """The zero-secret default — the posture CI's container boots in.

    `admin_access_open()` is false unless ALLOW_UNGATED_ADMIN is set, so the
    link stays hidden on a stock deploy with no Clerk keys. That matches the
    page, which fails closed in exactly the same situation.
    """
    monkeypatch.delenv("ALLOW_UNGATED_ADMIN", raising=False)
    assert _run_reveal(monkeypatch) == [{"display": "none"}] * 2


def test_the_ungated_override_reveals_it(monkeypatch):
    """Proves the predicate is consulted rather than the style hard-coded.

    Without this, a section that was simply never revealed would pass every
    other test in this file.
    """
    monkeypatch.setenv("ALLOW_UNGATED_ADMIN", "1")
    assert _run_reveal(monkeypatch) == [{}] * 2


def test_it_reveals_for_an_admin_user_and_hides_for_everyone_else(monkeypatch):
    """The signed-in case, with Clerk reporting enabled.

    `is_admin_user` is patched rather than a Clerk session faked: the point
    being pinned is that the callback delegates to the SAME predicate the
    control board uses, not that Clerk works.
    """
    import components.navbar as navbar
    import lib.auth as auth

    monkeypatch.setattr(auth, "clerk_enabled", lambda: True)

    monkeypatch.setattr(auth, "is_admin_user", lambda user=None: True)
    assert _run_reveal(monkeypatch) == [{}] * 2

    monkeypatch.setattr(auth, "is_admin_user", lambda user=None: False)
    assert _run_reveal(monkeypatch) == [{"display": "none"}] * 2
    assert navbar.ADMIN_NAV_ID  # module still importable after patching


def test_the_owner_email_is_always_an_admin():
    """`is_admin_user` folds OWNER_EMAIL in, so the nav is owner-only by default.

    With ADMIN_EMAILS unset — the state this deployment is in — the allowlist
    reduces to the owner's address alone, which is the requested behaviour.
    Using the page's own predicate rather than a literal comparison means
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


def test_the_board_is_still_hidden_from_agents(client):
    """Unchanged by this work, and worth re-asserting beside it."""
    assert client.get("/admin/control-board/llms.txt").status == 404


def _reveal_dependency(app):
    """The reveal callback's entry in the serialised dependency list.

    `prevent_initial_call` is recorded on `app._callback_list`, NOT in
    `app.callback_map` — the map's values carry the handler and its I/O spec
    and have no such key, so reading it there returns None for every callback
    and an assertion against it can only ever fail. Both structures are also
    empty until `_setup_server()` runs, which is why these tests take `client`:
    module-level `@callback` registers into Dash's global registry and only
    transfers to the app on the first request.
    """
    matches = [
        cb for cb in app._callback_list
        if ADMIN_NAV_ID in json.dumps(cb.get("output"))
    ]
    assert matches, "the reveal callback is not registered"
    assert len(matches) == 1, f"expected one reveal callback, found {len(matches)}"
    return matches[0]


def test_the_reveal_callback_fires_on_first_load(app, client):
    """The app sets `prevent_initial_callbacks=True` globally.

    Without the per-callback opt-out the section stays hidden until the visitor
    navigates — including for the owner, on the page they signed in to, which
    is the page they are most likely to be looking at.
    """
    client.get("/")  # force _setup_server() before inspecting the registry
    assert _reveal_dependency(app).get("prevent_initial_call") is False, (
        "the reveal callback would not fire on first load"
    )


def test_the_pattern_output_covers_every_shell(app, client):
    """One callback, both copies — an ALL output rather than two callbacks."""
    client.get("/")
    output = _reveal_dependency(app)["output"]
    assert "ALL" in json.dumps(output), (
        f"{output} is not a pattern-matching output; the drawer's copy would "
        "never be revealed"
    )
