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

1. **Discovery finds this site's own icons**, from `assets/favicon/`, and
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

ICON_DIR = "assets/favicon"


def _hrefs(entries):
    """href strings out of the package's mixed icon shapes (str | dict)."""
    return {e if isinstance(e, str) else e["href"] for e in entries}


def test_discovery_finds_this_sites_own_icons(app):
    from dash_improve_my_llms.seo import discover_icons

    found = _hrefs(discover_icons(app))
    assert found, (
        f"Discovery found nothing. {ICON_DIR}/ is one of the package's covered "
        "directory names — if the folder was renamed, the crawler document "
        "silently loses every icon, because discovery fails soft by design. "
        "This site used the nonstandard `favicon_io/` until 2026-08-22; the "
        "package covered that name too, which is why the drift was invisible."
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


# The standard eight. `scripts/make_favicons.py` writes seven of them plus the
# root-level assets/favicon.ico; site.webmanifest is hand-maintained text.
STANDARD_SET = (
    "favicon.ico",
    "favicon-16x16.png",
    "favicon-32x32.png",
    "favicon-96x96.png",
    "apple-touch-icon.png",
    "android-chrome-192x192.png",
    "android-chrome-512x512.png",
    "site.webmanifest",
)


def test_the_standard_set_is_complete():
    """Same eight files, same names, in every satellite.

    The names are load-bearing beyond this repo: `templates/index.html` and
    the package's discovery patterns both hardcode them, so a set that is
    merely "close" produces a head of dead links rather than an error.
    """
    present = {p.name for p in Path(ICON_DIR).iterdir() if p.is_file()}
    missing = [n for n in STANDARD_SET if n not in present]
    assert not missing, f"missing from {ICON_DIR}/: {missing}"


def test_every_href_resolves(client):
    """EVERY href, not a sample — a head full of 404s is worse than a head
    with no icons at all, because it looks fixed.

    Covers the three places a path is written down: the generated set, the
    hand-written links in templates/index.html, and the manifest's own icon
    entries. They have drifted apart before.
    """
    import json
    import re

    hrefs = {f"/{ICON_DIR}/{name}" for name in STANDARD_SET}
    hrefs.add("/assets/favicon.ico")  # the root redirect target

    index = Path("templates/index.html").read_text()
    hrefs.update(re.findall(r'(?:href|content)="(/assets/favicon[^"]*)"', index))

    manifest = json.loads((Path(ICON_DIR) / "site.webmanifest").read_text())
    hrefs.update(icon["src"] for icon in manifest.get("icons", []))

    for href in sorted(hrefs):
        assert client.get(href).ok, f"{href} does not resolve"


def test_the_manifest_points_at_this_sites_own_files(client):
    """A manifest whose icons 404 makes the install prompt silently
    unavailable — the browser just never offers it, with nothing logged."""
    import json

    manifest = json.loads((Path(ICON_DIR) / "site.webmanifest").read_text())
    assert manifest["name"] and manifest["short_name"], "manifest identity blank"
    assert manifest.get("icons"), "manifest declares no icons"
    stray = [i["src"] for i in manifest["icons"] if not i["src"].startswith(f"/{ICON_DIR}/")]
    assert not stray, f"manifest icons outside {ICON_DIR}/: {stray}"


def test_apple_touch_icon_is_opaque():
    """iOS composites the icon's alpha onto ITS OWN background — black on
    some surfaces, white on others — so a transparent apple-touch icon
    renders differently everywhere it appears. scripts/make_favicons.py
    flattens exactly this one file onto opaque white (every other size
    keeps its alpha; browsers and Android handle it correctly).

    Read the colour type straight out of the PNG header — stdlib only, no
    Pillow in the test environment. IHDR is always the first chunk: colour
    type is the byte at offset 25. 2 = RGB (opaque), 6 = RGBA. A palette
    PNG (3) can smuggle transparency back in through a tRNS chunk, so pin
    that absent too.
    """
    data = (Path(ICON_DIR) / "apple-touch-icon.png").read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG?"
    colour_type = data[25]
    assert colour_type in (0, 2, 3), (
        f"apple-touch-icon.png has colour type {colour_type} (an alpha "
        "channel) — regenerate it with scripts/make_favicons.py, which "
        "flattens this one icon onto opaque white."
    )
    assert b"tRNS" not in data, (
        "apple-touch-icon.png carries a tRNS transparency chunk — iOS will "
        "composite it onto an unpredictable background."
    )


def _declared_lastmods() -> set[str]:
    """Every date this site DECLARES, from the source that declares it.

    The docs pages declare theirs in frontmatter. The two GENERATED pages
    (template 1.6.38's /changelog and /api) have no frontmatter to put one
    in, so each derives its date from the artefact whose change IS the
    page's change — and both are read here from those same sources, never
    from the sitemap, so this test can still catch an invented date.

      /changelog -> the newest DATED release heading in CHANGELOG.md
      /api       -> `generated` in the committed props extract, written by
                    scripts/build_api_metadata.py when the props change

    Neither is an mtime: both are committed values that move only when the
    content moves, which is the rule the root CLAUDE.md states.
    """
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

    from pages.changelog import newest_date

    changelog_date = newest_date()
    assert changelog_date, "CHANGELOG.md has no dated release heading"
    dates.add(changelog_date)

    from lib.api_reference import slim_generated_on

    api_date = slim_generated_on("dash_leaflet2")
    assert api_date, (
        "dash_leaflet2/api_metadata.json has no `generated` date — run "
        "`python scripts/build_api_metadata.py`"
    )
    dates.add(api_date)
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
