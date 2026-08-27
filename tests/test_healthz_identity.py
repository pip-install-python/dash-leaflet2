"""What /healthz owes the hub's sweep and the orchestrator's wire check.

Ported from the template's 1.6.10 health work. `tests/test_network_surfaces.py`
already covers that the route answers JSON and names this app; these four pin
the properties that made the round self-verifying — and each one exists
because its absence was invisible from outside.

The through-line: a health endpoint whose payload is a snapshot, or whose
fields vary by backend, is a diagnostic that lies precisely when something is
wrong. Every field here is rebuilt per request, from one function, on every
backend.
"""

from __future__ import annotations

import lib.health as health


def test_the_payload_is_built_per_request_not_snapshotted(client, monkeypatch):
    """The defect this replaced: the route closed over a payload built at
    registration.

    Harmless while every field was static, and silently wrong the moment one
    was not — `geo` is configured long after `/healthz` is registered, so a
    snapshot reports the guardrail unconfigured on a host where it is
    configured. Proven by mutating the environment AFTER the app booted and
    watching the answer change.
    """
    import json

    before = json.loads(client.get("/healthz").text)
    assert before["reporting"] is False, "the suite is not secretless?"

    monkeypatch.setenv("CROSS_APP_WEBHOOK_SECRET", "set-after-boot")
    after = json.loads(client.get("/healthz").text)
    assert after["reporting"] is True, (
        "the payload did not pick up an env change made after registration — "
        "it is a snapshot closed over at registration time"
    )


def test_it_names_which_satellite_answered(client):
    """`build` says which commit; this says which APP.

    Different questions, and on a fleet where every host runs the same
    template and a hostname can be repointed between services, "is this the
    site I think it is?" is the one a wire check cannot answer any other way.
    """
    import json

    payload = json.loads(client.get("/healthz").text)
    assert payload.get("app") == "leaflet", (
        f"healthz names the satellite {payload.get('app')!r}, not 'leaflet'"
    )


def test_it_reports_which_interpreter_is_serving(client):
    """Spec item 5's observability half — the field the battery has teeth on.

    A fork can declare one Python in its Dockerfile and serve another for
    months, because nothing on the wire can contradict either: the template
    carried a patch-pinned 3.11.8 image, a 3.12 matrix and a 3.12.0
    render.yaml simultaneously (ops-seat finding, 2026-08-25). This field is
    what makes the serving interpreter visible;
    `scripts/network_smoke.py::python_matches_declared` compares it to the
    Dockerfile's FROM minor from a seat where the interpreter IS the deploy
    artifact.

    Deliberately NOT asserted here: that the value equals the fleet minor.
    This suite legitimately runs on the CI window legs (3.10, 3.13) and on
    whatever a developer has locally, where that assertion would be false by
    design. Presence and shape are this pin's business; agreement is the
    battery's, against a host.
    """
    import json
    import re

    payload = json.loads(client.get("/healthz").text)
    served = payload.get("python")
    assert served, (
        "healthz carries no `python` field — the serving interpreter is "
        "invisible, and the battery's python_matches_declared has nothing "
        "to compare (spec SYNC-1.6.22-1.6.29 item 5)"
    )
    assert re.fullmatch(r"\d+\.\d+\.\d+", served), (
        f"healthz python is {served!r} — expected a full X.Y.Z from "
        "platform.python_version()"
    )
    assert served.split(".")[0] == "3", f"unexpected major in {served!r}"


def test_build_is_reported_when_the_platform_provides_it(monkeypatch):
    """CD waits on this to confirm the artifact it shipped is the one serving.

    Optional on purpose: omitted where `RENDER_GIT_COMMIT` does not exist, so
    a local run and a fork on another platform keep the same probe contract
    rather than reporting a field they cannot fill.
    """
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    assert "build" not in health.health_payload("flask")

    monkeypatch.setenv("RENDER_GIT_COMMIT", "deadbeef")
    assert health.health_payload("flask")["build"] == "deadbeef"


def test_geo_reports_flags_and_counts_but_never_the_denylist(client):
    """The block that makes a stale image VISIBLE from outside.

    `geo` exists only on dash-improve-my-llms >= 2.7.0, so its ABSENCE on a
    deployed host is the tell that the dependency layer was cached and the
    floor did not actually move — the cache trap, readable without shell
    access. Its presence is equally load-bearing in the other direction:
    counts and flags ONLY. A health endpoint is not where anyone should learn
    which countries a site denies.
    """
    payload = health.health_payload("flask")
    assert "geo" in payload, (
        "no geo block — the running dash-improve-my-llms predates 2.7.0, "
        "which on a deployed host means the image is stale"
    )
    geo = payload["geo"]
    assert set(geo) <= {"configured", "denied", "resolved", "error"}, (
        f"geo leaks keys beyond flags and counts: {sorted(geo)}"
    )
    assert isinstance(geo.get("denied"), int), "denied must be a count"
    assert isinstance(geo.get("configured"), bool)
    # `resolved` is the caller's OWN country reflected back, which
    # Cloudflare's /cdn-cgi/trace already discloses — never the policy.
    assert isinstance(geo.get("resolved", ""), str)


def test_a_broken_geo_probe_cannot_take_down_the_health_check(monkeypatch):
    """A diagnostic that can fail the thing it diagnoses is worse than none.

    The hub reads /healthz to decide whether this satellite is up; an
    exception here would report a live host as down.
    """
    from dash_improve_my_llms import geo

    def boom():
        raise RuntimeError("geo exploded")

    monkeypatch.setattr(geo, "is_configured", boom)
    payload = health.health_payload("flask")
    assert payload["ok"] is True
    assert payload["geo"] == {"configured": False, "denied": 0, "error": True}
