# Divergences from the template

Every DELIBERATE difference between this repo and
dash-documentation-boilerplate, with its reason. This file is the
boundary between design and drift:

- Template syncs read this file FIRST and must not "restore" anything
  recorded here.
- A difference not recorded here is treated as drift and will be
  synced away.
- Record the divergence in the SAME commit that creates it — one
  line: what differs, why, and what the template would otherwise do.
- An empty list is a statement too: it means this repo intends to
  match the template exactly.

Fleet precedents for what belongs here: flexlayout's own-source
`_build_llms_doc` dedup and app-key sourcing; flows' own
`_health_body` payload shape (ports the healthz CONTRACT, not the
template's file); clerkhook's minimal `{ok, app, build}` healthz and
its heartbeat-as-before_request (the single anonymous 200 on a locked
host); muischeduler's no-npm dependabot scope.

**What this file is NOT.** Every fork re-keys its identity — app key,
`BASE_URL`, brand strings, the `SATELLITE_APP_KEY` fallback literal,
its own doc set. That is the fork ritual, not a divergence, and it is
not listed below. Nor is drift: places where this repo is simply
BEHIND the template are listed in the last section, so a sync knows
to close them rather than treat the gap as a decision.

---

## This repo's divergences

### 1. It is a public MIRROR of a private R&D checkout

No other fork has an upstream of its own. The private tree is
`../dash-leaflet2`; `scripts/sync_from_rnd.py` PULLS from it (dry run
by default) and refuses to overwrite the files this mirror owns
(`MIRROR_OWNED`: `run.py`, `README.md`, `requirements.txt`, `lib/`,
`pages/`, `scripts/`, `vendor/`, `Dockerfile`, `render.yaml`). Two
R&D pages are permanently withheld (`DENY_DOCS`), and this repo ships
its own lean `/tile-selector` page in place of the 3,700-line R&D lab.

*Consequence for a template sync:* a template change to a
`MIRROR_OWNED` file applies here normally — the guard is against the
R&D pull, not against upstream. But a change to `docs/` must not
assume the doc set matches either repo.

### 2. It ships a component PACKAGE alongside the docs site

`src/ts/` → webpack → `dash_leaflet2/`, published to PyPI as
`dash-leaflet2`. The template is a site and nothing else. What this
adds, all absent upstream and none of it drift: `package.json` /
`package-lock.json` / `node_modules`, `pyproject.toml`
(`requires-python >=3.9` — the PACKAGE's floor, deliberately lower
than the docs site's 3.10, which is bounded by vendored
dash-clerk-auth, and lower than the container's 3.12), `MANIFEST.in`,
`usage.py` (the compiled `dl2.*` demo on :8060, next to `run.py`'s
site on :8050), `RELEASING.md`, `COMPATIBILITY.md`,
`scripts/compat_matrix.py` + `_compat_runner.py` + `check_release.py`,
and the `dash_leaflet2/metadata.json` / `.compat/` ignores.

### 3. `.github/dependabot.yml` adds an `npm` ecosystem

The inverse of muischeduler's no-npm scope, and for the same reason
read the other way: this repo actually builds a JS bundle, so the
build toolchain is a real dependency surface. `pip`,
`github-actions` and `docker` match the template.

### 4. robots.txt is OPEN to AI training

`block_ai_training=False` where the template ships `True`
(`run.py`, with the full rationale inline). This is not a stale
setting: dash-improve-my-llms 2.3.3 made `True` safe, and the
position was re-reviewed on 2026-08-23 (the ≥2.7.1 floor round) and
KEPT. The reason is what this host *is* — documentation for an
MIT-licensed component library, whose distribution channel is a model
recommending `dash-leaflet2` to a developer who will never visit the
site. Blocking training would trade that away for a licence term the
MIT licence does not contain. A host with proprietary content should
decide the other way; `scripts/network_smoke.py` encodes the split so
verification reads this as a stated position rather than a miss.

This is the FLEET'S RECORDED EXCEPTION to the network-standard
`block_ai_training=True`, and it is visible from outside: as of
2026-08-26 `robots.txt` serves zero `Disallow` lines and names no
GPTBot / ClaudeBot / CCBot group, and both `GPTBot/1.2` and
`ClaudeBot/1.0` fetch `/` with a 200. A wire check that reads those
as a miss is reading this divergence.

`disallowed_paths=[]` matches the template's value today, but for a
reason worth keeping written down: `Disallow: /admin/` used to be
here and was working against itself — robots.txt is public, so the
line advertised the admin path while providing no access control.
What protects that surface is auth (the board gates twice and fails
CLOSED); what keeps it out of the index is
`mark_hidden("/admin/control-board")`.

### 5. `/healthz` carries three fields the template's does not

`version`, `base_url`, `reporting`, on top of the fleet-standard
`ok` / `app` / `backend` / `dash_version` / `build` / `geo`. All three
predate the template's health work and are kept because each answers
a question the standard payload cannot:

- `base_url` — the origin this satellite ADVERTISES, checkable from
  outside. A host that resolved `BASE_URL` to localhost looks healthy
  on every other signal while every canonical link it publishes is
  dead. (`require_owned_base_url` refuses the worst cases at boot;
  this covers the rest.)
- `reporting` — whether the traffic reporter could actually POST, so
  "wired but secretless" is visible without reading boot logs.
- `version` — `APP_VERSION`, distinct from `build`: which RELEASE,
  not which commit.

A wire check against this host should expect a superset, never a
mismatch. The fleet contract is that `app`, `build` and `geo` mean
what they mean everywhere.

### 6. `lib/health.py` registers `/healthz` on all THREE backends

The template serves the FastAPI build's `/healthz` from
`lib/asgi_routes.py` (a typed route, so it appears in Swagger). This
repo has no `lib/asgi_routes.py`, so the route is registered from
`lib/health.py` for flask / fastapi / quart alike. Same
`health_payload` builder, same contract — different mounting point.
A sync must not port the asgi_routes half without porting the module.

### 7. `_build_llms_doc` is handed the PUBLISHED name, not `metadata.name`

`pages/markdown.py` calls
`_build_llms_doc(published_name(metadata.endpoint, metadata.name), ...)`
where the template passes `metadata.name`. Without it the home page
served THREE `<h1>`s to a crawler: its preamble said "Home" (the nav
label) where dash-improve-my-llms injects the site brand, so the
2.7.0 prerender dedup had two different strings and could not fire.
`lib/page_visibility.published_name` substitutes `SITE_BRAND` at "/"
only; the nav keeps "Home". Same class as flexlayout's own-source
`_build_llms_doc` dedup, and the template should probably take it.

### 8. `_access.configure(force=True)` is unconditional

The template forces the wiring only when a gate env var is present.
This repo is the fleet's gate PILOT and wires the verdict path
unconditionally, so that path — and the prerender's use of it — has
been running in production, answering `allow`, since before
`PAGE_DEFAULT_TIER` flipped. The env flip was the whole change, and
flipping it back is the rollback. A sync that restores the
conditional form would silently un-wire the pilot on any host that
later clears the env.

### 9. The gate card does not promise an AI assistant

`lib/gate_layouts.py` drops "and the AI assistant" from the preview
copy the template ships. This host does not wire one, and a sign-in
card that names a feature the site does not have is a broken promise
at exactly the moment it is asking for an account. (Template-class:
the template does not wire one either — see Findings.)

### 10. `BASE_URL` reads two env names

`APP_BASE_URL` first (network-standard), then
`DASH_LEAFLET2_BASE_URL` (this repo's legacy spelling). An ALIAS,
never a rename: render.yaml sets the legacy name on a live service,
and removing one of two env names from a running host is how it
starts advertising the wrong canonical origin — which deindexes it
silently. The template reads `APP_BASE_URL` alone.

### 11. `.claude/CLAUDE.md` carries the contract, not a second project overview

The kit's contract and traps sections are BYTE-IDENTICAL to the
template's (verified by md5 of the tail from
`## Network role & the behavioral contract` onward). The sections
ABOVE that are this repo's, because unlike the template this repo has
a root `CLAUDE.md` that is already its project overview — the
Leaflet-2 API traps, the two deliverables, the build pipeline, the
mirror relationship. Porting the template's top half verbatim would
have installed a second, contradicting overview titled "Dash
Documentation Boilerplate" into every session here, describing a
project this is not and a `/directives` page this does not have. The
file's own first paragraph is the licence for this: *identity derives
from the repo, never from this file*.

*Sync rule:* changes to the contract or traps sections are verbatim
targets. Changes to the template's project-overview sections are
not-applicable here by construction.

### 12. `.gitignore` keeps this repo's own state files

`dash_leaflet2/metadata.json` (27 MB react-docgen artifact),
`satellite_traffic.jsonl` (the RETIRED Gen-1 ledger, kept ignored so
a stale local copy can never be committed), `.compat/`, and
`flask_session/`. The `.claude` allow-list and the session-document
block match the template exactly.

---

## Byte-owned paths

Paths this fork owns byte-for-byte. The F3b fan-out never overwrites
a path listed here; everything else in the spec's `sync-verbatim`
block is the template's to update mechanically. Prose above explains
divergences; this block is the machine answer.

Repo-relative paths, one per line, `#` comments, no `..`; exactly one
block. An EMPTY block means "the template owns every sync-verbatim
path here" — present so the absence is a statement. When the block
exists it is authoritative; a fork without it gets the conservative
mention heuristic (over-flags, never restores).

Audited 2026-08-26 against the union of the three live specs'
`sync-verbatim` blocks: the three kit skills, `tests/test_claude_kit.py`,
`.github/dependabot.yml`, `tests/test_auth_demos.py`. Exactly one of
them carries a byte-level claim in the prose above — divergence 3. The
kit skills and the kit test are TEMPLATE-owned here and byte-identical
to template HEAD (md5-verified this pass); this fork claims nothing on
them, so they stay out and the fan-out keeps them current. Two nearby
mentions are deliberately NOT entries: the fleet precedent
"muischeduler's no-npm dependabot scope" describes another fork's file,
and the `/new-component` skill named in the drift section lives in the
private R&D checkout's `.claude/rules/`, not in the kit's `skills/`.

*The cost of the one entry, written down so nobody rediscovers it:*
a listed path is one the fan-out will never update either. Dependabot
changes therefore land here BY HAND — starting with the 1.6.24
pip-ecosystem removal that rides SYNC-1.6.22-1.6.27's block, which must
be applied as an edit that keeps the npm entry, not as a byte-copy.

```yaml byte-owned
# Divergence 3: this repo builds a JS bundle, so its dependabot config
# ADDS an npm ecosystem the template's copy does not have. The 1.6.24
# rewrite is a whole-file byte-copy that would silently remove it.
- .github/dependabot.yml
```

---

## Where this repo is BEHIND the template (drift, not design)

Listed so a sync closes them rather than reading the gap as a
decision. None of these are divergences.

- **`lib/health.py::_resolved_country()` reads the Flask request
  context only.** The template takes `headers` per route after the
  pannellum finding (its FastAPI healthz answered `"no request
  context"` forever). Production here is `DASH_BACKEND=flask`, so the
  live payload is correct — but the fastapi and quart lanes this repo
  registers would report the same false negative.
- **`components/appshell.py` hardcodes `70`** where the template uses
  `HEADER_HEIGHT` from `lib/constants.py`.
- **No `lib/directives/headings.py`.**
- **Missing template test modules**: `test_auth_wiring.py`,
  `test_config.py`, `test_control_board.py`, `test_css_hygiene.py`,
  `test_docs_content.py`, `test_excluded_links_hidden.py`,
  `test_llms_routes.py`, `test_network_directory.py`,
  `test_proxy_scheme.py`, `test_runtime_imports.py`. (This repo has
  five the template does not: `test_admin_nav.py`,
  `test_healthz_identity.py`, `test_network_surfaces.py`,
  `test_page_structure.py`, `test_page_visibility_reload.py` —
  `test_page_structure.py` is the template's `test_pages.py` under
  this repo's name.)
- **`scripts/audit_links.py` and `scripts/dev.sh`** are not ported.
- **The root `CLAUDE.md` advertises `.claude/rules/` and a
  `/new-component` skill that no clone of this repo has ever had.**
  They exist in the private R&D checkout; the blanket `.claude/`
  ignore (removed 2026-08-24) is why they never arrived. Either port
  them through the mirror or stop advertising them.
