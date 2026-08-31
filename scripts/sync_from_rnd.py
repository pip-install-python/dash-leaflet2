#!/usr/bin/env python
"""Re-export the public mirror from the private R&D checkout.

`2plot_leaflet` (this repo) is the PUBLIC mirror of `dash-leaflet2`. The R&D
checkout keeps pages that must never ship — the AI tile-generation lab and the
sprite authoring shell — so this script pulls everything else forward and
refuses to copy anything on the denylist.

    python scripts/sync_from_rnd.py                 # dry run: show what changes
    python scripts/sync_from_rnd.py --apply         # actually copy
    python scripts/sync_from_rnd.py --source ../dash-leaflet2 --apply

Direction is deliberately **pull, not push**. The public repo decides what it
accepts; a new R&D page cannot leak by being forgotten in an exclude list on
the other side, because anything under `docs/` that this script has not been
told about shows up in the dry run as a NEW page for you to approve.

What it never copies
--------------------
* the pages in :data:`DENY_DOCS` and their assets
* local-only state: `.env`, `.venv`, `node_modules`, `build`, `dist`,
  `__pycache__`, `.git`, `.claude`, `.idea`, analytics ledgers
* files this mirror owns outright (:data:`MIRROR_OWNED`) — `README.md`,
  `run.py`, `requirements.txt`, the `lib/` network clients, `pages/`,
  `scripts/`, `vendor/`, `Dockerfile`, `render.yaml`. These have diverged on
  purpose and an R&D copy would clobber the public wiring.

Everything else — the compiled `dash_leaflet2/` package, `src/ts/`, the
remaining docs pages, assets, `usage.py`, `CHANGELOG.md` — is fair game.
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = PROJECT_ROOT.parent / "dash-leaflet2"

# Docs slugs that stay internal. Each is a directory under docs/.
DENY_DOCS = {
    "sprite-generator",   # AI sprite authoring shell — separate unreleased project
    "tile-selector",      # AI tile-generation lab; the mirror ships its OWN lean
                          # /tile-selector page documenting the dl2 component
}

# Asset files that belong to the denied pages only.
DENY_ASSETS = {
    "assets/sprite_generator.css",
    "assets/tile_selector.css",
    "assets/sprites/sailboat",
    "assets/sprites/soldier",
}

# Paths the mirror owns; never overwritten from R&D.
MIRROR_OWNED = {
    "README.md",
    "COMPATIBILITY.md",
    "run.py",
    "app.py",              # renamed to run.py here — never resurrect it
    "requirements.txt",
    "requirements-docs.txt",
    "pyproject.toml",      # public metadata (urls, classifiers) differs
    "Dockerfile",
    "render.yaml",
    ".gitignore",
    "CLAUDE.md",
    "lib/ad_client.py",
    "lib/satellite_analytics.py",   # retired for the trio below — never resurrect it
    "lib/analytics_tracker.py",
    "lib/satellite_reporter.py",
    "lib/traffic_rollup.py",
    "lib/health.py",
    "lib/asgi_middleware.py",
    "lib/page_tiers.py",
    "lib/versions.py",
    "lib/auth.py",
    "lib/page_visibility.py",
    # The gate pilot. These are adapted from dash-documentation-boilerplate,
    # not from R&D — lib/access.py in particular resolves the control board's
    # overrides ahead of the frontmatter tier, which the template has no
    # counterpart for. A pull that overwrote it would silently drop the board.
    "lib/access.py",
    "lib/hub_client.py",
    "lib/gate_layouts.py",
    "lib/auth_demos.py",
    "lib/agent_key.py",
    "lib/constants.py",
    "pages/markdown.py",
    "pages/control_board.py",
    "components/appshell.py",
    "components/navbar.py",
    # ---- the 2plot template's surfaces (sync item 18, 2026-08-31) ----------
    # These arrived from dash-documentation-boilerplate, not from R&D, and
    # the network's sync specs are what keep them current. An R&D copy would
    # be a fork of a fork.
    #
    # ONE OF THEM IS NOT HYPOTHETICAL. `lib/directives/source.py` has ALREADY
    # diverged: this copy carries the CodeHighlight a11y fix item 16 requires
    # (`copyLabel` / `copiedLabel` — the copy button's accessible name, named
    # by the audit), and R&D's copy has neither line. Before this entry a
    # pull reverted that fix. It would have gone RED rather than unnoticed —
    # tests/test_nav_contract.test_code_highlight_copy_button_has_a_name
    # reads exactly this file — but a red test after the fact is a worse
    # place to learn it than a pull that never touches the file.
    #
    # The other six have no R&D counterpart today, so they are unprotected
    # rather than threatened: `walk_source` iterates the SOURCE tree and
    # never unlinks, so nothing deletes them. Listed anyway, because the day
    # R&D grows a file at one of these paths it would win silently.
    "lib/directives/source.py",
    "lib/directives/headings.py",
    "lib/api_reference.py",
    "lib/aside.py",
    "components/footer.py",
    "pages/api.py",
    "pages/changelog.py",
}

# Never traversed at all.
SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".claude", ".idea",
    "build", "dist", ".compat", "vendor", "scripts", "tests",
}
SKIP_SUFFIXES = {".pyc", ".pyo", ".log"}
SKIP_NAMES = {
    ".env", ".DS_Store", "page_visibility.json", "satellite_traffic.jsonl",
    "visitor_analytics.json", "package-lock.json",
}


def is_denied(rel: Path) -> str | None:
    """Return a reason string when this path must not be mirrored."""
    parts = rel.parts
    if parts and parts[0] == "docs" and len(parts) > 1 and parts[1] in DENY_DOCS:
        return f"R&D page: docs/{parts[1]}"
    rel_str = rel.as_posix()
    for denied in DENY_ASSETS:
        if rel_str == denied or rel_str.startswith(denied + "/"):
            return f"R&D asset: {denied}"
    if rel_str in MIRROR_OWNED:
        return "mirror-owned"
    # .egg-info is a DIRECTORY, so test every path part, not just the filename.
    if any(part.endswith(".egg-info") for part in parts):
        return "build artifact"
    return None


def walk_source(source: Path):
    """Yield every candidate relative path in the R&D checkout."""
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.suffix in SKIP_SUFFIXES or path.name in SKIP_NAMES:
            continue
        yield rel


def classify(source: Path, rel: Path) -> str:
    """'new' | 'changed' | 'same' relative to this mirror."""
    dst = PROJECT_ROOT / rel
    if not dst.exists():
        return "new"
    try:
        return "same" if filecmp.cmp(source / rel, dst, shallow=False) else "changed"
    except OSError:
        return "changed"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(DEFAULT_SOURCE),
                    help=f"R&D checkout to pull from (default: {DEFAULT_SOURCE})")
    ap.add_argument("--apply", action="store_true",
                    help="actually copy; without this it is a dry run")
    ap.add_argument("--show-same", action="store_true", help="also list unchanged files")
    args = ap.parse_args()

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"error: source {source} is not a directory", file=sys.stderr)
        return 2
    if source == PROJECT_ROOT:
        print("error: source and destination are the same directory", file=sys.stderr)
        return 2

    new: list[Path] = []
    changed: list[Path] = []
    same: list[Path] = []
    denied: list[tuple[Path, str]] = []

    for rel in walk_source(source):
        reason = is_denied(rel)
        if reason:
            denied.append((rel, reason))
            continue
        state = classify(source, rel)
        {"new": new, "changed": changed, "same": same}[state].append(rel)

    print(f"source: {source}")
    print(f"mirror: {PROJECT_ROOT}")
    print()

    if denied:
        print(f"BLOCKED ({len(denied)}) — not mirrored:")
        by_reason: dict[str, int] = {}
        for _, reason in denied:
            by_reason[reason] = by_reason.get(reason, 0) + 1
        for reason, count in sorted(by_reason.items()):
            print(f"  {count:>4}  {reason}")
        print()

    # A brand-new docs page in R&D is the case worth eyeballing: it is either a
    # page you meant to publish, or a new R&D page that belongs on the denylist.
    new_doc_slugs = sorted({
        p.parts[1] for p in new if p.parts and p.parts[0] == "docs" and len(p.parts) > 1
    })
    if new_doc_slugs:
        print("NEW DOCS PAGES — confirm each should be public, or add it to DENY_DOCS:")
        for slug in new_doc_slugs:
            print(f"  + docs/{slug}")
        print()

    for label, items in (("NEW", new), ("CHANGED", changed)):
        if items:
            print(f"{label} ({len(items)}):")
            for rel in items:
                print(f"  {rel}")
            print()
    if args.show_same and same:
        print(f"UNCHANGED ({len(same)}) — omitted; pass --show-same to list")

    print(f"summary: {len(new)} new · {len(changed)} changed · {len(same)} unchanged "
          f"· {len(denied)} blocked")

    if not args.apply:
        print("\nDry run. Re-run with --apply to copy the new + changed files.")
        return 0

    copied = 0
    for rel in new + changed:
        dst = PROJECT_ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, dst)
        copied += 1
    print(f"\nCopied {copied} files.")
    print("Now run:  python scripts/smoke_test.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
