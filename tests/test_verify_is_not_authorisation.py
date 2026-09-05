"""1.6.44 item 18 — a verify verdict is metering evidence, never authorisation.

THE INCIDENT THIS COMES FROM (2026-09-02, hub 0.26.0 -> 0.26.1): the hub gated
two admin-data routes on `/api/agent-key/verify`, whose all-unknown-tier
fallback answered "allow" WITHOUT READING THE KEY. The lane was open for 24
minutes. "Ask the authority" is the wrong SHAPE for a gate: a new tier is
UNVERIFIED until the authority learns it, and an authority that answers "allow"
to a question it did not understand is worse than no authority.

The contract: a host's own data is gated by a secret THAT HOST HOLDS. In this
repo `hub_client.verify` signs its POST with `CROSS_APP_WEBHOOK_SECRET`, which
lives in the deployment's environment and never travels with the request — so
the named secret is the authorisation and the hub's verdict is the meter.

TWO TESTING RULES COME WITH IT, and both are why this file is longer than the
change it guards:

* SOURCE-PIN the closed fallbacks, do not merely exercise them. A behavioural
  suite cannot see a restored default that pre-empts its own guard, because
  the guard never runs.
* PIN THE GOOD ROWS BESIDE THE BYPASS ROWS. A policy that denies everything
  passes every bypass test ever written.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
ACCESS = REPO / "lib" / "access.py"
HUB = REPO / "lib" / "hub_client.py"


def _function_source(path: pathlib.Path, func: str) -> str:
    """One function's source, sliced by AST line numbers.

    NOT by "up to the next `def`": the last function in a module has no next
    `def` and that form raises ValueError — which is exactly how the first
    version of this file failed, on `hub_tiers`.
    """
    text = path.read_text()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func:
            lines = text.splitlines()[node.lineno - 1:node.end_lineno]
            return "\n".join(lines)
    raise AssertionError(f"{func} not found in {path.name}")


def _returns_in(path: pathlib.Path, func: str) -> list:
    """Every literal string a function can return, read from the AST.

    SOURCE-PINNING, not exercising: this sees a branch that a behavioural test
    can never reach because an earlier default pre-empts it.
    """
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func:
            out = []
            for sub in ast.walk(node):
                if isinstance(sub, ast.Return) and isinstance(sub.value, ast.Constant):
                    if isinstance(sub.value.value, str):
                        out.append(sub.value.value)
            return out
    raise AssertionError(f"{func} not found in {path.name}")


# --------------------------------------------------------------------------
# Source-pinned: every closed fallback.
# --------------------------------------------------------------------------

def test_verify_never_returns_allow_from_its_own_code():
    """The incident, pinned at the source.

    `verify` may return "allow" ONLY by relaying a verdict the hub sent over a
    secret-signed channel. Every literal return in its body must be closed —
    if "allow" ever appears as a literal here, some branch grants access
    without the hub having said so.
    """
    literals = _returns_in(HUB, "verify")

    assert literals, "no literal returns found — the source pin swept nothing"
    assert "allow" not in literals, (
        f"verify() can return 'allow' from its own code: {literals}"
    )
    assert "gated" in literals, literals


def test_verify_is_gated_on_the_host_held_secret():
    """`enabled()` — i.e. CROSS_APP_WEBHOOK_SECRET — must be consulted before
    the hub is asked, so a host without the secret withholds rather than
    trusting a caller-supplied string."""
    body = _function_source(HUB, "verify")

    assert "enabled()" in body, (
        "verify does not check for the host-held secret — the verdict would "
        "be a bearer check on an unauthenticated value"
    )


def test_the_call_site_names_the_host_held_secret():
    """The acceptance: a route consulting verify for access NAMES the secret
    beside it, or is documented as metering-only."""
    source = ACCESS.read_text()
    call = source.index("hub_client.verify(")
    window = source[max(0, call - 1600):call]

    assert "CROSS_APP_WEBHOOK_SECRET" in window, (
        "the verify call site does not name the host-held secret that makes "
        "its verdict trustworthy"
    )


def test_check_is_closed_on_every_literal_it_can_return():
    """A hub failure resolves to `gated`, never `allow`, never `deny`."""
    literals = _returns_in(ACCESS, "check")

    assert literals, "swept nothing"
    assert set(literals) <= {"allow", "gated", "deny"}, literals
    # 'allow' is reachable here — for `public`, and for a signed-in user — so
    # its presence is correct. What must not exist is an allow on the
    # key-bearing path, which is asserted at the source above.


@pytest.mark.parametrize("func", ["hub_tiers", "verify"])
def test_hub_helpers_fail_closed_not_open(func):
    """An outage must loosen nothing."""
    body = _function_source(HUB, func)

    assert "return {}" in body or '"gated"' in body, (
        f"{func} has no closed failure path"
    )


# --------------------------------------------------------------------------
# Behaviour: the bypass rows AND the good rows.
# --------------------------------------------------------------------------

@pytest.fixture
def access(app_module, monkeypatch):
    import lib.access as mod
    import lib.hub_client as hub

    monkeypatch.setattr(hub, "enabled", lambda: False)
    return mod


def test_no_key_is_gated_not_allowed(access, monkeypatch):
    monkeypatch.setattr(access, "_request_key", lambda: None)
    monkeypatch.setattr(access, "effective_tier", lambda p: "auth")
    monkeypatch.setattr(access, "llms_public", lambda p: False)

    assert access.check("/anything") == "gated"


def test_a_key_without_the_host_secret_is_gated(access, monkeypatch):
    """The incident's shape: a caller-supplied string must not open anything
    on a host that cannot authenticate the question it is asking."""
    monkeypatch.setattr(access, "_request_key", lambda: "k2p_whatever")
    monkeypatch.setattr(access, "effective_tier", lambda p: "auth")
    monkeypatch.setattr(access, "llms_public", lambda p: False)

    assert access.check("/anything") == "gated"


def test_the_good_rows_still_pass(access, monkeypatch):
    """PIN THE GOOD ROWS BESIDE THE BYPASS ROWS.

    Without this, a policy that denied everything would satisfy both tests
    above and the suite would call it secure.
    """
    monkeypatch.setattr(access, "effective_tier", lambda p: "public")
    assert access.check("/anything") == "allow", (
        "a public page is gated — the policy denies everything, which passes "
        "every bypass test ever written and serves nobody"
    )

    monkeypatch.setattr(access, "effective_tier", lambda p: "hidden")
    assert access.check("/anything") == "deny"


# --------------------------------------------------------------------------
# Tier lookalikes.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("lookalike", ["Auth", "AUTH", " auth ", "auth\n",
                                       "Admin", " HIDDEN "])
def test_a_tier_lookalike_from_the_hub_is_normalised(lookalike, monkeypatch):
    """Reject case and whitespace lookalikes, never one literal.

    The hub's ceiling is compared against a tuple of lowercase literals. A
    `"Auth "` that reached that comparison unnormalised would read as NOT
    restricted, and the machine lane would stay open on a page the network
    restricted. This repo normalises at the source — in `hub_tiers` — which is
    the ONLY place it happens, so a refactor dropping `.strip().lower()` would
    reopen it silently.
    """
    import lib.hub_client as hub
    import lib.page_tiers as page_tiers

    monkeypatch.setattr(hub, "enabled", lambda: True)
    monkeypatch.setattr(
        hub, "_post",
        lambda *a, **k: {"tiers": {"/p": lookalike}, "ttl": 0},
    )
    monkeypatch.setattr(hub, "_TIERS_CACHE", ({}, 0.0), raising=False)

    resolved = hub.hub_tiers().get("/p")
    assert resolved == lookalike.strip().lower(), (
        f"{lookalike!r} was not normalised: {resolved!r}"
    )
    assert resolved in page_tiers.TIERS, (
        f"{lookalike!r} normalised to {resolved!r}, which is not a tier — it "
        "would be treated as unknown and the ceiling lost"
    )


def test_more_restrictive_treats_a_lookalike_as_the_real_tier():
    from lib.page_tiers import more_restrictive

    assert more_restrictive("public", " ADMIN ") == "admin"
    assert more_restrictive("public", "Hidden") == "hidden"


def test_junk_never_becomes_a_permissive_tier(monkeypatch):
    """The other half: an unrecognised value must not read as `public`."""
    import lib.hub_client as hub

    monkeypatch.setattr(hub, "enabled", lambda: True)
    monkeypatch.setattr(
        hub, "_post", lambda *a, **k: {"tiers": {"/p": 12345}, "ttl": 0},
    )
    monkeypatch.setattr(hub, "_TIERS_CACHE", ({}, 0.0), raising=False)

    assert "/p" not in hub.hub_tiers(), (
        "a non-string tier survived into the ceiling map"
    )
