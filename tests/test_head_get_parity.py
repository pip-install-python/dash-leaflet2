"""1.6.44 item 2 — HEAD parity, and why this fork PORTED what the template retired.

THE MEASUREMENT DECIDED THIS ITEM, not the spec's wording. The item says
"retire or record"; the ops seat warned separately not to read an ABSENT
`HeadAsGetMiddleware` as a retired one. This fork had never carried it —
`grep -rn HeadAsGet` over the tree returned zero lines — so "absent" was the
starting state, and the tempting conclusion was that nothing needed doing.

That conclusion was wrong, and one table shows why. Probed in-process on the
FastAPI lane at dimll 2.8.0, BEFORE porting anything:

    /healthz      browser/crawler/curl   GET 200 -> HEAD 405   (x3)
    /llms.txt     all three              GET 200 -> HEAD 200
    /robots.txt   all three              GET 200 -> HEAD 200
    /sitemap.xml  all three              GET 200 -> HEAD 200
    /             browser                GET 200 -> HEAD 405
    /             crawler, curl          GET 200 -> HEAD 200

Four of fifteen pairs mismatched. The template retires the middleware because
dimll **2.9.4** walks the router and adds HEAD wherever GET is allowed — its
own note says the retirement is "gated on the pin (item 1) and not on the
calendar". This fork deliberately kept the `>=2.8.0` floor (rider 1), so it
does not have that fix, and the residue is precisely the two routes the
package does not own: `/healthz`, declared `@server.get` in `lib/health.py`,
and `/`, Dash's lifespan-registered page catch-all.

The `/` row is the kit's own trap reproduced live: a crawler-UA `HEAD /`
returns 200 because the prerender middleware answers ABOVE routing, while a
browser gets the 405 from the route underneath. A fork that "verified HEAD"
with a crawler UA on `/` would have cleared this host and shipped the defect.

Production here is Flask, where Werkzeug derives HEAD from every GET rule, so
the wire was never affected — but `lib/backend.py` puts the ASGI lane one
environment variable away, and this is exactly the silent-until-switched
class of defect the fleet keeps rediscovering.
"""


from __future__ import annotations

import pytest

from conftest import backend

# The four machine-lane routes plus the app shell, each probed as three
# different consumers. 5 paths x 3 UAs = the 15 pairs the item names.
PATHS = ("/healthz", "/llms.txt", "/robots.txt", "/sitemap.xml", "/")

UAS = {
    "browser": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "crawler": (
        "Mozilla/5.0 (compatible; Googlebot/2.1; "
        "+http://www.google.com/bot.html)"
    ),
    "curl": "curl/8.7.1 2plot-internal/probe",
}


def test_the_shim_is_present_and_registered_outermost():
    """The inverse of what this test asserted when it was first written.

    It began as "the shim is absent, and that is the recorded state" — the
    reasonable reading of the spec before the parity table existed. The
    measurement inverted it. Kept as a positive assertion rather than deleted,
    because the removal trigger is a MEASUREMENT and not a date: when the pin
    reaches 2.9.4 at 1.6.45, re-run the parity table, confirm the package took
    over, and only then delete this and the class.
    """
    import lib.asgi_middleware as mod

    assert hasattr(mod, "HeadAsGetMiddleware"), (
        "HeadAsGetMiddleware is gone while this fork still resolves a dimll "
        "below 2.9.4 — the FastAPI lane is 405ing HEAD on /healthz and / again"
    )

    import inspect

    source = inspect.getsource(mod.register_asgi_middleware)
    assert "HeadAsGetMiddleware" in source, (
        "the class exists but register_asgi_middleware does not add it — it is "
        "inert, and the parity tests below only pass because of the client"
    )
    assert source.index("AnalyticsMiddleware") < source.index("HeadAsGetMiddleware"), (
        "HeadAsGetMiddleware must be added LAST so Starlette runs it "
        "OUTERMOST: the method rewrite has to precede anything that inspects "
        "the request"
    )


def test_the_package_has_not_yet_taken_over_the_head_fix():
    """The removal trigger, pinned so it fires on its own.

    When the resolved dash-improve-my-llms reaches 2.9.4 this goes RED, which
    is the prompt to re-measure the parity table without the middleware and
    retire it as the template did. Without this, the shim outlives its reason
    and silently masks a regression in the package's own fix — the template's
    stated motive for removing rather than leaving it harmless.
    """
    import dash_improve_my_llms as pkg

    def _v(text):
        parts = []
        for chunk in str(text).split(".")[:3]:
            digits = ""
            for ch in chunk:
                if not ch.isdigit():
                    break
                digits += ch
            if not digits:
                break
            parts.append(int(digits))
        return tuple(parts)

    assert _v(pkg.__version__) < (2, 9, 4), (
        f"dash-improve-my-llms resolved {pkg.__version__} >= 2.9.4: the "
        "package now adds HEAD wherever GET is allowed. Re-run the parity "
        "table WITHOUT HeadAsGetMiddleware, confirm 15/15, then delete the "
        "class, its registration and these two tests (1.6.45)."
    )


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("ua_name", sorted(UAS))
def test_head_reaches_the_same_status_as_get(client, path, ua_name):
    """15 pairs. No shim in the stack on any of them."""
    ua = UAS[ua_name]

    get = client.get(path, user_agent=ua)
    head = client.head(path, user_agent=ua)

    assert head.status == get.status, (
        f"{path} as {ua_name}: HEAD {head.status} != GET "
        f"{get.status} on backend={backend()!r}. A 405 here means this "
        "fork now needs the HeadAsGetMiddleware it has never carried."
    )


def test_the_parity_probe_actually_detects_a_head_405():
    """CONTROL — the reason the fifteen greens above are evidence.

    A parity assertion that cannot fail proves nothing (note 88: a sweep that
    found nothing and a sweep that swept nothing produce the same green). This
    builds the exact defect the middleware existed for — a FastAPI route
    declared GET-only — and asserts the probe sees 405 on HEAD while GET is
    200. If this control ever goes green-on-HEAD, the ecosystem changed and
    the fifteen assertions above stopped being meaningful.
    """
    fastapi = pytest.importorskip("fastapi")
    from starlette.testclient import TestClient

    api = fastapi.FastAPI()

    @api.get("/get-only")
    def _get_only():  # pragma: no cover - exercised through the client
        return {"ok": True}

    with TestClient(api) as probe:
        assert probe.get("/get-only").status_code == 200
        assert probe.head("/get-only").status_code == 405, (
            "FastAPI's APIRoute no longer 405s HEAD on a GET-only route — the "
            "defect class this item is about has changed shape"
        )


def test_a_bare_starlette_route_does_add_head():
    """The other half of the mechanism, so the kit's corrected text is pinned
    in code and not only in prose: Starlette's own Route DOES add HEAD."""
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient

    async def _ok(request):  # pragma: no cover - exercised through the client
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/plain", _ok, methods=["GET"])])
    with TestClient(app) as probe:
        assert probe.head("/plain").status_code == 200, (
            "starlette.routing.Route stopped adding HEAD alongside GET — the "
            "kit's traps section names this as the layer that does"
        )
