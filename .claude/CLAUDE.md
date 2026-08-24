# dash-leaflet2 — leaflet.2plot.dev

## Project Overview

The project facts are NOT restated here: `CLAUDE.md` at the repo ROOT is this
repo's overview — what it is (the public mirror of a private R&D checkout),
the two parallel deliverables (the `dash.hooks` documentation site and the
compiled `dl2.*` component package), the Leaflet 2.0.0-alpha.1 API traps that
cost real debugging time, the build/run/test commands, and the component
conventions. Both files load in every session; duplicating the overview would
only give the two copies a chance to disagree, and this is the copy that would
go stale.

This file carries the part the root file does not: **the 2plot network's
behavioral contract**, identical in every repo that ships this kit.

Versions, dependencies and history are deliberately not restated in either
file — they go stale. Read `requirements.txt` for the stack and `CHANGELOG.md`
for what changed and when.

---

## Custom Directives

| Directive | Syntax | Purpose |
|-----------|--------|---------|
| `toc` | `.. toc::` | Generate table of contents |
| `exec` | `.. exec::module.path` | Render Python component (markdown2dash) |
| `source` | `.. source::file/path.py` | Display source code |
| `kwargs` | `.. kwargs::ComponentName` | Show component props |
| `llms_copy` | `.. llms_copy::Name` | Copy-for-an-agent block |

The template documents these on a `/directives` page; this site does not have
one — its doc set is 27 component pages. `lib/directives/` is the source of
truth for the four this repo implements (`exec` comes from markdown2dash).

---

## Configuration

### Customization Points

| File | Purpose |
|------|---------|
| `lib/constants.py` | App-wide constants (`BASE_URL`, `SITE_BRAND`, colors, titles) |
| `assets/style.css` | Showcase CSS — loads BEFORE the hooks-injected `leaflet.css`, hence the `!important` |
| `assets/leaflet2_maps.js` | The showcase's `DEMOS` registry and `DL2.setMapTheme` |
| `templates/index.html` | HTML template (analytics, meta tags, SEO) |
| `components/appshell.py` | Theme configuration, MantineProvider settings |
| `components/navbar.py` | Navigation ordering and organization (incl. the full-height mobile drawer — the network-standard mobile nav) |
| `components/header.py` | Header, colour-scheme toggle, and the Clerk menu (`headless=True` means the package injects no UI of its own) |
| `pages/control_board.py` | `/admin/control-board` — live per-page tier + llms.txt toggles (owner/admin-gated, fails closed) |
| `lib/page_visibility.py` | The board's override store (persists to `PAGE_VISIBILITY_FILE`; overrides beat frontmatter in `lib/access.py`) |
| `lib/access.py` | The gate's enforcement engine — the two lanes, the three-input resolver |
| `lib/auth_demos.py` | Live-demo teasers rendered inside the sign-in gate cards |
| `src/ts/` | The component package's TypeScript — built into `dash_leaflet2/` |

---

## Development Notes

### Adding New Documentation Pages
1. Create folder in `docs/` (e.g., `docs/my-component/`)
2. Create markdown file with frontmatter — `lastmod:` is REQUIRED here (see
   the root `CLAUDE.md`: it rides the prose and is never scripted from mtimes):
```markdown
---
name: My Component
description: Description of my component
endpoint: /my-component
icon: mdi:code-tags
lastmod: 2026-08-24
---

.. toc::

## Overview
...
```
3. Add Python examples as needed — `example.py` exports `component`
4. Reference with `.. exec::docs.my-component.example`
5. A showcase map also needs one `DEMOS` entry in `assets/leaflet2_maps.js`
6. Page will auto-register and appear in navigation

### Creating Theme-Aware Charts
1. Import `dmc.add_figure_templates()`
2. Register templates at module level
3. Create callback with `Input("color-scheme-storage", "data")`
4. Use ternary to select template: `"mantine_dark" if theme == "dark" else "mantine_light"`
5. Recreate figure with template parameter

---

## Resources

- [Dash Documentation](https://dash.plotly.com/)
- [Dash Mantine Components](https://www.dash-mantine-components.com/)
- [Mantine](https://mantine.dev/)
- [dash-improve-my-llms](https://pypi.org/project/dash-improve-my-llms/)
- [Project Repository](https://github.com/pip-install-python/dash-leaflet2)
- [Template](https://github.com/pip-install-python/Dash-Documentation-Boilerplate)
- [Plotly Community Forum](https://community.plotly.com/)

---

## Network role & the behavioral contract

This repo is a member of the 2plot network — either the template
itself (dash-documentation-boilerplate) or a fork of it serving one
component's documentation. **Identity derives from the repo, never
from this file**: the app key comes from `SATELLITE_APP_KEY` and
run.py's fork point, the host from `lib/constants.py`'s `BASE_URL`,
the deliberate differences from the template from `DIVERGENCES.md`
at the repo root. If those disagree with anything written here,
they win.

### The contract — every session, every prompt

1. **Check the prompt against this tree before executing.** Prompts
   are written from the template's perspective and your fork may
   legitimately differ — floors, backends, payload shapes, page
   sets. A prompt step that doesn't fit this repo is a finding to
   return, not an instruction to force.
2. **Corrections are your job, not scope creep.** If a prompt's
   reference list doesn't match its steps, if its assumed state is
   wrong, or if executing it as written would produce a
   green-but-vacuous result, say so and propose the corrected
   version before running it.
3. **Verify your own deploy on the wire before reporting.** A push
   is not a result. Run `/wire-verify` (or its manual equivalent)
   against production and paste what came back. If your sandbox
   cannot reach your own domain, say exactly that — an unverified
   claim marked as unverified is honest; the same claim unmarked is
   not.
4. **Report observed versus expected, with evidence.** Paste the
   JSON, the status code, the test count. "Should work" and summary
   claims without artifacts are not reports.
5. **Divergence is legitimate when written down.** Before syncing
   template changes, read `DIVERGENCES.md`; never let a sync
   "restore" a recorded deliberate difference. When you deliberately
   diverge, record it there in the same commit — an unrecorded
   divergence is indistinguishable from drift and will be treated
   as drift.
6. **Never touch**: environment variable VALUES, hosting dashboards,
   secrets, other repos' trees, or anything the prompt didn't put in
   scope. Enumerate what you cannot do (closing PRs, dashboard
   steps) for the owner instead of claiming it done.

### Verification traps (fleet-learned, keep them)

- A `>=` floor can never pull a new release through a Docker cache
  hit — the requirements line changing IS the cache bust, and floors
  live in several encodings (requirements, run.py's boot floor,
  tests, CI): grep the number, move every one.
- `/healthz` build == HEAD is the deploy proof; a missing geo block
  on dimll ≥2.7 means the cache trap fired (unless DIVERGENCES.md
  says this host's healthz is deliberately minimal).
- Probe with GET, not HEAD — HEAD responses omit the Link headers.
- Run-watchers keyed on a commit sha can match Dependabot's runs on
  the same sha — key on the workflow path (cd.yml) instead.
- The browser lane and the machine lane are different documents;
  a fix proven on one is unproven on the other.
