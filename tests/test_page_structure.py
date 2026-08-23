"""What EVERY page owes a generic client, pinned across the whole set.

Ported from the template's `tests/test_pages.py` structure pin (1.6.11), which
earned its keep the day it shipped: it found five `<h1>`s on the tutorial
page's machine lane, on every fork, from a `.. source::` directive expanded
inside a ```markdown fence.

Here it found something different and larger — ALL 27 pages served two `<h1>`s
to a crawler (the home page three), because dash-improve-my-llms injected a
prerender header while the document body already opened with one. 2.7.0's
dedup fixed 26. The home page needed two more things, because its preamble
said "Home" (the nav label) where the package injects the site brand, and its
body then hand-wrote that same brand as a third: `_build_llms_doc` now takes
the PUBLISHED name so the two strings match and dedup can fire, and home.md's
duplicate title is an h2. None of it was visible in a browser, because the
app-shell lane renders from the component tree and never sees the generated
markdown.

The lesson worth keeping: a per-page assertion catches what a spot check
cannot. The defect was uniform, so any single page looked like "how this site
is", and it took the whole set to make it obvious.
"""

from __future__ import annotations

import re

import pytest

from conftest import BROWSER_UA, CRAWLER_UA

# HTML comments are stripped before counting: templates/index.html carries
# long explanatory blocks, and a `#` inside one is not a heading.
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_H1 = re.compile(r"<h1[ >]")


def _pages(app_module):
    """Every non-admin page path. Admin surfaces gate themselves and serve a
    card rather than a document, so the structure contract does not apply."""
    import dash

    return sorted(
        entry["path"]
        for entry in dash.page_registry.values()
        if not entry["path"].startswith("/admin")
    )


def test_every_page_serves_exactly_one_h1_to_a_generic_client(app_module, client):
    """One document, one top-level heading.

    Two h1s is not a cosmetic complaint: the crawler document is what search
    and assistants read, and a page whose outline says it has two titles has
    no title. This ran red on 27 of 27 pages before the 2.7.1 floor.
    """
    offenders = []
    for path in _pages(app_module):
        html = _COMMENT.sub("", client.get(path, user_agent=CRAWLER_UA).text)
        count = len(_H1.findall(html))
        if count != 1:
            headings = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
            offenders.append((path, count, [h.strip()[:40] for h in headings]))
    assert not offenders, "pages not serving exactly one <h1>:\n" + "\n".join(
        f"  {p}: {n} — {h}" for p, n, h in offenders
    )


def test_the_browser_lane_carries_the_prerendered_document(app_module, client):
    """Not an h1 count — the browser document EMBEDS the crawler document in
    `#dimll-prerender` (visibly, since 2.6.1 dropped `hidden`), so its heading
    count mirrors the crawler's by construction. Pinning "one h1" there would
    assert an architecture nothing promised. What is worth pinning is that the
    prerender is present and non-empty, which is the 2.6.1 contract.
    """
    for path in ("/", "/pointer-events"):
        html = client.get(path, user_agent=BROWSER_UA).text
        assert 'data-dimll-prerender="1"' in html, f"{path} has no prerender"
        assert "hidden>" not in html.split('data-dimll-prerender="1"')[1][:40], (
            f"{path}'s prerender is hidden — the package fell below 2.6.1"
        )


# ANCHORS ONLY. `<link rel=...>` in the head is a different thing entirely:
# 2.7.1 adds the llms.txt v2 discovery relations, so `rel="alternate"` and
# `rel="describedby"` BOTH legitimately point at /llms.txt. Counting bare
# hrefs reads that correct pair as a duplicate — which it is not, and a test
# that says so would be pressure to remove a feature.
_FOOTER_ANCHOR = re.compile(r'<a[^>]+href="([^"]*?/llms\.txt[^"]*)"')


def test_no_duplicate_llms_links_in_the_prerender_footer(app_module, client):
    """2.7.0 de-doubled the home footer's /llms.txt link.

    A duplicated link is a small thing that costs twice: an agent follows it
    twice, and a human reading the footer wonders which one is different.
    """
    for path in ("/", "/pointer-events"):
        html = client.get(path, user_agent=CRAWLER_UA).text
        links = _FOOTER_ANCHOR.findall(html)
        duplicates = {u for u in links if links.count(u) > 1}
        assert not duplicates, f"{path} repeats an llms.txt anchor: {duplicates}"


def test_home_carries_the_root_llms_link_exactly_once(app_module, client):
    html = client.get("/", user_agent=CRAWLER_UA).text
    roots = [u for u in _FOOTER_ANCHOR.findall(html) if u.rstrip("/").endswith("/llms.txt")]
    assert len(set(roots)) == len(roots), f"home repeats a root llms.txt anchor: {roots}"


def test_the_v2_discovery_relations_are_present(app_module, client):
    """2.7.1's llms.txt v2 discovery: rel=alternate + rel=describedby in the
    head, and a representation digest. Their ABSENCE is the tell that the
    package fell below the floor — the same signal /healthz's geo block gives
    the orchestrator from outside."""
    html = client.get("/", user_agent=CRAWLER_UA).text
    assert 'rel="alternate" type="text/markdown"' in html, "no rel=alternate"
    assert 'rel="describedby"' in html, "no rel=describedby"
    assert "llms-source-digest" in html, "no representation digest"


def test_the_source_expansion_is_fence_aware():
    """A directive inside a fenced block is documentation, not an instruction.

    No page here teaches `.. source::` today, so this is a unit check rather
    than an end-to-end one — carried from the template so the guard cannot be
    quietly lost in a future re-copy.
    """
    from pages.markdown import _expand_source_directives

    fenced = "```markdown\n.. source::requirements.txt\n```\n"
    assert _expand_source_directives(fenced) == fenced.rstrip("\n") + "\n" or \
        ".. source::requirements.txt" in _expand_source_directives(fenced), \
        "a fenced directive was expanded"

    bare = ".. source::requirements.txt\n"
    assert "```" in _expand_source_directives(bare), "a real directive was not expanded"


@pytest.mark.parametrize("marker", ["dimll-prerender"])
def test_no_page_mentions_the_prerender_marker_in_served_text(app_module, client, marker):
    """THE MARKER TRAP. A page that MENTIONS the marker string used to lose
    its prerender entirely — the probe could not tell a mention from the real
    thing. 2.7.0 hardened it; this pins that nothing here leans on that.

    Counted in the crawler document, where the marker should never appear at
    all: it is an app-shell construct.
    """
    for path in _pages(app_module):
        html = client.get(path, user_agent=CRAWLER_UA).text
        assert marker not in html, f"{path}'s crawler document mentions {marker!r}"
