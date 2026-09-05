"""1.6.44 item 4 — the fleet probe convention, in both halves.

A PROBE is machinery fetching a network host to check it. The contract is that
it never lands in anybody's ledger, and the mechanism is the User-Agent: the
string carries `INTERNAL_UA_TOKEN`, which every tracker in the fleet drops at
WRITE time, before classification.

THE OUTBOUND HALF WAS ALREADY HERE and the spec's own note says the detect
over-reports because of it — `scripts/` have carried `INTERNAL_UA` since
1.6.40. What was actually missing on this tree, exactly as the ops rider
predicted, was THE WORKFLOWS: five curls across ci.yml and cd.yml sent no
User-Agent at all. They arrive as `curl/8.x`, which classifies crawler-lane
and carries no internal token, so **every CD verification wrote rows into the
production ledger it was verifying** — two of those curls hit `$SITE_URL`,
which is leaflet.2plot.dev.

The rest of the convention is the `/probe` spelling: same token, so suppression
is unchanged, but the far side's log can now tell "a host checking itself"
(`2plot-internal/probe`) from "a host using another host"
(`2plot-internal/1.0`).

This file re-MEASURES the classifier table rather than asserting the template's
recorded claim, per the spec: "port the TEST that re-measures that table, not
the claim". A floor bump is precisely what would move it.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from dash_improve_my_llms import classify
from lib.constants import INTERNAL_UA_TOKEN, PROBE_UA_SUFFIX, probe_ua

REPO = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((REPO / ".github" / "workflows").glob("*.yml"))

ENGINES = {
    "chrome": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "googlebot": (
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    ),
    "curl": "curl/8.7.1",
}


def _facts(ua):
    """(lane, bot_type, vendor_key) from the package's one classifier."""
    r = classify(ua)

    def get(key):
        return r.get(key) if isinstance(r, dict) else getattr(r, key, None)

    return get("lane"), get("bot_type"), get("vendor_key")


# --------------------------------------------------------------------------
# The measured table.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("engine", sorted(ENGINES))
def test_appending_the_suffix_moves_neither_lane_nor_vendor_nor_class(engine):
    """The whole convention rests on this, so it is measured, not quoted.

    If appending the suffix ever changes the classification, every probe in
    the fleet starts exercising a different document than the one it was sent
    to check — and the batteries stay green while asserting about the wrong
    lane.
    """
    bare = ENGINES[engine]
    tagged = probe_ua(bare, "test-suite")

    assert _facts(tagged) == _facts(bare), (
        f"the probe suffix moved the classification of {engine}: "
        f"{_facts(bare)} -> {_facts(tagged)}"
    )


def test_the_table_is_non_vacuous_the_engines_do_not_all_classify_alike():
    """Control for the parametrised test above (note 88).

    If every engine classified identically, the three assertions would pass
    while proving nothing about the suffix. They must differ from each other.
    """
    lanes = {e: _facts(ENGINES[e]) for e in ENGINES}

    assert lanes["chrome"][0] == "browser"
    assert lanes["googlebot"][0] == "crawler"
    assert lanes["googlebot"][2] == "googlebot"
    assert len(set(lanes.values())) >= 2, lanes


def test_an_engineless_probe_is_refused():
    """`probe_ua()` REFUSES rather than returning a crawler-lane string.

    Measured on the resolved package: a UA carrying only the suffix is
    crawler-lane. A browser-lane assertion sent that way silently receives the
    prerendered crawler document and passes against the wrong artifact — the
    failure no amount of reading the probe's output reveals.
    """
    lane, _, _ = _facts(PROBE_UA_SUFFIX)
    assert lane == "crawler", (
        "the premise changed: a suffix-only UA is no longer crawler-lane, so "
        "re-derive whether the refusal below is still the right behaviour"
    )

    for bad in ("", "   ", None):
        with pytest.raises(ValueError):
            probe_ua(bad)


def test_the_probe_ua_carries_the_suppression_token():
    ua = probe_ua(ENGINES["curl"], "network-smoke")
    assert INTERNAL_UA_TOKEN in ua
    assert ua.startswith("curl/8.7.1"), "the engine token must LEAD the string"
    assert ua.endswith("network-smoke")


# --------------------------------------------------------------------------
# The workflows — the half that was actually missing here.
# --------------------------------------------------------------------------

# `curl` calls that are NOT probes of a network host, and are out of scope.
# actionlint's installer fetches a release script from raw.githubusercontent —
# it is not a 2plot host and has no ledger to pollute.
CURL_EXEMPT = ("raw.githubusercontent.com",)

CURL_LINE = re.compile(r"^\s*(?:[a-z_]+=\"?\$\()?\s*(?:if\s+)?curl\b[^\n]*", re.M)


def test_every_workflow_curl_that_probes_a_host_sends_the_probe_ua():
    """The gap this item closed on this tree, pinned so it cannot reopen.

    Before 1.6.44 these five curls sent no User-Agent. Two of them fetch
    `$SITE_URL/healthz` — production — on every CD run.
    """
    assert WORKFLOWS, "no workflow files found: this sweep swept nothing"

    offenders = []
    checked = 0
    for wf in WORKFLOWS:
        for line in CURL_LINE.findall(wf.read_text()):
            if any(x in line for x in CURL_EXEMPT):
                continue
            checked += 1
            if '-A "$PROBE_UA"' not in line:
                offenders.append(f"{wf.name}: {line.strip()}")

    assert checked >= 5, (
        f"only {checked} workflow curls swept — the regex stopped matching and "
        "this test is now green over nothing"
    )
    assert not offenders, "workflow curls with no probe UA:\n" + "\n".join(offenders)


@pytest.mark.parametrize("wf", WORKFLOWS, ids=lambda p: p.name)
def test_the_workflow_probe_ua_literal_matches_the_python_constant(wf):
    """A constant recorded in two places drifts, and the copy nothing imports
    is the one that drifts (the kit's own floor rule, applied to a UA).

    A workflow cannot import `lib.constants`, so the literal is unavoidable —
    what is avoidable is nobody noticing when the two part ways.
    """
    text = wf.read_text()
    declared = re.findall(r'^\s*PROBE_UA:\s*"([^"]+)"', text, re.M)

    probes = [
        line for line in CURL_LINE.findall(text)
        if not any(x in line for x in CURL_EXEMPT)
    ]
    if not probes:
        pytest.skip(f"{wf.name} makes no host probes")

    assert declared, f"{wf.name} uses $PROBE_UA but never defines it"
    for value in declared:
        assert PROBE_UA_SUFFIX in value, (
            f"{wf.name} declares PROBE_UA={value!r}, which does not carry "
            f"{PROBE_UA_SUFFIX!r} — the far side will not suppress it"
        )
        assert not value.startswith(INTERNAL_UA_TOKEN), (
            f"{wf.name}'s PROBE_UA leads with the internal token instead of an "
            "engine token, so it classifies crawler-lane"
        )


# --------------------------------------------------------------------------
# The scripts, and the Dockerfile the rider put in scope.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["network_smoke.py", "smoke_live.py"])
def test_the_batteries_use_the_probe_spelling(name):
    text = (REPO / "scripts" / name).read_text()
    assert "PROBE_UA_SUFFIX" in text or "2plot-internal/probe" in text, (
        f"scripts/{name} still uses the server-to-server spelling"
    )


def test_the_dockerfile_healthcheck_if_present_carries_the_token():
    """RECORDED FINDING: this repo's Dockerfile has NO HEALTHCHECK.

    The ops rider put the Dockerfile HEALTHCHECK in scope for item 4. There is
    nothing to fix here — but a HEALTHCHECK added later would probe
    `/healthz` on a loop forever, so this asserts the convention on the
    instruction if it ever appears rather than leaving a silent gap.
    """
    text = (REPO / "Dockerfile").read_text()
    healthchecks = [ln for ln in text.splitlines() if ln.strip().startswith("HEALTHCHECK")]

    if not healthchecks:
        pytest.skip("no HEALTHCHECK in this Dockerfile (recorded, 1.6.44 item 4)")

    for line in healthchecks:  # pragma: no cover - none today
        assert INTERNAL_UA_TOKEN in line, (
            "a HEALTHCHECK was added without the probe UA: it polls /healthz "
            "for the life of the container and every poll enters the ledger"
        )
