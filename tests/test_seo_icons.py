"""dimll 2.6.0's SEO honesty features, pinned from this app's side.

Adapted from the boilerplate's copy, and the adaptation is the point: the
reference host DECLARES its icons with `configure_seo(icons=[...])` and proves
discovery agrees with the declaration. **This app declares nothing.** It has
never called `configure_seo`, so until the 2.6.0 floor its crawler document
carried zero icons while browsers got six from `templates/index.html` — the
crawler/browser identity drift the whole Tier-B standard exists to close, in
its most complete form.

So the contract here is one step earlier than the template's: discovery alone
has to find this site's OWN art, and the crawler head has to carry exactly
what discovery found. Discovery is a courtesy in the package — it returns []
and logs at debug on anything unexpected — which means a renamed favicon
directory would take the icons away in silence. These tests are that silence's
alarm.

Three contracts:

1. **Discovery finds this site's own icons**, from `assets/favicon_io/`, and
   the crawler head emits them. Not zero, and not another host's art.
2. **The sitemap tells the truth or says nothing.** `<lastmod>` is emitted
   verbatim from frontmatter and omitted when unset. No date may appear that
   no page declared — the invented daily "today" is the exact lie 2.6.0 ends.
3. **The two heads agree on identity.** Content may differ between the crawler
   document and the browser document; `og:image` and the page's schema.org
   type may not go missing from one of them.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import BROWSER_UA, CRAWLER_UA, SAMPLE_PAGE

ICON_DIR = "assets/favicon_io"


def _hrefs(entries):
    """href strings out of the package's mixed icon shapes (str | dict)."""
    return {e if isinstance(e, str) else e["href"] for e in entries}


def test_discovery_finds_this_sites_own_icons(app):
    from dash_improve_my_llms.seo import discover_icons

    found = _hrefs(discover_icons(app))
    assert found, (
        f"Discovery found nothing. {ICON_DIR}/ is one of the package's covered "
        "directory names — if the folder was renamed, the crawler document "
        "silently loses every icon, because discovery fails soft by design."
    )
    stray = [h for h in found if ICON_DIR not in h]
    assert not stray, f"icons discovered outside {ICON_DIR}/: {stray}"


def test_the_crawler_head_carries_them(app, client):
    """The half that actually reaches Google. Discovery returning a good list
    is not the same as the crawler document emitting it."""
    from dash_improve_my_llms.seo import discover_icons

    html = client.get(SAMPLE_PAGE, user_agent=CRAWLER_UA).text
    emitted = set(re.findall(
        r'<link[^>]*rel="(?:icon|apple-touch-icon)"[^>]*href="([^"]+)"', html
    ))
    assert emitted == _hrefs(discover_icons(app)), (
        "The crawler head and discovery disagree.\n"
        f"head only:      {sorted(emitted - _hrefs(discover_icons(app)))}\n"
        f"discovery only: {sorted(_hrefs(discover_icons(app)) - emitted)}"
    )


def test_the_icons_actually_resolve(client):
    """A head full of 404s is worse than a head with no icons: it looks fixed."""
    for name in ("favicon.ico", "favicon-32x32.png", "apple-touch-icon.png",
                 "android-chrome-192x192.png"):
        r = client.get(f"/{ICON_DIR}/{name}")
        assert r.ok, f"{name} -> HTTP {r.status}"


def _declared_lastmods() -> set[str]:
    dates = set()
    for md in Path("docs").glob("**/*.md"):
        if md.name == "SKILL.md":
            continue
        text = md.read_text()
        if not text.startswith("---"):
            continue
        head = text[3:].split("\n---", 1)[0]
        m = re.search(r'^lastmod:\s*"?(\d{4}-\d{2}-\d{2})"?\s*$', head, re.MULTILINE)
        if m:
            dates.add(m.group(1))
    return dates


def test_sitemap_lastmod_is_verbatim_or_absent(client):
    sitemap = client.get("/sitemap.xml").text
    emitted = re.findall(r"<lastmod>([^<]+)</lastmod>", sitemap)
    declared = _declared_lastmods()

    assert emitted, (
        "No <lastmod> anywhere — the frontmatter stamps were removed, or the "
        "package fell below the 2.6.0 floor. Truth-or-silence permits silence "
        "per page, but this docs set deliberately declares real git dates."
    )
    undeclared = [d for d in emitted if d not in declared]
    assert not undeclared, (
        f"Sitemap emits dates nobody declared: {sorted(set(undeclared))} — an "
        "invented date is the lie that gets a whole sitemap discarded. Before "
        "2.6.0 every entry read 'today', regenerated on every crawl."
    )


def test_every_page_declares_a_date(client):
    """This site stamped all of its pages, so silence anywhere means a page
    was added without one — worth hearing about while the set is small."""
    sitemap = client.get("/sitemap.xml").text
    blocks = re.findall(r"<url>.*?</url>", sitemap, re.DOTALL)
    assert blocks, "sitemap has no <url> entries at all"
    bare = [re.search(r"<loc>([^<]+)</loc>", b).group(1)
            for b in blocks if "<lastmod>" not in b]
    assert not bare, (
        f"pages in the sitemap with no declared lastmod: {bare} — add "
        "`lastmod: <git log -1 --format=%cs>` to their frontmatter."
    )


def test_the_two_heads_agree_on_identity(client):
    """Content may differ between the crawler and browser documents; identity
    may not. Both of these went missing from the crawler side until
    pages/markdown.py started passing the full record through."""
    crawler = client.get(SAMPLE_PAGE, user_agent=CRAWLER_UA).text
    browser = client.get(SAMPLE_PAGE, user_agent=BROWSER_UA).text

    def og_image(html):
        return re.findall(r'property="og:image" content="([^"]*)"', html)

    assert og_image(crawler), "the crawler document declares no og:image"
    assert og_image(crawler) == og_image(browser), (
        f"og:image differs — crawler {og_image(crawler)}, "
        f"browser {og_image(browser)}"
    )
    assert "TechArticle" in crawler, (
        'the crawler document types this docs page as something other than '
        'TechArticle (the package default, "WebPage", says nothing a crawler '
        "could not already see)"
    )

    titles = re.findall(r"<title>([^<]*)</title>", crawler)
    assert titles and titles == re.findall(r"<title>([^<]*)</title>", browser), (
        f"crawler and browser <title> disagree: {titles} vs "
        f"{re.findall(r'<title>([^<]*)</title>', browser)}"
    )
