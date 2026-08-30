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
build toolchain is a real dependency surface. `github-actions` and
`docker` match the template.

`pip` is now ABSENT here as well (template 1.6.24, applied by hand
2026-08-26): on range requirements dependabot can only propose floor
RAISES, and floors move through sync specs instead. So the npm block
is the whole of this divergence.

THE FENCE WAS PROVEN ON THIS PATH, and it is worth recording that it
was not hypothetical. `SYNC-1.6.22-1.6.29`'s `sync-verbatim` block
lists `.github/dependabot.yml`, every one of its adoption gates is
satisfied here, and the F3b fan-out ran against this repo on
2026-08-26 (PR #25, merged). It copied three files and SKIPPED this
one — the npm ecosystem is still here because the `byte-owned` block
below told the machine to leave it alone. Without the fence the copy
would have landed and removed the npm block silently, since removal
by byte-copy looks identical to an intended removal in a diff.

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
`ok` / `app` / `backend` / `dash_version` / `build` / `geo` /
`python`. All three
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

### 13. The site CI matrix's legs are the FLOOR and the adjacent minor

The template's Python window rolls: its two include legs are X.Y-1
and X.Y-2 around the fleet Python. This repo's are **3.10 and 3.13**
against a 3.14 image — the second is the template's shape, the first
is not.

3.10 is a real floor, not a preference: `python-frontmatter` 1.3
imports `typing.TypeGuard`, and the vendored `dash-clerk-auth` 1.0.5
declares `requires-python >=3.10`. A rolling window would stop
exercising that floor the moment the fleet Python moved twice — which
is precisely when a floor breaks quietly, because nothing else in the
tree resolves `requirements.txt` at its lower bound.

So `tests/test_python_version.py` here asserts what this fork
actually means — one leg IS the declared floor, one leg is directly
below the fleet Python — instead of the template's "within three of
the fleet minor". Both halves are still pinned, so the window can
neither collapse to one nor drift. The floor itself is stated ONCE,
as `lib.constants.DOCS_PYTHON_FLOOR`, and the test reads it from
there rather than repeating the literal.

*Not to be confused with the PACKAGE lane.* `Package · Python` runs
3.9–3.13, testing the `dash_leaflet2` wheel's own
`requires-python >=3.9` against a bare `pip install dash`. That
window is the package's business and is deliberately wider than the
site's; `test_the_package_lane_is_out_of_scope_and_stays_wide` fails
if anyone ever "aligns" it with the image. Two Pythons in one
`ci.yml` is the shape spec 1.6.28 describes, and this is that shape.

### 14. `scripts/smoke_live.py` asserts this host's open-training posture

The template's copy has no equivalent: divergence 4 is this fork's,
so the check that proves it on a live host is too. The block asserts
`robots.txt` serves no `ClaudeBot` stanza and fingerprints the
crawler rules the running artifact produces.

This is why item 6 of `SYNC-1.6.22-1.6.29` was ported here as
CONTRACT — the wake loop, the retry knobs and the SSL context, added
to this fork's file — rather than by the byte-copy the spec
recommends. A byte-copy would have deleted the assertion, and a
deleted check does not fail; it just stops being true without
telling anyone. The spec anticipates exactly this ("a fork that
replaced the tool records the divergence and ports the contract
half"); the record is this entry.


### 15. `/api` reads a COMMITTED props extract, not `metadata.json`

Template 1.6.38's `lib/api_reference.py` reads the component package's
`metadata.json` — which, on a pip-installed Dash component package,
sits next to `__init__.py`. In this repo that file is a 27 MB
react-docgen BUILD artifact: `.gitignore` excludes it (divergence 12)
and `MANIFEST.in` excludes it from the wheel. It is an input to
`dash-generate-components`, never a runtime file.

So on Render — which clones this repo and builds the Dockerfile —
`metadata.json` does not exist, and the template's code would have
rendered an empty `/api` while every local check passed, because
locally the file IS there. Measured both ways before and after.

`scripts/build_api_metadata.py` distils it to
`dash_leaflet2/api_metadata.json` (26 components, 302 props, 78 KB),
which IS committed; `load_package` prefers `metadata.json` when
present so a developer who has just re-run `npm run build:backends`
sees new props immediately. That file also carries `generated`, the
date the props last changed — which is `/api`'s sitemap `lastmod`,
written by the thing that regenerates the content so the two can
never drift, and committed so a Docker rebuild cannot reset it the
way an mtime would.

*Consequence for a sync:* `lib/api_reference.py` is NOT byte-identical
to the template's and cannot become cargo here until upstream has a
fallback of its own. Everything else in that file is verbatim.

### 16. Two generated pages register through `register_llms_doc`

`/changelog` and `/api` arrive from template 1.6.38 leaving a
module-level `LLMS_DOC` for the package to discover. That publishes
the prose but sends no `lastmod`, so both pages entered the sitemap
dateless — which `tests/test_seo_icons.py` fails here and nowhere
upstream, because the template has no such test. Both now register
through `lib.page_visibility.register_llms_doc`, like every docs page
here, which also brings them under the control board's per-page
llms.txt toggle instead of silently skipping them.

`/changelog` additionally needed its date parser widened: this repo's
CHANGELOG has always written `## [0.2.2] — 2026-08-05` with an EM
DASH, and the template's regex accepts only an ASCII hyphen, so it
matched every version and dropped every date — a Timeline with no
dates on it. The pattern now takes `-`, `–` or `—`.

### 17. `network_smoke.py`'s manifest check sends a BROWSER UA — AHEAD of the template, retires at 1.6.40

Not a permanent difference: a fix this repo made first, recorded so a
sync does not revert it in the window before upstream ships the same
one. The ops seat has 1.6.40 staged with the identical shape (Chrome
tokens first, internal token appended), and it confirms note 53
independently; when it lands this entry goes and the file returns to
byte-parity.

What it fixes, measured on the real dash-improve-my-llms 2.8.0
(2026-08-30): the tool's default `UA` is the bare internal token, and
from 2.8.0 `classify()` puts that on the CRAWLER lane —
`classify(UA)["lane"] == "crawler"`. So every check fetching `/` gets
the crawler document, and `installable_as_an_app` failed on "no
manifest link", because a crawler document carries none — correctly, a
crawler cannot install an app. The site was never uninstallable.

Why it matters more than a test fix: this is a LIVE tool, run by
`cd.yml`'s verify job against production AFTER the promote. On a fork
with no `tests/test_proxy_scheme.py` — this one — CI never sees it, so
the first sighting would have been a red CD run on a deploy that had
already shipped. Same class as the trap sync item 12 documents for
that test file; it simply lands somewhere CI cannot reach.

`scripts/smoke_live.py` needs no equivalent change and has none: its
`fetch` already defaults to a browser UA and names `CRAWLER_UA`
explicitly per check.

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
changes therefore land here BY HAND. The first such change has now
been made: template 1.6.24's pip-ecosystem removal, applied
2026-08-26 as an edit that keeps the npm block rather than the
whole-file byte-copy the spec's block would have performed. That is
the standing cost of this entry, and the standing procedure for it —
read the template's copy, port the intent, keep divergence 3.

Re-audited 2026-08-26 against `SYNC-1.6.22-1.6.29`, which added
`.github/dependabot.yml` and `tests/test_auth_demos.py` to the
verbatim block. The audit's answer is unchanged: one entry.
`tests/test_auth_demos.py` arrived from the fan-out and is
template-owned here — this fork claims nothing on its bytes.
`scripts/smoke_live.py` rode the block for exactly one round (1.6.28)
and was pulled back out at 1.6.29; had it still been cargo it would
have needed an entry, because this fork's copy carries a check the
template's does not (the open-training assertion, divergence 4). It
is contract-class now, so the fence stays at one path — but the near
miss is the reason to re-run this audit every round rather than
trusting the last one.

Re-audited 2026-08-29 for `SYNC-1.6.22-1.6.35` (items 12 + 13), whose
block adds `tests/test_analytics_classifier.py` and
`tests/test_traffic_rollup_v4.py`. Both arrived here as byte copies of
template HEAD and this fork claims nothing on their bytes, so the
answer is unchanged: one entry. Item 12's other two tests
(`test_read_ledger.py`, `test_traffic_page.py`) are contract-class
upstream and were ported, not copied — they call this tree's conftest
fixtures and `pages/control_board.py`. Item 13's
`tests/test_cd_promotes_release.py` is likewise a port: it parses THIS
fork's cd.yml, whose host string, wait sizing and comments are its own.

```yaml byte-owned
# Divergence 3: this repo builds a JS bundle, so its dependabot config
# ADDS an npm ecosystem the template's copy does not have. The 1.6.24
# rewrite is a whole-file byte-copy that would silently remove it.
- .github/dependabot.yml
```

---

## Declared posture

What this host SERVES, measured — not what the template ships. The hub
used to keep this as a seeded table it could not re-measure; the fence
(template 1.6.30, item 9) homes each posture in the repo that serves
it. `tests/test_claude_kit.py` validates the SHAPE and holds `runtime`
against `render.yaml`; no test can tell a stale 200 from a fresh one,
so the values below carry the date they were taken.

- **`ai_bots`** — re-measured 2026-08-30T14:25Z against
  `https://leaflet.2plot.dev` for BOTH vendor UAs the fleet checks:
  `ClaudeBot/1.0` and `GPTBot/1.2` each answer 200 on `/`, `/llms.txt`
  and `/healthz` (six lines, all 200); `robots.txt` serves zero
  `Disallow` lines and names no training UA at all. That is
  **divergence 4** on the wire, not a miss: this host ships
  `block_ai_training=False` because it is documentation for an
  MIT-licensed component library whose distribution channel is a model
  recommending `dash-leaflet2`.

  As of template 1.6.37 this is no longer a divergence in POSTURE —
  the fleet default flipped to allow, and the tool became per-vendor
  policy rather than per-class blocking. What remains recorded here is
  that this host got there first and has the wire history to show it.
  IN-PROCESS AND WIRE AGREE, all six: the app answers 200 itself, so
  there is no edge wall in front of this host either (the template's
  drop assumed a Cloudflare rule; the owner has since confirmed the
  feature is Enterprise-only on this plan and no zone rule exists).
- **`healthz: full`** — and a superset at that; see divergence 5, which
  adds `version`, `base_url` and `reporting` to the fleet-standard
  payload.
- **`runtime: docker`** — `render.yaml` builds the Dockerfile, so
  `PYTHON_VERSION` is deliberately ABSENT there (spec 1.6.28 item 5:
  on a Docker service nothing reads it, and a string that reads like
  the platform's setting and can never be true is its own defect).
- **`deploy: release-branch`** — since 2026-08-29 (template 1.6.35,
  item 13). Render watches `release`; only `cd.yml`'s `deploy` job
  writes it, fast-forward, after the CI matrix is green. `main` ahead
  of `release` is an uncertified push pending, never drift. An absent
  `deploy:` key would read as "this host still watches main".

```yaml posture
ai_bots: {"/": 200, "/llms.txt": 200, "/healthz": 200, "/robots.txt": 200, "/sitemap.xml": 200}
healthz: full
runtime: docker
deploy: release-branch
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
- **Missing template test modules**: `test_auth_wiring.py`,
  `test_config.py`, `test_control_board.py`, `test_css_hygiene.py`,
  `test_docs_content.py`, `test_llms_routes.py`,
  `test_network_directory.py`, `test_proxy_scheme.py`,
  `test_runtime_imports.py`. (`test_excluded_links_hidden.py` and
  `test_nav_contract.py` arrived with the 1.6.38 navigation contract;
  `lib/directives/headings.py` came with it too, so both are off this
  list. `test_admin_nav.py` was REWRITTEN against the new admin
  mechanism rather than retired — see below.) (This repo has
  five the template does not: `test_admin_nav.py`,
  `test_healthz_identity.py`, `test_network_surfaces.py`,
  `test_page_structure.py`, `test_page_visibility_reload.py` —
  `test_page_structure.py` is the template's `test_pages.py` under
  this repo's name.)
- **`scripts/audit_links.py` and `scripts/dev.sh`** are not ported.
- **The Dockerfile has no `HEALTHCHECK`, and `CMD` binds a bare
  `${PORT}`** rather than `${PORT:-8050}` (SYNC-1.6.10-1.6.16 item 5).
  An empty `PORT` collapses the bind. This also makes
  SYNC-1.6.17-1.6.21 item 2 UNSATISFIABLE until it is fixed: that item
  asks CI to assert `{{.State.Health.Status}}`, which is `none` on an
  image that declares no healthcheck — so `ci.yml` still polls
  `{{.State.Running}}`. Item 5 has to land first; the two are one
  change in practice.
- **`cd.yml`'s build-match wait is under-sized in four ways**
  (SYNC-1.6.10-1.6.16 item 4). It does compare `build == GITHUB_SHA`
  against the body — the part that matters, and it certified the last
  two deploys — but: the loop is 60 x 15s where the spec wants >=100;
  `timeout-minutes: 20` where it wants >=30; a hookless deploy emits
  `::notice::` where it wants `::warning::`; and the verify job's `if`
  excludes `'cancelled'` but not `'skipped'` (muicharts' guard). A
  floor bump busts the pip cache, so the round with the most to prove
  is the one whose deploy is slowest — dash-email timed out on exactly
  this class.
- **`kickoff/` is missing from `.gitignore`.** The template's
  session-document block carries it (its `.gitignore` line 169, in a
  separate block above the `*-*.md` patterns, which is how this list
  read as complete once before — batch-1's correction). Probed
  2026-08-26: `kickoff/probe.md` is committable in this repo today.
  Nothing is at risk right now because no `kickoff/` exists here.
- **The root `CLAUDE.md` advertises `.claude/rules/` and a
  `/new-component` skill that no clone of this repo has ever had.**
  They exist in the private R&D checkout; the blanket `.claude/`
  ignore (removed 2026-08-24) is why they never arrived. Either port
  them through the mirror or stop advertising them.
