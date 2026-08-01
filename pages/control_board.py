"""/admin/control-board — live page-visibility control board.

A single pane over every docs page registered through ``pages/markdown.py``:
flip a page between public / auth / admin / hidden and toggle whether its
``llms.txt`` is served to anonymous and AI traffic. Changes persist to
``page_visibility.json`` and apply on the next page render — no restart, no
redeploy.

Access: the ``ADMIN_EMAILS`` / ``ADMIN_USER_IDS`` allowlist plus the owner
email (see ``lib.auth.is_admin_user``).

**This page fails CLOSED.** Everything else degrades to public when Clerk is
unavailable — docs must stay readable — but this board can hide any page on the
site, so without Clerk it returns a 404-style response instead. That is the
DEFAULT state: ``dash-clerk-auth`` is not on PyPI and is not a dependency here,
so a stock deploy has no Clerk. Set ``ALLOW_UNGATED_ADMIN=1`` to work on it
locally.
"""
from datetime import datetime

import dash
import dash_mantine_components as dmc
from dash import ALL, Input, Output, callback, ctx, html
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify

from lib.auth import admin_access_open, clerk_enabled, current_user, is_admin_user
from lib.constants import OG_IMAGE_URL, PAGE_TITLE_PREFIX
from lib.page_visibility import (
    TIERS,
    controllable_pages,
    forbidden_layout,
    hidden_layout,
    set_llms_public,
    set_visibility,
    sign_in_layout,
)

dash.register_page(
    __name__,
    path="/admin/control-board",
    name="Control Board",
    title=PAGE_TITLE_PREFIX + "Control Board",
    description="Admin control board for page visibility and llms.txt exposure.",
    # Not for sharing — this page is marked hidden and Disallowed — but Dash
    # emits an empty og:image without it, and "every page" should mean every
    # page. See lib.constants.OG_IMAGE_URL.
    image_url=OG_IMAGE_URL,
)

_TIER_COLORS = {"public": "teal", "auth": "blue", "admin": "grape", "hidden": "gray"}

_TIER_HELP = [
    ("public", "teal", "Anyone — no account needed. The default for this site."),
    ("auth", "blue", "Any signed-in user. The sign-in card on these pages drives account creation."),
    ("admin", "grape", "Only allowlisted accounts. llms.txt for these pages is never served anonymously."),
    ("hidden", "gray", "Nobody — the page and its llms.txt return a 404-style response."),
]


def _stat_card(label, value, color):
    return dmc.Paper(
        dmc.Stack(
            [
                dmc.Text(str(value), size="28px", fw=700, c=color),
                dmc.Text(label, size="xs", c="dimmed", tt="uppercase"),
            ],
            gap=2,
            align="center",
        ),
        withBorder=True,
        radius="md",
        p="md",
        style={"minWidth": "120px"},
    )


def _page_row(path, settings):
    return dmc.TableTr(
        [
            dmc.TableTd(
                dmc.Stack(
                    [
                        dmc.Anchor(settings["name"], href=path, size="sm", fw=600),
                        dmc.Text(path, size="xs", c="dimmed", ff="monospace"),
                    ],
                    gap=0,
                )
            ),
            dmc.TableTd(
                dmc.SegmentedControl(
                    id={"type": "cb-vis", "path": path},
                    value=settings["visibility"],
                    data=[{"value": t, "label": t.capitalize()} for t in TIERS],
                    size="xs",
                    color=_TIER_COLORS.get(settings["visibility"], "blue"),
                )
            ),
            dmc.TableTd(
                dmc.Switch(
                    id={"type": "cb-llms", "path": path},
                    checked=bool(settings["llms_public"]),
                    onLabel="ON",
                    offLabel="OFF",
                    size="md",
                    color="teal",
                ),
                style={"textAlign": "center"},
            ),
            dmc.TableTd(
                dmc.Anchor(
                    DashIconify(icon="tabler:external-link", width=16),
                    href=f"{path.rstrip('/')}/llms.txt",
                    target="_blank",
                ),
                style={"textAlign": "center"},
            ),
        ]
    )


def _build_board():
    pages = controllable_pages()
    counts = {t: 0 for t in TIERS}
    for s in pages.values():
        counts[s["visibility"]] = counts.get(s["visibility"], 0) + 1

    dev_banner = None
    if not clerk_enabled():
        dev_banner = dmc.Alert(
            "Clerk keys are not configured — every tier currently falls open to "
            "public and this board is ungated. Set CLERK_SECRET_KEY / "
            "CLERK_PUBLISHABLE_KEY / CLERK_SIGN_IN_URL / ADMIN_EMAILS in production.",
            title="Dev mode — auth disabled",
            color="yellow",
            icon=DashIconify(icon="tabler:alert-triangle"),
        )

    return dmc.Container(
        dmc.Stack(
            [
                dmc.Group(
                    [
                        DashIconify(
                            icon="tabler:adjustments-bolt",
                            width=34,
                            color="var(--mantine-color-green-5)",
                        ),
                        dmc.Stack(
                            [
                                dmc.Title("Page Control Board", order=2),
                                dmc.Text(
                                    "Toggle who can see each documentation page and "
                                    "whether its llms.txt is served to anonymous / AI "
                                    "traffic. Changes apply immediately; sitemap "
                                    "entries refresh on restart.",
                                    c="dimmed",
                                    size="sm",
                                ),
                            ],
                            gap=2,
                        ),
                    ],
                    gap="md",
                ),
                dev_banner,
                dmc.Group(
                    [
                        _stat_card(t.capitalize(), counts.get(t, 0), c)
                        for t, c, _ in _TIER_HELP
                    ]
                    + [_stat_card("Total", len(pages), "green")],
                    gap="sm",
                ),
                dmc.Accordion(
                    dmc.AccordionItem(
                        [
                            dmc.AccordionControl("What do the tiers mean?"),
                            dmc.AccordionPanel(
                                dmc.Stack(
                                    [
                                        dmc.Group(
                                            [
                                                dmc.Badge(t.capitalize(), color=c, variant="light"),
                                                dmc.Text(desc, size="sm", c="dimmed"),
                                            ],
                                            gap="sm",
                                        )
                                        for t, c, desc in _TIER_HELP
                                    ],
                                    gap="xs",
                                )
                            ),
                        ],
                        value="tiers",
                    ),
                    variant="contained",
                ),
                dmc.Paper(
                    dmc.Table(
                        [
                            dmc.TableThead(
                                dmc.TableTr(
                                    [
                                        dmc.TableTh("Page"),
                                        dmc.TableTh("Visibility"),
                                        dmc.TableTh("llms.txt public", style={"textAlign": "center"}),
                                        dmc.TableTh("llms.txt", style={"textAlign": "center"}),
                                    ]
                                )
                            ),
                            dmc.TableTbody(
                                [_page_row(path, settings) for path, settings in pages.items()]
                            ),
                        ],
                        striped=True,
                        highlightOnHover=True,
                        verticalSpacing="sm",
                    ),
                    withBorder=True,
                    radius="md",
                    p="md",
                ),
                html.Div(id="cb-feedback"),
            ],
            gap="lg",
        ),
        size="lg",
        py="xl",
    )


def layout(**kwargs):
    """Admin-gated at render time; ``**kwargs`` absorbs Clerk handshake params."""
    if clerk_enabled():
        user = current_user()
        if user is None:
            return sign_in_layout("Control Board")
        if not is_admin_user(user):
            return forbidden_layout("Control Board")
    elif not admin_access_open():
        # Fail CLOSED. Everything else in this app degrades to public without
        # Clerk, because docs must stay readable — but this board can hide any
        # page on the site, so an ungated deploy would hand that to anyone who
        # guesses the URL. `dash-clerk-auth` is not a dependency (not on PyPI),
        # so this is the DEFAULT state, not an edge case.
        # ALLOW_UNGATED_ADMIN=1 to work on the board locally.
        return hidden_layout()
    return _build_board()


@callback(
    Output("cb-feedback", "children"),
    Input({"type": "cb-vis", "path": ALL}, "value"),
    Input({"type": "cb-llms", "path": ALL}, "checked"),
    prevent_initial_call=True,
)
def save_visibility_change(_vis_values, _llms_values):
    """Persist whichever toggle fired to page_visibility.json."""
    trig = ctx.triggered_id
    if not isinstance(trig, dict):
        raise PreventUpdate
    # Server-side re-check, and the half that actually matters: a 404 layout
    # only hides the UI. Pattern-matching callbacks stay callable by anyone who
    # can POST to /_dash-update-component with a reconstructed component id, so
    # the same gate has to run here or the board is still writable.
    if clerk_enabled():
        if not is_admin_user():
            raise PreventUpdate
    elif not admin_access_open():
        raise PreventUpdate

    path = trig["path"]
    new_value = ctx.triggered[0]["value"]
    if trig["type"] == "cb-vis":
        set_visibility(path, new_value)
        message = f"{path} → visibility: {new_value}"
    else:
        set_llms_public(path, bool(new_value))
        message = f"{path} → llms.txt public: {'on' if new_value else 'off'}"

    return dmc.Alert(
        f"Saved {message}  ·  {datetime.now().strftime('%H:%M:%S')}",
        color="teal",
        variant="light",
        icon=DashIconify(icon="tabler:device-floppy"),
        withCloseButton=True,
    )
