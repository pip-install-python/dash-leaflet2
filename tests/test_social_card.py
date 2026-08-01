"""The social card and the installable-app surfaces.

Both fail silently and both fail *outside* this app, which is why they need
tests rather than a look at the page:

* a link preview is built by Facebook, Twitter/X, Slack, Discord and LinkedIn
  from tags nobody on the team ever sees rendered — and an EMPTY `og:image`
  is worse than none, because a scraper treats the empty value as the declared
  image and renders a blank card. Every page on this site shipped exactly that
  until `image_url=` was passed to `register_page`;
* the web app manifest decides whether a browser offers "install". Its
  `name`/`short_name` were empty strings and its icon paths pointed at
  `/android-chrome-192x192.png` at the site root, where nothing is served, so
  no browser could ever have made the offer. Nothing about that is visible on
  the page.

Note on where the tags come from — the split matters when one of these fails:
`og:image`, `twitter:image` and the whole `twitter:*` set are emitted by DASH
(`dash/_pages.py`, per page, from `register_page`), while `og:site_name`,
the `og:image:*` auxiliaries and the icon links come from
`templates/index.html`. dash-improve-my-llms adds a third set, but only on the
prerender path, which social scrapers do not take — its bot list has
`facebookbot` (Meta's AI training crawler) and not `facebookexternalhit` (the
link-preview fetcher). That is why deleting index.html would silently kill
every unfurl.
"""

from __future__ import annotations

import json
import re

from conftest import REPO_ROOT, SAMPLE_PAGE
from lib.constants import (
    OG_IMAGE_ALT,
    OG_IMAGE_HEIGHT,
    OG_IMAGE_URL,
    OG_IMAGE_WIDTH,
    SITE_BRAND,
)

MANIFEST = REPO_ROOT / "assets" / "favicon_io" / "site.webmanifest"


def _visible(html: str) -> str:
    """The document with HTML comments removed.

    templates/index.html documents itself, and a regex cannot tell an example
    tag inside a comment from a live one — this file's first draft reported
    phantom `rel="icon"` links that were pure prose.
    """
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


def _meta(html: str, key: str, value: str) -> list[str]:
    """Every `content` for a given property/name — a list, to catch duplicates.

    Tags carrying `data-dimll-prerender` are excluded. dash-improve-my-llms
    injects its own description and OpenGraph block and marks each one exactly
    so it can be told apart; counting those would hide what these tests are
    for, which is duplication between templates/index.html and the tags Dash
    generates from `register_page`.
    """
    pattern = (
        rf'<meta[^>]*(?:property|name)="{re.escape(value)}"[^>]*content="([^"]*)"'
        rf'|<meta[^>]*content="([^"]*)"[^>]*(?:property|name)="{re.escape(value)}"'
    )
    body = re.sub(r'<meta[^>]*data-dimll-prerender[^>]*>', "", _visible(html))
    return ["".join(m) for m in re.findall(pattern, body)]


# ------------------------------------------------------------- the og image --


def test_the_og_image_is_never_empty(client, page_paths):
    """The regression this file exists for.

    Dash emits `og:image` unconditionally and leaves it empty when it can find
    no image. An empty tag is a blank preview card on every platform.
    """
    for path in [p for p in page_paths if not p.startswith("/admin")][:8]:
        html = client.get(path).text
        images = _meta(html, "property", "og:image")
        assert images, f"{path} declares no og:image at all"
        assert all(src.strip() for src in images), (
            f"{path} serves an EMPTY og:image {images} — the card renders blank"
        )


def test_the_og_image_is_absolute(client):
    """A relative og:image is unusable: the scraper has no base to resolve it."""
    for prop in ("og:image", "twitter:image"):
        values = _meta(client.get("/").text, "property", prop)
        assert values, f"no {prop} on the home page"
        for src in values:
            assert src.startswith("https://"), f"{prop}={src!r} is not absolute"


def test_the_image_is_the_one_the_constants_declare(client):
    assert OG_IMAGE_URL in client.get("/").text


def test_the_image_is_declared_exactly_once(client):
    """Two og:image tags let the scraper pick, and it will pick the wrong one.

    templates/index.html deliberately ships only the AUXILIARY image tags
    (dimensions, type, alt) precisely so it cannot duplicate the URL Dash
    already emits. This is what keeps that rule honest.
    """
    html = client.get(SAMPLE_PAGE).text
    assert len(_meta(html, "property", "og:image")) == 1
    assert len(_meta(html, "property", "twitter:image")) == 1


def test_the_auxiliary_image_tags_match_the_constants(client):
    """index.html hard-codes the dimensions; lib/constants.py is the source."""
    html = client.get("/").text
    assert _meta(html, "property", "og:image:width") == [str(OG_IMAGE_WIDTH)]
    assert _meta(html, "property", "og:image:height") == [str(OG_IMAGE_HEIGHT)]
    assert _meta(html, "property", "og:image:alt") == [OG_IMAGE_ALT]
    assert _meta(html, "property", "og:image:secure_url") == [OG_IMAGE_URL]


def test_the_twitter_card_is_a_large_image(client):
    assert _meta(client.get("/").text, "property", "twitter:card") == [
        "summary_large_image"
    ]


def test_no_meta_tag_dash_emits_is_also_declared_statically(client):
    """The rule templates/index.html's OG block is built on.

    Dash emits all of these per page from `register_page`. A static copy in the
    template makes two of each, and the static one describes the SITE where
    Dash's describes the PAGE — redundant and less accurate at once. Which tag
    a scraper honours is undefined; in practice the later wins.
    """
    html = client.get(SAMPLE_PAGE).text
    for tag in ("description", "og:type", "og:title", "og:description",
                "og:image", "twitter:card", "twitter:url", "twitter:title",
                "twitter:description", "twitter:image"):
        found = _meta(html, "property", tag)
        assert len(found) <= 1, f"{tag} is declared {len(found)} times: {found}"


def test_the_tags_dash_omits_are_declared_here(client):
    """The other half of the rule — these are not covered by Dash."""
    html = client.get("/").text
    for tag in ("og:site_name", "og:url", "og:image:alt", "twitter:image:alt"):
        assert _meta(html, "property", tag), (
            f"{tag} is missing and Dash does not emit it"
        )


def test_og_site_name_is_present_because_dash_omits_it(client):
    """The one image-adjacent tag Dash genuinely does not emit."""
    assert _meta(client.get("/").text, "property", "og:site_name")


# ------------------------------------------------------------- the manifest --


def test_the_manifest_is_linked_from_the_document(client):
    """Without the link element the manifest may as well not exist."""
    html = client.get("/").text
    assert 'rel="manifest"' in html, "no manifest link — no install prompt"
    assert "/assets/favicon_io/site.webmanifest" in html


def test_the_manifest_is_served(client):
    response = client.get("/assets/favicon_io/site.webmanifest")
    assert response.ok, f"the manifest 404s ({response.status})"


def test_the_manifest_is_installable():
    """The fields a browser requires before it will offer to install.

    An empty `name` disqualifies it, and that is exactly how it shipped.
    """
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["name"].strip(), "empty name — no browser will offer install"
    assert manifest["short_name"].strip(), "empty short_name"
    assert manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["name"] == SITE_BRAND, "the manifest name is not the site brand"


def test_every_manifest_icon_actually_resolves(client):
    """The failure that made the manifest inert.

    Icons were declared at `/android-chrome-192x192.png` — the site root —
    while the files live under `/assets/favicon_io/`. A manifest whose icons
    404 is not installable, and nothing reports it.
    """
    manifest = json.loads(MANIFEST.read_text())
    icons = manifest.get("icons") or []
    assert icons, "the manifest declares no icons"
    for icon in icons:
        src = icon["src"]
        assert src.startswith("/assets/"), f"{src} is not under /assets/"
        assert client.get(src).ok, f"manifest icon {src} does not resolve"
    # A 192px icon is the documented floor for an install prompt.
    assert any(i.get("sizes") == "192x192" for i in icons)
    assert any(i.get("sizes") == "512x512" for i in icons)


def test_the_apple_touch_icon_is_declared_and_resolves(client):
    """iOS ignores the manifest and uses this for Add to Home Screen."""
    html = client.get("/").text
    match = re.search(r'<link[^>]*rel="apple-touch-icon"[^>]*href="([^"]+)"', html)
    assert match, "no apple-touch-icon — iOS home-screen icon falls back to a screenshot"
    assert client.get(match.group(1)).ok


def test_the_favicon_resolves(client):
    """Dash walks assets recursively, so the favicon_io subfolder is found."""
    html = client.get("/").text
    hrefs = re.findall(r'<link[^>]*rel="icon"[^>]*href="([^"]+)"', html)
    assert hrefs, "no favicon link"
    for href in hrefs:
        assert client.get(href.split("?")[0]).ok, f"favicon {href} does not resolve"


def test_the_theme_colour_agrees_with_the_manifest(client):
    """A mismatch shows as one colour in the browser chrome and another in the
    installed app's splash screen."""
    manifest = json.loads(MANIFEST.read_text())
    assert _meta(client.get("/").text, "name", "theme-color") == [
        manifest["theme_color"]
    ]


# --------------------------------------------------- the template itself ----


def test_the_index_template_is_still_wired_in(app_module):
    """A guard on the whole file.

    `templates/index.html` looks removable — dash-improve-my-llms appears to
    cover OG — but its injection runs only on the prerender path, which social
    scrapers do not take. Deleting the template silently kills every unfurl,
    the icons and the manifest at once, and nothing else in this suite would
    notice on its own.
    """
    index = (REPO_ROOT / "templates" / "index.html").read_text()
    for placeholder in ("{%metas%}", "{%favicon%}", "{%css%}", "{%app_entry%}",
                        "{%config%}", "{%scripts%}", "{%renderer%}"):
        assert placeholder in index, f"{placeholder} missing from the template"
    assert app_module.app.index_string.startswith("<!DOCTYPE html>")


def test_the_structured_data_points_at_a_network_host():
    """`pip-install-python.com` was this site's published Organization URL.

    It is not a 2plot network host, and it appeared three times in the
    structured data every crawler reads: the Organization `url`, the
    SoftwareSourceCode `author.url`, and a link in the noscript footer.

    Scoped to the template on purpose. `lib/network_directory.py` also lists
    the domain, but that is a deliberate directory of AFFILIATED (explicitly
    non-network) sites — a separate editorial decision, not template drift.
    """
    index = (REPO_ROOT / "templates" / "index.html").read_text()
    assert "pip-install-python.com" not in index

    for block in re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', index, re.S
    ):
        data = json.loads(block)
        for url in re.findall(r'"url":\s*"([^"]+)"', block):
            assert "pip-install-python.com" not in url, data.get("@type")
