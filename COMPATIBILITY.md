# Dash compatibility matrix

`pyproject.toml` declares `dash>=4.1`. This file is where that claim gets its
evidence.

## Method

`scripts/compat_matrix.py` builds one throwaway virtualenv per Dash version,
installs `dash[fastapi]==<version>` **first** (so the rest of the requirements
resolve against the version under test), then installs `requirements.txt` with
the pinned Dash line stripped, and runs `scripts/smoke_test.py` inside that venv.

Each run reports whether the resolver quietly upgraded Dash to satisfy something
else — a silent upgrade would make the result meaningless.

The smoke suite drives the app through the backend's **test client**: real
request handling, no socket bind and no browser. Per version it checks

- every `docs/<slug>/<slug>.md` registered a route, with **no duplicate paths**
  (a duplicate is what previously made the DMC search `Select` throw
  "Duplicate options are not supported")
- every page layout **builds and survives Dash's own JSON encoder** — this is
  where a broken example, a renamed prop or a dropped component actually shows up
- every route answers, plus `/_dash-layout`, `/_dash-dependencies`, `/healthz`,
  `/llms.txt`, `/robots.txt` and `/sitemap.xml`
- callbacks registered

`--browser` adds a second leg that boots each venv's `run.py` for real and sweeps
every page with Playwright for console and page errors. That is the only leg that
can catch a *runtime* Leaflet regression (tiles not painting, a v2 API that moved)
as opposed to a *construction* regression.

## Running it

```bash
python scripts/compat_matrix.py                       # 4.1.0, 4.2.0, 4.3.0, 4.4.1
python scripts/compat_matrix.py 4.4.1 --backends flask fastapi
python scripts/compat_matrix.py --browser --keep      # + console errors, keep venvs
```

Needs network access and a few GB of scratch space — each venv is a full install
of the documentation site (~200 MB). Venvs are deleted afterwards unless you pass
`--keep`. Raw per-run JSON lands in `.compat/<version>-<backend>.json`.

## Results

| Dash | Backend | Checks | Result | Notes |
|------|---------|--------|--------|-------|
| `4.1.0` | flask | — | ⏳ not yet run | support floor |
| `4.2.0` | flask | — | ⏳ not yet run | |
| `4.2.0rc3` | flask | 68/68 | ✅ pass | run against the development venv, not the matrix |
| `4.3.0` | flask | — | ⏳ not yet run | |
| `4.4.1` | flask | — | ⏳ not yet run | current release |

> The `4.2.0rc3` row is a real run of `scripts/smoke_test.py` (27 pages, 148
> callbacks, every route 200) against the development environment. Every other
> row is **pending** — run `python scripts/compat_matrix.py` and this table is
> regenerated from the actual results.

## Known risk areas

Things worth looking at first if a version fails:

- **`Dash(backend=...)`** is Dash 4.1+. On older Dash the kwarg does not exist;
  `lib/backend.py` resolves the name but `run.py` passes it unconditionally, so
  4.0 and below cannot boot. That is the reason for the `>=4.1` floor.
- **React version pin.** `run.py` calls `_dash_renderer._set_react_version("18.2.0")`
  because DMC 2.x targets React 18.2 while Dash 4 ships 18.3.1. If a Dash release
  drops or renames that private hook, the docs site breaks even though the
  `dash_leaflet2` package itself is fine.
- **`prevent_initial_callbacks=True`** is set app-wide. The ad slot's mount
  callback explicitly opts back in with `prevent_initial_call=False`; a change to
  how Dash resolves that interaction would silently stop serving ads.
- **`dash.hooks`** (`hooks.stylesheet`, `hooks.script`, `hooks.index`) delivers
  Leaflet 2 from the CDN for the showcase pages and carries the Clerk satellite
  index fix. The hooks API is young and is a plausible source of churn.
- **Generated component classes.** `dash_leaflet2/*.py` are emitted by
  `dash-generate-components` against the Dash version present at build time. If a
  future Dash changes the generated-class contract, the committed classes may need
  regenerating with `npm run build:backends`.

None of these affect a consumer who only does `pip install dash-leaflet2` and
imports `dl2.*` — the package depends on `dash>=4.1` and nothing else.
