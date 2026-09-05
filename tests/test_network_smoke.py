"""Run the network battery against the in-process app.

`scripts/network_smoke.py` only ever executes in two places a developer never
watches: against the container CI just booted, and against production after a
deploy. That is exactly the code that rots — a typo in a check turns it into a
silent pass and the battery keeps reporting green over a broken host.

So it runs here too, with its `fetch` pointed at the test client. Three
distinct things get proven, and it is worth being explicit about which:

1. the battery's own logic still works (the checks fire, and they can fail);
2. this app satisfies every check the network standard makes of a satellite;
3. the per-site block at the top of the script — the expected H1, the hidden
   paths, the sample page — still matches the app it describes.

What it cannot prove is the deployed artifact, which is the whole reason the
container run and the post-deploy run exist as well.
"""

from __future__ import annotations

import pytest  # noqa: F401  (fixtures come from conftest)

from conftest import BASE, CRAWLER_UA, REPO_ROOT
from lib.constants import INTERNAL_UA_TOKEN, SITE_BRAND


# `battery` and `wired` moved to tests/conftest.py at 1.6.44 item 19, so
# tests/test_robots_posture.py can drive the same harness rather than
# building a second one that would drift from this one.

def test_the_battery_passes_against_this_app(wired, capsys):
    wired.satellite_checks(BASE)
    output = capsys.readouterr().out

    failed = [(name, detail) for name, verdict, detail in wired._RESULTS
              if verdict == wired.FAIL]
    assert failed == [], f"battery failures against the in-process app:\n{output}"
    assert len(wired._RESULTS) >= 9, "checks silently stopped running"


def test_every_request_the_battery_makes_is_internal(wired):
    """A battery that pollutes the ledger it is auditing is worse than none."""
    wired.satellite_checks(BASE)
    untokened = [ua for ua in wired.seen_agents if INTERNAL_UA_TOKEN not in ua]
    assert untokened == [], f"battery sent untokened User-Agents: {untokened}"


def test_the_expected_h1_tracks_the_brand_constant(battery):
    """The per-site block is a copy of `SITE_BRAND`; copies drift."""
    assert battery.SITE_H1 == f"# {SITE_BRAND}"


def test_the_expected_og_image_tracks_the_constant(battery):
    """Same reason: the battery hard-codes the URL so it can run standalone."""
    from lib.constants import OG_IMAGE_URL

    assert battery.OG_IMAGE_URL == OG_IMAGE_URL


def test_the_sample_page_is_a_real_page(battery, page_paths):
    """The battery probes one named page; a rename would make it 404 forever."""
    assert battery.SAMPLE_PAGE in page_paths


def test_the_hidden_paths_are_really_marked_hidden(battery, app_module):
    """A path in the battery's list that is NOT actually hidden makes the
    check pass for the wrong reason — it would 404 for some other cause.

    REWRITTEN (item 18): this asked run.py's SOURCE for `mark_hidden("...")`,
    which was true when run.py marked the only hidden page. It stopped being
    true when pages/traffic.py arrived and marked ITSELF at import, the same
    way pages/control_board.py could. Asking the package's own hidden set
    instead is both simpler and indifferent to which module did the marking —
    a source grep can only ever know the sites it was written to look at.
    """
    from dash_improve_my_llms import is_hidden

    listed = {p.rsplit("/llms.txt", 1)[0] for p in battery.HIDDEN_DOC_PATHS}
    for path in listed:
        if path == "/admin":
            continue  # the canary, deliberately not a registered page
        assert is_hidden(path), (
            f"{path} is in the battery's hidden list but nothing marked it "
            "hidden — the 404 the battery sees has some other cause"
        )


def test_the_battery_reports_a_failure_rather_than_swallowing_it(wired):
    """The check that keeps every other assertion here honest.

    If `check()` ever caught too broadly, the battery would print `pass` for a
    host that is on fire. Break one expectation on purpose and require it to
    be reported.
    """
    wired.SITE_H1 = "# not this site"
    try:
        wired.satellite_checks(BASE)
    finally:
        wired.SITE_H1 = f"# {SITE_BRAND}"

    verdicts = {name: verdict for name, verdict, _ in wired._RESULTS}
    assert verdicts.get("llms_txt_identity") == wired.FAIL


def test_the_default_base_url_matches_the_container_port(battery):
    """CI boots the image and runs the battery with no --base-url."""
    dockerfile = (REPO_ROOT / "Dockerfile").read_text()
    port = battery.DEFAULT_BASE_URL.rsplit(":", 1)[1]
    assert f"EXPOSE {port}" in dockerfile, (
        f"the battery defaults to port {port}; the image exposes something else"
    )
    assert f"PORT={port}" in dockerfile, "the image defaults to a different port"


def test_every_urlopen_in_the_live_tools_carries_an_ssl_context():
    """The source pin for SYNC-1.6.10-1.6.16 item 7, widened to both tools.

    macOS Python ships without OS trust-store integration, so a bare
    `urlopen` fails every https fetch with CERTIFICATE_VERIFY_FAILED. In
    these scripts that does not read as a TLS problem — it reads as the host
    being down: `network_smoke.fetch` re-raises after its retries, and
    `smoke_live.fetch` returns status 0, so a healthy satellite is reported
    unreachable and a seat goes looking at the deploy.

    CI runs on Linux and is BLIND to this by construction, and the wired
    tests monkeypatch the transport — only a source-level pin holds it. The
    template pinned `smoke_live.py` upstream in `tests/test_auth_wiring.py`
    (which this repo does not carry) and MISSED `network_smoke.py`, where
    the same defect sat until 2026-08-27. Hence: both files, checked by AST
    so a mention in a comment cannot satisfy it.
    """
    import ast

    for name in ("network_smoke.py", "smoke_live.py"):
        path = REPO_ROOT / "scripts" / name
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "urlopen"
        ]
        assert calls, f"{name}: no urlopen found — did the transport move?"
        for call in calls:
            kwargs = {kw.arg for kw in call.keywords}
            assert "context" in kwargs, (
                f"{name} line {call.lineno}: urlopen without context= — on "
                "macOS every https fetch fails and the host reads as down"
            )


def test_the_batterys_default_ua_is_browser_lane_and_still_internal():
    """1.6.40 (muischeduler's finding, and this repo's independently): at
    dimll >= 2.8 a UA without a browser engine token is crawler-lane, so a
    default-UA check reads the crawler document. The default names the
    browser lane FIRST and keeps the internal token (a substring match) so
    the tracker still drops it; CRAWLER_UA stays the other lane."""
    from dash_improve_my_llms import classify

    from lib.constants import INTERNAL_UA_TOKEN
    from scripts import network_smoke as ns

    assert classify(ns.UA)["lane"] == "browser"
    assert ns.UA.startswith("Mozilla/5.0") and "AppleWebKit" in ns.UA
    assert INTERNAL_UA_TOKEN in ns.UA and ns.UA.endswith("network-smoke")
    assert classify(ns.CRAWLER_UA)["lane"] == "crawler"
    assert INTERNAL_UA_TOKEN in ns.CRAWLER_UA


# ---------------------------------------------------------------------------
# 1.6.44 item 5 — the four invariants, and the machinery they needed first.
# ---------------------------------------------------------------------------

ITEM_5_INVARIANTS = (
    "head_get_parity_three_uas",
    "api_llms_rows_present",
    "discovery_link_headers_per_lane",
    "directory_counts_are_derived",
)


def test_the_four_invariants_are_registered_by_name(wired, capsys):
    """Registered BY NAME, per the detect — not merely defined.

    A check that exists as a nested function and is never added to the
    registry runs never and fails never.
    """
    wired.satellite_checks(BASE)
    capsys.readouterr()

    ran = {name for name, _, _ in wired._RESULTS}
    missing = [n for n in ITEM_5_INVARIANTS if n not in ran]
    assert not missing, f"registered but never ran: {missing}; ran={sorted(ran)}"


def test_the_four_invariants_pass_against_this_app(wired, capsys):
    wired.satellite_checks(BASE)
    capsys.readouterr()

    verdicts = {name: v for name, v, _ in wired._RESULTS}
    bad = {n: verdicts[n] for n in ITEM_5_INVARIANTS if verdicts[n] == wired.FAIL}
    assert not bad, bad


def test_an_empty_api_packages_SKIPS_and_does_not_pass(wired, capsys, monkeypatch):
    """THE MUTATION THE SPEC ASKS FOR, and the defect it replaces.

    Until 1.6.44 this check answered a 404 with `expect(True, "")` and printed
    `[pass]` — a host serving no /api at all scored a pass on an /api check.
    That is note 88's defect exactly: a sweep that swept nothing is
    indistinguishable from a sweep that found nothing wrong.

    `skip` had to become a real verdict before this could be fixed, so both
    halves are asserted here: the verdict is SKIP, and it is specifically NOT
    PASS.
    """
    import lib.constants as constants

    monkeypatch.setattr(constants, "API_PACKAGES", [])
    wired.satellite_checks(BASE)
    capsys.readouterr()

    verdicts = {name: v for name, v, _ in wired._RESULTS}
    got = verdicts["api_llms_rows_present"]

    assert got == wired.SKIP, (
        f"api_llms_rows_present returned {got!r} with API_PACKAGES empty; "
        "a pass here is a check that swept nothing"
    )
    assert got != wired.PASS


def test_a_non_empty_api_packages_really_passes(wired, capsys):
    """The other direction, so the skip above is not the only outcome.

    Without this, a check hard-wired to skip forever would satisfy the
    mutation test and assert nothing about this host's actual /api.
    """
    from lib.constants import API_PACKAGES

    assert API_PACKAGES, "this host declares no API_PACKAGES — control is void"
    wired.satellite_checks(BASE)
    capsys.readouterr()

    verdicts = {name: v for name, v, _ in wired._RESULTS}
    assert verdicts["api_llms_rows_present"] == wired.PASS


def test_skip_is_a_verdict_of_its_own(battery):
    """`skip()` must not be reachable as a pass or a failure."""
    results = []
    battery_results = battery._RESULTS
    try:
        battery._RESULTS = results

        def skipper():
            battery.skip("precondition absent")

        def passer():
            battery.expect(True, "")

        def failer():
            battery.expect(False, "boom")

        battery.check("skipper", skipper)
        battery.check("passer", passer)
        battery.check("failer", failer)
    finally:
        battery._RESULTS = battery_results

    assert [v for _, v, _ in results] == [battery.SKIP, battery.PASS, battery.FAIL]


def test_the_header_container_keeps_repeats_and_parses_a_folded_value(battery):
    """`get_all()` is necessary and NOT sufficient — measured on this host.

    Two shapes are both legal and both occur. Repeated headers are what a
    plain dict loses; a comma-FOLDED single header is what `get_all()` alone
    cannot count. This host serves the second shape: one `link` header
    carrying both relations, measured in-process.
    """
    import re

    repeated = battery._Headers([
        ("Link", '</llms.txt>; rel="alternate"'),
        ("Link", '</llms.txt>; rel="describedby"'),
        ("Content-Type", "text/html"),
    ])
    assert len(repeated.get_all("link")) == 2, "repeated names collapsed"
    assert repeated["link"] == '</llms.txt>; rel="describedby"', (
        "the dict view should still hold the LAST value, for every existing caller"
    )
    assert repeated["content-type"] == "text/html", "keys are not lower-cased"

    folded = battery._Headers([
        ("Link", '</llms.txt>; rel="alternate", </llms.txt>; rel="describedby"'),
    ])
    assert len(folded.get_all("link")) == 1
    rels = set(re.findall(r'rel="?([a-zA-Z-]+)"?', ", ".join(folded.get_all("link"))))
    assert rels == {"alternate", "describedby"}, (
        "a folded value must be PARSED, not counted — this is the shape this "
        f"host actually serves: {rels}"
    )


def test_this_host_really_folds_its_discovery_relations(client):
    """Pin the measurement the comment above rests on.

    If this host ever starts sending two separate `Link` headers instead, the
    parsing code still works — but the claim in the comment would be stale,
    and a stale measured claim is what the kit's traps section keeps warning
    about.
    """
    import re

    values = client.get("/", user_agent=CRAWLER_UA).header_all("link")
    assert values, "no Link header at all on the crawler lane"

    rels = set(re.findall(r'rel="?([a-zA-Z-]+)"?', ", ".join(values)))
    assert {"alternate", "describedby"} <= rels, rels
    assert len(values) < len(rels), (
        f"{len(values)} Link header(s) carrying {len(rels)} relations — this "
        "host no longer folds them; update the comment in scripts/network_smoke"
    )
