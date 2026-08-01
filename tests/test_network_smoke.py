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

import importlib.util
import sys

import pytest

from conftest import REPO_ROOT
from lib.constants import BASE_URL, INTERNAL_UA_TOKEN, SITE_BRAND

BASE = BASE_URL


@pytest.fixture(scope="module")
def battery():
    spec = importlib.util.spec_from_file_location(
        "network_smoke", REPO_ROOT / "scripts" / "network_smoke.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["network_smoke"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def wired(battery, client, monkeypatch):
    """Point the battery's `fetch` at the test client.

    The signature is `fetch(url, ua=..., method=..., body=..., headers=...)`
    and it returns `(status, lowercased_headers, text)`. Only GET is used by
    the satellite battery, so a non-GET here is a bug in the script rather
    than something to emulate.
    """
    seen_agents = []

    def _png_header(width: int, height: int) -> bytes:
        """The 24 bytes the card check actually reads.

        PNG signature (8) + length/type of the IHDR chunk (8) + width and
        height as big-endian uint32 (8). The battery reads bytes 16..24 and
        nothing else, so a synthetic header is a faithful stand-in for a real
        image — and it keeps the suite off the network.
        """
        return (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR"
                + width.to_bytes(4, "big") + height.to_bytes(4, "big"))

    def fetch_raw(url, ua=battery.UA, method="GET", body=None, headers=None,
                  timeout=None, retries=1):
        assert method == "GET", f"the satellite battery issued a {method}"
        seen_agents.append(ua)
        accept = (headers or {}).get("Accept")

        # Off-host URLs — today just the CDN-hosted social card — resolve to a
        # stub at the DECLARED size, so the check passes here and still has to
        # be earned against the real CDN after a deploy. Reaching the real CDN
        # from a unit test would make the suite depend on another service.
        if not url.startswith(BASE) and "://" in url:
            return (200, {"content-type": "image/png"},
                    _png_header(battery.OG_IMAGE_WIDTH, battery.OG_IMAGE_HEIGHT))

        path = url[len(BASE):] if url.startswith(BASE) else url
        response = client.get(path or "/", user_agent=ua, accept=accept)
        return response.status, dict(response.headers), response.text.encode()

    # `fetch_raw`, NOT `fetch`. The card check reads PNG bytes, and `fetch` is
    # a thin decoding delegate — patching it would leave `fetch_raw` reaching
    # the real CDN from a unit test, and patching only `fetch` in a repo where
    # they were separate implementations is how the boilerplate's copy of this
    # test silently kept hitting the network.
    monkeypatch.setattr(battery, "fetch_raw", fetch_raw)
    monkeypatch.setattr(battery, "_RESULTS", [])
    battery.seen_agents = seen_agents
    return battery


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


def test_the_hidden_paths_are_the_ones_run_py_marks_hidden(battery):
    """A hidden page nobody listed here is a leak the battery cannot see."""
    run_py = (REPO_ROOT / "run.py").read_text()
    listed = {p.rsplit("/llms.txt", 1)[0] for p in battery.HIDDEN_DOC_PATHS}
    for path in listed:
        if path == "/admin":
            continue  # the canary, deliberately not a registered page
        assert f'mark_hidden("{path}")' in run_py, (
            f"{path} is in the battery's hidden list but run.py does not mark "
            "it hidden — the check would pass for the wrong reason"
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
