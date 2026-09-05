"""1.6.44 item 15 — a Legal section whose privacy page is bound to the code.

Two pages, ONE markdown string each: what the browser renders IS what the
machine lane is served. A site whose privacy page says one thing to a reader
and another to a crawler has two privacy policies and only one of them was
reviewed.

THE BINDING IS THE ITEM. The privacy prose describes what
`lib/analytics_tracker.py` stores, so a test reads a REAL visit row — produced
by the real tracker, not a fixture of expected keys — and asserts every key in
it is described on the page. If the tracker starts storing something new, this
goes red rather than the page going quietly false.

BUILT AFTER ITEM 16, deliberately: the page states what the tracker stores
AFTER the privacy work. A fork that builds 15 first publishes prose about a
mechanism it does not have.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from conftest import CRAWLER_UA

REPO = pathlib.Path(__file__).resolve().parent.parent

CHROME = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Row keys that are not "stored about a visit" in the page's sense, or that
# the page covers under a heading rather than a bullet.
_KEY_PROSE = {
    "timestamp": "time",
    "path": "path",
    "device_type": "device type",
    "user_agent": "user-agent",
    "visitor_key": "visitor key",
    "location": "location",
    "ip_address": "ip address",
}


# --------------------------------------------------------------------------
# Registration and the nav category.
# --------------------------------------------------------------------------

def test_legal_is_in_category_order():
    from lib.constants import CATEGORY_ORDER

    assert "Legal" in CATEGORY_ORDER
    assert CATEGORY_ORDER[-1] == "Legal", (
        "the drop says 'between Components and Admin'; this tree has no "
        "Components category and the navbar builds Admin separately, so LAST "
        "is that position here — if that changed, re-derive it"
    )


@pytest.mark.parametrize("path", ["/terms", "/privacy"])
def test_the_page_is_registered(app_module, path):
    import dash

    registered = {e["path"] for e in dash.page_registry.values()}
    assert path in registered, sorted(registered)


@pytest.mark.parametrize("path", ["/terms", "/privacy"])
def test_the_page_renders_for_a_browser(client, path):
    response = client.get(path)
    assert response.status == 200


# --------------------------------------------------------------------------
# The acceptance: both lanes, one document.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("path", ["/terms", "/privacy"])
def test_the_machine_lane_serves_the_page(client, path):
    response = client.get(f"{path}/llms.txt", user_agent=CRAWLER_UA)

    assert response.status == 200, f"{path}/llms.txt is {response.status}"
    assert len(response.text) > 500, (
        f"{path}/llms.txt is {len(response.text)} bytes — a stub, not the page"
    )


@pytest.mark.parametrize("path", ["/terms", "/privacy"])
def test_both_appear_in_the_root_index(client, path):
    """The acceptance names this: present in the ROOT index, not merely
    reachable by guessing the URL."""
    index = client.get("/llms.txt", user_agent=CRAWLER_UA).text

    assert f"{path}/llms.txt" in index or path in index, (
        f"{path} is not listed in the root /llms.txt index"
    )


@pytest.mark.parametrize("path,marker", [
    ("/terms", "Terms of Use"),
    ("/privacy", "Privacy"),
])
def test_the_two_lanes_serve_the_same_document(client, path, marker):
    """ONE markdown string. The browser lane renders it; the machine lane is
    handed it. A divergence here is two policies."""
    from pages.legal import PRIVACY_DOC, TERMS_DOC

    source = TERMS_DOC if path == "/terms" else PRIVACY_DOC
    machine = client.get(f"{path}/llms.txt", user_agent=CRAWLER_UA).text

    assert marker in machine
    # A distinctive sentence from the source must survive into the machine
    # document — matched on a fragment rather than byte-for-byte, since the
    # package frames the document with its own header.
    probe = source.split("\n## ")[1].split("\n")[0].strip()
    assert probe in machine, (
        f"the machine lane does not carry the section {probe!r} from the "
        "single source string"
    )


# --------------------------------------------------------------------------
# The binding: the page describes what the code actually stores.
# --------------------------------------------------------------------------

@pytest.fixture
def real_visit_row(tmp_path, monkeypatch):
    """A row from the REAL tracker, not a hand-written list of keys.

    That is the whole point: a fixture enumerating expected keys would pass
    forever after the tracker started storing something new.
    """
    from lib.analytics_tracker import AnalyticsTracker

    monkeypatch.setenv("ANALYTICS_VISITOR_SALT", "test-salt")
    tracker = AnalyticsTracker(data_file=tmp_path / "a.json")
    tracker.track_visit("/", CHROME, "203.0.113.7",
                        headers={"CF-IPCountry": "US", "CF-IPCity": "Portland"})
    tracker.flush()
    return json.loads(tracker.data_file.read_text())["visits"][0]


def test_the_row_is_not_empty(real_visit_row):
    """Note 88: an empty row would make the binding test below vacuous."""
    assert len(real_visit_row) >= 5, real_visit_row


def test_every_stored_key_is_described_on_the_privacy_page(real_visit_row):
    """THE BINDING. If the tracker starts storing something, say so."""
    from pages.legal import PRIVACY_DOC

    page = PRIVACY_DOC.lower()
    undescribed = []
    for key in real_visit_row:
        prose = _KEY_PROSE.get(key)
        if prose is None:
            undescribed.append(f"{key} (no prose mapping at all)")
        elif prose not in page:
            undescribed.append(f"{key} -> expected {prose!r} on the page")

    assert not undescribed, (
        "the tracker stores keys the privacy page does not describe: "
        f"{undescribed}"
    )


def test_the_page_does_not_claim_something_the_code_stopped_doing(real_visit_row):
    """The other direction, which is the one that goes quietly false.

    The page says the raw address is not written to disk. Assert that against
    a real row rather than trusting the sentence.
    """
    from pages.legal import PRIVACY_DOC

    assert "ip_address" not in real_visit_row, (
        "the privacy page says the address is not written to disk, and it is"
    )
    assert "not written to disk" in PRIVACY_DOC


def test_the_page_names_the_removal_as_a_removal():
    """'Removed — not disabled' is a factual claim about item 16."""
    from pages.legal import PRIVACY_DOC

    assert "removed" in PRIVACY_DOC.lower()

    import ast

    tracker_src = (REPO / "lib" / "analytics_tracker.py").read_text()
    tree = ast.parse(tracker_src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "requests" not in imported, (
        "the privacy page claims the lookup was REMOVED while the HTTP client "
        "is still imported"
    )


def test_the_healthz_field_the_page_points_at_exists(client):
    """The page tells a reader to check `geo.headers_seen` on /healthz. If
    that field is not there, the page is instructing them to look at nothing."""
    from pages.legal import PRIVACY_DOC

    assert "geo.headers_seen" in PRIVACY_DOC

    payload = json.loads(client.get("/healthz").text)
    assert "headers_seen" in payload.get("geo", {}), payload.get("geo")


def test_the_sitemap_date_is_declared_not_invented():
    """`LEGAL_LASTMOD` lives in the module whose change IS these pages'
    change, and tests/test_seo_icons.py reads it from there."""
    from pages.legal import LEGAL_LASTMOD

    import re

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", LEGAL_LASTMOD), LEGAL_LASTMOD
    seo = (REPO / "tests" / "test_seo_icons.py").read_text()
    assert "LEGAL_LASTMOD" in seo, (
        "the sitemap guard cannot see this date, so it would read every Legal "
        "entry as an invented one"
    )
