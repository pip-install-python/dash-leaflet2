# Releasing — development to production

Three deliverables ship from this repo, and they are independent. You can do
them in any order, but this is the order that fails cheapest:

| # | Deliverable | Where | Rollback |
|---|---|---|---|
| 1 | Source | `github.com/pip-install-python/dash-leaflet2` | force-push the old ref |
| 2 | Package | `pypi.org/project/dash-leaflet2` | **none — a version is permanent** |
| 3 | Docs | `https://leaflet.2plot.dev` (Render) | redeploy the previous commit |

The one irreversible step is PyPI. A filename can never be reused, even after
deletion, so a bad `0.2.0` costs you `0.2.1` forever. Everything below is
arranged so the irreversible step happens last, after the reversible ones have
already proven the artifact.

---

## Phase 0 — before anything leaves the machine

These are the checks nobody can do for you later.

```bash
# 1. Everything still boots and every page renders
python scripts/smoke_test.py                 # expect 70/70

# 2. Version consistency, packaging leaks, stale bundle
python scripts/check_release.py --version 0.2.0

# 3. The support claim, actually measured (needs network, ~15 min)
python scripts/compat_matrix.py              # writes COMPATIBILITY.md
```

**Status: done for 0.2.0.** The matrix has been run — 4.1.0 / 4.2.0 / 4.3.0 /
4.4.1 all pass 70/70, and the package was verified separately with nothing but
Dash installed. See `COMPATIBILITY.md`. `dash>=4.1` is measured, not assumed.

That run is also what found `backend=` to be Dash 4.2+ rather than 4.1, which
`run.py` now handles. Re-run the matrix for any release that touches `run.py`,
the requirements, or the component build.

The clean-clone install has also been exercised (`pip install -r
requirements.txt` into this project's venv), which is what proves the two
`./vendor/*.tar.gz` lines work — they replaced absolute `file:///Users/...`
paths that would have broken for everyone else.

---

## Phase 1 — GitHub

### 1.1 Free the name without destroying the backup

`github.com/pip-install-python/dash-leaflet2` is a **private** repo holding the
R&D project. Rename it rather than deleting it: the public mirror gets the name,
and the private repo survives as the R&D backup — which matters, because the
R&D checkout currently has ~106 uncommitted entries (including the two internal
pages) that exist on one disk and nowhere else.

**The order below is not arbitrary.** GitHub redirects the old URL to the new
one after a rename. The local R&D checkout still has the *old* URL in its
config, so the moment a new repo is created at that old name, the R&D checkout
would be pointing straight at the **public** repo. Re-point it BEFORE creating
the new repo.

1. **Rename on GitHub** — Settings → General → Repository name →
   `dash-leaflet2-rnd`. Leave it private.

2. **Re-point the local R&D checkout immediately**, before step 3:

   ```bash
   cd ../dash-leaflet2
   git remote set-url origin https://github.com/pip-install-python/dash-leaflet2-rnd.git
   git remote -v          # must show ...-rnd.git
   ```

   With origin now on the private repo, the internal pages should be
   **committed** there — that is the backup, and the first time that work has
   existed anywhere but this disk:

   ```bash
   git add -A && git commit -m "R&D snapshot" && git push
   ```

   Do NOT gitignore `docs/sprite-generator/` or `docs/tile-selector/` in this
   checkout any more. They belong in the private repo. What keeps them out of
   the public mirror is `scripts/sync_from_rnd.py`'s `DENY_DOCS`, plus the fact
   that the mirror is a separate checkout with its own remote.

3. **Create the new public repo** — `pip-install-python/dash-leaflet2`, public,
   and **completely empty**: no README, no .gitignore, no licence. Any
   initialising commit creates unrelated history and forces a `--force` push
   that this plan is specifically designed to avoid.

### 1.2 Push the mirror

Against an empty repo this is an ordinary push — no `--force`, nothing
overwritten:

```bash
cd ../2plot_leaflet
git remote add origin https://github.com/pip-install-python/dash-leaflet2.git
git push -u origin main
```

If this errors with "Updates were rejected", the new repo was not created empty.
Delete the initialising commit on GitHub rather than reaching for `--force`.

### 1.3 Repo settings

- **Description**: `Leaflet 2-native mapping components for Plotly Dash 4`
- **Website**: `https://leaflet.2plot.dev`
- **Topics**: `dash`, `plotly-dash`, `leaflet`, `leaflet2`, `maps`, `gis`, `python`
- **Settings → Actions → General**: allow GitHub Actions
- **Settings → Environments**: create an environment named `pypi`. Add yourself
  as a required reviewer if you want a manual gate between tag and upload.
- **Branch protection on `main`**: require the `CI` checks once the first run
  is green (you cannot select checks that have never run).

CI runs on this push: the smoke suite across Dash 4.1 → 4.4.1, plus a wheel
build that installs into a clean venv with only `dash` present. Let it go green
before continuing.

---

## Phase 2 — PyPI

### 2.1 Claim the name

`dash-leaflet2` has never been published. **Verify it is available before
tagging** — if someone else holds it, everything downstream changes:

```bash
pip index versions dash-leaflet2     # or just open pypi.org/project/dash-leaflet2
```

### 2.2 Configure trusted publishing

No API token is stored anywhere. PyPI verifies a short-lived OIDC token minted
by GitHub for this exact repo + workflow + environment.

On **pypi.org → Your projects → Publishing → Add a pending publisher**:

| Field | Value |
|---|---|
| PyPI project name | `dash-leaflet2` |
| Owner | `pip-install-python` |
| Repository name | `dash-leaflet2` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

A "pending publisher" is the right choice for a name that does not exist yet —
the first successful upload creates the project.

### 2.3 Dry run to TestPyPI

Do this before the real tag. Actions → Release → *Run workflow*, leave
`dry_run` checked. It builds, verifies and uploads to TestPyPI. Then install
from there into a clean venv:

```bash
python -m venv /tmp/tp && /tmp/tp/bin/pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  dash-leaflet2
/tmp/tp/bin/python -c "import dash_leaflet2 as d; print(d.__version__, len(d.__all__))"
```

TestPyPI needs its own pending publisher (same form, on test.pypi.org).

### 2.4 Tag and publish

```bash
git tag -a v0.2.0 -m "dash-leaflet2 0.2.0 — first public release"
git push origin v0.2.0
```

`release.yml` then: asserts the tag matches `pyproject.toml`, re-runs
`check_release.py`, runs the smoke suite, builds, publishes via OIDC, and opens
a GitHub Release with this version's CHANGELOG section attached.

### 2.5 Verify

```bash
python -m venv /tmp/real && /tmp/real/bin/pip install dash-leaflet2
/tmp/real/bin/python -c "import dash_leaflet2 as d; print(d.__version__)"
```

Check the PyPI page renders the README and the "Documentation" URL points at
`leaflet.2plot.dev`.

---

## Phase 3 — leaflet.2plot.dev

### 3.1 Create the service

Render dashboard → **New → Blueprint** → select the repo. `render.yaml`
declares the service, `/healthz` as the health check, and every environment
variable — secrets are marked `sync: false` for you to fill in.

### 3.2 Fill in the secrets

In the Render dashboard, on the service:

| Variable | Where it comes from |
|---|---|
| `CROSS_APP_WEBHOOK_SECRET` | the same value every other 2plot satellite holds |
| `CLERK_SECRET_KEY` / `CLERK_PUBLISHABLE_KEY` | Clerk dashboard, the production instance |
| `CLERK_FRONTEND_API` | `https://<app>.clerk.accounts.dev` — **required** in satellite mode |
| `ADMIN_EMAILS` | who reaches `/admin/control-board` |
| `MUI_PRO_API_KEY` | optional; only `/tile-layers-pro`'s tree control |

`SESSION_SECRET` is generated by Render (`generateValue: true`).

### 3.3 Custom domain

Add `leaflet.2plot.dev` to the service and point the CNAME at the Render
hostname. **`CLERK_SATELLITE_DOMAIN` must match this exactly** — it is already
set to `leaflet.2plot.dev` in `render.yaml`.

### 3.4 Register with the network — three separate places

This is the step most easily forgotten, and each one fails silently.

**a. Clerk redirect whitelist (2plotai repo).** Add the satellite origin to
`CLERK_ALLOWED_REDIRECT_ORIGINS`, **with a scheme**:

```
https://leaflet.2plot.dev
```

A missing scheme silently strands users on the primary's home page after
sign-in. That has already happened twice in this network — `lib/auth.py` in
2plotai documents it.

**b. Traffic hub health sweep (2plot.ai env).** Append to `PULSE_POLL_TARGETS`:

```
leaflet=https://leaflet.2plot.dev/healthz
```

**c. Network directory (2plotai `lib/network_directory.py`).** Add the
`leaflet` key so `/traffic` gives the series a proper label and colour instead
of a bare slug. The ad network's `/admin/ad-board` keys off `AD_APP_ID`
(`dash-leaflet2`) separately.

### 3.5 Post-deploy checklist

1. `GET /healthz` → `{"ok": true, "app": "leaflet", "version": "0.2.0", "reporting": true}`.
   `reporting: false` means `CROSS_APP_WEBHOOK_SECRET` is missing.
2. `/llms.txt`, `/robots.txt`, `/sitemap.xml` all 200, and sitemap URLs use
   `leaflet.2plot.dev` (i.e. `DASH_LEAFLET2_BASE_URL` took effect).
3. **Flip the theme toggle on three pages and confirm the basemap changes.**
   This is the one thing no automated check covers end to end — the smoke test
   proves the JS parses, not that the tiles swap in a browser.
4. Sign in — you should bounce to 2plot.ai and land **back here**, not on the
   primary's home page.
5. `/admin/control-board` shows the page table with **no** dev-mode banner. If
   the banner is there, Clerk is not configured and every tier is falling open
   to public.
6. `2plot.ai/traffic` grows a `leaflet` series within one
   `SATELLITE_REPORT_INTERVAL_S` (30 min).
7. An ad slot appears in the aside of a page that has a table of contents.

---

## Cutting the next release

1. Land work on `main`; CI must be green.
2. Move `## [Unreleased]` content under a new `## [X.Y.Z] — <date>` heading.
3. Bump the version in **four** places — `pyproject.toml`, `package.json`,
   `package-info.json`, `lib/constants.py`. `check_release.py` fails if they
   drift. (`dash_leaflet2/package-info.json` is generated by
   `npm run build:backends` from the root one; it is the file
   `dash_leaflet2.__version__` actually reads.)
4. If any `.tsx` changed, `npm run build` and commit the regenerated bundle and
   classes — `check_release.py` flags a bundle older than `src/ts`.
5. `python scripts/check_release.py --version X.Y.Z`
6. Tag `vX.Y.Z` and push. Everything else is automated.

## Known gaps

Worth doing, not blocking:

- **`tests/` is empty.** The smoke suite is integration-level; there are no unit
  tests for `dl2_locations`, `dl2_tiles`, or the component prop contracts.
- **`attribution` is construction-only** in `dl2.TileLayer` — a theme swap
  changes the tiles but cannot change the credit, so `TilePair.attribution()`
  names both providers. Making it mutable in `TileLayer.tsx` (alongside `url`,
  `opacity`, `zIndex`) would be a genuine improvement.
- **`walking-sim` does not theme its tiles**, deliberately — the Esri imagery
  stack is photographic and the layer choice is already user-driven.
- **Control-board overrides are ephemeral on Render's free tier.** They live in
  a JSON file on the container filesystem and reset on deploy. Point
  `PAGE_VISIBILITY_FILE` at a persistent disk if they must survive.
- **No browser-level CI.** `compat_matrix.py --browser` exists and drives
  Playwright, but it is not wired into Actions.
