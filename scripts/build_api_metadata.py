#!/usr/bin/env python3
"""Distil dash_leaflet2/metadata.json down to what /api actually renders.

WHY THIS EXISTS (and why no other fork in the fleet has it): the template's
`lib/api_reference.py` reads the component package's `metadata.json`, which
on a pip-installed Dash component package sits next to `__init__.py`. In
THIS repo that file is a 27 MB react-docgen build artifact that is both
.gitignored (DIVERGENCES 12) and excluded from the wheel (MANIFEST.in) —
it is a build INPUT, not a runtime file. Render clones the repo and builds
the Dockerfile, so production never has it, and `/api` would render an empty
page while every local check passed.

This writes `dash_leaflet2/api_metadata.json` — the same 26 components in
the shape `load_package()` already returns, about 64 KB — which IS committed.
`lib/api_reference.load_package` prefers metadata.json when it is there, so a
developer who just re-ran `npm run build:backends` sees new props immediately;
everyone else gets this file.

RUN IT whenever a component's props change:

    npm run build              # regenerates metadata.json + the Python classes
    python scripts/build_api_metadata.py
    git add dash_leaflet2/api_metadata.json

`tests/test_nav_contract.py` fails if the committed file has drifted from
metadata.json while metadata.json is present, so a forgotten run is caught
locally rather than shipping a stale API page.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from lib.api_reference import SLIM_METADATA, load_package  # noqa: E402

PACKAGE = "dash_leaflet2"


def build() -> Path:
    source = REPO / PACKAGE / "metadata.json"
    if not source.is_file():
        raise SystemExit(
            f"{source} is missing — it is the react-docgen artifact, so run\n"
            "    npm run build:backends\n"
            "first. (It is .gitignored on purpose; this script is what makes\n"
            "the API page work without it.)"
        )
    components = load_package(PACKAGE)
    if not components:
        raise SystemExit(f"{source} parsed to zero components — refusing to "
                         "write an empty API reference over a good one.")
    out = REPO / PACKAGE / SLIM_METADATA
    # `generated` is /api's sitemap <lastmod>. Written HERE, by the thing that
    # regenerates the content, so the date and the content move together and
    # neither can be scripted from an mtime that a Docker build resets.
    previous = {}
    if out.is_file():
        try:
            previous = json.loads(out.read_text(encoding="utf-8"))
        except ValueError:
            previous = {}
        if not isinstance(previous, dict):
            previous = {}  # a pre-`generated` extract: re-stamp it
    unchanged = previous.get("components") == components
    generated = (previous.get("generated") if unchanged
                 else date.today().isoformat())
    out.write_text(
        json.dumps({"generated": generated, "components": components},
                   indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if unchanged:
        print("props unchanged — kept generated:", generated)
    props = sum(len(c["props"]) for c in components)
    print(f"{out.relative_to(REPO)}: {len(components)} components, "
          f"{props} props, {out.stat().st_size / 1024:.0f} KB "
          f"(from {source.stat().st_size / 1024 / 1024:.1f} MB)")
    return out


if __name__ == "__main__":
    build()
