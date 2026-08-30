import logging
import re
from pathlib import Path
from typing import List, Optional

import dash
import dash_mantine_components as dmc
import frontmatter
from markdown2dash import Admonition, BlockExec, Divider, Image, create_parser
from pydantic import BaseModel, field_validator

from lib import aside
from lib.ad_client import inject_ad_into_aside
from lib.constants import OG_IMAGE_URL, PAGE_TITLE_PREFIX, NAME_CONTENT_MAP
from lib import page_tiers
from lib.directives.headings import patch_renderer
from lib.directives.kwargs import Kwargs
from lib.directives.llms_copy import LlmsCopy
from lib.directives.source import SC
from lib.directives.toc import TOC
from lib.gate_layouts import gated_layout
from lib.page_visibility import (
    published_name,
    register_default,
    register_llms_doc,
)
from lib.versions import substitute_versions

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

directory = "docs"

# Read all markdown files except SKILL.md sidecars — those describe the
# wiring of a page for agents, not a page route, so they have a different
# (no-endpoint) frontmatter shape and would fail Meta validation.
files = (p for p in Path(directory).glob("**/*.md") if p.name != "SKILL.md")


class Meta(BaseModel):
    name: str
    description: str
    endpoint: str
    package: str = "dash-leaflet2"
    category: Optional[str] = None
    icon: Optional[str] = None
    # Sidebar position within its category (template 1.6.38); ties break on
    # name. Absent on every page here on purpose: the sidebar has always
    # rendered each category alphabetically, and 1000-then-name reproduces
    # that exactly — so the contract arrives without reordering 27 pages.
    order: int = 1000
    # Baseline access tier: public | auth | admin | hidden. Omitted → the
    # deployment default (PAGE_DEFAULT_TIER / PAGE_DEFAULT_VISIBILITY). The
    # control board's overrides always win over whatever is declared here.
    #
    # `tier` is canonical — it is the network's word, and the ledger the hub's
    # ceilings compare against. `visibility` is this repo's older spelling of
    # the SAME four values and is accepted as an alias; see `_declared_tier`.
    tier: Optional[str] = None
    visibility: Optional[str] = None
    # Whether this page's prose may be served at /<page>/llms.txt (and in the
    # crawler document and the prerender) to anonymous and AI traffic, even
    # when `tier` gates the interactive page. Omitted → LLMS_PUBLIC_DEFAULT,
    # so the fleet-wide agent flip is one env change rather than 28 edits.
    # Also live-toggleable from the control board.
    llms_public: Optional[bool] = None
    # Sitemap <lastmod>, YYYY-MM-DD, emitted VERBATIM by dash-improve-my-llms
    # >= 2.6.0 — and omitted entirely when absent. Truth or silence: set it
    # when the page's prose genuinely changes, in the SAME commit as the
    # prose. Never script it from file mtimes, which reset on every Docker
    # build and would re-invent the every-page-changed-today sitemap that
    # the floor exists to end. The initial values here are each page's real
    # `git log -1 --format=%cs` date.
    #
    # The validator is not optional: YAML parses a bare `lastmod: 2026-07-28`
    # into a datetime.date before pydantic ever sees it, and Optional[str]
    # rejects that — every page would fail Meta validation at import.
    lastmod: Optional[str] = None

    @field_validator("lastmod", mode="before")
    @classmethod
    def _lastmod_to_iso(cls, value):
        return value.isoformat() if hasattr(value, "isoformat") else value


def _declared_tier(metadata: "Meta", source: str) -> Optional[str]:
    """The one tier this page declares, from `tier:` or the `visibility:` alias.

    ONE value feeds both ledgers — lib.page_tiers (what the hub's ceiling
    compares against and what lib.access enforces) and lib.page_visibility
    (the control board's row). They were two independent frontmatter keys
    until this pass, which meant a page could declare `visibility: auth` and
    be enforced as public, with nothing to show for it but a board row that
    lied.

    A page that sets both to the same value is fine and silent. A page that
    sets them to DIFFERENT values is a bug in the document, so it warns and
    `tier:` wins — the canonical key beats the alias, and a warning beats
    guessing.
    """
    if metadata.tier and metadata.visibility and metadata.tier != metadata.visibility:
        logger.warning(
            "%s declares tier=%r and visibility=%r — they are the same field. "
            "Using tier=%r; drop the `visibility:` line.",
            source, metadata.tier, metadata.visibility, metadata.tier,
        )
    return metadata.tier or metadata.visibility


_SOURCE_DIRECTIVE = re.compile(r'^\.\. source::(.+?)$', re.MULTILINE)
_LANG_MAP = {
    'py': 'python', 'pyi': 'python',
    'js': 'javascript', 'jsx': 'jsx',
    'ts': 'typescript', 'tsx': 'tsx',
    'css': 'css', 'scss': 'scss', 'sass': 'sass', 'less': 'less',
    'html': 'html', 'htm': 'html', 'xml': 'xml',
    'json': 'json',
    'yaml': 'yaml', 'yml': 'yaml',
    'md': 'markdown', 'rst': 'rst', 'txt': 'text',
    'sh': 'bash', 'bash': 'bash',
    'sql': 'sql', 'r': 'r',
    'toml': 'toml', 'ini': 'ini', 'conf': 'conf',
}


def _expand_source_directives(markdown_content: str) -> str:
    """Inline `.. source::path` directives with the referenced file content.

    This produces the prose that dash-improve-my-llms 2.0 will serve at
    `/<page>/llms.txt`. Replacing the directive with the real file content
    is what makes the LLM output self-contained for the "paste into a chat
    window" audience.

    FENCE-AWARE, and it has to be: a directive INSIDE a fenced code block is
    documentation showing the syntax, not a directive to act on. Expanding
    one injects a ```python fence inside the already-open fence, which CLOSES
    it early — from there the inlined file renders as markdown and every
    `# comment` line becomes an <h1>, so the page's machine lane serves
    broken structure while the browser lane looks perfect (markdown2dash
    parses fences properly). No page in THIS repo teaches the directive
    today, so this is carried from the template as a guard rather than a
    fix: the day someone documents `.. source::` in a fenced block, nothing
    silently breaks. tests/test_page_structure.py pins the outcome.
    """
    def expansion(directive_line: str) -> str:
        file_path = _SOURCE_DIRECTIVE.match(directive_line).group(1).strip()
        try:
            full = Path(file_path)
            content = full.read_text()
            ext = full.suffix.lstrip('.').lower()
            lang = _LANG_MAP.get(ext, ext or 'text')
            tail = '' if content.endswith('\n') else '\n'
            return f'\n```{lang}\n# File: {file_path}\n\n{content}{tail}```\n'
        except FileNotFoundError:
            return f'\n<!-- Error: File not found: {file_path} -->\n'
        except Exception as exc:
            return f'\n<!-- Error reading {file_path}: {exc} -->\n'

    out: List[str] = []
    fence = None  # the marker that opened the block we are inside, if any
    for line in markdown_content.split('\n'):
        head = line.lstrip()[:3]
        if fence is None and head in ('```', '~~~'):
            fence = head
        elif fence is not None and head == fence:
            fence = None
        elif fence is None and _SOURCE_DIRECTIVE.match(line):
            out.append(expansion(line))
            continue
        out.append(line)
    return '\n'.join(out)


def _build_llms_doc(name: str, description: str, expanded_markdown: str, path: str) -> str:
    """Wrap the expanded markdown with the heading/description preamble that
    /llms.txt readers expect.

    ``name`` must be the PUBLISHED name, not the registered one. The package
    injects its own `<h1>` header into the crawler document from the published
    identity, and >= 2.7.0 dedups that against the document's opening h1 — so
    the two have to be the same string or the page serves both. They were not
    for "/" alone: the preamble said "Home" (the nav label) while the injected
    header said the site brand, which is exactly the substitution
    `lib.page_visibility.published_name` exists to make. See its docstring for
    why "Home" must never become this site's published identity.
    """
    parts: List[str] = [f"# {name}\n"]
    if description:
        parts.append(f"> {description}\n")
    parts.append("---\n")
    parts.append(expanded_markdown.rstrip() + "\n")
    parts.append("\n---\n")
    parts.append(f"*Source: {path}*\n")
    return "\n".join(parts)


# Headings containing inline code/emphasis crash markdown2dash's renderer and,
# when they don't, get an id their own TOC anchor doesn't match; and inline
# `![alt](src)` images raise on the DMC child list because markdown2dash
# defines no `image` renderer at all. Must run BEFORE create_parser()
# instantiates the renderer. See lib/directives/headings.py.
patch_renderer()

directives = [Admonition(), BlockExec(), Divider(), Image(), Kwargs(), LlmsCopy(), SC(), TOC()]
parse = create_parser(directives)

for file in files:
    logger.info("Loading %s..", file)
    metadata, content = frontmatter.parse(file.read_text())
    metadata = Meta(**metadata)

    # Substitute derived facts BEFORE any consumer sees the text, so the
    # browser page, the copy button, and /<page>/llms.txt all publish the
    # same truth. A doc writes {{VERSION:<distribution>}} instead of a
    # version number — any installed package, so this site can document
    # dash-leaflet2's own version the same way the boilerplate documents
    # dash-improve-my-llms's. See lib/versions.py for why.
    content = substitute_versions(content, source=str(file))

    # Store raw markdown content in NAME_CONTENT_MAP for the LLM copy button.
    NAME_CONTENT_MAP[metadata.name] = content

    # Pages with a `.. toc::` fill the aside; the shell collapses it for
    # every other page (lib/aside.py, template 1.6.39 — full-width /changelog).
    if ".. toc::" in content:
        aside.register(metadata.endpoint)

    layout = parse(content)

    # add heading and description to the layout
    section = [
        dmc.Title(metadata.name, order=2, className="m2d-heading"),
        dmc.Text(metadata.description, className="m2d-paragraph"),
    ]
    layout = section + layout

    # 2plot.dev ad network: the slot joins the Stack inside the `.. toc::`
    # aside so it scrolls with the table of contents. Pages without a TOC get
    # no ad, and the call is fail-silent — an ad must never break registration.
    inject_ad_into_aside(layout, metadata.endpoint)

    # ONE declared value, TWO ledgers. `declared` is None for a page that
    # says nothing, which both registries read as "use the deployment
    # default" — so PAGE_DEFAULT_TIER moves every undeclared page at once,
    # which is what makes the dark launch and its flip a single env change.
    declared = _declared_tier(metadata, str(file))

    # The control board's row. Overrides written here win at resolution time
    # (lib.access.local_tier), which is what makes a toggle apply live.
    register_default(
        metadata.endpoint,
        metadata.name,
        visibility=declared,
        llms_public=metadata.llms_public,
    )

    # The network ledger: what the hub's page-tier ceiling compares against
    # and what lib.access enforces underneath any override. Registered BEFORE
    # dash.register_page so no request can reach the layout ahead of the tier
    # that is meant to gate it.
    page_tiers.register(metadata.endpoint, declared, llms_public=metadata.llms_public)

    # register with dash. The layout goes through lib.gate_layouts, which
    # re-resolves access on EVERY render — that is what makes a control-board
    # toggle, a hub ceiling change and an env flip all apply without a
    # restart, and what puts the sign-in card in front of a gated page.
    dash.register_page(
        metadata.name,
        metadata.endpoint,
        name=metadata.name,
        title=PAGE_TITLE_PREFIX + metadata.name,
        description=metadata.description,
        # The social card. Without this Dash emits `og:image content=""` and
        # `twitter:image content=""` on every page — an empty image unfurls as
        # a blank card, which is worse than declaring no image at all. An
        # absolute `image_url` also beats Dash's assets-derived path, which
        # would be relative and therefore useless to a scraper.
        image_url=OG_IMAGE_URL,
        layout=gated_layout(metadata.endpoint, metadata.name, layout),
        category=metadata.category,
        icon=metadata.icon,
        order=metadata.order,
    )

    # Feed the expanded markdown into dash-improve-my-llms so /<page>/llms.txt
    # serves the directive-expanded prose. Still routed through
    # page_visibility, which now registers the REAL prose and lets
    # lib.access.check decide per request whether the fetch may have it — see
    # that module's llms.txt-bridge comment for why the old stub swap went.
    #
    # The kwargs below are the CRAWLER document's record, and they must not
    # describe the page differently from the `dash.register_page` call above:
    # that call is what a browser reads, this one is what Googlebot reads, and
    # a site whose two heads disagree is the shape of every SEO defect the
    # network measured in 2026-08. Content may differ between the two
    # documents; identity may not. Before this passed anything, the crawler
    # document carried no og:image at all (browsers got one) and typed every
    # documentation page as a bare schema.org WebPage.
    expanded = _expand_source_directives(content)
    register_llms_doc(
        metadata.endpoint,
        metadata.name,
        metadata.description,
        _build_llms_doc(published_name(metadata.endpoint, metadata.name),
                        metadata.description, expanded, metadata.endpoint),
        # Same string dash.register_page got. Measured, not assumed: it does
        # NOT double the brand — the package composes its own
        # "<page> · <site>" only when no title is declared.
        title=PAGE_TITLE_PREFIX + metadata.name,
        image_url=OG_IMAGE_URL,
        # TechArticle, not the package's WebPage default: every page here
        # documents software, and "WebPage" tells a crawler nothing it could
        # not already see. run.py declares the home page separately.
        schema_type="TechArticle",
        # None omits the sitemap tag on >= 2.6.0 (the floor in
        # requirements.txt), which is the truth-or-silence half. `lastmod`
        # only exists from 2.6.0; below the floor it is at best ignored, and
        # the sitemap goes back to stamping every page "today" — which is why
        # the floor is a floor and not a preference.
        lastmod=metadata.lastmod,
    )
