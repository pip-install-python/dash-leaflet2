"""`.. source::` — publish real code to both lanes, from ONE parse.

Phase 1 of the owner's decision 0ab. The directive grows two options:

    .. source::docs/text-marker/example.py
        :region: minimal
        :caption: A caption you place like a Marker

`:region:` names a span of the REAL file, delimited by `# region <name>` /
`# endregion`. That is the whole point of the phase: the pages previously
carried a hand-written `CODE = \"\"\"…\"\"\"` constant beside the module it
described, and nothing tied the two together — measured across 17 example
files, not one shared a single distinctive line with its own module. It
could not "drift"; it was never attached. A region cannot drift, because
there is only one copy and the directive reads it.

`:caption:` carries the words that used to be `code_panel`'s first
argument, so the caption survives the helper it lived in.

BOTH LANES, ONE EXTRACTOR. `extract_region` below is imported by
`pages/markdown.py`, which builds the machine document — the browser gets a
CodeHighlightTabs and an agent gets a fenced block, and neither can show a
different region from the other because there is one implementation. That
is note 80's rule applied to a directive rather than discovered through one.

Markers are `# region` / `# endregion` deliberately: PyCharm folds them
natively, so they earn their place in the file for the person editing it
and are not tooling scaffolding that only the docs build cares about.
"""
import os
import re
import textwrap

import dash_mantine_components as dmc
from dash.development.base_component import Component
from dash_iconify import DashIconify
from markdown2dash import SourceCode

# `# region <name>` … `# endregion`. The name is required: an unnamed region
# would make two regions in one file indistinguishable, and the failure
# would be a silently wrong snippet rather than an error.
REGION_START = re.compile(r"^[ \t]*#[ \t]*region[ \t]+(\S+)[ \t]*$")
REGION_END = re.compile(r"^[ \t]*#[ \t]*endregion\b")


class RegionNotFound(LookupError):
    """A named region is missing from the file it was asked for.

    Its own type so both lanes can render the same explicit failure. A
    missing region must never fall back to the whole file: that is the
    silent-wrong-content failure this phase exists to remove, and it would
    look like success on every page.
    """


def extract_region(text: str, name: str) -> str:
    """The lines between `# region <name>` and `# endregion`, dedented.

    Dedented because a region inside a function or a list literal is
    indented in place, and a snippet a reader is meant to copy should not
    carry its container's indentation. The markers themselves are dropped.
    """
    out, inside = [], False
    for line in text.split("\n"):
        if not inside:
            m = REGION_START.match(line)
            if m and m.group(1) == name:
                inside = True
            continue
        if REGION_END.match(line):
            return textwrap.dedent("\n".join(out)).strip("\n")
        out.append(line)
    if inside:
        raise RegionNotFound(f"region {name!r} is opened but never closed")
    raise RegionNotFound(f"no region {name!r} in this file")


def read_source(path: str, region: str | None = None) -> str:
    """The file, or one named region of it. The single reader both lanes use."""
    with open(path, "r") as fh:
        text = fh.read()
    return extract_region(text, region) if region else text


class SC(SourceCode):
    NAME = "source"

    def render(self, renderer, title: str, content: str, **options) -> Component:
        defaultExpanded = options.pop("defaultExpanded", "false")
        withExpandedButton = options.pop("withExpandedButton", "true")
        region = (options.pop("region", "") or "").strip() or None
        caption = (options.pop("caption", "") or "").strip() or None

        mapping = {
            "py": {"language": "python", "icon": DashIconify(icon="devicon:python")},
            "css": {"language": "css", "icon": DashIconify(icon="devicon:css3")},
        }
        files = title.split(", ")
        code = []
        for file in files:
            extension = file.split(".")[-1]
            try:
                body = read_source(file, region)
            except RegionNotFound as exc:
                # LOUD, and in the page: a caption promising a snippet above
                # an empty block is the shape this phase removes.
                body = f"# ERROR: {exc}"
            code.append(
                {
                    # The region, when there is one, belongs in the tab label:
                    # the tab otherwise claims to be the whole file.
                    "fileName": os.path.basename(file) + (f" · {region}" if region else ""),
                    "code": body,
                    "language": mapping[extension]["language"],
                    "icon": mapping[extension]["icon"],
                }
            )
        block = dmc.CodeHighlightTabs(
            code=code,
            defaultExpanded=defaultExpanded == "true",
            withExpandButton=withExpandedButton == "true",
            # The copy button is icon-only; without these it has no
            # accessible name (the audit's "copy button without text").
            copyLabel="Copy code",
            copiedLabel="Copied",
        )
        if not caption:
            return block
        # Mirrors what `code_panel(title, code)` rendered — a Title(order=4)
        # above the code — so a converted page reads the same as before.
        return dmc.Stack([dmc.Title(caption, order=4, mb=0), block], gap="sm")
