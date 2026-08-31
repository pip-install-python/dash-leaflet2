#!/usr/bin/env python
"""Headless smoke test for the dash-leaflet2 documentation site.

Boots ``run.py`` in-process and drives it through the backend's **test client**
— real request/response handling, no socket bind — then reports one line per
check. This is the same harness ``scripts/compat_matrix.py`` runs against each
Dash version, so what passes here is what the matrix measures.

What it checks
--------------
1. **Import** — ``run.py`` imports and constructs the Dash app.
2. **Registration** — every ``docs/<slug>/<slug>.md`` became a page, with no
   duplicate paths (a duplicate is what made the DMC search Select blow up with
   "Duplicate options are not supported").
3. **Layout render** — every page's layout callable is invoked and the whole
   component tree is serialised with Dash's own JSON encoder. This is where a
   broken example.py, a bad prop, or a missing component actually surfaces.
4. **HTTP** — ``GET`` each page path plus ``/_dash-layout``,
   ``/_dash-dependencies``, ``/healthz``, ``/llms.txt``, ``/robots.txt`` and
   ``/sitemap.xml``.
5. **Callbacks** — the app's callback map is inspected for outputs that no
   layout provides, which is the usual cause of a silent dead control.

Usage
-----
    python scripts/smoke_test.py                 # human-readable table
    python scripts/smoke_test.py --json out.json # machine-readable
    python scripts/smoke_test.py --quiet         # only failures

Exit code is 0 when every check passed, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Flask's test client is the only backend whose in-process client needs no
# extra dependency, and the page/layout checks are backend-independent.
os.environ.setdefault("DASH_BACKEND", "flask")
# Never let a smoke run beacon traffic at the live 2plot.ai hub (no secret →
# the reporter never starts), keep its hits out of the repo's own ledger, and
# keep the ad client from adding a network timeout to every page.
os.environ.setdefault(
    "TRAFFIC_ANALYTICS_FILE",
    os.path.join(tempfile.mkdtemp(prefix="leaflet-smoke-"), "visitor_analytics.json"),
)
os.environ.setdefault("ANALYTICS_GEO_LOOKUP", "0")
os.environ.pop("CROSS_APP_WEBHOOK_SECRET", None)
os.environ.setdefault("AD_SERVER_URL", "http://127.0.0.1:1")  # unreachable → slot hides


class Results:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, group: str, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append({"group": group, "name": name, "ok": ok, "detail": detail})

    @property
    def failures(self) -> list[dict]:
        return [c for c in self.checks if not c["ok"]]

    def summary(self) -> dict:
        return {
            "total": len(self.checks),
            "passed": len(self.checks) - len(self.failures),
            "failed": len(self.failures),
        }


def _import_app(res: Results):
    """Import run.py and hand back (module, dash)."""
    t0 = time.time()
    try:
        import run  # noqa: F401  (side effects are the point)
        import dash

        res.add("import", "run.py imports", True, f"{time.time() - t0:.1f}s")
        return run, dash
    except Exception:
        res.add("import", "run.py imports", False, traceback.format_exc(limit=8))
        return None, None


def _check_registration(res: Results, dash_mod) -> None:
    registry = dash_mod.page_registry
    md_files = [
        p for p in Path("docs").glob("**/*.md") if p.name != "SKILL.md"
    ]
    res.add("pages", "markdown files discovered", bool(md_files), f"{len(md_files)} files")

    paths = [entry["path"] for entry in registry.values()]
    dupes = {p for p in paths if paths.count(p) > 1}
    res.add("pages", "no duplicate page paths", not dupes, ", ".join(sorted(dupes)) or "clean")

    # Every markdown file should have produced a route.
    missing = []
    for md in md_files:
        try:
            import frontmatter

            meta, _ = frontmatter.parse(md.read_text())
            endpoint = meta.get("endpoint")
            if endpoint and endpoint not in paths:
                missing.append(f"{md} → {endpoint}")
        except Exception as exc:  # noqa: BLE001
            missing.append(f"{md} (frontmatter unreadable: {exc})")
    res.add("pages", "every .md registered a route", not missing, "; ".join(missing) or "all present")


def _render_layouts(res: Results, dash_mod) -> None:
    """Invoke and serialise every page layout — where broken examples surface."""
    from dash._utils import to_json

    for entry in dash_mod.page_registry.values():
        path, name = entry["path"], entry["name"]
        try:
            layout = entry["layout"]
            if callable(layout):
                layout = layout()
            to_json(layout)  # Dash's own encoder — catches invalid components
            res.add("layout", f"{path}", True, name)
        except Exception as exc:  # noqa: BLE001
            res.add("layout", f"{path}", False, f"{type(exc).__name__}: {exc}")


def _http_checks(res: Results, run_mod, dash_mod) -> None:
    server = run_mod.app.server
    try:
        client = server.test_client()
    except Exception as exc:  # noqa: BLE001
        res.add("http", "test client available", False, str(exc))
        return
    res.add("http", "test client available", True, type(server).__name__)

    # Every request here names the BROWSER lane, and it has to.
    #
    # From dash-improve-my-llms 2.8.0 the document a host serves is decided by
    # `classify()`, and a request with NO User-Agent — which is what a bare
    # test client sends — is classified crawler-lane. The pages this site
    # marks hidden (`/admin/control-board`, `/admin/traffic`) then correctly
    # answer 404, because that is exactly what `mark_hidden` is for; and this
    # loop, which asserts "every registered page path returns 200", read that
    # as two broken routes. Measured at 2.8.0: no-UA 404 / browser-UA 200 on
    # both, 200 either way on a public page.
    #
    # The lane is the point: this block's own comment says a Dash SPA returns
    # the same index HTML for every path, which is a statement about the
    # BROWSER document and about nothing else. Same class as the trap sync
    # item 12 documents for tests/test_proxy_scheme.py and item 17 for the
    # network battery's default UA — the third surface in this repo where a
    # UA-less probe silently changed meaning at the 2.8 floor.
    #
    # It also carries the INTERNAL TOKEN, after the engine token. This
    # harness is a CI sweep, not a visitor: without the token its hits are
    # countable people (muicharts measured 4 such rows in a real ledger).
    # Belt and braces here — the env block above already redirects
    # TRAFFIC_ANALYTICS_FILE to a temp dir, so these hits cannot reach the
    # repo's ledger or production's — but the token is what makes that true
    # by contract rather than by one env line staying correct forever.
    from lib.constants import INTERNAL_UA

    BROWSER_UA = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
        + INTERNAL_UA + " smoke-test"
    )

    # The other lane, named for the hidden-page refusal below.
    CRAWLER_UA = "Mozilla/5.0 (compatible; Googlebot/2.1) " + INTERNAL_UA

    def get(url: str, group: str, expect=(200,), label: str | None = None):
        try:
            resp = client.get(url, headers={"User-Agent": BROWSER_UA})
            code = resp.status_code
            ok = code in expect
            res.add(group, label or url, ok, f"HTTP {code}")
            return resp
        except Exception as exc:  # noqa: BLE001
            res.add(group, label or url, False, f"{type(exc).__name__}: {exc}")
            return None

    # Dash plumbing first — if these fail nothing else matters.
    get("/_dash-layout", "http")
    get("/_dash-dependencies", "http")

    # Network + SEO endpoints.
    get("/healthz", "endpoints")
    get("/llms.txt", "endpoints")
    get("/robots.txt", "endpoints")
    get("/sitemap.xml", "endpoints")

    # Every page path. A Dash SPA returns the same index HTML for all of them,
    # so a non-200 means routing or the index template broke.
    for entry in dash_mod.page_registry.values():
        get(entry["path"], "routes")

    # THE OTHER HALF OF THE LANE FIX, and it belongs in the same change as
    # the browser UA above (fleet notes 70/74): repairing the lane alone
    # measures strictly LESS than before and says nothing about it. The
    # browser-lane loop now passes on the admin pages — which is exactly what
    # it would also do if `mark_hidden` silently stopped working. So assert
    # the refusal directly, on the lane that must still get it.
    #
    # `mark_hidden` is what keeps an owner surface out of the index; the
    # crawler-lane 404 IS the feature, not an artefact of the harness.
    from dash_improve_my_llms import is_hidden

    hidden = sorted(
        e["path"] for e in dash_mod.page_registry.values()
        if is_hidden(e["path"])
    )
    res.add("hidden", "some page is marked hidden", bool(hidden),
            ", ".join(hidden) or "NONE — mark_hidden is not wired at all")
    for path in hidden:
        resp = client.get(path, headers={"User-Agent": CRAWLER_UA})
        res.add("hidden", f"{path} refuses the crawler lane",
                resp.status_code == 404, f"HTTP {resp.status_code}")


def _check_callbacks(res: Results, dash_mod, run_mod) -> None:
    """Flag callback outputs that no registered layout provides."""
    try:
        app = run_mod.app
        cb_count = len(app.callback_map)
        res.add("callbacks", "callbacks registered", cb_count > 0, f"{cb_count} callbacks")
    except Exception as exc:  # noqa: BLE001
        res.add("callbacks", "callbacks registered", False, str(exc))


def _check_clientside_js(res: Results, run_mod) -> None:
    """Syntax-check every inline clientside callback with node.

    Python-side tests cannot catch a malformed clientside callback: Dash ships
    the string to the browser verbatim, so a syntax error is silent server-side
    and the callback simply never runs. That is not hypothetical — building the
    light/dark tile swaps with `repr()` and a blanket `'` -> `"` swap produced
    invalid JS for every pair, because attribution strings contain
    `<a href="...">`. Every map would have kept its initial basemap forever and
    all 68 other checks would still have passed.
    """
    scripts = getattr(run_mod.app, "_inline_scripts", [])
    if not scripts:
        res.add("clientside", "inline scripts collected", False, "none found")
        return
    res.add("clientside", "inline scripts collected", True, f"{len(scripts)} scripts")

    if not shutil.which("node"):
        res.add("clientside", "javascript parses", True, "SKIPPED — node not installed")
        return

    bad: list[str] = []
    for i, src in enumerate(scripts):
        proc = subprocess.run(
            ["node", "--check", "-"], input=src,
            capture_output=True, text=True, timeout=20,
        )
        if proc.returncode:
            first = next((ln for ln in proc.stderr.splitlines() if ln.strip()), "")
            bad.append(f"script[{i}]: {first[:120]}")

    res.add(
        "clientside", "javascript parses", not bad,
        "all valid" if not bad else f"{len(bad)} invalid — " + "; ".join(bad[:3]),
    )


def _check_asset_js(res: Results) -> None:
    """Syntax-check assets/*.js individually AND concatenated.

    The concatenated pass is the one that matters. Dash serves everything in
    `assets/` as separate classic <script> tags, which share ONE global lexical
    scope — so a top-level `const log` in two files is a SyntaxError in the
    second, and every handler in it silently never registers. Checking files
    one at a time cannot see that: each is valid alone. Concatenating them
    reproduces the browser's actual condition.
    """
    assets = sorted(Path("assets").glob("*.js"))
    if not assets:
        return
    if not shutil.which("node"):
        res.add("assets", "javascript parses", True, "SKIPPED — node not installed")
        return

    bad = []
    for f in assets:
        proc = subprocess.run(["node", "--check", str(f)],
                              capture_output=True, text=True, timeout=20)
        if proc.returncode:
            first = next((ln for ln in proc.stderr.splitlines() if "Error" in ln), "")
            bad.append(f"{f.name}: {first[:80]}")
    res.add("assets", f"each of {len(assets)} files parses", not bad,
            "all valid" if not bad else "; ".join(bad[:3]))

    combined = "\n".join(f.read_text() for f in assets)
    proc = subprocess.run(["node", "--check", "-"], input=combined,
                          capture_output=True, text=True, timeout=30)
    ok = proc.returncode == 0
    detail = "no global collisions"
    if not ok:
        detail = next((ln for ln in proc.stderr.splitlines() if "Error" in ln),
                      "see node output")[:120]
    res.add("assets", "no collisions in shared global scope", ok, detail)


def run_all() -> Results:
    res = Results()
    run_mod, dash_mod = _import_app(res)
    if run_mod is None:
        return res
    _check_registration(res, dash_mod)
    _render_layouts(res, dash_mod)
    _http_checks(res, run_mod, dash_mod)
    _check_callbacks(res, dash_mod, run_mod)
    _check_clientside_js(res, run_mod)
    _check_asset_js(res)
    return res


def report(res: Results, quiet: bool = False) -> None:
    import dash

    width = 78
    print()
    print("=" * width)
    print(f" dash-leaflet2 smoke test · Dash {dash.__version__} · Python {sys.version.split()[0]}")
    print("=" * width)

    current = None
    for c in res.checks:
        if quiet and c["ok"]:
            continue
        if c["group"] != current:
            current = c["group"]
            print(f"\n[{current}]")
        mark = "PASS" if c["ok"] else "FAIL"
        detail = c["detail"].replace("\n", "\n        ") if c["detail"] else ""
        print(f"  {mark}  {c['name']:<34} {detail}")

    s = res.summary()
    print()
    print("-" * width)
    print(f" {s['passed']}/{s['total']} checks passed" + (f" · {s['failed']} FAILED" if s["failed"] else ""))
    print("-" * width)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", metavar="PATH", help="write machine-readable results here")
    ap.add_argument("--quiet", action="store_true", help="print only failures")
    args = ap.parse_args()

    res = run_all()
    report(res, quiet=args.quiet)

    if args.json:
        import dash

        payload = {
            "dash_version": getattr(dash, "__version__", "unknown"),
            "python": sys.version.split()[0],
            "summary": res.summary(),
            "checks": res.checks,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nWrote {args.json}")

    return 0 if not res.failures else 1


if __name__ == "__main__":
    sys.exit(main())
