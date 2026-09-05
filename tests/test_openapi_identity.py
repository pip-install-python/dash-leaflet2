"""1.6.44 item 1 — the host owns its API identity, and says which package it runs.

Two independent contracts, one drop:

* run.py hands ``LLMSConfig`` three ``openapi_*`` knobs so the FastAPI lane's
  ``/openapi.json`` is titled from THIS repo's constants instead of defaulting
  to "FastAPI" / "0.1.0";
* ``/healthz`` reports the RESOLVED dash-improve-my-llms version.

The reason this file exists at all rather than a one-line assert: the knobs
arrived in dimll 2.9.4 and **this repo's requirements line is a `>=2.8.0`
floor, not the template's `==2.9.4` pin**. 2.8.0's ``LLMSConfig`` takes
thirteen parameters and not one is an ``openapi_*``, so passing them
unguarded is a ``TypeError`` at import — a dead site — on any venv or image
that resolves below 2.9.4. The guard is therefore load-bearing until the
fleet pin lands at 1.6.45, and it is pinned in BOTH directions here: a guard
that always returns ``{}`` would also "pass" a one-sided test while quietly
never shipping the feature.
"""

from __future__ import annotations

import inspect
import json


# --------------------------------------------------------------------------
# The signature guard, both directions.
# --------------------------------------------------------------------------

class _ConfigShape280:
    """A 2.8.0-shaped config: no ``openapi_*`` parameters at all."""

    def __init__(self, warn_missing_llms_doc=True, sitemap=True):
        self.warn_missing_llms_doc = warn_missing_llms_doc


class _ConfigShape294:
    """A 2.9.4-shaped config: the three knobs are real parameters."""

    def __init__(
        self,
        warn_missing_llms_doc=True,
        sitemap=True,
        openapi_title=None,
        openapi_description=None,
        openapi_version=None,
    ):
        self.openapi_title = openapi_title


def _kwargs_against(config_cls, monkeypatch):
    """Run run.py's guard against a substituted config class."""
    import run

    monkeypatch.setattr(run, "LLMSConfig", config_cls)
    return run._openapi_kwargs()


def test_guard_passes_the_knobs_on_a_294_shaped_config(app_module, monkeypatch):
    """The feature actually ships where the package accepts it."""
    kwargs = _kwargs_against(_ConfigShape294, monkeypatch)

    assert set(kwargs) == {
        "openapi_title",
        "openapi_description",
        "openapi_version",
    }, f"the guard dropped knobs a 2.9.4-shaped config accepts: {kwargs}"
    assert kwargs["openapi_title"].startswith("dash-leaflet2"), (
        "the title must come from this repo's constants, not the package default"
    )
    assert kwargs["openapi_version"] == "1.0"


def test_guard_withholds_the_knobs_on_a_280_shaped_config(app_module, monkeypatch):
    """The direction that keeps the site alive on the floor we actually declare.

    Without this branch, `LLMSConfig(**knobs)` raises TypeError at import on
    every environment resolving below 2.9.4 — and requirements.txt permits
    exactly that, deliberately, until 1.6.45.
    """
    kwargs = _kwargs_against(_ConfigShape280, monkeypatch)

    assert kwargs == {}, (
        "the guard passed openapi_* to a config that cannot accept them — "
        f"this is a TypeError at import on a 2.8.0 resolve: {kwargs}"
    )


def test_the_two_shapes_actually_differ(app_module):
    """Non-vacuity: prove the fixtures are not the same shape.

    A guard test whose two fixtures both lack (or both have) the parameters
    passes while asserting nothing about the guard.
    """
    p280 = inspect.signature(_ConfigShape280).parameters
    p294 = inspect.signature(_ConfigShape294).parameters

    assert "openapi_title" not in p280
    assert "openapi_title" in p294


def test_the_real_config_is_constructible_with_whatever_the_guard_returns(
    app_module,
):
    """The end-to-end form: the guard's output must not raise on the RESOLVED
    package, whichever one that is."""
    from dash_improve_my_llms import LLMSConfig

    import run

    LLMSConfig(warn_missing_llms_doc=True, **run._openapi_kwargs())


# --------------------------------------------------------------------------
# llms_version, read off the wire.
# --------------------------------------------------------------------------

def test_healthz_reports_the_resolved_llms_version_on_the_wire(client):
    """Read from the SERVED JSON, never from `health_payload`.

    The template's finding (item 20): a pydantic `response_model` drops every
    field it does not declare, in silence, so `llms_version` was in the payload
    dict and absent from the FastAPI lane's response from the moment it landed.
    This repo's FastAPI lane returns a bare `JSONResponse` with no model, so
    nothing filters it — but the assertion belongs on the wire regardless,
    because that is where the defect was invisible.
    """
    import dash_improve_my_llms as pkg

    body = json.loads(client.get("/healthz").text)

    assert "llms_version" in body, (
        "llms_version is absent from the SERVED payload — if it is present in "
        "health_payload() but missing here, a response model is filtering it"
    )
    assert body["llms_version"] == pkg.__version__, (
        f"healthz says {body['llms_version']!r}, the import resolves "
        f"{pkg.__version__!r} — the health probe is not reading the package "
        "that is actually serving"
    )


def test_llms_version_is_omitted_not_faked_when_the_package_cannot_be_read(
    monkeypatch,
):
    """Silence beats invention. Mutation-checked: the helper returns {} rather
    than an "unknown" string a dashboard would render as a version."""
    import builtins

    import lib.health as health

    real_import = builtins.__import__

    def _boom(name, *args, **kwargs):
        if name == "dash_improve_my_llms":
            raise ImportError("simulated")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _boom)
    assert health._llms_version() == {}


def test_every_key_health_payload_produces_reaches_the_wire(client):
    """Item 20's guard, asserted on whichever lane answers here.

    The two-sided form: not "llms_version is present" but "the served JSON and
    the payload function agree on their key SET". A response model that starts
    filtering any field fails this, not just the one field a reviewer thought
    to name.
    """
    import lib.health as health
    from lib.backend import resolve_backend

    produced = set(health.health_payload(resolve_backend()))
    served = set(json.loads(client.get("/healthz").text))

    missing = produced - served
    assert not missing, (
        f"health_payload produces {sorted(missing)} but the wire does not "
        "serve them — a response model or serializer is dropping fields"
    )
