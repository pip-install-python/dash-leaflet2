"""A fixture module with named regions, for tests/test_source_directive.py.

Deliberately has TWO regions and prose outside both, so a test can prove the
directive published the right one rather than the whole file.
"""

PREAMBLE = "not in any region"


def build():
    # region minimal
    layout = {
        "kind": "map",
        "center": [37.808, -122.409],
    }
    return layout
    # endregion


def other():
    # region second
    return "the other region"
    # endregion


TRAILER = "also not in any region"
