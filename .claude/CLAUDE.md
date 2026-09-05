# dash-leaflet2 — leaflet.2plot.dev

## Project Overview

The project facts are NOT restated here: `CLAUDE.md` at the repo ROOT is this
repo's overview — what it is (and what `../dash-leaflet2` really is: a
local sibling working tree, same origin, unpushed — corrected 2026-08-31),
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

### Acceptance output (1.6.44 item 10)

**PRINT THE RESOLVED VERSION BESIDE THE RESULT, and say which tool
produced it.** An acceptance is a claim about a tree AT A VERSION.
"suite green" is not a result; "423 passed, 3 skipped, exit 0,
dash-improve-my-llms 2.8.0 imported from
`.venv/lib/python3.12/site-packages/dash_improve_my_llms/__init__.py`"
is.

Resolve it by IMPORTING and printing `mod.__file__` — never by reading
`requirements.txt`, which states an intent rather than a fact, and
never by parsing source, which truncates (the regex trap below cost
this seat a wrong field count in a spec). This repo's line is a `>=`
FLOOR, which makes the gap wider here than on a pinned host: the
number in the file and the number in the venv are different questions
and often different answers.

The gap is real and was measured on excalidraw 2026-09-01 —
`llms_version` 2.9.4 on the wire while its suite ran 2.8.0, so its CI
and its production disagreed about which package's behaviour was being
accepted, and every green tick meant the older one. This fork will
reproduce that shape at 1.6.45: CI legs install `>=2.8.0` and resolve
current, while production serves whatever the last image built.

NAME THE TOOLS WHOSE LOCAL INVOCATION IS NOT CI'S. `actionlint`
without shellcheck on PATH skips every `run:` block's shell analysis,
so "actionlint clean" locally is a weaker statement than the CI job's;
a local ABSENCE of the binary is weaker still, and both must be
reported as what they are. Same for a backend leg this seat cannot
run — `quart` is not installed in this venv, so a three-lane claim
made from here is a two-lane measurement plus an assumption.

The general form: **when the check you ran differs from the check CI
runs, the report says so in the same sentence as the result.**

### Writing a detect (1.6.44 item 13)

**PARSE, or strip comments AND STRINGS.** A detect of the form "this
token must not appear in this file" matches the COMMENT that explains
why the token is absent — and stripping comments still leaves the
DOCSTRING doing the same job. The better-documented the code, the more
reliably a raw grep reports the very defect the documentation denies.

Measured on this tree, twice in one pass:

* item 6's a11y detects hunted `trigger="hover"`, `loading=` and
  `Pillow`, and matched the comments saying those must never appear;
* item 8 tripped the PRE-EXISTING UA-list guard, which already stripped
  comments and the MODULE docstring — a FUNCTION docstring quoting a
  measured `classify()` result read as a resurrected vendor table.

`tests/conftest.py::live_source()` is the answer: `ast.unparse` drops
comments outright and docstrings are removed explicitly. Use it for
every "string absent from module" assertion. `ast.parse` is the tool;
a comment strip is not.

TWO MORE FAILURE MODES, both formatting-bound and both cheap to avoid:

* a phrase that WRAPS across a line defeats a literal grep — FLATTEN
  whitespace before matching prose;
* an indented blockquote's `> ` markers do the same.

And match prose CASE-INSENSITIVELY. The template shipped a detect
grepping `"ASSERT THE CORPUS IS NON-EMPTY"` in the capitals a spec uses
for emphasis while the trap ships in sentence case, so `grep -c`
returned 0 on the tree that authored it — a detect that could not pass
anywhere, inside the item about checks that cannot fail.

### Verification traps (fleet-learned, keep them)

- A `>=` floor can never pull a new release through a Docker cache
  hit — the requirements line changing IS the cache bust, and floors
  live in several encodings (requirements, run.py's boot floor,
  tests, CI): grep the number, move every one.
- `/healthz` build == HEAD **of `release`** is the deploy proof on a
  release-branch host — read the fuller trap below before acting on
  this line, which was written UNQUALIFIED here until 1.6.44 and so
  said "HEAD" where it meant HEAD of `release`. A missing geo block on
  dimll ≥2.7 means the cache trap fired (unless DIVERGENCES.md says
  this host's healthz is deliberately minimal).
- Always GET, never HEAD — and the mechanism, measured 2026-08-27
  after two rounds of wrong diagnoses: on the ASGI backends HEAD is
  answered by NOTHING AT ALL. Werkzeug derives a HEAD rule from
  every GET rule; FastAPI's `APIRoute` does not, so a route declared
  `@router.get(...)` returns 405, and every ASGI host in the network
  was 405ing HEAD on every route — `/healthz`, `/robots.txt`,
  `/sitemap.xml` included. Get the LAYER right (corrected 1.6.33,
  after this text and two seats' drops all said "Starlette", and
  three probes went looking in the wrong package):
  `starlette.routing.Route` DOES add HEAD wherever GET is present —
  `self.methods.add("HEAD")`, the same courtesy Werkzeug does — and
  FastAPI's `APIRoute` is the one that takes `methods` literally.
  A HEAD probe therefore tells you about
  the router's method table and never about the document. GET is
  never wrong, which is the whole reason to have one rule.
  Do NOT "verify" the trap on one host and conclude HEAD is fine:
  excalidraw measured twice and was right about its own Flask host
  and wrong about the fleet. Do not verify it on `HEAD /` either —
  a crawler-UA `HEAD /` is answered by the prerender middleware
  before routing, so it returns 200 on a host that 405s everything
  else, and that one case is how this repo's 1.6.31 in-process
  probe cleared the app code. Earlier text here said the ASGI hosts
  DROP the `Link` headers on HEAD: a 405 carries no `Link`, so the
  observation was true and the diagnosis was not. Fixed in the
  template at 1.6.32 (a HEAD→GET ASGI middleware, because the
  package's own adapter declares its routes GET-only); the fleet's
  two ASGI forks consume it as spec item 11, and the hub plus four
  second-ring hosts had the same defect — if you serve a non-Flask
  backend, assume you have it until you have probed a route that is
  NOT `/`. The middleware stays after dimll 2.7.2 fixes the
  package's own routes: `/` is Dash's page catch-all and every Dash
  route is an `APIRoute` too. AMENDED 1.6.44: at dimll **2.9.4** the
  package walks the router itself and adds HEAD wherever GET is
  allowed — Dash's lifespan-registered catch-all included — so the
  template retired the shim, gated on the PIN and not the date. This
  fork keeps its `>=2.8.0` floor until 1.6.45 and therefore KEEPS the
  middleware (DIVERGENCES 17); it had never carried it before, so the
  starting state was absent, not retired, and those two look identical
  to a grep. Measured here at 2.8.0 on the FastAPI lane, 15 pairs:
  `/healthz` 405 on all three UAs and `/` 405 to a BROWSER while
  returning 200 to a crawler and to curl. That last row is this trap's
  own warning firing in practice — the prerender answers `HEAD /`
  above routing, so the crawler UA everyone reaches for is the one UA
  that cannot see the defect. Probe a route the app owns, with a
  browser UA, on the ASGI lane.
- Any throwaway Python probe a session writes against a production
  host needs the certifi SSL context AND a retry guard. Fixing the
  shipped tools does not cover the next ad-hoc script: the template
  seat hit `CERTIFICATE_VERIFY_FAILED` in a hand-written CD watcher
  one hour after shipping that exact fix inside both live tools,
  and the ops seat hit it plus an `IncompleteRead` on a chunked
  response in the same session. It is a seat habit, not a repo
  contract, which is what this file is for.
- Run-watchers keyed on a commit sha can match Dependabot's runs on
  the same sha — key on the workflow path (cd.yml) instead.
- The browser lane and the machine lane are different documents;
  a fix proven on one is unproven on the other.
- SUPERSESSION: cd.yml's build-match wait cannot tell "not deployed
  yet" from "already replaced" — both look like a live build that
  is not the sha it wants. A bot-merged PR (any GITHUB_TOKEN merge)
  is one road in: it lands with ZERO workflow runs on the merge sha
  (anti-recursion) yet still reaches production, because the deploy
  hook builds branch HEAD — so an in-flight CD run ships the merge
  while its own wait holds out for the superseded release sha
  (observed live on 4a1d430, 2026-08-25). It is NOT the only road,
  and taking the bot actor off main does not close the class: two
  human pushes inside one deploy window, or hook dispatch lag,
  produce exactly the same state. Since 1.6.25 the wait fails FAST
  when the live build is a DESCENDANT of the wanted sha (compare
  API) instead of going red at timeout — that is the diagnosis, and
  it works whoever merged. The policy — actions PRs: human merge
  when green, never a bot actor on main — removes the most common
  road, not the trap.
- Anonymous api.github.com is 60 requests/hour. With no `gh` and no
  token, read a run ONCE after CI's own jobs report complete — a
  blind 20 s poll loop spends the whole budget reading rate-limit
  bodies as "not done yet" (modelviewer, 2026-08-26).
- A GitHub API JSON body WITHOUT the field you asked for
  (`workflow_runs` absent, not empty) is a rate-limit error body,
  never an empty result — check the field exists before trusting
  the answer.
- `git fetch` before any audit: the fan-out pushes to these repos
  now, and a checkout current yesterday is 2–3 merges behind
  origin/main today (three pilot sessions, same day, 2026-08-26).
- A failed STEP is not a failed RUN. A job with
  `continue-on-error: true` (pip-audit here) reports its step red
  and the RUN still concludes `success`; the reverse also bites —
  a green-looking job list under a run whose conclusion is
  `failure`. Read the run's `conclusion`, then the annotations;
  never infer either one from the other.
- Never round-trip JSON through zsh `echo` — it interprets the
  `\n` inside a multi-line commit message and hands the parser
  real control characters (a broken API read on the template, then
  the same hour on the ops seat). Pipe curl straight into
  `python3`, or use `printf '%s'`.
- Repeated HTTP headers survive only if you keep them: both
  `dict(resp.headers)` and `{k: v for k, v in resp.headers.items()}`
  keep the LAST value per name, and dimll emits several `Link`
  headers (muicharts, 2026-08-26). Iterate the items, or ask for
  `resp.headers.get_all(name)`; in curl, `-D -` and read the raw
  block.
- Name the crawler UA when you probe the machine lane. Which
  document a host serves is decided by the package's UA
  classification, not by the absence of a UA: on the template
  today, curl's default `curl/8.x` receives the SAME crawler
  document as Googlebot (18,779 bytes, byte-identical) while a
  Chrome UA gets the 148 KB app shell. One host (muicharts) reported
  a UA-less probe classified the other way; treat that as
  UNCONFIRMED — muischeduler filed the same observation and then
  RETRACTED it (its report had the two documents swapped), leaving
  one unreproduced sighting, and a trap carrying an unreproducible
  fact spends somebody's afternoon. The advice does not depend on
  it: either lane can be the one you did not mean to test, so send
  `-A "<a real crawler UA>"` and confirm from the body which
  document came back.
- There is ONE classifier: `dash_improve_my_llms.classify()`. Never
  add a User-Agent list to this app — the tracker had one for a year
  (`lib/analytics_tracker.py`, until 1.6.34), it filed ClaudeBot as
  *search* (it is Anthropic's training crawler; the package's registry
  and this repo's own `run.py` comment both said so six lines from
  where the list ignored them), it still named the retired
  `anthropic-ai` / `claude-web` tokens, and it counted every UA-less or
  library client as a human. Every host in the fleet reported those
  numbers. A token the registry lacks is a pushback to the package
  seat, not a list here; `tests/test_analytics_classifier.py` greps the
  module for the old tokens and goes red if one comes back.
- `/healthz` BUILD == HEAD OF `release` IS THE DEPLOY PROOF on a repo
  with a promote lane, and `build == HEAD` means HEAD of **`release`**,
  not main
  (1.6.35). Render deploys `release`; only cd.yml's `deploy` job writes
  it, fast-forward, after the CI matrix is green. `main` ahead of
  `release` is an uncertified push pending — its CD run is red or still
  running — never "drift" and never a reason to deploy by hand or to
  write `release` yourself (a non-fast-forward push fails the next run
  on purpose). Compare the wire against `git rev-parse origin/release`;
  the one measurement behind this: 2026-08-29 14:12Z, de0bcff pushed
  to main, built by Render inside the minute, red in CD at 14:13Z,
  served for ~6 minutes. A host whose DIVERGENCES.md posture fence has
  no `deploy:` key still watches main — there the trap is the old one.
- Headless browsers are CRAWLER-lane from dash-improve-my-llms 2.9.0
  (measured on the wheel, 2026-08-29: `HeadlessChrome/…` and a
  Playwright UA classify `lane: crawler, bot_type: monitor,
  vendor_key: headless`; 2.8.0 said browser). A host that screenshots
  ITSELF for social cards — Playwright, Puppeteer, a headless Chrome
  in a job — now receives the crawler document, not the app shell,
  unless the screenshot service sends its own non-headless UA. If a
  card went blank or textual after a floor bump, look here before
  the template. Same class as the two lane traps above: name the UA,
  confirm from the body which document answered.
- Which branch Render actually builds can be measured on a GREEN push,
  by TIMING, without waiting for a red one (leaflet, 2026-08-31 — the
  method, not just its answer). `main == release == wire` at every step
  of a promote tells you nothing: both refs hold the same sha, so the
  wire cannot separate them, and four promotes across three hosts said
  nothing at all. Sample `/healthz` every ~45 s from the moment of the
  push and note when the swap lands relative to the PROMOTE, not the
  push. leaflet measured build+swap at 2m03s from the promote; had
  Render reacted to the push instead, the same 2m03s would have put the
  build live ~1m52s earlier than it appeared, and the wire was still
  serving the old sha well past that point. That is STRONG EVIDENCE
  that Render is building `release` — not proof, since a queued or slow
  build could in principle produce the same shape. The canonical
  discriminator is unchanged and still owed: the first push that goes
  RED on main must leave `release` unmoved and the wire unchanged.
  Worth taking on every SECOND promote — it costs one background
  sampler and converts "asserted" into "strongly evidenced".
  AMENDED 1.6.44 (item 17) WITH THE CONCRETE FORM, because this was a
  method nobody should re-derive live at 2 a.m. mid-promote:
  `scripts/promote_sampler.py --sha <sha>` takes **eight samples at 45**
  second intervals and prints the wire and the CD run state on ONE
  timeline. Three things a hand-written watcher gets wrong and this does
  not. (1) One loop, one timeline — sampling the wire and the run state
  separately invites exactly the arithmetic error the measurement exists
  to avoid. (2) It times against the PROMOTE STEP's `completed_at`,
  never the deploy JOB's: the job CONTAINS the build-match wait, so it
  completes when the wait SEES the swap — it tracks the swap and never
  the promote, and measured -13 s and 0 s on two pairs, useless either
  way. (3) It retries each sample three times and records `unreadable`
  as a state DISTINCT from `old`, because the container restart lands
  exactly where the bracket needs its sample; an un-retried loop is
  systematically blind at the only moment that matters, and folding
  `unreadable` into `old` invents a bracket nobody observed. The sampler
  REFUSES to report a bracket it did not observe — a single "new" sample
  cannot say what it followed.
- Verify the artifact the claim is about, and say which one you
  measured. Three hosts got this wrong in one round while holding the
  rule: a skip link checked in the received HTML lives in the RENDERED
  DOM (muicharts, twice inside an hour, having written the rule
  itself); a props table absent from the crawler document is a defect
  of the site, not of the harness — pannellum moved that assertion onto
  the rendered layout and the pin passed for a fortnight over a corpus
  serving zero props. WHEN A LANE DISAGREES, THAT IS THE FINDING; never
  relocate the assertion to the lane that passes. And an owner-gated
  section needs BOTH cookie states to be a measurement at all
  (modelviewer: `credentials: 'include'` → 2,962 B with admin hrefs,
  `'omit'` → 108 B with none — hidden, not merely styled away).
  The error runs BOTH ways and the second one is worse, because it
  sends someone hunting a bug that does not exist: `curl https://…/ |
  grep -c skip-link` returns **0** on a host where the skip link is
  shipped and working (excalidraw, 2026-08-31) — it is a Dash
  component in `app.layout`, so React renders it and the served HTML
  never contains it. A fork "verifying the skip link on the wire" with
  curl reports a missing feature that is present. Anything built by
  the layout rather than written into the template is invisible to the
  two artifacts curl can reach; assert it through the layout or a real
  browser, and say which you used.
- Assert the corpus is NON-EMPTY before trusting any negative, and print
  the count beside the result (note 88). A sweep that found nothing and a
  sweep that swept nothing produce the same green, and only one of them
  is evidence. Measured here 2026-09-01: this repo's `.flake8` excludes
  `docs/*/`, so `flake8 docs/` exits 0 with a file in `docs/` containing
  `def broken(:` — the linter is not passing that file, it is not reading
  it; `py_compile` sees it at once. Same family, same day: a naive
  substring count read fenced documentation as defects (this seat), a
  file-scoped grep matched prose ABOUT the defect it was hunting
  (muicharts, clerkhook), a `git show … && diff` printed "(empty = same)"
  on a comparison that never ran (llms), and `pytest … | tail -2 && git
  commit` committed over a red suite because a pipeline's exit status is
  the LAST command's (this seat, one hour after writing the note above).
  Capture the exit code; count what you swept; say both.
- A VERIFY VERDICT IS METERING EVIDENCE, NEVER SOLE AUTHORISATION
  (1.6.44 item 18; the security incident of 2026-09-02, hub 0.26.0 ->
  0.26.1, 2plot.dev `5ca793c`). The hub gated two admin-data routes on
  2plot.dev's `/api/agent-key/verify`, whose all-unknown-tier fallback
  answered "allow" WITHOUT READING THE KEY; the lane was open
  00:52-01:16Z. The contract: a host's own data is gated by a secret
  THAT HOST HOLDS. A verify verdict may be a second factor, and it is
  metering evidence first. A new tier is UNVERIFIED until the authority
  learns it, so "ask the authority" is the wrong SHAPE for a gate — the
  failure mode of an unreachable or ignorant authority must be closed,
  and an authority that answers "allow" to a question it did not
  understand is worse than no authority.
  A key presented in a request proves nothing on its
  own — anyone can put a string in a query parameter. What makes
  `hub_client.verify`'s answer trustworthy is the HOST-HELD SECRET
  beside it: the POST is signed with `CROSS_APP_WEBHOOK_SECRET`, which
  lives in the deployment's environment and never travels with the
  request, and without it `enabled()` is false and the answer is
  "gated" without anyone being asked. So a route that consults `verify`
  for access must NAME the host-held secret beside it, or be documented
  as metering-only; a `verify` call somewhere the secret is not
  required is a bearer check on an unauthenticated value.
  Two testing rules come with it, both learned the hard way.
  SOURCE-PIN THE CLOSED FALLBACKS, do not merely exercise them: a
  behavioural suite cannot see a restored default that pre-empts its
  own guard, because the guard never runs. And PIN THE GOOD ROWS BESIDE
  THE BYPASS ROWS — a policy that denies everything passes every bypass
  test ever written. Reject case and whitespace LOOKALIKES of a tier
  (`"Auth "`, `"ADMIN"`), never one literal: this repo normalises hub
  tiers at the source, which is the only place it happens, so a
  refactor that drops the `.strip().lower()` would silently let a
  restricted ceiling read as unrestricted.
- A SHELL'S CWD CAN SHADOW AN INSTALLED PACKAGE, and it produces the
  most convincing wrong answer of the family: measuring `EVENT_FIELDS`
  across two dimll versions, a seat ran the comparison with the cwd
  inside an unpacked 2.9.4 wheel, so `import dash_improve_my_llms`
  resolved from the CURRENT DIRECTORY rather than site-packages — and
  two readings of ONE wheel were reported as two versions agreeing, in
  a CHANGELOG and a shipped spec. The load-bearing half was true and
  the supporting detail was invented. When comparing versions,
  `print(mod.__file__)` and assert it is the path you meant, or set
  PYTHONPATH explicitly and import in a fresh process per version; and
  print the unpacked file count before the read. Parsing the constant
  out of source is NOT the safe alternative: the regex form truncated
  on a `)` inside a comment, and an AST form written to replace it
  agreed with the wrong answer until the import settled it. IMPORT THE
  THING.
- NAME THE CHECK THAT ACTUALLY RAN, not the one you meant to run
  (1.6.44 item 7). `.flake8` excludes `docs/*/` and the lint job never
  passes it `docs` anyway, so "flake8 is clean" was reported for a year
  as covering the exec'd examples this documentation site RENDERS, and
  it never read one of them. Measured here 2026-09-05: a file in
  `docs/` containing `def broken(:` leaves `flake8 docs/` at exit 0
  with ZERO output, while `py_compile` exits 1 with the SyntaxError on
  the same file. The general form: a report says which invocation
  produced the number, over how many files, and with what exit code,
  because "lint passed" is a claim about a COMMAND and everyone reads
  it as a claim about the CODE. CI now runs the sweep as its own step
  (`py_compile sweep of docs/`) and fails when the corpus is EMPTY.
- A CD LANE THAT CALLS ci.yml MUST NOT ALSO LET ci.yml RUN ITSELF on a
  push to main (1.6.44 item 12). Both runs resolve to the same commit,
  both go green, and the only symptoms are the runner bill and an
  unreadable workflow list. This repo does NOT have the defect —
  ci.yml declares `{pull_request, workflow_dispatch, workflow_call}`
  and cd.yml owns the push — and `tests/test_workflow_double_run.py`
  keeps it that way in BOTH directions, since "no push trigger" is also
  satisfied by deleting the triggers that make CI useful. Reading the
  triggers at all needs care: YAML 1.1 folds an unquoted `on:` key to
  the BOOLEAN True, so `workflow["on"]` raises KeyError on every
  workflow file ever written, and a test that catches that and moves on
  asserts nothing while looking thorough.
- A FORK'S TRAPS SECTION DRIFTS BEHIND THE TEMPLATE'S SILENTLY (1.6.44
  item 14). The kit is contract-class, so no sync copies it and nothing
  printed the gap: emojimart carried 7 entries against 22, and its HEAD
  trap still held the diagnosis 1.6.32 had corrected — a fork can be
  acting on a fact the fleet retired months ago. Detect, printed as a
  PAIR: `python3 scripts/kit_traps.py` reports `fork N / template M`
  and names what is missing. Matching is by TOKEN OVERLAP of each
  trap's opening sentence, never exact text, because a fork is EXPECTED
  to merge a trap into its own wording; a strict check would train
  forks to paste over their own adaptations. MERGED, NEVER INSTALLED
  OVER. Known limit, measured on this fork: the 0.6 overlap threshold
  cannot see a template trap that a fork carries SPLIT ACROSS TWO
  bullets, and reported two such as missing here. SECOND limit, found
  by this fork's own test fixture: `_tokens()` scores only the FIRST
  SENTENCE, so a fork that opens a reworded trap with a short
  colon-terminated summary is judged on a handful of words and reads as
  missing however faithfully the rest of the entry carries the trap.
  Neither is patched here — the counts are compared ACROSS the fleet,
  and a fork that quietly changes the algorithm makes its number
  incomparable with everyone else's. Both are pushbacks to the template
  seat. Read the pair as a prompt to look, not as a verdict.
- PRINT THE RESOLVED VERSION BESIDE THE RESULT, and say which tool
  produced it (1.6.44 item 10). An acceptance is a claim about a tree
  AT A VERSION: "suite green" is not a result. Resolve by IMPORTING and
  printing `mod.__file__` — never by reading `requirements.txt`, which
  states an intent, and on this fork's `>=` FLOOR the intent and the
  fact are routinely different numbers. excalidraw served
  `llms_version` 2.9.4 while its suite ran 2.8.0, so every green tick
  meant the older package. The same rule names the tools whose LOCAL
  invocation is not CI's: `actionlint` without shellcheck skips every
  `run:` block's shell analysis, and a local ABSENCE of the binary is
  weaker still — both are absent on this seat, as is `quart`, so a
  three-lane claim from here is two lanes plus an assumption.
- And the same family one turn later, MEASURED TWICE — this seat and
  clerkhook hit it independently within the hour, so it is a property
  of the TECHNIQUE and not one seat's slip. It nearly shipped a wrong
  fact into a spec: extracting a package constant with
  `re.search(r"EVENT_FIELDS = \((.*?)\)", src, re.S)` truncated at a `)`
  inside a COMMENT in the middle of the tuple, printed eight of sixteen
  fields, and reported `'ua' present: False` — confidently, with a
  number beside it. Caught only because eight looked too few. When you
  parse a language construct out of source with a regex, check the count
  against something independent (the file, `python -c "from … import X;
  print(len(X))"`, the CHANGELOG) before you believe a negative.
