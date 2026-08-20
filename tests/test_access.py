"""Access control — the checks that justify this design over the simpler ones.

The package already covers the six-surface gate matrix in its own suite. What
is new *here* is the resolution, which has three inputs on this site and two
on the boilerplate: a control-board override, a frontmatter registration, and
the hub's ceiling — then a local Clerk session answering for a person in a
browser, or a hub call answering for an agent with a key. So these tests
concentrate on the seams, and specifically on what happens when the hub is
unavailable.

From AUTH-NETWORK.md, checks 1 and 3 are the point:

    1. Signed-in browser, hub UNREACHABLE  -> still allowed (local resolution)
    3. Agent with valid key, hub down      -> gated, not 500, not prose

If 1 fails, every satellite's availability is coupled to one host for no
benefit. If 3 fails, an outage either leaks prose or takes the site down.

`configure_access` is process-wide, so `access_on` saves and restores it —
otherwise a gate configured here would leak into every later test in the
session and the failures would look like anything but the cause. Note the
teardown re-runs `configure(force=True)`: unlike the boilerplate, run.py wires
the policy unconditionally, so leaving the package reset would take the gate
off the app for every test that follows.
"""

from __future__ import annotations

import re

import pytest

from conftest import CRAWLER_UA
from lib import access, auth, hub_client, page_tiers, page_visibility
from lib.network_directory import peers_for

# Two real documentation pages. GATED_PAGE is whatever the tests move around;
# PUBLIC_PAGE stays public so the "never reaches the session or the hub"
# assertions have something to prove it on.
GATED_PAGE = "/flyto"
PUBLIC_PAGE = "/pointer-events"
VALID_KEY = "k2p_testref_testsig"

# Every 2plot origin except this one. A key must never travel to any of them.
#
# Full ORIGINS, not bare hosts: `2plot.dev` is a substring of this site's own
# `leaflet.2plot.dev`, so a host-substring match flags same-origin links —
# which legitimately DO carry the key (that is `access.link_suffix`, the reason
# an authorised agent can follow the index one hop). `https://2plot.dev` does
# not appear inside `https://leaflet.2plot.dev`, so the origin form separates
# the two cleanly.
PEER_ORIGINS = [p["url"].rstrip("/") for p in peers_for("https://leaflet.2plot.dev")]


def _snapshot():
    return (
        page_tiers.registered(),
        dict(page_tiers._LOCAL_LLMS_PUBLIC),
        {path: dict(entry) for path, entry in page_visibility._overrides.items()},
    )


def _restore(snapshot):
    tiers, llms, overrides = snapshot
    page_tiers._LOCAL_TIERS.clear()
    page_tiers._LOCAL_TIERS.update(tiers)
    page_tiers._LOCAL_LLMS_PUBLIC.clear()
    page_tiers._LOCAL_LLMS_PUBLIC.update(llms)
    page_visibility._overrides.clear()
    page_visibility._overrides.update(overrides)


@pytest.fixture
def restore_tiers():
    """Any test that registers a tier outside `access_on` must clean up, or the
    inertness assertion below sees a gate a later reader cannot explain."""
    saved = _snapshot()
    yield
    _restore(saved)


class FakeUser:
    """Stands in for ClerkUser. Only the attributes lib/auth reads."""

    def __init__(self, email="reader@example.com", user_id="user_1",
                 session_id="sess_1", plan=None):
        self.email = email
        self.user_id = user_id
        self.session_id = session_id
        self.plan = plan


@pytest.fixture
def access_on(app_module, monkeypatch):
    """Turn gating on for one test, then put the process back as it was."""
    import dash_improve_my_llms as pkg
    from dash_improve_my_llms import access as pkg_access

    saved = _snapshot()
    # llms_public=False: these tests exercise a machine lane that actually
    # gates. The default-open axis (the data-window posture) has its own
    # section below.
    page_tiers.register(GATED_PAGE, "auth", llms_public=False)
    hub_client.clear_cache()
    access.configure(force=True)
    try:
        yield pkg
    finally:
        # The package ships reset() for exactly this; using it rather than
        # restoring _config by hand means the teardown cannot drift from
        # whatever configure_access sets next release. Then re-wire, because
        # this app boots with the policy installed.
        pkg_access.reset()
        _restore(saved)
        hub_client.clear_cache()
        access.configure(force=True)


@pytest.fixture
def hub_down(monkeypatch):
    """Every hub call fails, the way a real outage does: no exception escapes."""
    def unreachable(route, payload, timeout):
        return None

    monkeypatch.setattr(hub_client, "_post", unreachable)
    monkeypatch.setattr(hub_client, "enabled", lambda: True)
    hub_client.clear_cache()


@pytest.fixture
def hub_allows(monkeypatch):
    def allow(route, payload, timeout):
        return {"verdict": "allow", "ttl": 60}

    monkeypatch.setattr(hub_client, "_post", allow)
    monkeypatch.setattr(hub_client, "enabled", lambda: True)
    hub_client.clear_cache()


def signed_in(monkeypatch, user=None):
    monkeypatch.setattr(auth, "clerk_enabled", lambda: True)
    monkeypatch.setattr(auth, "current_user", lambda: user or FakeUser())


def anonymous(monkeypatch):
    monkeypatch.setattr(auth, "clerk_enabled", lambda: True)
    monkeypatch.setattr(auth, "current_user", lambda: None)


# ---------------------------------------------------------------------------
# The two checks that justify the design
# ---------------------------------------------------------------------------


def test_signed_in_browser_is_allowed_while_the_hub_is_unreachable(
    access_on, hub_down, monkeypatch
):
    """Check 1. The reason Clerk runs on satellites at all.

    Without local resolution every access decision needs the hub, so one host
    being down gates every restricted document on all twenty subdomains.
    """
    signed_in(monkeypatch)
    assert access.check(GATED_PAGE) == "allow"


def test_agent_with_a_key_is_gated_when_the_hub_is_down(
    access_on, hub_down, monkeypatch
):
    """Check 3. Not 500, not prose — gated."""
    anonymous(monkeypatch)
    monkeypatch.setattr(access, "_request_key", lambda: VALID_KEY)
    assert access.check(GATED_PAGE) == "gated"


def test_agent_with_a_valid_key_is_allowed_when_the_hub_answers(
    access_on, hub_allows, monkeypatch
):
    """Check 2."""
    anonymous(monkeypatch)
    monkeypatch.setattr(access, "_request_key", lambda: VALID_KEY)
    assert access.check(GATED_PAGE) == "allow"


def test_the_hub_is_not_consulted_for_a_signed_in_reader(access_on, monkeypatch):
    """Local-first is an ordering claim; this asserts the ordering itself.

    A passing check-1 could also be produced by a hub that happened to allow.

    "Zero hub calls" means the per-reader agent-key endpoints. The page-tiers
    feed is different in kind: one cached per-app fetch per TTL, consulted for
    every path (a hub ceiling must bind even on locally-public pages), and its
    failure resolves to the local tier — so it never couples a signed-in
    reader's access to hub availability, which is what this test protects.
    """
    calls = []
    monkeypatch.setattr(hub_client, "_post", lambda *a, **k: calls.append(a) or None)
    monkeypatch.setattr(hub_client, "enabled", lambda: True)
    signed_in(monkeypatch)
    assert access.check(GATED_PAGE) == "allow"
    agent_key_calls = [c for c in calls if "/api/agent-key/" in c[0]]
    assert agent_key_calls == [], "a signed-in reader triggered a per-reader hub call"


# ---------------------------------------------------------------------------
# Tiers, degradation and the hub ceiling
# ---------------------------------------------------------------------------


def test_public_pages_never_reach_the_session_or_the_hub(access_on, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda: pytest.fail("session consulted"))
    monkeypatch.setattr(hub_client, "_post", lambda *a, **k: pytest.fail("hub consulted"))
    assert access.check(PUBLIC_PAGE) == "allow"


def test_admin_tier_gates_a_signed_in_non_admin(access_on, monkeypatch):
    page_tiers.register(GATED_PAGE, "admin")
    signed_in(monkeypatch)
    monkeypatch.setattr(auth, "is_admin_user", lambda user=None: False)
    assert access.check(GATED_PAGE) == "gated"
    monkeypatch.setattr(auth, "is_admin_user", lambda user=None: True)
    assert access.check(GATED_PAGE) == "allow"


def test_hidden_is_deny_even_with_a_session(access_on, monkeypatch):
    page_tiers.register(GATED_PAGE, "hidden")
    signed_in(monkeypatch)
    assert access.check(GATED_PAGE) == "deny"


def test_everything_but_hidden_falls_open_without_clerk(access_on, monkeypatch):
    """Documentation must not brick over a missing credential.

    `hidden` still holds, because it means "there is nothing here" rather than
    "not yet" — and admin surfaces gate on `admin_access_open()`, not on this.
    """
    monkeypatch.setattr(auth, "clerk_enabled", lambda: False)
    for tier, expected in (("auth", "allow"), ("admin", "allow"), ("hidden", "deny")):
        page_tiers.register(GATED_PAGE, tier)
        assert access.check(GATED_PAGE) == expected, tier


def test_the_hub_sets_the_ceiling(restore_tiers):
    """A satellite may restrict further; it may never loosen."""
    page_tiers.register("/x", "public")
    assert page_tiers.effective_tier("/x", "auth") == "auth", "hub ceiling did not hold"
    page_tiers.register("/x", "admin")
    assert page_tiers.effective_tier("/x", "auth") == "admin", "local restriction lost"
    assert page_tiers.effective_tier("/x", None) == "admin", "hub outage changed the tier"


def test_a_hub_published_tier_gates_a_locally_public_page(access_on, monkeypatch):
    """The ceiling, end to end through the real feed: this site says public,
    the hub's /api/page-tiers says auth, an anonymous reader is gated."""
    anonymous(monkeypatch)

    def hub(route, payload, timeout):
        assert route == "/api/page-tiers"
        assert payload == {"app": hub_client.app_id()}
        return {"tiers": {PUBLIC_PAGE: "auth"}, "ttl": 300}

    monkeypatch.setattr(hub_client, "_post", hub)
    monkeypatch.setattr(hub_client, "enabled", lambda: True)
    hub_client.clear_cache()
    assert access.check(PUBLIC_PAGE) == "gated", "hub ceiling not applied"


def test_the_hub_ceiling_binds_a_control_board_override_too(access_on, monkeypatch):
    """The board is the most local input there is, so it is the one that could
    quietly outrank the network. It must not: an operator here may lock a page
    down further, never open one the hub restricted."""
    anonymous(monkeypatch)
    page_visibility._overrides[PUBLIC_PAGE] = {"visibility": "public"}

    monkeypatch.setattr(hub_client, "_post",
                        lambda *a, **k: {"tiers": {PUBLIC_PAGE: "admin"}, "ttl": 300})
    monkeypatch.setattr(hub_client, "enabled", lambda: True)
    hub_client.clear_cache()
    assert access.resolve_page_access(PUBLIC_PAGE) == "sign_in"


def test_the_tier_feed_is_fetched_once_per_ttl_not_per_request(monkeypatch):
    calls = []

    def hub(route, payload, timeout):
        calls.append(route)
        return {"tiers": {"/x": "auth"}, "ttl": 300}

    monkeypatch.setattr(hub_client, "_post", hub)
    monkeypatch.setattr(hub_client, "enabled", lambda: True)
    hub_client.clear_cache()
    for _ in range(5):
        assert hub_client.hub_tiers() == {"/x": "auth"}
    assert len(calls) == 1, "every request paid a hub round trip"


def test_a_failed_tier_fetch_is_cached_and_loosens_nothing(restore_tiers, monkeypatch):
    """An outage answers {} (hub unknown -> local tier holds) and is cached,
    so a down hub costs one timeout per window, not one per request."""
    calls = []
    monkeypatch.setattr(hub_client, "_post", lambda *a, **k: calls.append(a) or None)
    monkeypatch.setattr(hub_client, "enabled", lambda: True)
    hub_client.clear_cache()
    for _ in range(5):
        assert hub_client.hub_tiers() == {}
    assert len(calls) == 1, "a down hub was hammered per-request"
    page_tiers.register("/x", "admin")
    assert page_tiers.effective_tier("/x", hub_client.hub_tiers().get("/x")) == "admin"


def test_a_junk_tier_from_the_hub_cannot_loosen_a_local_tier(restore_tiers):
    page_tiers.register("/x", "admin")
    assert page_tiers.effective_tier("/x", "not-a-tier") == "admin"
    assert page_tiers.effective_tier("/x", "public") == "admin"


# ---------------------------------------------------------------------------
# One resolver, three inputs — this repo's own seam
# ---------------------------------------------------------------------------


def test_a_control_board_override_beats_the_frontmatter_registration(restore_tiers):
    """The whole reason the board survived the unification: a toggle applies on
    the next render, with no restart and no redeploy."""
    page_tiers.register(GATED_PAGE, "public")
    assert access.local_tier(GATED_PAGE) == "public"
    page_visibility._overrides[GATED_PAGE] = {"visibility": "admin"}
    assert access.local_tier(GATED_PAGE) == "admin"


def test_an_untouched_page_falls_through_to_its_frontmatter(restore_tiers):
    """The distinction a merged read cannot make. `get_settings` answers
    "public" for a page nobody configured, which would silently outrank a
    frontmatter `tier: admin` if the resolver used it."""
    page_tiers.register(GATED_PAGE, "admin")
    assert page_visibility.tier_override(GATED_PAGE) is None
    assert access.local_tier(GATED_PAGE) == "admin"


def test_the_board_also_owns_the_machine_axis(restore_tiers):
    page_tiers.register(GATED_PAGE, "auth", llms_public=True)
    assert access.llms_public(GATED_PAGE) is True
    page_visibility._overrides[GATED_PAGE] = {"llms_public": False}
    assert access.llms_public(GATED_PAGE) is False


def test_the_default_tier_env_alias_is_honoured(monkeypatch, restore_tiers):
    """PAGE_DEFAULT_VISIBILITY is this site's older spelling and is set on the
    live service. Dropping it would change the deployment's posture silently."""
    monkeypatch.delenv("PAGE_DEFAULT_TIER", raising=False)
    monkeypatch.setenv("PAGE_DEFAULT_VISIBILITY", "auth")
    assert page_tiers._default_tier() == "auth"
    assert page_visibility.default_tier() == "auth", "board and gate disagree"
    monkeypatch.setenv("PAGE_DEFAULT_TIER", "public")
    assert page_tiers._default_tier() == "public", "canonical key must win"


def test_frontmatter_accepts_tier_and_the_visibility_alias():
    """One declared value, two ledgers — and `tier:` wins a disagreement."""
    from pages.markdown import Meta, _declared_tier

    base = {"name": "x", "description": "d", "endpoint": "/x"}
    assert _declared_tier(Meta(**base), "x.md") is None
    assert _declared_tier(Meta(**base, tier="auth"), "x.md") == "auth"
    assert _declared_tier(Meta(**base, visibility="auth"), "x.md") == "auth"
    assert _declared_tier(Meta(**base, tier="admin", visibility="auth"), "x.md") == "admin"


# ---------------------------------------------------------------------------
# The mint path (nothing calls it on this deployment; forks will)
# ---------------------------------------------------------------------------


def test_current_key_sends_the_token_never_an_asserted_identity(monkeypatch):
    """The hub 401s caller-asserted identity by design — a satellite POSTing
    {"user_id": ...} could claim to be anyone. Only the Clerk session token
    travels, because only Clerk's signature says who the reader is."""
    captured = {}

    def hub(route, payload, timeout):
        captured.update({"route": route, "payload": payload})
        return {"key": "k2p_minted"}

    monkeypatch.setattr(hub_client, "_post", hub)
    monkeypatch.setattr(hub_client, "enabled", lambda: True)
    assert hub_client.current_key("clerk-session-token") == "k2p_minted"
    assert captured["route"] == "/api/agent-key/current"
    assert captured["payload"] == {
        "token": "clerk-session-token", "app": hub_client.app_id()
    }
    assert "user_id" not in captured["payload"]


def test_the_satellite_identifies_itself_as_leaflet(monkeypatch):
    """The hub labels its series, and scopes its page-tier ceilings, by this
    key. A wrong one means this site enforces another app's tiers."""
    monkeypatch.delenv("SATELLITE_APP_KEY", raising=False)
    monkeypatch.delenv("AD_APP_ID", raising=False)
    assert hub_client.app_id() == "leaflet"


def test_current_key_degrades_to_none_when_the_hub_is_down(hub_down):
    """None -> the copy button falls back to the plain URL."""
    assert hub_client.current_key("clerk-session-token") is None
    assert hub_client.current_key("") is None


# ---------------------------------------------------------------------------
# What must never leak
# ---------------------------------------------------------------------------


def test_a_key_never_reaches_the_sitemap_or_canonical_tags(access_on, client):
    """Authority is scoped to the response it arrived in.

    A key in a canonical tag or a sitemap entry would be published to every
    crawler that reads them.
    """
    sitemap = client.get(f"/sitemap.xml?key={VALID_KEY}").text
    assert VALID_KEY not in sitemap

    html = client.get(f"{PUBLIC_PAGE}?key={VALID_KEY}", user_agent=CRAWLER_UA).text
    canonicals = re.findall(r'rel="canonical"\s+href="([^"]*)"', html)
    assert canonicals and all(VALID_KEY not in c for c in canonicals)


def test_a_key_never_reaches_a_peer_host(access_on, client):
    """The directory points at other origins; a capability must not travel."""
    assert PEER_ORIGINS, "the peer list resolved empty — this test would prove nothing"
    body = client.get(f"/llms.txt?key={VALID_KEY}").text
    for line in body.splitlines():
        if any(origin in line for origin in PEER_ORIGINS):
            assert VALID_KEY not in line, f"key leaked to a peer link: {line}"


def test_the_cache_never_stores_the_key_itself():
    hub_client.clear_cache()
    hub_client._cache_put(hub_client._fingerprint(VALID_KEY), "/x", "allow", 60)
    assert all(VALID_KEY not in str(k) for k in hub_client._VERDICT_CACHE)


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def test_markdown_is_byte_identical_with_and_without_a_signed_in_reader(
    access_on, client, monkeypatch
):
    """Check 5. Identity is chrome for people; it must cost an agent nothing."""
    anonymous(monkeypatch)
    anonymous_body = client.get(f"{PUBLIC_PAGE}/llms.txt").text
    signed_in(monkeypatch)
    signed_in_body = client.get(f"{PUBLIC_PAGE}/llms.txt").text
    assert anonymous_body == signed_in_body


def test_viewer_identity_uses_session_first_seen_not_the_token_iat(monkeypatch):
    """A Clerk session token refreshes about every 60 seconds, so its `iat`
    renders a "signed in since" clock that resets. This must be stable."""
    monkeypatch.setattr(auth, "clerk_enabled", lambda: True)
    monkeypatch.setattr(auth, "current_user", lambda: FakeUser(session_id="sess_stable"))
    auth._SESSION_FIRST_SEEN.clear()
    first = auth.viewer_identity()
    second = auth.viewer_identity()
    assert first["since"] == second["since"]
    assert first["name"] == "reader@example.com"


def test_viewer_identity_is_none_when_nobody_is_signed_in(monkeypatch):
    monkeypatch.setattr(auth, "clerk_enabled", lambda: True)
    monkeypatch.setattr(auth, "current_user", lambda: None)
    assert auth.viewer_identity() is None


# ---------------------------------------------------------------------------
# Wiring
# ---------------------------------------------------------------------------


def test_the_policy_is_wired_at_boot_even_though_every_page_is_public():
    """The dark launch, asserted. The auto-detect would skip this deployment —
    every tier is public in the test posture — so run.py forces it, and the
    verdict path is live before PAGE_DEFAULT_TIER ever flips.
    """
    assert not access.gating_configured(), "a test left a non-public tier behind"
    assert access.configure() is False, "auto-detect should still decline"
    assert access.configured(), "run.py must wire the policy regardless"


def test_a_check_that_raises_degrades_to_gated(access_on, monkeypatch):
    """The package's fail-safe, asserted from this side of the contract.

    Not `allow` — a bug in this repo's policy must not publish gated prose.
    Not `deny` — a bug must not black-hole every document on the site.
    """
    from dash_improve_my_llms import access as pkg_access

    def boom(path):
        raise RuntimeError("policy bug")

    monkeypatch.setattr(pkg_access._config, "check", boom)
    assert pkg_access.resolve(GATED_PAGE) == "gated"


# ---------------------------------------------------------------------------
# The second axis: llms_public — "interactive gated, machine open"
# ---------------------------------------------------------------------------


def test_interactive_gated_machine_open_is_the_window_contract(access_on, monkeypatch):
    """THE contract of the data-window posture, in one test: the same
    anonymous request is gated in a browser and allowed on the machine lane.
    Do not "fix" either half — the split is the design (the prose is
    anonymously fetchable at /<page>/llms.txt by decision, while the
    interactive experience funnels through the sign-in card)."""
    page_tiers.register(GATED_PAGE, "auth")  # llms_public -> env default: open
    anonymous(monkeypatch)
    assert access.check(GATED_PAGE) == "allow"
    assert access.resolve_page_access(GATED_PAGE) == "sign_in"


def test_llms_public_false_gates_the_anonymous_machine_fetch(access_on, monkeypatch):
    """The phase-4 posture, per page: axis pinned closed, anonymous machine
    fetches meet the gate doc. (access_on registers llms_public=False.)"""
    anonymous(monkeypatch)
    assert access.check(GATED_PAGE) == "gated"


def test_llms_public_default_env_is_the_phase_4_flip(access_on, monkeypatch):
    """LLMS_PUBLIC_DEFAULT=0 flips every page that did not pin the axis —
    the whole agent flip is this env change, no code."""
    page_tiers.register(GATED_PAGE, "auth")  # no pin -> follows the env
    anonymous(monkeypatch)
    assert access.check(GATED_PAGE) == "allow"
    monkeypatch.setenv("LLMS_PUBLIC_DEFAULT", "0")
    assert access.check(GATED_PAGE) == "gated"


def test_an_explicit_llms_public_pin_survives_the_env_flip(access_on, monkeypatch):
    page_tiers.register(GATED_PAGE, "auth", llms_public=True)
    monkeypatch.setenv("LLMS_PUBLIC_DEFAULT", "0")
    anonymous(monkeypatch)
    assert access.check(GATED_PAGE) == "allow"


def test_the_open_axis_never_loosens_a_hub_imposed_gate(access_on, monkeypatch):
    """Hub ceiling says auth, local axis says open — the machine lane stays
    gated. A satellite env default must not expose what the network
    restricted; the exemption is for locally declared gates only."""
    anonymous(monkeypatch)

    def hub(route, payload, timeout):
        return {"tiers": {PUBLIC_PAGE: "auth"}, "ttl": 300}

    monkeypatch.setattr(hub_client, "_post", hub)
    monkeypatch.setattr(hub_client, "enabled", lambda: True)
    hub_client.clear_cache()
    assert access.check(PUBLIC_PAGE) == "gated"


def test_machine_surfaces_follow_the_axis_end_to_end(access_on, client, monkeypatch):
    """Through the real routes: the gate doc when the axis is closed, the
    prose when it is open — same page, same anonymous reader."""
    anonymous(monkeypatch)
    gated_body = client.get(f"{GATED_PAGE}/llms.txt").text
    assert "not public" in gated_body
    page_tiers.register(GATED_PAGE, "auth", llms_public=True)
    open_body = client.get(f"{GATED_PAGE}/llms.txt").text
    assert "not public" not in open_body
    assert open_body != gated_body


def test_the_prerender_carries_the_verdict_not_the_prose(access_on, client, monkeypatch):
    """The leak check. A gated page's browser HTML embeds a prerendered body
    for crawlers and copy-paste; if that block still held the prose, the gate
    would be a client-side illusion and view-source would defeat it."""
    anonymous(monkeypatch)
    html = client.get(GATED_PAGE).text
    assert "not public" in html, "the gate doc never reached the prerender"

    page_tiers.register(GATED_PAGE, "auth", llms_public=True)
    open_html = client.get(GATED_PAGE).text
    assert "not public" not in open_html, "the open axis did not restore the prose"


def test_the_legacy_llms_stub_no_longer_shadows_the_check(access_on, client, monkeypatch):
    """page_visibility used to swap a page's registered prose for a stub. With
    a policy wired, the real prose is registered and the check decides — so an
    AUTHORISED reader gets documentation, not the stub that used to be baked in
    underneath the verdict."""
    signed_in(monkeypatch)
    body = client.get(f"{GATED_PAGE}/llms.txt").text
    assert "not publicly available" not in body, "the legacy stub is still in the registry"


# ---------------------------------------------------------------------------
# resolve_page_access — the interactive verdict
# ---------------------------------------------------------------------------


def test_resolve_page_access_anonymous_matrix(access_on, monkeypatch):
    anonymous(monkeypatch)
    for tier, expected in (("public", "allow"), ("auth", "sign_in"),
                           ("admin", "sign_in"), ("hidden", "hidden")):
        page_tiers.register(GATED_PAGE, tier)
        assert access.resolve_page_access(GATED_PAGE) == expected, tier


def test_resolve_page_access_signed_in_matrix(access_on, monkeypatch):
    signed_in(monkeypatch)
    monkeypatch.setattr(auth, "is_admin_user", lambda user=None: False)
    page_tiers.register(GATED_PAGE, "auth")
    assert access.resolve_page_access(GATED_PAGE) == "allow"
    page_tiers.register(GATED_PAGE, "admin")
    assert access.resolve_page_access(GATED_PAGE) == "forbidden"
    monkeypatch.setattr(auth, "is_admin_user", lambda user=None: True)
    assert access.resolve_page_access(GATED_PAGE) == "allow"


def test_admin_layouts_fail_closed_without_clerk_docs_fall_open(access_on, monkeypatch):
    """The boilerplate's posture, pinned so the retired
    `page_visibility.resolve_access` (which fell fully open without Clerk keys)
    cannot come back through a later port: docs stay readable, admin stays
    sealed."""
    monkeypatch.setattr(auth, "clerk_enabled", lambda: False)
    monkeypatch.setattr(auth, "admin_access_open", lambda: False)
    page_tiers.register(GATED_PAGE, "auth")
    assert access.resolve_page_access(GATED_PAGE) == "allow"
    page_tiers.register(GATED_PAGE, "admin")
    assert access.resolve_page_access(GATED_PAGE) == "forbidden"
    monkeypatch.setattr(auth, "admin_access_open", lambda: True)
    assert access.resolve_page_access(GATED_PAGE) == "allow"


def test_a_key_never_unlocks_a_browser_layout(access_on, hub_allows, monkeypatch):
    """Keys are machine-surface capabilities. A ?key= that opened layouts
    would turn every copied URL into a shareable session."""
    page_tiers.register(GATED_PAGE, "auth", llms_public=False)
    anonymous(monkeypatch)
    monkeypatch.setattr(access, "_request_key", lambda: VALID_KEY)
    assert access.check(GATED_PAGE) == "allow"                   # machine lane: yes
    assert access.resolve_page_access(GATED_PAGE) == "sign_in"   # layout: no


def test_run_py_pins_the_funnel_public(app_module):
    """PAGE_DEFAULT_TIER=auth must never gate the funnel or the corpus
    pseudo-paths — run.py pins them explicitly, and this is the regression net
    for those pins. The home page matters most: it is the one page a
    signed-out visitor has no reason to want an account for yet."""
    for path in ("/", "/llms-small.txt", "/llms-full.txt"):
        assert page_tiers.local_tier(path) == "public", path
    assert page_visibility.get_settings("/")["visibility"] == "public", \
        "the board would show the home page gated while the site serves it"
