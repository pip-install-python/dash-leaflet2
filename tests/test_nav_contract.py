"""The navigation contract (1.6.38) — uniform where it must be, free where it may.

Owner's brief of 2026-08-30 (DESIGN-navigation-uniformity): the sidebar's
sections come from frontmatter against CATEGORY_ORDER; the network is ONE
registry rendered as the top bar's Other Apps menu; Resources is one
constant; Admin is owner-only and absent from the tree otherwise; every
icon-only control has a name; no `dcc.*` where DMC has the component. Each
pin here is one line of that brief.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
ALLOWED_DCC = {"Location", "Store", "Interval", "Upload", "Graph"}


def _calls(src: str, name: str):
    """Yield the source text of every `name(` call, parens balanced."""
    for m in re.finditer(re.escape(name) + r"\(", src):
        depth, i = 0, m.start()
        while i < len(src):
            if src[i] == "(":
                depth += 1
            elif src[i] == ")":
                depth -= 1
                if depth == 0:
                    yield src[m.start():i + 1]
                    break
            i += 1


# ------------------------------------------------------------- a11y --


# Every directory that renders UI components. `lib/directives/` joined
# `components/` because the directives ARE renderers — `SC` returns a
# CodeHighlightTabs, LlmsCopy returns a copy control — so an icon-only
# button added there would have been checked by nothing. There is none
# today; this is a forward guard, and cheap.
A11Y_UI_DIRS = ("components", "lib/directives")


@pytest.mark.parametrize("control", ["dmc.Burger", "dmc.ActionIcon"])
def test_every_icon_only_control_in_components_has_a_name(control):
    """Requirement 9: the audits named the unlabelled Burger and copy
    button. Every Burger/ActionIcon in a UI directory carries aria-label."""
    unlabelled = []
    scanned = 0
    for folder in A11Y_UI_DIRS:
        for path in sorted((REPO / folder).glob("*.py")):
            scanned += 1
            for call in _calls(path.read_text(), control):
                if "aria-label" not in call:
                    unlabelled.append(f"{folder}/{path.name}: {call[:60]}…")
    assert unlabelled == [], unlabelled
    # Not a silent skip: a glob that stopped matching would make this pass
    # by scanning nothing, which is the failure mode a grep-shaped pin has.
    assert scanned >= 2, f"only {scanned} module(s) scanned across {A11Y_UI_DIRS}"


def test_code_highlight_copy_button_has_a_name():
    """The copy button is icon-only; without these it is announced as
    nothing.

    It was also, briefly, the pin that would have caught a
    `scripts/sync_from_rnd.py` pull reverting this file — the sibling tree's
    copy had neither line. That script is retired and deleted (2026-08-31,
    DIVERGENCES 1), so nothing can revert it any more and the a11y reason is
    now the whole reason this test exists. Which is reason enough."""
    src = (REPO / "lib" / "directives" / "source.py").read_text()
    assert "copyLabel=" in src and "copiedLabel=" in src


def test_no_dcc_where_dmc_has_the_component():
    """Requirement 10, fleet-wide: `dcc.` only for Location, Store,
    Interval, Upload, Graph (no DMC equivalent)."""
    offenders = []
    for folder in ("pages", "components"):
        for path in sorted((REPO / folder).glob("*.py")):
            code = "\n".join(line for line in path.read_text().splitlines()
                             if not line.lstrip().startswith("#"))
            for m in re.finditer(r"\bdcc\.([A-Za-z]+)", code):
                if m.group(1) not in ALLOWED_DCC:
                    offenders.append(f"{folder}/{path.name}: dcc.{m.group(1)}")
    assert offenders == [], offenders


def test_the_traffic_page_uses_a_date_picker_not_a_dropdown():
    src = (REPO / "pages" / "traffic.py").read_text()
    assert "dcc.Dropdown" not in src
    assert "dmc.DatePickerInput" in src and 'valueFormat="YYYY-MM-DD"' in src
    assert "presets=" in src and "minDate=" in src and "maxDate=" in src


# --------------------------------------------------------- registry --


def test_other_apps_menu_is_the_registrys_primary_set(app_module):
    """Requirement 4 + the owner's review (2026-08-30): the PRIMARY
    applications only — never the docs subdomains — from the registry,
    no duplicates, self omitted, short labels (the domain)."""
    from components.header import create_other_apps_menu
    from lib.constants import BASE_URL
    from lib.network_directory import AFFILIATED, PEERS, PRIMARY, other_apps_for

    menu = create_other_apps_menu()
    items = menu.children[1].children
    hrefs = [i.href for i in items]
    expected = [e["url"] for e in other_apps_for(BASE_URL)]
    assert hrefs == expected
    assert set(h.rstrip("/") for h in hrefs) == PRIMARY - {BASE_URL.rstrip("/")}
    assert {"https://2plot.ai", "https://2plot.dev", "https://2plot.media",
            "https://piratesbargain.com", "https://ai-agent.buzz"} == set(PRIMARY)
    assert PRIMARY <= {e["url"].rstrip("/") for e in PEERS + AFFILIATED}, "PRIMARY names a URL the registry lacks"
    assert not any(".2plot.dev" in h for h in hrefs), "a docs subdomain leaked into the menu"
    assert len(set(hrefs)) == len(hrefs), "a host is listed twice"
    for item in items:
        label = item.children
        assert "." in label and " " not in label and "—" not in label, label
        assert item.target == "_blank"


def test_resources_are_third_party_only():
    """Owner's review (2026-08-30): the sidebar's Resources holds dmc and
    the upstream project only; the owner's own links are top bar + footer."""
    from lib.constants import DISCORD_URL, GITHUB_URL, YOUTUBE_URL, resources

    items = resources()
    assert items[0]["label"] == "dmc" and items[0]["url"] == "https://www.dash-mantine-components.com/"
    urls = [r["url"] for r in items]
    for banned in (GITHUB_URL, DISCORD_URL, YOUTUBE_URL, "github.com", "discord", "youtube",
                   "community.plotly.com", "https://2plot.dev"):
        assert not any(banned in u for u in urls), banned


def test_github_icon_and_same_as_share_one_constant(app_module):
    from components.header import create_header
    from lib.constants import GITHUB_URL, SAME_AS

    assert GITHUB_URL in SAME_AS
    assert GITHUB_URL.startswith("https://github.com/pip-install-python/")
    assert GITHUB_URL.count("/") == 4, "the REPOSITORY, not the profile"
    assert GITHUB_URL in str(create_header([]))


# ---------------------------------------------------------- sidebar --


def test_sections_follow_category_order_and_never_hold_admin(app_module):
    import dash

    from components.navbar import sections_for
    from lib.constants import CATEGORY_ORDER

    data = list(dash.page_registry.values())
    sections = sections_for(data)
    titles = [t for t, _ in sections]
    known = [t for t in titles if t in CATEGORY_ORDER]
    assert known == [c for c in CATEGORY_ORDER if c in titles], titles
    for _, entries in sections:
        assert not any(e["path"].startswith("/admin/") for e in entries)
        assert not any(e["path"] in ("/", "/changelog", "/api") for e in entries)
    # the template's own docs all declare a category
    assert "Documentation" not in titles, "a docs page lost its category: frontmatter"


def test_frontmatter_order_sorts_within_a_section(app_module):
    import dash

    from components.navbar import sections_for

    for title, entries in sections_for(dash.page_registry.values()):
        orders = [int(e.get("order") or 1000) for e in entries]
        assert orders == sorted(orders), (title, orders)


def test_anonymous_tree_has_no_admin_href(app_module, monkeypatch):
    """Requirement 7: hidden, not blocked. The startup tree carries only an
    empty Admin placeholder; the callback returns nothing to a non-admin."""
    import dash

    from components.navbar import create_content, render_admin_section

    tree = str(create_content(dash.page_registry.values()))
    assert "/admin/" not in tree
    assert "navbar-admin-desktop" in tree
    monkeypatch.delenv("ALLOW_UNGATED_ADMIN", raising=False)
    assert render_admin_section("navbar-admin-desktop") == (None, None)


def test_admin_tree_lists_every_admin_page(app_module, monkeypatch):
    from components.navbar import render_admin_section

    monkeypatch.setenv("ALLOW_UNGATED_ADMIN", "1")
    desktop, mobile = render_admin_section("navbar-admin-desktop")
    text = str(desktop)
    assert "/admin/control-board" in text and "/admin/traffic" in text
    assert str(mobile) == text


def test_search_lists_only_sidebar_pages(app_module):
    import dash

    from components.navbar import search_data

    values = [d["value"] for d in search_data(dash.page_registry.values())]
    assert values and not any(v.startswith("/admin/") for v in values)
    assert "/" not in values and "/changelog" not in values


# ---------------------------------------------------------- footer --


def test_footer_is_the_contract(app_module):
    from datetime import datetime

    from components.footer import create_footer
    from lib.constants import DISCORD_URL, GITHUB_PROFILE_URL, GITHUB_URL, YOUTUBE_SUBSCRIBE_URL

    text = str(create_footer())
    assert f"© {datetime.now().year} Pip Install Python LLC" in text
    for href in (GITHUB_PROFILE_URL, DISCORD_URL, YOUTUBE_SUBSCRIBE_URL):
        assert href in text
    assert GITHUB_URL not in text, "the repo link is the top bar's; the footer links the profile"
    assert "/changelog" not in text, "the sidebar's single Changelog link is the one"
    assert "/terms" not in text and "/privacy" not in text


# ------------------------------------------------------- changelog --


def test_changelog_page_is_the_file(app_module, client):
    from pages.changelog import parse_changelog

    versions = parse_changelog()
    newest = re.search(r"^## \[([^\]]+)\]", (REPO / "CHANGELOG.md").read_text(), re.M).group(1)
    assert versions and versions[0]["version"] == newest
    doc = client.get("/changelog/llms.txt", user_agent="Mozilla/5.0 (compatible; Googlebot/2.1)")
    assert doc.status == 200
    assert doc.text.startswith("# Changelog") and "\n# Changelog" not in doc.text, "the file's H1 was not deduplicated"
    assert f"## [{newest}]" in doc.text
    page = client.get("/changelog", user_agent="Mozilla/5.0 (compatible; Googlebot/2.1)")
    assert page.status == 200 and newest in page.text


# ------------------------------------------------------------- api --


def test_api_reference_reads_a_dash_package_metadata():
    from lib import api_reference

    comps = api_reference.load_package("tests.fixtures.fake_dash_pkg")
    names = [c["name"] for c in comps]
    assert names == ["FakeGauge", "FakeWidget"], "sorted, exported only"
    widget = comps[1]
    props = {p["name"]: p for p in widget["props"]}
    assert "setProps" not in props
    assert props["value"]["required"] and props["value"]["default"] == "0"
    assert props["variant"]["type"].startswith("one of ")
    assert widget["props"][0]["name"] == "id"
    md = api_reference.as_markdown(["tests.fixtures.fake_dash_pkg"])
    assert "| `value` * | number | 0 | Current value. |" in md


def test_api_page_renders_one_table_per_component():
    from pages.api import build_page

    text = str(build_page(["tests.fixtures.fake_dash_pkg"]))
    assert "api-table-FakeWidget" in text and "api-table-FakeGauge" in text
    assert "Current value." in text


def test_api_page_is_registered_because_this_fork_documents_a_package(app_module):
    """INVERTED FROM THE TEMPLATE, deliberately — and this is a spec
    correction, not a local exemption.

    Upstream this test reads `assert API_PACKAGES == []` with the reason
    "the template documents no component package". That assertion can never
    hold on a COMPONENT fork, which is every fork item 16 tells to set
    `API_PACKAGES = [its package]` — so the test as shipped is guaranteed
    red on exactly the hosts the /api page exists for. What the contract
    actually says (item 16 §7) is "not registered when the list is empty",
    and that conditional is what both halves below pin: this fork declares
    one package, so /api registers and renders its components; the
    empty-list branch is covered by `pages.api.should_register`.
    """
    import dash

    from lib.constants import API_PACKAGES
    from lib.api_reference import load_package

    assert API_PACKAGES == ["dash_leaflet2"]
    assert "/api" in [p["path"] for p in dash.page_registry.values()]
    # ...and it is not an empty shell: the real package resolves.
    assert len(load_package("dash_leaflet2")) > 0

    # The other half of the conditional, asserted against the guard that
    # actually exists rather than a helper invented for the test:
    # pages/api.py registers under a bare `if API_PACKAGES:`, and the
    # generator has nothing to say for an empty list.
    import inspect

    from lib.api_reference import load_packages
    from pages import api

    # The guard gained a second clause at 1.6.41 (`and not
    # _docs_page_owns("/api")` — a docs page may claim the path), so pin the
    # part that is this item's contract rather than the whole line.
    assert "if API_PACKAGES and" in inspect.getsource(api)
    assert load_packages([]) == []


def test_missing_package_is_reported_not_raised():
    from lib import api_reference

    out = api_reference.load_packages(["no_such_dash_package_xyz"])
    assert out[0]["components"] == [] and "error" in out[0]


# ------------------------------------------------ 1.6.39 fix-forward --


def test_the_aside_collapses_on_pages_without_a_toc(app_module):
    """Owner's note 1: /changelog full width. Docs pages with `.. toc::`
    keep the column; everything else collapses it."""
    from lib.aside import aside_config, has_aside

    # PORTED page names, and one real difference: this site's HOME page
    # carries a `.. toc::` of its own (docs/home/home.md), where the
    # template's does not — so `/` belongs with the pages that KEEP the
    # column here, not with the ones that collapse it.
    assert has_aside("/pointer-events") and has_aside("/layers-control")
    assert has_aside("/"), "docs/home/home.md declares `.. toc::` on this fork"
    for path in ("/changelog", "/admin/traffic", "/admin/control-board", "/api"):
        assert not has_aside(path), path
        assert aside_config(path)["collapsed"]["desktop"] is True
    assert aside_config("/pointer-events")["collapsed"]["desktop"] is False
    assert aside_config(None)["collapsed"]["mobile"] is True


def test_the_mobile_drawer_is_always_mounted(app_module):
    """Owner's note 2: the burger must not depend on a mount-on-open
    transition, and #navbar-admin-mobile must exist on every load."""
    from components.navbar import create_navbar_drawer

    drawer = create_navbar_drawer([])
    assert drawer.keepMounted is True
    assert "navbar-admin-mobile" in str(drawer)


def test_code_blocks_cannot_widen_the_page():
    """Owner's note 3: the overflow rule lives in the stylesheet, for every
    container a code block can sit in — never a per-page fix."""
    css = (REPO / "assets" / "main.css").read_text()
    for selector in (".mantine-List-itemWrapper", ".mantine-List-itemLabel",
                     ".mantine-Timeline-itemBody", ".mantine-CodeHighlight-root",
                     ".mantine-CodeHighlightTabs-root", ".mantine-AppShell-main pre",
                     "table.m2d-block-kwargs", "code.m2d-codespan"):
        assert selector in css, selector
    # and the changelog's rows let an unbreakable code token wrap
    src = (REPO / "pages" / "changelog.py").read_text()
    assert '"overflowWrap": "anywhere"' in src and '"minWidth": 0' in src
    wrappers = css[css.index(".mantine-List-itemWrapper"):]
    assert "min-width: 0" in wrappers[:400]
    pre_rule = css[css.index(".mantine-AppShell-main pre"):]
    assert "overflow-x: auto" in pre_rule[:200]
    assert "overflow-wrap: anywhere" in css[css.index("code.m2d-codespan"):][:200]


def test_other_apps_dropdown_is_solid_and_every_primary_app_has_an_icon(app_module):
    """Seat's note 4."""
    from components.header import create_other_apps_menu
    from lib.network_directory import ICONS, PRIMARY

    dropdown = create_other_apps_menu().children[1]
    assert dropdown.styles["dropdown"]["backgroundColor"]
    for url in PRIMARY:
        assert ICONS.get(url) not in (None, "mdi:web"), f"{url} has no icon"


def test_battery_hidden_paths_match_the_registry(app_module):
    """Note 74: the battery's literal tuple is pinned against the registry,
    so a page added, renamed or deleted moves it in the SAME change.

    PORTED with a SUPERSET assertion, not the template's set equality, and
    the difference is deliberate. This fork's battery carries one extra
    entry — `/admin/llms.txt` — that is a canary rather than a page: `/admin`
    is not registered, so a registry-derived set can never contain it, and
    equality would force its deletion. The property the item actually asks
    for is that no registered admin page is MISSING from the battery, which
    is what this asserts; the canary is additionally pinned by name so it
    cannot be dropped by accident either.

    This pin arrived red: /admin/traffic registered in the 1.6.34 ledger
    round and HIDDEN_DOC_PATHS did not notice, so the live battery was not
    checking the newest owner surface at all.
    """
    import dash

    from scripts.network_smoke import HIDDEN_DOC_PATHS

    admin = {p["path"] for p in dash.page_registry.values()
             if p["path"].startswith("/admin/")}
    wanted = {f"{p}/llms.txt" for p in admin}
    missing = wanted - set(HIDDEN_DOC_PATHS)
    assert not missing, (
        f"network_smoke.HIDDEN_DOC_PATHS drifted from the registered admin "
        f"pages — the live battery never checks these: {sorted(missing)}"
    )
    assert "/admin/llms.txt" in HIDDEN_DOC_PATHS, (
        "the /admin canary went missing; it is the check that catches a 404 "
        "which has stopped being a real refusal"
    )


_REQUEST_METHODS = ("get", "post", "open", "request", "put", "delete", "head")


def _code_only(src: str) -> str:
    """Source with docstrings and `#` comments removed.

    muicharts, 2026-08-31: the words pass while the header is gone — its
    grep matched "User-Agent" inside an explanatory COMMENT, so deleting
    the real header left the pin green. This one proved the point on
    itself: the comment below describing the chained form made the pin
    flag its own file.
    """
    src = re.sub(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'', "", src)
    return re.sub(r"#[^\n]*", "", src)


def _client_names_a_ua(src: str, var: str) -> bool:
    """Does `var` — a bound `.test_client()` — name a UA on the wire?

    Either the client carries one for every request (`environ_base`), or
    every request call on it passes `headers=`. A client that issues no
    requests in this file cannot get the lane wrong here.
    """
    if re.search(re.escape(var) + r"\.environ_base\b[^\n]*HTTP_USER_AGENT", src):
        return True
    calls = [c for m in _REQUEST_METHODS for c in _calls(src, f"{var}.{m}")]
    return bool(calls) and all(_names_a_ua(c) for c in calls)


def _names_a_ua(call: str) -> bool:
    """`headers=` is NOT evidence of a User-Agent (muischeduler, 2026-08-31).

    A call passing `headers={"CF-IPCountry": "FR"}` satisfies a `headers=`
    grep and names no lane at all — this repo had exactly that one, and its
    mutation check stayed green until the pin asked for the UA specifically.
    A fleet-wide grep on `headers=` reports clean trees that are not.
    """
    return any(
        token in call
        for token in ("HTTP_USER_AGENT", "user_agent=", "User-Agent", "USER_AGENT")
    )


def test_every_test_client_user_names_headers():
    """Notes 70/74: a bare test client sends `Werkzeug/x.y` — crawler lane
    at dimll ≥ 2.8 — so a mark_hidden page 404s and an every-page-200 loop
    goes red at the floor bump. Any file that drives `.test_client()` must
    pass a named UA.

    Resolved per CALL SITE, not per file (pannellum, 2026-08-31): the
    substring form this pin shipped with — `"headers=" in src` — read the
    whole file, so a tool whose `headers=` sat on a DIFFERENT code path
    (urllib probes) passed while all three of its in-process fetches were
    bare, and it flagged a bare-app test with no dimll middleware and no
    lane to get wrong. It missed the only real offender in the tree that
    measured it.
    """
    offenders = []
    for folder in ("tests", "scripts"):
        for path in sorted((REPO / folder).glob("*.py")):
            src = _code_only(path.read_text())
            if ".test_client()" not in src:
                continue
            # `(?!\s*\.)` — a CHAINED call binds the RESPONSE, not the
            # client (`body = app.server.test_client().get(...)`), and the
            # first cut of this pin read `body` as an unnamed client with no
            # requests and flagged a line that already passed headers (llms,
            # 2026-08-31, measured on its test_prerender_idempotency.py).
            bound = set(re.findall(r"(\w+)\s*=\s*[\w.]*\.test_client\(\)(?!\s*\.)", src))
            bound |= set(re.findall(r"\.test_client\(\)\s+as\s+(\w+)", src))
            # Chained calls still get checked — on the call itself, since
            # there is no client name to follow.
            for meth in _REQUEST_METHODS:
                for call in _calls(src, f".test_client().{meth}"):
                    if "headers=" not in call:
                        offenders.append(f"{folder}/{path.name}::<chained {meth}>")
            if not bound:
                # Wrapped in place (conftest hands the raw client to a Client
                # that always sends one) — no name to follow, so fall back.
                if "headers=" not in src and "HTTP_USER_AGENT" not in src:
                    offenders.append(f"{folder}/{path.name}")
                continue
            for var in sorted(bound):
                if not _client_names_a_ua(src, var):
                    offenders.append(f"{folder}/{path.name}::{var}")


def test_the_sweep_harness_ua_is_browser_lane_and_internal():
    """The other half of notes 70/74, which repairing the lane alone misses:
    a CI sweep that names the browser lane WITHOUT the internal token lands
    in the ledger as N countable people (muicharts measured 4 such rows).
    Both properties, or the fix measures strictly less than it looks."""
    import re

    from dash_improve_my_llms import classify

    from lib.constants import INTERNAL_UA, INTERNAL_UA_TOKEN

    src = (REPO / "scripts" / "smoke_test.py").read_text()
    block = re.search(r'BROWSER_UA = \(\s*(.*?)\n    \)', src, re.S).group(1)

    # The token half is a SOURCE pin: the expression must actually splice
    # INTERNAL_UA in. Composing the string and then asserting the token is
    # in it would be true by construction — the first draft of this test did
    # exactly that and asserted nothing.
    assert "INTERNAL_UA" in block, (
        "the sweep harness's UA does not splice INTERNAL_UA — its hits are "
        f"countable people in whatever ledger they reach: {block!r}"
    )

    # The lane half is a real classification of the real string: the literal
    # fragments, joined with the value the expression names.
    ua = "".join(re.findall(r'"([^"]*)"', block)) + INTERNAL_UA
    assert classify(ua)["lane"] == "browser", ua
    assert INTERNAL_UA_TOKEN in ua.lower()


# ---------------------------------------------------- lane parity (note 80) --
#
# The amendment's lesson, not its fix: the muicharts defect was that the TEST
# asserted section HEADINGS, which a directive-stripped machine document still
# carries while every row under them is gone. So these assert ROWS and row
# CONTENT, and each is mutation-checked below — a pin that cannot go red when
# the content disappears is the defect, not the guard.


def _api_machine_doc(client):
    from conftest import CRAWLER_UA

    return client.get("/api/llms.txt", user_agent=CRAWLER_UA).text


def test_api_machine_lane_carries_prop_ROWS_not_just_headings(app_module, client):
    """Note 79's battery invariant, in-process: /api's machine document must
    carry real prop rows. Headings alone are exactly what the broken shape
    still produces."""
    from lib.api_reference import load_package

    doc = _api_machine_doc(client)
    comps = load_package("dash_leaflet2")
    assert comps, "no components resolved at all"

    # Row CONTENT: a component's name, one of its prop names, and that prop's
    # type — the three cells that make a row a row.
    sample = next(c for c in comps if c["props"])
    prop = sample["props"][0]
    for cell in (sample["name"], prop["name"]):
        assert cell in doc, f"{cell!r} missing from /api/llms.txt"

    # And ROW COUNT, so a document carrying one lucky row cannot pass: every
    # component must appear, and the table's pipes must be there in bulk.
    missing = [c["name"] for c in comps if c["name"] not in doc]
    assert not missing, f"components absent from the machine lane: {missing}"
    assert doc.count("|") > sum(len(c["props"]) for c in comps), (
        "the machine document has headings but no table rows"
    )


def test_the_api_row_pin_goes_red_when_the_rows_go(app_module):
    """MUTATION CHECK for the pin above. Disable the row generation and the
    assertion must fail; if it still passes, it was reading headings."""
    from lib import api_reference

    real = api_reference.load_packages
    try:
        api_reference.load_packages = lambda pkgs: [
            {"package": p, "components": []} for p in pkgs
        ]
        stripped = api_reference.as_markdown(["dash_leaflet2"])
    finally:
        api_reference.load_packages = real

    # The heading survives — which is precisely why heading pins are useless.
    assert "# API reference" in stripped
    comps = real(["dash_leaflet2"])[0]["components"]
    assert comps[0]["name"] not in stripped, (
        "the mutation did not actually remove the rows; this check proves "
        "nothing about the pin above"
    )


def test_docs_source_directive_reaches_both_lanes(app_module, client):
    """This fork's equivalent of note 80's directive seam, and the reason it
    is NOT a defect here: `.. source::` output is expanded into the PROSE
    (pages/markdown._expand_source_directives) — the same treatment the
    amendment prescribes — so the example's code reaches the machine lane
    instead of living only in the React tree. `.. exec::` renders an
    interactive map, whose textual content IS that source."""
    from pathlib import Path

    from conftest import CRAWLER_UA

    slug = "pointer-events"
    example = Path(f"docs/{slug}/example.py")
    assert example.is_file()
    lines = [ln.strip() for ln in example.read_text().splitlines()
             if ln.strip().startswith("import ")]
    assert lines, "the example imports nothing — pick another control page"

    doc = client.get(f"/{slug}/llms.txt", user_agent=CRAWLER_UA).text
    assert lines[0] in doc, (
        f"{lines[0]!r} is in example.py and rendered on the page, but not in "
        "the machine document — the directive's output lives only in the "
        "React tree (note 80's shape)"
    )
    # No directive line is served RAW to an agent either.
    for d in (".. toc::", ".. exec::", ".. source::", ".. llms_copy::"):
        assert d not in doc, f"{d} served literally to an agent"


def test_api_survives_a_package_with_no_metadata_json(tmp_path, monkeypatch):
    """Contract highlight 7: upstream `load_package` returns [] SILENTLY when
    metadata.json is absent — and it IS absent here, because
    dash_leaflet2/metadata.json is a 27 MB build artifact this repo
    gitignores AND excludes from the wheel (DIVERGENCES 15). So /api would
    ship empty on Render while every local check passed, because locally the
    file exists.

    The item asks for a pin that resolves the package into a directory with
    NO metadata.json and asserts components still come back. That is the
    committed-extract road, and this is the shape production actually runs.
    """
    import json
    import sys

    from lib import api_reference

    pkg = tmp_path / "extract_only_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("class Only:\n    pass\n")
    (pkg / api_reference.SLIM_METADATA).write_text(json.dumps({
        "generated": "2026-08-30",
        "components": [{"name": "Only", "description": "d", "props": [
            {"name": "id", "type": "string", "required": False,
             "default": "", "description": "x"}]}],
    }))
    assert not (pkg / "metadata.json").exists(), "the point is its absence"

    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("extract_only_pkg", None)
    try:
        comps = api_reference.load_package("extract_only_pkg")
        assert [c["name"] for c in comps] == ["Only"], comps
        assert api_reference.slim_generated_on("extract_only_pkg") == "2026-08-30"
    finally:
        sys.modules.pop("extract_only_pkg", None)

    # And the negative: a package with NEITHER file yields [] rather than
    # raising — the silent-empty behaviour, pinned so it stays visible.
    bare = tmp_path / "bare_pkg"
    bare.mkdir()
    (bare / "__init__.py").write_text("")
    sys.modules.pop("bare_pkg", None)
    try:
        assert api_reference.load_package("bare_pkg") == []
    finally:
        sys.modules.pop("bare_pkg", None)


def test_this_repo_really_has_no_committed_metadata_json(app_module):
    """The premise of the pin above, asserted rather than assumed: if
    metadata.json were ever committed, the extract road would stop being
    exercised in production and this fork would quietly rejoin the class of
    hosts whose /api works locally and is empty on the wire."""
    import subprocess

    out = subprocess.run(
        ["git", "check-ignore", "dash_leaflet2/metadata.json"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert out.returncode == 0, "dash_leaflet2/metadata.json is no longer gitignored"
    tracked = subprocess.run(
        ["git", "ls-files", "dash_leaflet2/metadata.json"],
        capture_output=True, text=True, cwd=REPO,
    ).stdout.strip()
    assert tracked == "", f"metadata.json is tracked: {tracked!r}"
    assert (REPO / "dash_leaflet2" / "api_metadata.json").is_file(), (
        "the committed extract is missing — /api would be empty in production"
    )
