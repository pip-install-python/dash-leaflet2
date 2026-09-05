"""1.6.44 item 20 — the ledger block, measured rather than declared.

THIS HOST PAID FOR THIS ITEM. leaflet ran for weeks with a disk DECLARED in
render.yaml and no disk actually attached, and nothing on the wire could
contradict the declaration: the ledger was being written to the container
filesystem and thrown away on every redeploy, while the blueprint said
otherwise and every other health signal was green.

So `persistent` is MEASURED. True iff the resolved ledger path lies OUTSIDE the
repository root — on a mounted disk such as `/var/data/...`. A path under the
app tree is the container filesystem and reads false EVEN WHERE A BLUEPRINT
DECLARES A DISK. A boolean that reports the deployment's INTENTION is worth
nothing; this one reports the filesystem.
"""

from __future__ import annotations

import json
import pathlib

import pytest

import lib.health as health
from conftest import live_source

REPO = pathlib.Path(__file__).resolve().parent.parent


def test_the_block_has_exactly_the_four_keys():
    ledger = health.health_payload("flask")["ledger"]

    assert set(ledger) == {"path", "persistent", "visits", "reads"}, sorted(ledger)


def test_row_contents_never_appear():
    """Counts, a boolean and a path. A health endpoint is not where anyone
    should learn who visited."""
    ledger = health.health_payload("flask")["ledger"]

    assert isinstance(ledger["visits"], int)
    assert isinstance(ledger["reads"], int)
    assert isinstance(ledger["persistent"], bool)
    blob = json.dumps(ledger)
    for leak in ("user_agent", "ip_address", "visitor_key", "Mozilla"):
        assert leak not in blob, f"{leak} leaked into the health payload"


# --------------------------------------------------------------------------
# persistent, BOTH directions.
# --------------------------------------------------------------------------

def test_a_path_inside_the_repo_is_not_persistent(tmp_path, monkeypatch):
    """The failure this host actually had: a declared disk that was not there.

    A ledger under the app tree is the container filesystem, whatever
    render.yaml says.
    """
    inside = REPO / "visitor_analytics.json"
    monkeypatch.setattr("lib.analytics_tracker.analytics_path", lambda: inside)

    ledger = health._ledger_block()

    assert ledger["persistent"] is False, (
        f"a path inside the repo root reported persistent: {ledger['path']}"
    )


def test_a_path_outside_the_repo_is_persistent(tmp_path, monkeypatch):
    """The other direction, without which the boolean could be hardwired False
    and pass every test above."""
    outside = tmp_path / "var" / "data" / "visitor_analytics.json"
    outside.parent.mkdir(parents=True)
    monkeypatch.setattr("lib.analytics_tracker.analytics_path", lambda: outside)

    ledger = health._ledger_block()

    assert ledger["persistent"] is True, (
        f"a mounted-disk path reported non-persistent: {ledger['path']}"
    )


def test_the_two_paths_really_differ(tmp_path):
    """Non-vacuity for the pair: if tmp_path were inside the repo the two
    tests above would be asserting the same thing twice."""
    assert not str(tmp_path).startswith(str(REPO)), (
        f"tmp_path {tmp_path} is inside the repo — the flip test is vacuous"
    )


# --------------------------------------------------------------------------
# The counts, and the failure modes.
# --------------------------------------------------------------------------

def test_the_counts_are_read_from_the_file_the_tracker_writes(tmp_path, monkeypatch):
    ledger_file = tmp_path / "visitor_analytics.json"
    ledger_file.write_text(json.dumps({
        "visits": [{"path": "/"}, {"path": "/a"}, {"path": "/b"}],
        "reads": [{"path": "/llms.txt"}],
    }))
    monkeypatch.setattr("lib.analytics_tracker.analytics_path", lambda: ledger_file)

    ledger = health._ledger_block()

    assert (ledger["visits"], ledger["reads"]) == (3, 1), ledger


def test_a_missing_file_is_zeros_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "lib.analytics_tracker.analytics_path", lambda: tmp_path / "nope.json"
    )
    ledger = health._ledger_block()

    assert (ledger["visits"], ledger["reads"]) == (0, 0)
    assert ledger["path"], "the path is still reported so a reader can look"


def test_a_corrupt_ledger_does_not_break_the_probe(tmp_path, monkeypatch):
    """A diagnostic that can take the health probe down with it is a
    liability — and a half-written file is the normal state during a flush."""
    broken = tmp_path / "visitor_analytics.json"
    broken.write_text('{"visits": [{"path": "/"')
    monkeypatch.setattr("lib.analytics_tracker.analytics_path", lambda: broken)

    ledger = health._ledger_block()

    assert ledger["visits"] == 0
    assert ledger["path"]


def test_healthz_still_answers_200_when_the_ledger_is_unreadable(
    client, monkeypatch
):
    """End to end: the route, not the helper."""
    def boom():
        raise RuntimeError("disk gone")

    monkeypatch.setattr("lib.analytics_tracker.analytics_path", boom)
    response = client.get("/healthz")

    assert response.status == 200
    assert json.loads(response.text)["ok"] is True


# --------------------------------------------------------------------------
# The wire, on whichever lane answers.
# --------------------------------------------------------------------------

def test_the_block_reaches_the_wire(client):
    """Item 20 carries item 1's fix: every key `health_payload` produces must
    reach the served JSON.

    This repo has no pydantic `response_model` on /healthz — the FastAPI lane
    returns a bare JSONResponse — so nothing filters undeclared keys here. The
    assertion is on the WIRE anyway, because that is where the template's
    defect was invisible: `llms_version` was in the payload dict and absent
    from the response for as long as it had existed.
    """
    served = json.loads(client.get("/healthz").text)

    assert "ledger" in served, "the ledger block does not reach the wire"
    assert set(served["ledger"]) == {"path", "persistent", "visits", "reads"}


def test_no_response_model_is_filtering_this_lane():
    """Source-pinned, because a behavioural test cannot tell 'no model' from
    'a model that happens to declare every key today'."""
    # PARSED, not read (item 13, and this is its third sighting in this
    # stack): item 1's comment in lib/health.py EXPLAINS what a response_model
    # would do, so a raw read matches the explanation of the absence.
    source = live_source(REPO / "lib" / "health.py")

    assert "response_model" not in source, (
        "a response_model appeared on /healthz — it must declare the known "
        "keys AND set ConfigDict(extra='allow'), or it will silently drop "
        "every field added after it"
    )
    assert not (REPO / "lib" / "asgi_routes.py").exists(), (
        "lib/asgi_routes.py now exists — the template serves its typed "
        "/healthz from there, and item 20's response-model guard becomes "
        "load-bearing for this fork too"
    )


@pytest.mark.parametrize("backend", ["flask", "fastapi", "quart"])
def test_every_backend_renders_the_same_block(backend):
    """A probe contract that varies by backend is not a contract."""
    ledger = health.health_payload(backend)["ledger"]

    assert set(ledger) == {"path", "persistent", "visits", "reads"}
