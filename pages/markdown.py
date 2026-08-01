import logging
import re
from pathlib import Path
from typing import List, Optional

import dash
import dash_mantine_components as dmc
import frontmatter
from markdown2dash import Admonition, BlockExec, Divider, Image, create_parser
from pydantic import BaseModel

from lib.ad_client import inject_ad_into_aside
from lib.constants import OG_IMAGE_URL, PAGE_TITLE_PREFIX, NAME_CONTENT_MAP
from lib.directives.kwargs import Kwargs
from lib.directives.llms_copy import LlmsCopy
from lib.directives.source import SC
from lib.directives.toc import TOC
from lib.page_visibility import gated_layout, register_default, register_llms_doc

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
    # Baseline access tier for this page. Omitted → lib.page_visibility's
    # DEFAULT_TIER ("public"). The admin control board's overrides always win.
    visibility: Optional[str] = None
    # Whether this page's prose may be served at /<page>/llms.txt to anonymous
    # and AI traffic. Also live-toggleable from the control board.
    llms_public: bool = True


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
    """
    def replace(match: re.Match) -> str:
        file_path = match.group(1).strip()
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

    return _SOURCE_DIRECTIVE.sub(replace, markdown_content)


def _build_llms_doc(name: str, description: str, expanded_markdown: str, path: str) -> str:
    """Wrap the expanded markdown with the heading/description preamble that
    /llms.txt readers expect."""
    parts: List[str] = [f"# {name}\n"]
    if description:
        parts.append(f"> {description}\n")
    parts.append("---\n")
    parts.append(expanded_markdown.rstrip() + "\n")
    parts.append("\n---\n")
    parts.append(f"*Source: {path}*\n")
    return "\n".join(parts)


directives = [Admonition(), BlockExec(), Divider(), Image(), Kwargs(), LlmsCopy(), SC(), TOC()]
parse = create_parser(directives)

for file in files:
    logger.info("Loading %s..", file)
    metadata, content = frontmatter.parse(file.read_text())
    metadata = Meta(**metadata)

    # Store raw markdown content in NAME_CONTENT_MAP for the LLM copy button.
    NAME_CONTENT_MAP[metadata.name] = content

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

    # Baseline tier from frontmatter; the control board overrides it live.
    register_default(
        metadata.endpoint,
        metadata.name,
        visibility=metadata.visibility,
        llms_public=metadata.llms_public,
    )

    # register with dash. The layout goes through the visibility gate, which
    # re-checks access on EVERY render — that is what makes a control-board
    # toggle apply without a restart.
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
    )

    # Feed the expanded markdown into dash-improve-my-llms so /<page>/llms.txt
    # serves the directive-expanded prose. Routed through page_visibility so
    # the control board's llms.txt switch can swap the body for a stub.
    expanded = _expand_source_directives(content)
    register_llms_doc(
        metadata.endpoint,
        metadata.name,
        metadata.description,
        _build_llms_doc(metadata.name, metadata.description, expanded, metadata.endpoint),
    )
