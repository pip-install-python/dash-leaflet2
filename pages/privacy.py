"""/privacy — the Privacy page (1.6.44 item 15).

Content lives in `pages/legal.py` so both Legal pages share one module and one
renderer; this file is the registration. The single markdown string is what the
browser renders AND what the machine lane is served as `llms_doc` — a site
cannot have two versions of its own privacy.
"""
from __future__ import annotations

import dash

from lib import page_tiers, page_visibility
from lib.constants import OG_IMAGE_URL, PAGE_TITLE_PREFIX
from pages.legal import LEGAL_LASTMOD, PRIVACY_DESCRIPTION, PRIVACY_DOC, _render

dash.register_page(
    __name__,
    path="/privacy",
    name="Privacy",
    title=PAGE_TITLE_PREFIX + "Privacy",
    description=PRIVACY_DESCRIPTION,
    image_url=OG_IMAGE_URL,
    icon="tabler:shield-lock",
    category="Legal",
    order=2,
)

LLMS_DOC = PRIVACY_DOC


def layout(**_kwargs):
    return _render(PRIVACY_DOC, "m2d-page-privacy")


# The full machine record, exactly as pages/changelog.py does it (1.6.41, this
# repo's own finding): a module-level LLMS_DOC alone leaves the package to
# discover the page with no `lastmod` and outside the control board's llms.txt
# toggle.
#
# `lastmod` is REQUIRED here where the template's copy omits it:
# `tests/test_seo_icons.py::test_every_page_declares_a_date` fails on any
# sitemap entry without one, and this repo stamped all 27 of its pages. Bump it
# in the SAME COMMIT as any edit to the prose in pages/legal.py — never script
# it from an mtime, which resets on every Docker build.
from dash_improve_my_llms import register_page_metadata  # noqa: E402

page_visibility.register_default("/privacy", "Privacy",
                                 visibility="public", llms_public=True)
page_tiers.register("/privacy", "public", llms_public=True)
register_page_metadata(
    path="/privacy",
    name="Privacy",
    description=PRIVACY_DESCRIPTION,
    title=PAGE_TITLE_PREFIX + "Privacy",
    image_url=OG_IMAGE_URL,
    schema_type="WebPage",
    llms_doc=PRIVACY_DOC,
    lastmod=LEGAL_LASTMOD,
)
