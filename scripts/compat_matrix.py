#!/usr/bin/env python
"""Dash compatibility matrix for dash-leaflet2.

`pyproject.toml` claims `dash>=4.1`. This script is what turns that claim into
evidence: it builds one throwaway virtualenv per Dash version, installs the
docs site into each, and runs `scripts/smoke_test.py` there — page
registration, layout render + JSON serialisation of every example, and an HTTP
sweep of every route through the backend's test client.

    python scripts/compat_matrix.py                       # default versions
    python scripts/compat_matrix.py 4.1.0 4.4.1           # specific versions
    python scripts/compat_matrix.py --backends flask fastapi
    python scripts/compat_matrix.py --keep                # keep the venvs
    python scripts/compat_matrix.py --report COMPATIBILITY.md

Each run writes `.compat/<version>-<backend>.json` (the raw smoke-test output)
and a markdown table you can paste into COMPATIBILITY.md.

Requirements
------------
Network access, and a `python3` that can create venvs. Each venv is a real
install of the docs site (~200 MB), so the default four-version run needs a
few GB of scratch space and several minutes. They are deleted afterwards
unless you pass `--keep`.

Why not Playwright here
-----------------------
The smoke test drives the app through the backend's in-process test client,
which needs no socket and no browser and still exercises routing, layout
construction and serialisation — the layer where a Dash version bump actually
breaks things. Browser-side checks (Leaflet actually painting tiles, console
errors) need a real server; run `--browser` for that leg, which starts each
venv's `run.py` on a port and drives it with Playwright if it is installed.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = PROJECT_ROOT / ".compat"

# The support claim is `dash>=4.1`. These are the rungs we actually test:
# the floor, the two intermediate minors, and the current release.
DEFAULT_VERSIONS = ["4.1.0", "4.2.0", "4.3.0", "4.4.1"]
DEFAULT_BACKENDS = ["flask"]

# The line in requirements.txt carrying the Dash pin. It is stripped so each
# venv gets exactly the version under test rather than the pinned one.
DASH_PIN_MARKER = "# COMPAT-MATRIX: dash"


def log(msg: str) -> None:
    print(f"[compat] {msg}", flush=True)


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def requirements_without_dash() -> str:
    """requirements.txt with the pinned Dash line removed."""
    lines = (PROJECT_ROOT / "requirements.txt").read_text().splitlines()
    kept = [ln for ln in lines if DASH_PIN_MARKER not in ln]
    if len(kept) == len(lines):
        log(f"WARNING: no line tagged '{DASH_PIN_MARKER}' in requirements.txt — "
            "the pinned Dash may fight the version under test.")
    return "\n".join(kept) + "\n"


def make_venv(version: str) -> tuple[Path, Path] | None:
    """Create a venv with `dash[fastapi]==<version>` + the docs requirements."""
    venv = WORK_DIR / f"venv-{version}"
    py = venv / "bin" / "python"
    if py.exists():
        log(f"{version}: reusing existing venv")
        return venv, py

    log(f"{version}: creating venv")
    r = run([sys.executable, "-m", "venv", str(venv)])
    if r.returncode:
        log(f"{version}: venv creation FAILED\n{r.stderr[:800]}")
        return None

    run([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"])

    # Dash first so the requirements resolve against the version under test.
    log(f"{version}: installing dash[fastapi]=={version}")
    r = run([str(py), "-m", "pip", "install", "-q", f"dash[fastapi]=={version}"])
    if r.returncode:
        log(f"{version}: dash install FAILED\n{r.stderr[-1500:]}")
        return None

    req = WORK_DIR / f"requirements-{version}.txt"
    req.write_text(requirements_without_dash())
    log(f"{version}: installing docs requirements")
    r = run([str(py), "-m", "pip", "install", "-q", "-r", str(req)], cwd=PROJECT_ROOT)
    if r.returncode:
        log(f"{version}: requirements install FAILED\n{r.stderr[-1500:]}")
        return None

    # Confirm the resolver did not quietly upgrade Dash to satisfy something.
    r = run([str(py), "-c", "import dash; print(dash.__version__)"])
    actual = r.stdout.strip()
    if actual != version:
        log(f"{version}: NOTE resolved Dash is {actual!r}, not {version!r}")
    return venv, py


def smoke(py: Path, version: str, backend: str) -> dict:
    """Run scripts/smoke_test.py in this venv and return its JSON result."""
    out = WORK_DIR / f"{version}-{backend}.json"
    env = dict(os.environ, DASH_BACKEND=backend, SATELLITE_ANALYTICS_DRY_RUN="1")
    env.pop("CROSS_APP_WEBHOOK_SECRET", None)

    t0 = time.time()
    r = subprocess.run(
        [str(py), "scripts/smoke_test.py", "--quiet", "--json", str(out)],
        cwd=PROJECT_ROOT, env=env, capture_output=True, text=True,
    )
    elapsed = time.time() - t0

    if out.exists():
        data = json.loads(out.read_text())
    else:
        data = {
            "dash_version": version,
            "summary": {"total": 0, "passed": 0, "failed": 1},
            "checks": [{
                "group": "harness", "name": "smoke_test.py ran", "ok": False,
                "detail": (r.stderr or r.stdout)[-2000:],
            }],
        }
    data["backend"] = backend
    data["requested_version"] = version
    data["elapsed_s"] = round(elapsed, 1)
    data["exit_code"] = r.returncode
    return data


def browser_leg(py: Path, version: str, backend: str, port: int) -> dict:
    """Optional: boot run.py for real and collect browser console errors."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        return {"skipped": "playwright not installed in the driving interpreter"}

    env = dict(os.environ, DASH_BACKEND=backend, PORT=str(port),
               HOST="127.0.0.1", DASH_DEBUG="false",
               SATELLITE_ANALYTICS_DRY_RUN="1")
    proc = subprocess.Popen([str(py), "run.py"], cwd=PROJECT_ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import urllib.request

        base = f"http://127.0.0.1:{port}"
        for _ in range(60):  # wait for the server to answer
            try:
                urllib.request.urlopen(base, timeout=1)
                break
            except Exception:
                time.sleep(1)
        else:
            return {"error": "server never came up"}

        from playwright.sync_api import sync_playwright

        pages_json = json.loads(
            subprocess.run(
                [str(py), "-c",
                 "import sys;sys.path.insert(0,'.');import run,dash,json;"
                 "print(json.dumps([p['path'] for p in dash.page_registry.values()]))"],
                cwd=PROJECT_ROOT, env=env, capture_output=True, text=True,
            ).stdout.strip().splitlines()[-1]
        )

        results = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for path in pages_json:
                page = browser.new_page()
                errors: list[str] = []
                page.on("console", lambda m: m.type == "error" and errors.append(m.text))
                page.on("pageerror", lambda e: errors.append(str(e)))
                try:
                    page.goto(base + path, wait_until="networkidle", timeout=30000)
                    page.wait_for_timeout(1500)  # let Leaflet paint
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"navigation: {exc}")
                results.append({"path": path, "console_errors": errors})
                page.close()
            browser.close()
        return {"pages": results}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def markdown_report(rows: list[dict]) -> str:
    lines = [
        "# Dash compatibility matrix",
        "",
        "Generated by `python scripts/compat_matrix.py`. Each cell is a full",
        "install of the documentation site against that Dash version, driven",
        "through `scripts/smoke_test.py`: every page registered, every layout",
        "rendered and JSON-serialised, every route fetched.",
        "",
        "| Dash | Backend | Checks | Result | Time | Notes |",
        "|------|---------|--------|--------|------|-------|",
    ]
    for r in rows:
        s = r.get("summary", {})
        total, passed, failed = s.get("total", 0), s.get("passed", 0), s.get("failed", 0)
        verdict = "✅ pass" if total and not failed else "❌ fail"
        notes = ""
        actual = r.get("dash_version")
        if actual and actual != r.get("requested_version"):
            notes = f"resolved to {actual}"
        if failed:
            first = next((c for c in r.get("checks", []) if not c["ok"]), None)
            if first:
                detail = first["detail"].splitlines()[-1][:90] if first["detail"] else ""
                notes = (notes + "; " if notes else "") + f"{first['name']}: {detail}"
        lines.append(
            f"| `{r['requested_version']}` | {r['backend']} | {passed}/{total} | "
            f"{verdict} | {r.get('elapsed_s', '?')}s | {notes} |"
        )

    failures = [r for r in rows if r.get("summary", {}).get("failed")]
    if failures:
        lines += ["", "## Failures", ""]
        for r in failures:
            lines.append(f"### Dash {r['requested_version']} · {r['backend']}", )
            lines.append("")
            for c in r.get("checks", []):
                if not c["ok"]:
                    lines.append(f"- **{c['group']} / {c['name']}** — {c['detail'][:600]}")
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("versions", nargs="*", default=None,
                    help=f"Dash versions to test (default: {' '.join(DEFAULT_VERSIONS)})")
    ap.add_argument("--backends", nargs="+", default=DEFAULT_BACKENDS,
                    choices=["flask", "fastapi", "quart"])
    ap.add_argument("--keep", action="store_true", help="keep the venvs afterwards")
    ap.add_argument("--browser", action="store_true",
                    help="also boot each venv and collect browser console errors")
    ap.add_argument("--report", default="COMPATIBILITY.md",
                    help="markdown report path (default: COMPATIBILITY.md)")
    args = ap.parse_args()

    versions = args.versions or DEFAULT_VERSIONS
    WORK_DIR.mkdir(exist_ok=True)

    rows: list[dict] = []
    port = 8600
    for version in versions:
        made = make_venv(version)
        if made is None:
            rows.append({
                "requested_version": version, "backend": args.backends[0],
                "summary": {"total": 0, "passed": 0, "failed": 1},
                "checks": [{"group": "install", "name": "venv + install", "ok": False,
                            "detail": "see log above"}],
            })
            continue
        _, py = made
        for backend in args.backends:
            log(f"{version}/{backend}: running smoke test")
            row = smoke(py, version, backend)
            s = row["summary"]
            log(f"{version}/{backend}: {s['passed']}/{s['total']} passed "
                f"({s['failed']} failed) in {row['elapsed_s']}s")
            if args.browser:
                log(f"{version}/{backend}: browser leg on :{port}")
                row["browser"] = browser_leg(py, version, backend, port)
                port += 1
            rows.append(row)

    report = markdown_report(rows)
    Path(args.report).write_text(report)
    print()
    print(report)
    log(f"wrote {args.report}")

    if not args.keep:
        for version in versions:
            shutil.rmtree(WORK_DIR / f"venv-{version}", ignore_errors=True)
        log("removed venvs (pass --keep to retain them)")

    return 0 if all(not r.get("summary", {}).get("failed") for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
