#!/usr/bin/env python
"""Pre-release consistency check for dash-leaflet2.

Run this before cutting a tag. It catches the release-shaped mistakes that no
functional test can see, because the app runs perfectly with all of them:

1. **Version drift across four files.** `pyproject.toml` decides what PyPI
   serves, but `dash_leaflet2.__version__` is read at import time from
   `dash_leaflet2/package-info.json`, which is *generated* by
   `npm run build:backends -p package-info.json` from the **root**
   `package-info.json`. Those are different files. The root one sat at 0.0.1
   while everything else said 0.1.0 — so the next component rebuild would have
   silently shipped a wheel labelled 0.1.0 whose `__version__` said 0.0.1.
2. **The built bundle missing or stale** relative to the TypeScript source.
3. **CHANGELOG not mentioning the version being released.**
4. **Packaging leaks** — the 27 MB react-docgen artifact, or vendored docs-only
   tarballs, ending up in the wheel.

    python scripts/check_release.py            # check
    python scripts/check_release.py --version 0.2.0   # also assert the target

Exit code 0 when clean, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

problems: list[str] = []
notes: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label:<44} {detail}")
    if not ok:
        problems.append(f"{label}: {detail}")


def versions() -> dict[str, str]:
    out: dict[str, str] = {}
    out["pyproject.toml"] = re.search(
        r'^version\s*=\s*"([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M
    ).group(1)
    out["package.json"] = json.loads((ROOT / "package.json").read_text())["version"]
    out["package-info.json (build input)"] = json.loads(
        (ROOT / "package-info.json").read_text()
    )["version"]
    built = ROOT / "dash_leaflet2" / "package-info.json"
    if built.exists():
        out["dash_leaflet2/package-info.json (shipped)"] = json.loads(
            built.read_text()
        )["version"]
    out["lib/constants.py APP_VERSION"] = re.search(
        r'^APP_VERSION\s*=\s*"([^"]+)"', (ROOT / "lib" / "constants.py").read_text(), re.M
    ).group(1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", help="assert every source reports this version")
    args = ap.parse_args()

    print("\ndash-leaflet2 release check\n" + "=" * 60)

    print("\n[versions]")
    vs = versions()
    for name, v in vs.items():
        print(f"        {name:<44} {v}")
    unique = set(vs.values())
    check("all version sources agree", len(unique) == 1,
          "consistent" if len(unique) == 1 else f"differ: {sorted(unique)}")
    target = args.version or vs["pyproject.toml"]
    if args.version:
        check(f"every source is {args.version}", unique == {args.version},
              "ok" if unique == {args.version} else f"found {sorted(unique)}")

    print("\n[build artifacts]")
    bundle = ROOT / "dash_leaflet2" / "dash_leaflet2.js"
    check("JS bundle committed", bundle.exists(),
          f"{bundle.stat().st_size // 1024} KB" if bundle.exists() else "MISSING — run npm run build")
    if bundle.exists():
        newest_src = max(
            (p.stat().st_mtime for p in (ROOT / "src" / "ts").rglob("*")
             if p.is_file()), default=0)
        check("bundle newer than src/ts", bundle.stat().st_mtime >= newest_src,
              "up to date" if bundle.stat().st_mtime >= newest_src
              else "STALE — run npm run build")
    generated = list((ROOT / "dash_leaflet2").glob("*.py"))
    check("generated component classes present", len(generated) > 20,
          f"{len(generated)} .py files")

    print("\n[changelog]")
    changelog = (ROOT / "CHANGELOG.md").read_text()
    check(f"CHANGELOG mentions {target}", target in changelog,
          "found" if target in changelog else f"add a [{target}] section")
    if "## [Unreleased]" in changelog:
        body = changelog.split("## [Unreleased]", 1)[1].split("## [", 1)[0]
        if body.strip() and "Nothing yet" not in body:
            notes.append(
                "CHANGELOG still has content under [Unreleased] — move it under "
                f"[{target}] before tagging."
            )

    print("\n[packaging]")
    pyproject = (ROOT / "pyproject.toml").read_text()
    check("metadata.json excluded from package-data",
          "metadata.json" not in pyproject.split("[tool.setuptools.package-data]")[-1],
          "not packaged (27 MB artifact)")
    check("only dash_leaflet2 is packaged",
          'packages = ["dash_leaflet2"]' in pyproject, "vendor/ and docs/ stay out")
    check("dash is the only runtime dependency",
          re.search(r'dependencies\s*=\s*\[\s*"dash>=[\d.]+"\s*\]', pyproject) is not None,
          "docs deps live in requirements.txt")
    check("LICENSE present", (ROOT / "LICENSE").exists())
    check("README present", (ROOT / "README.md").exists())

    print("\n[docs site]")
    for f in ("Dockerfile", "render.yaml", "DEPLOYMENT.md", "requirements.txt"):
        check(f"{f} present", (ROOT / f).exists())
    reqs = (ROOT / "requirements.txt").read_text()
    check("vendored deps use relative paths", "file:///" not in reqs,
          "no absolute file:// URLs")
    for tarball in re.findall(r"^\./(vendor/\S+)", reqs, re.M):
        check(f"{tarball} committed", (ROOT / tarball).exists())

    print("\n" + "=" * 60)
    for n in notes:
        print(f"NOTE: {n}")
    if problems:
        print(f"\n{len(problems)} problem(s) — not ready to tag:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nClean. Ready to tag "
          f"v{target} (see RELEASING.md for the rest of the runbook).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
