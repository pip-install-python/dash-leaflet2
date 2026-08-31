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
from lib.directives.source import RegionNotFound, read_source
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
    # A SHORT sidebar/search label, when the page's real name is too long for
    # the rail. Shortening `name:` instead would churn <title>, og:title and
    # the llms.txt heading, which are the same string — this is the seam that
    # lets the two differ. Absent means the name is already short enough,
    # which is true of every page here today.
    nav: Optional[str] = None
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
_EXEC_DIRECTIVE = re.compile(r'^\.\. exec::(.+?)$', re.MULTILINE)
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
    """Inline `.. source::path` and `.. exec::module` into the prose.

    ONE fence-aware pass, two directives, two consumers — the browser lane
    renders components, the machine lane gets the code that produces them.
    `.. exec::` joined this function at 1.6.43 (owner's decision 0aa) after
    the item-18 fan-out found the same class live on six forks: a directive
    that renders Dash components puts its output only in the React tree,
    and the machine lane is built from the markdown SOURCE where the
    directive line is stripped. Measured here first: /fastapi-showcase
    served 19,378 bytes about three components whose code was nowhere in
    it. The dedupe rule below keeps this composable with the hand-paired
    road four of this repo's docs already take.

    This produces the prose that dash-improve-my-llms 2.0 will serve at
    `/<page>/llms.txt`. Replacing the directive with the real file content
    is what makes the LLM output self-contained for the "paste into a chat
    window" audience.

    FENCE-AWARE, and it has to be: a directive INSIDE a fenced code block
    is documentation showing the syntax, not a directive (docs/example and
    docs/directives both teach `.. source::` inside ```markdown fences).
    Expanding it injects a ```python fence inside the already-open fence,
    which CLOSES it early — from there the inlined file renders as
    markdown, every `# comment` line becomes an <h1>, and the machine lane
    of the page serves broken structure (found 2026-08-23 by the
    single-h1 pin in tests/test_pages.py; the browser lane was never
    affected because markdown2dash parses fences properly).
    """
    def _options(start: int) -> dict:
        """The directive's own indented `:key: value` continuation lines.

        Read by BOTH directives now. Before phase 1 only `.. exec::`
        consumed them, so every `.. source::` option line fell through to
        `out` and was published as prose — 54 of them across this corpus,
        e.g. a bare `:defaultExpanded: false` sitting under the code fence
        in /events-python/llms.txt. Skipping them is half this function's
        job; honouring them is the other half.
        """
        opts = {}
        j = start
        while j < len(lines) and lines[j].strip().startswith(':'):
            key, _, val = lines[j].strip().lstrip(':').partition(':')
            opts[key.strip()] = val.strip()
            j += 1
        return opts

    def expansion(directive_line: str, opts: dict) -> str:
        file_path = _SOURCE_DIRECTIVE.match(directive_line).group(1).strip()
        region = opts.get('region') or None
        caption = opts.get('caption') or None
        try:
            full = Path(file_path)
            ext = full.suffix.lstrip('.').lower()
            lang = _LANG_MAP.get(ext, ext or 'text')
            # THE SAME READER THE BROWSER LANE USES (lib/directives/source),
            # so the two lanes cannot show different code for one directive.
            content = read_source(str(full), region)
            tail = '' if content.endswith('\n') else '\n'
            header = f'# File: {file_path}'
            if region:
                header += f'  (region: {region})'
            block = f'\n```{lang}\n{header}\n\n{content}{tail}```\n'
            # The caption becomes bold prose rather than a heading: a
            # heading here would join the page's outline and the `.. toc::`,
            # which the component lane's Title(order=4) does not.
            return f'\n**{caption}**\n{block}' if caption else block
        except RegionNotFound as exc:
            return f'\n<!-- Error: {exc} in {file_path} -->\n'
        except FileNotFoundError:
            return f'\n<!-- Error: File not found: {file_path} -->\n'
        except Exception as exc:
            return f'\n<!-- Error reading {file_path}: {exc} -->\n'

    def exec_target_file(module_path: str) -> str:
        """`docs.fastapi-showcase.async_demo` -> `docs/fastapi-showcase/async_demo.py`."""
        return module_path.strip().split('\n')[0].strip().replace('.', '/') + '.py'

    def exec_expansion(module_path: str) -> str:
        """The exec'd component's SOURCE, which is what an agent can use.

        A component cannot be serialised into markdown and a screenshot is
        worse than nothing to a reader who cannot render it; the source is
        what produces the demo (llms' shaping, 2026-08-31).
        """
        target = exec_target_file(module_path)
        try:
            content = Path(target).read_text()
            tail = '' if content.endswith('\n') else '\n'
            return f'\n```python\n# File: {target}\n\n{content}{tail}```\n'
        except FileNotFoundError:
            return f'\n<!-- Error: exec target not found: {target} -->\n'
        except Exception as exc:
            return f'\n<!-- Error reading {target}: {exc} -->\n'

    lines = markdown_content.split('\n')

    # DEDUPE (owner's decision 0aa, 2026-08-31): where the page already pairs
    # an `.. exec::` with an explicit `.. source::` for the SAME target — the
    # hand-authored road four of this repo's five exec-using docs already
    # take — the auto-render is skipped and the directive line simply goes,
    # so the page never shows the code twice. The two roads compose instead
    # of colliding. Document-wide rather than "the source that FOLLOWS":
    # the property is that the code is already present, and a page that
    # shows the source first is not a different case.
    #
    # A `.. source::` naming a DIFFERENT file does NOT dedupe — otherwise the
    # rule silently swallows exactly the unpaired directive it exists to
    # catch, which is the whole defect. Pinned in tests/test_exec_lane.py.
    paired: set = set()
    fence = None
    for line in lines:
        head = line.lstrip()[:3]
        if fence is None and head in ('```', '~~~'):
            fence = head
        elif fence is not None and head == fence:
            fence = None
        elif fence is None:
            m = _SOURCE_DIRECTIVE.match(line)
            if m:
                paired.add(m.group(1).strip())

    out: List[str] = []
    fence = None  # the marker that opened the block we are inside, if any
    skip_options = False
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        head = line.lstrip()[:3]
        # A directive's own `    :option: value` continuation lines belong to
        # the directive; dropping the directive without them leaves the
        # options behind as prose.
        if skip_options:
            if line.strip().startswith(':') or not line.strip():
                if line.strip():
                    continue
            skip_options = False

        if fence is None and head in ('```', '~~~'):
            fence = head
        elif fence is not None and head == fence:
            fence = None
        elif fence is None and _SOURCE_DIRECTIVE.match(line):
            # `i` already points PAST this line, so it is the first
            # candidate option line.
            skip_options = True
            out.append(expansion(line, _options(i)))
            continue
        elif fence is None:
            m = _EXEC_DIRECTIVE.match(line)
            if m:
                skip_options = True
                # `:code: false` is the AUTHOR saying this module is
                # plumbing for an embed, not documentation (muischeduler,
                # 2026-08-31 — 12 of its 34 directives carry it). Rendering
                # it into the machine lane publishes exactly what the
                # browser lane deliberately hides, inverting the usual
                # asymmetry, and silently: the browser keeps looking right.
                # This repo shipped that inversion on all three of its own
                # unpaired directives before the correction landed.
                # Skipped, but NOT silently — broken, hidden and absent must
                # not look alike, which is the whole lesson of this round.
                opts = []
                j = i
                while j < len(lines) and lines[j].strip().startswith(':'):
                    opts.append(lines[j].strip())
                    j += 1
                hidden = any(o.replace(' ', '').lower() == ':code:false' for o in opts)
                target = exec_target_file(m.group(1))
                if target in paired:
                    # Dedupe wins over the withheld marker: the source IS in
                    # this document, via `.. source::`, so announcing it as
                    # withheld would be a false statement about the page.
                    pass
                elif hidden:
                    out.append(
                        f'\n<!-- component rendered from {target}; source withheld '
                        f'by `:code: false` -->\n'
                    )
                else:
                    out.append(exec_expansion(m.group(1)))
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
        nav=metadata.nav,
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
