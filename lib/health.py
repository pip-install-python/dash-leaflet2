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

Keep it cheap: the hub measures the round trip, so any work done here is
reported back as this app being slow.
"""
from __future__ import annotations

import os

import dash


def health_payload(backend: str) -> dict:
    from lib.constants import APP_VERSION, BASE_URL
    from lib.satellite_reporter import app_key

    return {
        "ok": True,
        "app": app_key(),
        "version": APP_VERSION,
        "base_url": BASE_URL,
        "backend": backend,
        "dash_version": dash.__version__,
        "reporting": bool(os.getenv("CROSS_APP_WEBHOOK_SECRET")),
    }


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
