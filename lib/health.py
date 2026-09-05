"""
``/healthz`` liveness probe — the hub's hourly sweep target.

The 2plot.ai hub sweeps every satellite's ``/healthz`` once an hour and records
up/down + latency — that's the "Satellite health & reach" panel on ``/traffic``
(the traffic rollup this app POSTs supplies the other half). render.yaml's
``healthCheckPath`` points here too, so the route must exist on every backend.

Adapted from the boilerplate's ``lib/health.py``: that repo serves the FastAPI
build's ``/healthz`` from ``lib/asgi_routes.py`` (a typed route, so it shows in
Swagger), which has no counterpart in this repo — so this module registers the
route on ALL THREE backends instead of skipping FastAPI.

The payload keeps this app's deployed shape rather than the boilerplate's
minimal one, deliberately:

* ``app`` — the network directory key. ``tests/test_network_surfaces.py`` pins
  it, and the hub labels this app's series from it.
* ``base_url`` — the origin this satellite ADVERTISES, checkable from outside.
  A host that resolved BASE_URL to localhost looks healthy on every other
  signal — pages render, /healthz is 200 — while every canonical link it
  publishes is dead. One curl shows the mismatch. (``require_owned_base_url``
  refuses the worst cases at boot; this covers the rest of the fleet's
  sweep-time checks.)
* ``reporting`` — whether the traffic reporter could actually POST, so "wired
  but secretless" is visible without reading boot logs.
* ``build`` — WHICH COMMIT the running instance was built from. A Render
  service with a disk restarts with a blip rather than overlapping instances,
  so a bare 200 proves nothing about which build answered; CD waits on this
  to verify the artifact it shipped rather than whichever build happens to be
  serving. Omitted where the platform variable does not exist, so a local run
  and a fork on another host keep the same probe contract.
* ``geo`` — the geo guardrail's LIVE state (dash-improve-my-llms >= 2.7.0).
  Counts and flags only, never the denylist's country codes: a health
  endpoint is not where anyone should learn policy. ``resolved`` reveals only
  the caller's own country back to them, which Cloudflare's /cdn-cgi/trace
  already does — and it localises a failure that is otherwise invisible,
  because geo can be fully configured and still never match if the country
  header is not reaching the app. "configured: true, denied: 7, resolved:
  unknown" says that in one line. The key is OMITTED on older packages, not
  error-flagged: a host on an older floor is not broken, it predates the
  diagnostic.

Keep it cheap: the hub measures the round trip, so any work done here is
reported back as this app being slow.
"""
from __future__ import annotations

import json
import os
import platform
from pathlib import Path

import dash


def _resolved_country() -> str:
    """``geo.explain_resolution`` over THIS request's headers, or a reason.

    Reads the framework's request object directly rather than anything the
    package threads through, so it answers "did the country header reach this
    app at all?" independently of how the enforcement seam is wired.
    """
    try:
        from dash_improve_my_llms import geo
        from dash_improve_my_llms._headers import normalize_headers
    except Exception:
        return "unavailable (pre-2.7.0 package)"

    try:
        from flask import has_request_context, request

        if not has_request_context():
            return "no request context"
        return geo.explain_resolution(normalize_headers(request.headers))
    except Exception:
        return "unavailable"


def _geo_headers_seen() -> list:
    """The visitor-location headers the tracker has seen this process.

    Through the tracker, never a second list here: one module decides what
    counts as a location header, and a health probe keeping its own would
    drift from the one doing the recording.
    """
    try:
        from lib.analytics_tracker import geo_headers_seen

        return geo_headers_seen()
    except Exception:
        return []


def _ledger_block() -> dict:
    """``{"path", "persistent", "visits", "reads"}`` — the ledger, from outside.

    Three facts that were previously invisible on the wire, and the first is
    the one this host paid for: **leaflet ran for weeks with a disk DECLARED
    in render.yaml and no disk actually attached**, and nothing served could
    contradict the declaration.

    So ``persistent`` is MEASURED, never declared. It is true iff the resolved
    ledger path lies OUTSIDE the repository root — i.e. on a mounted disk such
    as ``/var/data/...``. A path under the app tree is the container
    filesystem and reads false EVEN WHERE A BLUEPRINT DECLARES A DISK. A
    boolean that reports the deployment's INTENTION is worth nothing; this one
    reports the filesystem.

    ``visits`` and ``reads`` are the two tables' current row counts, read from
    the same file the tracker writes. A missing file is ``0`` and ``0`` —
    never an error, and /healthz stays 200: this block is a diagnostic, and a
    diagnostic that can take the health probe down with it is a liability.

    Row CONTENTS never appear here. Counts, a boolean and a path.
    """
    block = {"path": None, "persistent": False, "visits": 0, "reads": 0}
    try:
        from lib.analytics_tracker import analytics_path

        path = Path(analytics_path()).resolve()
        block["path"] = str(path)
        repo_root = Path(__file__).resolve().parent.parent
        try:
            path.relative_to(repo_root)
            block["persistent"] = False      # inside the tree: container fs
        except ValueError:
            block["persistent"] = True       # outside it: a mounted disk

        if path.exists():
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                for table in ("visits", "reads"):
                    rows = data.get(table)
                    block[table] = len(rows) if isinstance(rows, list) else 0
    except Exception:
        # Never let a diagnostic break the health probe. An unreadable or
        # half-written ledger reports zeros, and the `path` already in the
        # block is what a reader needs in order to go and look.
        pass
    return block


def _llms_version() -> dict:
    """``{"llms_version": "2.8.0"}``, or ``{}`` if the package cannot be read.

    Omitted rather than reported as "unknown": a health payload that invents a
    version is worse than one that is silent about it, and run.py's
    ``LLMS_PKG_FLOOR`` already refuses to boot below the floor — so an absent
    key here means the import broke AFTER boot, which is itself the finding.

    This is the resolved PACKAGE version, and it is the only honest answer to
    "which dash-improve-my-llms is this host actually serving?". requirements.txt
    states a floor; the image states an intention; this states the fact. The
    two questions a fork confuses at its peril: `llms_version` is the package,
    `openapi_version` (run.py) is the API surface's own shape.
    """
    try:
        import dash_improve_my_llms as _pkg

        version = getattr(_pkg, "__version__", None)
        return {"llms_version": version} if version else {}
    except Exception:
        return {}


def health_payload(backend: str) -> dict:
    """Built PER REQUEST, never snapshotted.

    Every field here was static once (ok/app/version/backend never change for
    a running process), which made a registration-time snapshot look harmless.
    It is not: `geo` is configured well after this route is registered, so a
    snapshot reports the guardrail as unconfigured on a host where it is
    configured — the diagnostic lying in exactly the situation it exists for.
    Every backend below renders from this one function for the same reason:
    a probe contract that varies by backend is not a contract.
    """
    from lib.constants import APP_VERSION, BASE_URL
    from lib.satellite_reporter import app_key

    payload = {
        "ok": True,
        "app": app_key(),
        "version": APP_VERSION,
        "base_url": BASE_URL,
        "backend": backend,
        "dash_version": dash.__version__,
        # WHICH interpreter is actually serving. Before this field the repo
        # could declare one Python in the Dockerfile and serve another, and
        # nothing on the wire could contradict either — the drift was
        # invisible to the battery by construction (ops-seat finding,
        # 2026-08-25). scripts/network_smoke.py asserts this minor against
        # the Dockerfile's FROM tag, so image and declaration can no longer
        # part ways silently. render.yaml has no say here: this service is
        # `runtime: docker`, so the image IS the declaration.
        "python": platform.python_version(),
        "reporting": bool(os.getenv("CROSS_APP_WEBHOOK_SECRET")),
        # ADDITIVE (1.6.44 item 1). Every existing key keeps its meaning; a
        # consumer that does not know this one ignores it. The template's own
        # finding is why the test below reads it off the WIRE on the lane that
        # actually answers rather than off `health_payload`: a pydantic
        # `response_model` DROPS undeclared fields in silence, so a key can be
        # in this dict and absent from the served JSON. This repo's FastAPI
        # lane returns a bare `JSONResponse` with no model, so nothing filters
        # it — recorded, because that is the reason it works here.
        **_llms_version(),
        # Where this host's ledger actually lives, whether it survives a
        # redeploy, and how much is in it (1.6.44 item 20).
        "ledger": _ledger_block(),
    }

    build = os.environ.get("RENDER_GIT_COMMIT")
    if build:
        payload["build"] = build

    try:
        from dash_improve_my_llms import geo
    except ImportError:
        pass  # pre-2.7: omit the key rather than flagging an error
    else:
        try:
            payload["geo"] = {
                "configured": bool(geo.is_configured()),
                "denied": len(geo.effective_policy().get("deny_countries") or []),
                "resolved": _resolved_country(),
                # WHICH visitor-location headers actually arrive here (1.6.44
                # item 16). Since the ip-api lookup was removed, the edge is
                # the ONLY source of location, so "the city is missing" and
                # "the zone transform is off" became the same question — and
                # this is the one line that answers it. Read through the
                # tracker rather than re-derived: one module decides what
                # counts as a location header.
                "headers_seen": _geo_headers_seen(),
            }
        except Exception:  # a diagnostic must never break the health probe
            payload["geo"] = {"configured": False, "denied": 0, "error": True}

    return payload


def register_health_route(app, backend: str) -> None:
    """Mount ``/healthz`` on whichever backend is running."""
    server = app.server

    if backend == "fastapi":
        from starlette.responses import JSONResponse

        @server.get("/healthz", include_in_schema=False)
        async def _healthz():  # pragma: no cover — asgi runtime
            return JSONResponse(health_payload(backend))

    elif backend == "quart":
        from quart import jsonify

        @server.get("/healthz")
        async def _healthz():  # pragma: no cover — quart runtime
            return jsonify(health_payload(backend))

    else:
        from flask import jsonify

        @server.get("/healthz")
        def _healthz():
            return jsonify(health_payload(backend))

    print(f"[dash-leaflet2] /healthz registered ({backend}) — "
          "the 2plot.ai hourly health sweep probes this path.")
