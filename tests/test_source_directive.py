"""`.. source::` regions and captions — phase 1 of decision 0ab.

THE DEFECT THIS REMOVES: every example page carried a hand-written
`CODE = \"\"\"…\"\"\"` constant describing the module beside it, published by
`code_panel(caption, CODE)`. Measured across 17 example files, not one
shared a single distinctive line with its own module — the snippet could
not "drift", it was never attached to the code at all. A region is read
from the real file, so there is exactly one copy and a wrong snippet
becomes impossible rather than unlikely.

Every pin here asserts CONTENT — the lines that must and must not appear —
and the parity pin is MUTATION-CHECKED at the bottom: disable the
extraction and watch it go red. A pin that cannot fail guards nothing
(this session learned that twice).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIXTURE = "tests/fixtures/region_sample.py"

IN_MINIMAL = '"kind": "map",'
IN_SECOND = 'return "the other region"'
OUTSIDE_ANY = 'PREAMBLE = "not in any region"'


# ------------------------------------------------------------- extractor --


def test_a_region_is_extracted_dedented_without_its_markers():
    from lib.directives.source import extract_region

    got = extract_region(Path(FIXTURE).read_text(), "minimal")
    assert IN_MINIMAL in got
    assert got.startswith("layout = {"), f"not dedented: {got[:40]!r}"
    assert "# region" not in got and "# endregion" not in got
    assert OUTSIDE_ANY not in got, "the extractor returned more than the region"
    assert IN_SECOND not in got, "the extractor crossed into the next region"


def test_the_right_region_of_several_is_returned():
    from lib.directives.source import extract_region

    got = extract_region(Path(FIXTURE).read_text(), "second")
    assert IN_SECOND in got and IN_MINIMAL not in got


def test_a_missing_region_raises_rather_than_falling_back():
    """THE IMPORTANT ONE. Falling back to the whole file would publish
    something plausible and wrong — the exact failure this phase removes,
    and it would look like success on every page."""
    from lib.directives.source import RegionNotFound, extract_region

    with pytest.raises(RegionNotFound):
        extract_region(Path(FIXTURE).read_text(), "no-such-region")


def test_an_unclosed_region_raises():
    from lib.directives.source import RegionNotFound, extract_region

    with pytest.raises(RegionNotFound):
        extract_region("# region open\nbody\n", "open")


# ----------------------------------------------------------- lane parity --


def _machine(md_text: str, app_module) -> str:
    from pages.markdown import _expand_source_directives

    return _expand_source_directives(md_text)


def _browser_code(region=None, caption=None):
    """The code string the browser lane renders, via the real directive."""
    from lib.directives.source import SC

    opts = {}
    if region:
        opts["region"] = region
    if caption:
        opts["caption"] = caption
    rendered = SC().render(None, FIXTURE, "", **opts)
    blob = str(rendered)
    return blob


DOC = f""".. source::{FIXTURE}
    :region: minimal
    :caption: The minimal shape
"""


def test_both_lanes_publish_the_same_region(app_module):
    """ONE extractor, two consumers — neither lane can show code the other
    does not. The parity is the point of putting the reader in
    lib/directives/source.py rather than in each lane."""
    machine = _machine(DOC, app_module)
    browser = _browser_code(region="minimal", caption="The minimal shape")

    for lane, text in (("machine", machine), ("browser", browser)):
        assert IN_MINIMAL in text, f"{lane} lane lost the region's content"
        assert OUTSIDE_ANY not in text, f"{lane} lane published the whole file"
        assert IN_SECOND not in text, f"{lane} lane published the wrong region"


def test_the_caption_reaches_both_lanes(app_module):
    machine = _machine(DOC, app_module)
    assert "The minimal shape" in machine
    assert "**The minimal shape**" in machine, "caption is not marked up as one"
    assert "The minimal shape" in _browser_code(region="minimal",
                                                caption="The minimal shape")


def test_the_machine_lane_names_the_region_it_published(app_module):
    """A fenced block claiming to be a file, that is really 6 lines of it,
    misleads an agent about what it has."""
    machine = _machine(DOC, app_module)
    assert f"# File: {FIXTURE}  (region: minimal)" in machine


def test_option_lines_never_reach_the_prose(app_module):
    """54 of these were being published across this corpus before phase 1:
    only `.. exec::` consumed its option lines, so every `.. source::`
    option fell through as prose — a bare `:defaultExpanded: false` sitting
    under the code fence in /events-python/llms.txt."""
    doc = f""".. source::{FIXTURE}
    :region: minimal
    :defaultExpanded: false
    :withExpandedButton: true
"""
    machine = _machine(doc, app_module)
    for opt in (":defaultExpanded:", ":withExpandedButton:", ":region:"):
        assert opt not in machine, f"{opt} leaked into the machine document"
    assert IN_MINIMAL in machine, "the code went with the options"


def test_a_missing_region_is_loud_in_both_lanes(app_module):
    doc = f".. source::{FIXTURE}\n    :region: nope\n"
    machine = _machine(doc, app_module)
    assert "Error" in machine and "nope" in machine
    assert OUTSIDE_ANY not in machine, "a missing region fell back to the file"
    browser = _browser_code(region="nope")
    assert "ERROR" in browser and OUTSIDE_ANY not in browser


def test_no_region_still_publishes_the_whole_file(app_module):
    """The existing behaviour, unchanged — 27 pages depend on it."""
    machine = _machine(f".. source::{FIXTURE}\n", app_module)
    assert OUTSIDE_ANY in machine and IN_MINIMAL in machine


# --------------------------------------------------------- mutation check --


def test_the_parity_pin_goes_red_when_extraction_is_disabled(app_module,
                                                             monkeypatch):
    """Disable the region reader and the parity assertions must fail. If
    they still pass they were reading something that is true either way."""
    from lib.directives import source as src_mod

    monkeypatch.setattr(src_mod, "extract_region",
                        lambda text, name: text)   # "region" = the whole file
    import pages.markdown as md
    monkeypatch.setattr(md, "read_source",
                        lambda path, region=None: Path(path).read_text())

    machine = _machine(DOC, app_module)
    assert OUTSIDE_ANY in machine, (
        "the mutation did not take, so this check proves nothing about the "
        "parity pin above"
    )
    # ...which is exactly what test_both_lanes_publish_the_same_region forbids.


def test_the_directive_reads_its_options_from_one_place():
    """Source pin: both lanes must call the shared reader, not re-implement
    it. A second implementation is how the two lanes drift apart."""
    md_src = (REPO / "pages" / "markdown.py").read_text()
    assert "from lib.directives.source import" in md_src
    assert "read_source(" in md_src
    assert not re.search(r"def\s+extract_region", md_src), (
        "pages/markdown.py has its own extractor — there must be one"
    )
