"""/changelog — CHANGELOG.md as a DMC Timeline; the file itself is the LLMS_DOC.

Ported from pip-docs+ (the reference, 1.6.38). One source of truth: the
timeline is parsed from CHANGELOG.md at render time, and the crawler
document reproduces the file verbatim (minus its H1, which this page
already supplies), so the two never disagree.
"""
from __future__ import annotations

import re
from pathlib import Path

import dash
import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

from lib.constants import OG_IMAGE_URL, PAGE_TITLE_PREFIX, SITE_SHORT_NAME

CHANGELOG_PATH = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def newest_release_date(path: Path = CHANGELOG_PATH) -> str | None:
    """The date of the most recent DATED release heading, or None.

    This site's rule is that `lastmod:` rides the prose and is never scripted
    from file mtimes (they reset on every Docker build, which is how a sitemap
    ends up swearing all 27 pages changed today). This page has no frontmatter
    to carry one — so it derives the date from the prose itself, which is the
    same rule honoured by other means: a release heading IS the statement that
    the content changed that day. `[Unreleased]` carries no date and is
    skipped, so an in-flight section never post-dates the page.

    Upstream registers /changelog with no lastmod at all; this repo's
    tests/test_seo_icons.py fails the sitemap for that, which is how the gap
    was found.
    """
    for line in path.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^## \[[^\]]+\](?:\s*[-–—]\s*)(\d{4}-\d{2}-\d{2})", line)
        if m:
            return m.group(1)
    return None


dash.register_page(
    __name__,
    path="/changelog",
    name="Changelog",
    title=PAGE_TITLE_PREFIX + "Changelog",
    description=f"Version history of {SITE_SHORT_NAME}, rendered from CHANGELOG.md.",
    image_url=OG_IMAGE_URL,
    icon="tabler:history",
    lastmod=newest_release_date(),
)


def _build_llms_doc() -> str:
    intro = (
        "# Changelog\n\n"
        f"> Version history of {SITE_SHORT_NAME}. The timeline on this page is "
        "rendered from `CHANGELOG.md`, reproduced below.\n\n---\n\n"
    )
    try:
        body = CHANGELOG_PATH.read_text(encoding="utf-8")
    except OSError:
        return intro
    # CHANGELOG.md opens with its own `# Changelog` H1 and the intro already
    # supplies one — two identical h1s is the every-page structure pin's red.
    lines = body.split("\n")
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if line.startswith("# "):
            lines = lines[i + 1:]
        break
    return intro + "\n".join(lines).lstrip("\n")


LLMS_DOC = _build_llms_doc()


def parse_changelog(path: Path = CHANGELOG_PATH) -> list[dict]:
    """``[{version, date, sections: {name: [items]}}]`` in file order."""
    if not path.exists():
        return []
    versions: list[dict] = []
    current = None
    sections: dict = {}
    section = None
    items: list = []

    def close_section():
        if current is not None and section:
            sections.setdefault(section, []).extend(items)

    for line in path.read_text(encoding="utf-8").split("\n"):
        # PORTED: the template's regex accepts only an ASCII hyphen. This
        # repo's CHANGELOG has always used an EM DASH — `## [0.2.2] — 2026-08-05`
        # — so upstream's pattern matched the version and silently dropped
        # every date, rendering a Timeline with no dates at all. Accept all
        # three separators rather than rewriting six years of headings.
        vm = re.match(r"^## \[([^\]]+)\](?:\s*[-–—]\s*(.+))?", line)
        if vm:
            close_section()
            if current is not None:
                versions.append({**current, "sections": sections})
            current = {"version": vm.group(1), "date": vm.group(2) or ""}
            sections, section, items = {}, None, []
            continue
        sm = re.match(r"^### (.+)", line)
        if sm and current is not None:
            close_section()
            section, items = sm.group(1), []
            continue
        if current is None or not section:
            continue
        if line.startswith("- "):
            items.append({"type": "item", "text": line[2:]})
        elif line.startswith("  - "):
            items.append({"type": "subitem", "text": line[4:]})
        elif line.startswith("  ") and items and items[-1]["type"] in ("item", "subitem"):
            items[-1]["text"] += " " + line.strip()      # wrapped bullet
    close_section()
    if current is not None:
        versions.append({**current, "sections": sections})
    return versions


_SECTION_ICONS = {
    "added": ("tabler:plus", "green"),
    "changed": ("tabler:refresh", "blue"),
    "fixed": ("tabler:bug", "orange"),
    "removed": ("tabler:trash", "red"),
    "deprecated": ("tabler:alert-triangle", "yellow"),
    "security": ("tabler:shield-check", "violet"),
    "recorded": ("tabler:notes", "gray"),
}


def _section_icon(name: str):
    for key, val in _SECTION_ICONS.items():
        if key in name.lower():
            return val
    return "tabler:point", "gray"


def _inline(text: str):
    """`code` and **bold** inside one bullet."""
    out = []
    for i, part in enumerate(re.split(r"`([^`]+)`", text)):
        if i % 2:
            out.append(dmc.Code(part, style={"overflowWrap": "anywhere"}))
            continue
        for j, bp in enumerate(re.split(r"\*\*([^*]+)\*\*", part)):
            if not bp:
                continue
            out.append(html.Strong(bp) if j % 2 else bp)
    return out


# A bullet in a no-wrap Group: without min-width:0 the Text grows to the
# width of its longest unbreakable token — a 60-character test name in a
# `code` span — and the row leaves its card (measured on a phone: a 429px
# paragraph in a 218px group, a 549px document at 391px). `anywhere` lets
# that token break; the Code spans get the same.
_WRAP = {"flex": 1, "minWidth": 0, "overflowWrap": "anywhere"}


def _section(name: str, items: list):
    icon, color = _section_icon(name)
    rows = []
    for it in items:
        if it["type"] == "item":
            rows.append(dmc.Group(
                [DashIconify(icon="tabler:point-filled", width=8, color=f"var(--mantine-color-{color}-6)"),
                 dmc.Text(_inline(it["text"]), size="sm", style=_WRAP)],
                gap="xs", align="flex-start", wrap="nowrap"))
        else:
            rows.append(dmc.Group(
                [dmc.Box(w=16), DashIconify(icon="tabler:point", width=6),
                 dmc.Text(_inline(it["text"]), size="xs", c="dimmed", style=_WRAP)],
                gap="xs", align="flex-start", wrap="nowrap", ml="md"))
    return dmc.Paper(
        [dmc.Group([dmc.ThemeIcon(DashIconify(icon=icon, width=16), color=color,
                                  variant="light", size="sm", radius="xl"),
                    dmc.Text(name, fw=600, size="sm")], gap="xs", mb="xs"),
         dmc.Stack(rows, gap=4)],
        p="sm", radius="md", withBorder=True, mb="xs")


def _version_item(v: dict, is_current: bool):
    cards = [_section(n, items) for n, items in v["sections"].items() if items]
    return dmc.TimelineItem(
        bullet=dmc.ThemeIcon(DashIconify(icon="tabler:rocket", width=16),
                             variant="filled" if is_current else "light", size=28, radius="xl"),
        title=dmc.Group(
            [dmc.Badge(f"v{v['version']}", variant="filled" if is_current else "light", size="lg"),
             dmc.Text(v["date"], size="sm", c="dimmed") if v["date"] else None,
             dmc.Badge("Current", color="green", variant="outline", size="sm") if is_current else None],
            gap="sm"),
        children=dmc.Stack(cards, gap="xs", mt="sm") if cards
        else dmc.Text("No changes documented", c="dimmed", size="sm"),
    )


def timeline(versions: list[dict]):
    if not versions:
        return dmc.Text("CHANGELOG.md could not be found or parsed.", c="dimmed")
    return dmc.Timeline(
        [_version_item(v, i == 0) for i, v in enumerate(versions)],
        active=0, bulletSize=32, lineWidth=2,
    )


def layout(**kwargs):
    versions = parse_changelog()
    return dmc.Container(
        [
            dmc.Group(
                [dmc.ThemeIcon(DashIconify(icon="tabler:history", width=28), size=48, radius="md", variant="light"),
                 dmc.Stack([dmc.Title("Changelog", order=1),
                            dmc.Text(f"All notable changes to {SITE_SHORT_NAME}.", c="dimmed")], gap=0)],
                gap="md", mb="md"),
            dmc.Badge(f"{len(versions)} release{'s' if len(versions) != 1 else ''}",
                      variant="light", size="lg", mb="xl"),
            dmc.Divider(mb="xl"),
            timeline(versions),
            dmc.Text(
                ["This changelog follows ",
                 dmc.Anchor("Keep a Changelog", href="https://keepachangelog.com/en/1.1.0/", target="_blank"),
                 " and ", dmc.Anchor("Semantic Versioning", href="https://semver.org/", target="_blank"), "."],
                size="sm", c="dimmed", mt="xl"),
        ],
        id="m2d-page-changelog",
        size="md",
        py="xl",
    )


# ---------------------------------------------------------------------------
# THIS FORK'S WIRING. Upstream leaves a module-level `LLMS_DOC` for the
# package to discover, which gets the prose onto the page's llms.txt but sends
# no `lastmod` — so this page entered the sitemap dateless and
# tests/test_seo_icons.py failed it. (The template ships this page and has no
# such test, so the gap is invisible there.) Routing through
# lib.page_visibility.register_llms_doc is also what every docs page here
# does, so the control board's per-page llms.txt toggle reaches this page too
# instead of silently skipping it.
# ---------------------------------------------------------------------------
from lib.page_visibility import register_llms_doc  # noqa: E402

register_llms_doc(
    "/changelog",
    "Changelog",
    f"Version history of {SITE_SHORT_NAME}, rendered from CHANGELOG.md.",
    LLMS_DOC,
    title=PAGE_TITLE_PREFIX + "Changelog",
    image_url=OG_IMAGE_URL,
    schema_type="TechArticle",
    lastmod=newest_release_date(),
)
