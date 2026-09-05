"""
ASGI/Starlette middleware ports of Flask-only hooks used in this boilerplate.

When the Dash backend is FastAPI, these slot in where the Flask
``before_request`` decorator was used.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from lib.analytics_tracker import tracker


class HeadAsGetMiddleware:
    """Answer ``HEAD`` wherever ``GET`` is served (1.6.44 item 2).

    PORTED HERE, WHERE THE TEMPLATE RETIRED IT — and the difference is the
    package floor, not a preference. The template's retirement note is
    explicit that it is "gated on the pin (item 1) and not on the calendar":
    at dash-improve-my-llms **2.9.4** the package walks the router itself and
    adds HEAD wherever GET is allowed, including Dash's lifespan-registered
    page catch-all, which is the one case the middleware was kept for. This
    fork deliberately did NOT take that pin — rider 1 leaves our line at
    ``>=2.8.0`` until the fleet pin lands at 1.6.45 — so the package-side fix
    is simply not present here.

    Not assumed. MEASURED in-process on this tree's FastAPI lane at dimll
    2.8.0, 5 paths x 3 UAs, before this class existed:

        path          ua         GET  HEAD
        /healthz      browser    200   405   <-- MISMATCH
        /healthz      crawler    200   405   <-- MISMATCH
        /healthz      curl       200   405   <-- MISMATCH
        /llms.txt     *          200   200
        /robots.txt   *          200   200
        /sitemap.xml  *          200   200
        /             browser    200   405   <-- MISMATCH
        /             crawler    200   200
        /             curl       200   200

    Two things in that table are worth more than the verdict. The package's
    OWN routes already pass at 2.8.0 — 2.7.2 fixed those — so the residue is
    exactly the two routes the package does not own: ``/healthz`` (declared
    ``@server.get`` in ``lib/health.py``) and ``/``, Dash's page catch-all.
    And ``/`` passes for a crawler and for curl while failing for a browser,
    which is the kit's own trap reproduced live: a crawler-UA ``HEAD /`` is
    answered by the prerender middleware ABOVE routing, so probing that one
    case would have cleared a host that 405s the route underneath.

    Why middleware and not ``methods=["GET", "HEAD"]`` on the declaration we
    own: fixing ``/healthz`` alone leaves ``/`` 405ing to every browser, and
    ``/`` is registered by Dash from the ASGI lifespan where this repo has
    nothing to declare methods on. The fix has to sit above the router. Pure
    ASGI rather than ``BaseHTTPMiddleware`` so it neither buffers the
    response nor breaks streaming.

    The re-dispatch is a full ``GET``: same status, same headers, same work.
    The body is dropped here so the response is empty at every layer under
    test — on the wire h11 already frames a HEAD response as content-length 0
    and never writes those bytes, which is why Quart needs nothing.

    DELETE THIS when the pin reaches 2.9.4 at 1.6.45 — the same trigger as
    run.py's ``_openapi_kwargs`` guard — and re-run the parity table above to
    prove the package took over before removing it. Removing it on the date
    rather than on a measurement is how a fork ships the 405 back.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http" or scope.get("method") != "HEAD":
            await self.app(scope, receive, send)
            return

        sent_body = False

        async def send_without_body(message) -> None:
            nonlocal sent_body
            if message["type"] != "http.response.body":
                await send(message)
                return
            # A streaming handler emits many body messages; exactly one
            # empty, final message goes out or the server raises on the
            # message after the response completed.
            if sent_body:
                return
            sent_body = True
            await send({"type": "http.response.body", "body": b"",
                        "more_body": False})

        await self.app({**scope, "method": "GET"}, receive, send_without_body)


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Track every request through the analytics tracker.

    Mirrors the Flask ``before_request`` shim in ``run.py``. Failures are
    silently swallowed — analytics should never block a real response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            client = request.client
            ip = client.host if client else None
            # Headers carry the real client IP/country behind a proxy or CDN;
            # request.client is the last hop (the proxy) in production.
            tracker.track_visit(
                request.url.path,
                request.headers.get("user-agent", ""),
                ip,
                headers=dict(request.headers),
            )
        except Exception:
            pass
        return await call_next(request)


def register_asgi_middleware(app) -> None:
    """Attach all ASGI middleware to ``app.server`` (a FastAPI instance)."""
    app.server.add_middleware(AnalyticsMiddleware)
    # Added LAST so it runs OUTERMOST: the method rewrite has to happen before
    # anything else inspects the request, and the body suppression has to be
    # the last thing touching the response on the way out.
    app.server.add_middleware(HeadAsGetMiddleware)
