"""The agent- and crawler-facing surfaces, in-process.

Same contract as scripts/network_smoke.py, one layer down: the battery proves
the DEPLOYED artifact serves these, this proves the code does. The overlap is
deliberate — a pull request that breaks a surface fails here in seconds
without waiting for a container, and a deploy that breaks one fails there even
though the code is fine.

Everything asserted here is a silent failure in production: a sitemap on the
wrong host does not error, it deindexes; an owner-only page that answers
llms.txt does not error, it leaks; a page serving the JavaScript stub does not
error, it just indexes nothing.
"""

from __future__ import annotations

import json
import re

from conftest import BROWSER_ACCEPT, CRAWLER_UA, SAMPLE_PAGE, STUB_MARKER

# Both admin surfaces are hidden — the board from run.py, /admin/traffic from
# its own module at import. `/admin` is the canary for the next one.
HIDDEN_PATHS = ("/admin/control-board", "/admin/traffic", "/admin")


def test_healthz_is_json_and_names_this_app(client):
    """render.yaml's healthCheckPath, and the hub's hourly pulse target."""
    response = client.get("/healthz")
    assert response.ok
    body = json.loads(response.text)
    assert body["ok"] is True
    # The 2plot network-directory key — the hub labels this app's series from
    # it, so a rename here silently orphans the traffic chart.
    assert body["app"] == "leaflet"


def test_llms_index_publishes_the_page_directory(client):
    body = client.get("/llms.txt").text
    assert "## Pages" in body
    assert "## Network" in body


def test_llms_index_names_the_hub(client):
    """What lets an agent walk from this leaf back up to the network."""
    assert "https://2plot.dev" in client.get("/llms.txt").text


def test_a_page_document_is_not_a_dead_end(client):
    response = client.get(f"{SAMPLE_PAGE}/llms.txt")
    assert response.ok
    assert "/llms.txt" in response.text


def test_hidden_pages_404_their_llms_txt(client):
    for path in HIDDEN_PATHS:
        response = client.get(f"{path}/llms.txt")
        assert response.status == 404, f"{path}/llms.txt leaked ({response.status})"


def test_the_sitemap_stays_on_this_host_and_leaks_nothing(client):
    from lib.constants import BASE_URL

    response = client.get("/sitemap.xml")
    assert response.ok
    locs = re.findall(r"<loc>([^<]+)</loc>", response.text)
    assert locs, "sitemap lists no pages"
    foreign = [u for u in locs if not u.startswith(BASE_URL)]
    assert foreign == [], f"sitemap points off-host: {foreign[:3]}"
    for path in HIDDEN_PATHS:
        assert path not in response.text, f"hidden path {path} leaked into the sitemap"


def test_robots_carries_the_ai_search_allowlist(client):
    """The 2.3.2 / 2.3.3 artifact fingerprint, visible from outside.

    pip metadata is invisible to a live probe, so these stanzas are how a
    deployed host is proven to run the intended package.
    """
    lines = [ln.strip() for ln in client.get("/robots.txt").text.splitlines()]

    def rule(agent: str) -> str:
        marker = f"User-agent: {agent}"
        assert marker in lines, f"{marker} stanza missing"
        return lines[lines.index(marker) + 1]

    for agent in ("OAI-SearchBot", "ChatGPT-User", "PerplexityBot",
                  "Claude-User", "Claude-SearchBot"):
        assert rule(agent) == "Allow: /", f"{agent} is not allowed"

    assert any(ln.startswith("Sitemap:") for ln in lines), "no Sitemap line"


def test_robots_keeps_this_sites_deliberate_open_training_posture(client):
    """`block_ai_training=False` in run.py is a decision, not drift.

    For MIT-licensed component documentation, being in the training corpus is
    how a model recommends this library to somebody who never visits the site.
    Under that config dash-improve-my-llms emits no ClaudeBot stanza at all —
    training crawlers fall under `User-agent: *`. If someone flips the flag,
    this is the test that makes them say so out loud.
    """
    lines = [ln.strip() for ln in client.get("/robots.txt").text.splitlines()]
    assert "User-agent: ClaudeBot" not in lines


def test_robots_does_not_advertise_the_admin_surface(client):
    """Inverted on 2026-08-23, deliberately — this used to assert the
    opposite.

    `Disallow: /admin/` reads like a protection and is the reverse: robots.txt
    is public, so the line hands the admin path to every scraper that reads
    it, and it stops nobody who ignores the file. The surface is protected by
    auth (two independent checks, failing closed without Clerk) and kept out
    of the index by `mark_hidden`, which excludes it from the sitemap and
    /llms.txt rather than announcing it.
    """
    robots = client.get("/robots.txt").text
    assert "/admin" not in robots, "robots.txt advertises the admin path"


def test_the_admin_surface_is_still_excluded_from_the_index(client):
    """The half that actually matters, and the reason dropping the Disallow
    costs nothing: mark_hidden keeps it out of both machine catalogues."""
    assert "/admin" not in client.get("/sitemap.xml").text
    assert "/admin" not in client.get("/llms.txt").text


def test_a_crawler_gets_prose_not_the_javascript_stub(client, page_paths):
    """The prerender — the failure this whole network cares most about.

    A crawler that receives the stub indexes nothing, and the page looks
    perfect in a browser the entire time.
    """
    checked = [p for p in page_paths if not p.startswith("/admin")][:8]
    assert checked, "no public pages registered"
    for path in checked:
        html = client.get(path, user_agent=CRAWLER_UA).text
        assert STUB_MARKER not in html, f"{path} served the JavaScript stub"


def test_a_crawler_gets_a_canonical_on_this_host(client):
    from lib.constants import BASE_URL

    html = client.get("/", user_agent=CRAWLER_UA).text
    found = re.findall(r'rel="canonical"\s+href="([^"]*)"', html)
    assert len(found) == 1, f"expected one canonical, got {found}"
    assert found[0].startswith(BASE_URL), found[0]


def test_agents_and_browsers_get_different_types(client):
    """One URL, two audiences, and a `Vary` that stops a CDN mixing them."""
    md = client.get(f"{SAMPLE_PAGE}/llms.txt")
    assert md.content_type.startswith("text/markdown"), md.content_type
    assert "<!DOCTYPE html>" not in md.text, "viewer chrome reached an agent"

    html = client.get(f"{SAMPLE_PAGE}/llms.txt", accept=BROWSER_ACCEPT)
    assert "text/html" in html.content_type, html.content_type
    assert "mk-wordmark" in html.text, "the network wordmark is missing"

    for label, response in (("markdown", md), ("html", html)):
        assert "accept" in response.header("Vary").lower(), (
            f"no Vary: Accept on the {label} variant — a shared cache may "
            "serve it to everyone"
        )


def test_the_llms_viewer_is_noindex(client):
    """The rendered view must not compete with the page it documents."""
    html = client.get(f"{SAMPLE_PAGE}/llms.txt", accept=BROWSER_ACCEPT).text
    assert re.search(r'<meta[^>]+name="robots"[^>]+noindex', html)


def test_every_public_page_has_llms_prose(client, page_paths):
    """`warn_missing_llms_doc=True` in run.py should have nothing to say."""
    missing = []
    for path in page_paths:
        if path.startswith("/admin") or path == "/":
            continue
        response = client.get(f"{path.rstrip('/')}/llms.txt")
        if not response.ok or STUB_MARKER in response.text:
            missing.append(path)
    assert missing == [], f"pages with no agent-facing prose: {missing}"
