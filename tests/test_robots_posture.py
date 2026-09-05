"""1.6.44 item 19 — the served robots.txt against the one this app WROTE.

From the 2plot.dev proxy canary. An edge can inject, rewrite or replace
robots.txt in perfectly valid syntax with no tell beyond a comment marker: a
grep for `User-agent:` sails straight past it, and so does a status check,
because the file is served 200 either way.

So the check is a DIFF, not a shape test. To learn what the APP declares you
generate it in process; to learn what the WORLD is told you fetch it; and when
they differ, the difference is the finding.

The app's side comes from the PACKAGE's own `generate_robots_txt` with the
app's registered `RobotsConfig` — never a reimplementation, which would compare
the edge against this file's beliefs about the config instead of against the
app.
"""

from __future__ import annotations

import pathlib
import re
import sys

import yaml

from conftest import BASE

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))


def _directives(text):
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line and ":" in line:
            name, _, value = line.partition(":")
            out.append((name.strip().lower(), value.strip()))
    return out


# --------------------------------------------------------------------------
# The app's side.
# --------------------------------------------------------------------------

def test_the_app_generates_a_non_empty_robots(app_module):
    """Note 88 first: an empty generated side makes every diff below vacuous,
    and `ai_bot_posture` would SKIP rather than pass — which is the correct
    behaviour and also the one that hides a real problem."""
    from lib.robots_expected import expected_directives

    generated = expected_directives()
    assert len(generated) >= 5, f"only {len(generated)} directives generated"


def test_it_is_generated_through_the_packages_own_function(app_module):
    """Not a reimplementation."""
    source = (REPO / "lib" / "robots_expected.py").read_text()
    assert "generate_robots_txt" in source
    assert "_robots_config" in source, (
        "the app's registered RobotsConfig is not what is being rendered"
    )


def test_it_reuses_an_already_imported_app(app_module):
    """`import run` in a process that already imported it boots a SECOND app —
    every page re-parsed, every callback re-registered."""
    source = (REPO / "lib" / "robots_expected.py").read_text()
    assert 'sys.modules.get("run")' in source
    assert 'sys.modules.get("runmod")' in source


# --------------------------------------------------------------------------
# The battery row, and BOTH tamper shapes the acceptance names.
# --------------------------------------------------------------------------

def test_ai_bot_posture_is_registered_by_name(wired, capsys):
    wired.satellite_checks(BASE)
    capsys.readouterr()

    names = {name for name, _, _ in wired._RESULTS}
    assert "ai_bot_posture" in names, sorted(names)


def test_it_passes_against_the_untampered_app(wired, capsys):
    """The control. Both tamper tests below are worthless if the clean case
    does not pass — a row that always fails proves nothing about tampering."""
    wired.satellite_checks(BASE)
    capsys.readouterr()

    verdicts = {name: v for name, v, _ in wired._RESULTS}
    assert verdicts["ai_bot_posture"] == wired.PASS, (
        f"ai_bot_posture is {verdicts['ai_bot_posture']} on an untampered "
        "host — the comparison is broken, not the robots.txt"
    )


def _tampered_run(wired, monkeypatch, capsys, transform):
    """Run the battery with the SERVED robots.txt passed through `transform`."""
    original = wired.fetch_raw

    def fetch_raw(url, *args, **kwargs):
        status, headers, body = original(url, *args, **kwargs)
        if url.endswith("/robots.txt"):
            body = transform(body.decode()).encode()
        return status, headers, body

    monkeypatch.setattr(wired, "fetch_raw", fetch_raw)
    wired.satellite_checks(BASE)
    capsys.readouterr()
    return {name: (v, d) for name, v, d in wired._RESULTS}["ai_bot_posture"]


def test_an_injected_stanza_reads_RED(wired, monkeypatch, capsys):
    """SHAPE ONE: the edge ADDS a directive the app never wrote.

    Perfectly valid syntax, served 200. This is the shape a "security" default
    produces, and the one a status sweep cannot see.
    """
    verdict, detail = _tampered_run(
        wired, monkeypatch, capsys,
        lambda text: text + "\nUser-agent: GPTBot\nDisallow: /\n",
    )

    assert verdict == wired.FAIL, (
        f"an injected `Disallow: /` for GPTBot passed as {verdict}"
    )
    assert "did not generate" in detail, detail


def test_a_marker_with_nothing_under_it_reads_RED(wired, monkeypatch, capsys):
    """SHAPE TWO, which the acceptance names separately and which is subtler:
    a managed-block MARKER with no directives beneath it.

    Nothing was added and nothing removed, so a directive-only diff is clean —
    but the marker means something else owns this file now, and whatever it
    injects next will not be noticed. The comment itself is the finding.
    """
    verdict, detail = _tampered_run(
        wired, monkeypatch, capsys,
        lambda text: text + "\n# BEGIN Managed by the edge\n# END\n",
    )

    assert verdict == wired.FAIL, (
        f"an edge marker with an empty block passed as {verdict} — a "
        "directive-only diff cannot see this"
    )
    assert "marker" in detail, detail


def test_a_REMOVED_directive_reads_RED(wired, monkeypatch, capsys):
    """The third shape, and the one an added-only comparison misses entirely.

    Dropping this host's `Allow:` rules for AI search agents is the change
    most likely to be made on somebody's behalf, and it leaves a file that
    looks perfectly ordinary.
    """
    def drop_an_allow(text):
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("allow:"):
                del lines[i]
                break
        return "\n".join(lines)

    verdict, detail = _tampered_run(wired, monkeypatch, capsys, drop_an_allow)

    assert verdict == wired.FAIL, (
        f"a REMOVED directive passed as {verdict} — the comparison is "
        "one-directional"
    )
    assert "NOT served" in detail, detail


def test_it_skips_rather_than_passes_when_the_app_cannot_be_generated(
    wired, monkeypatch, capsys
):
    """A comparison with only one side is not a comparison.

    SKIP is the honest verdict — and the reason cd.yml's verify job must
    install the app, or this row skips forever and reads green.
    """
    import lib.robots_expected as expected

    def boom():
        raise RuntimeError("no checkout here")

    monkeypatch.setattr(expected, "expected_directives", boom)
    verdict, detail = _tampered_run(wired, monkeypatch, capsys, lambda t: t)

    assert verdict == wired.SKIP, verdict
    assert "cannot generate" in detail, detail


# --------------------------------------------------------------------------
# Rider 5: the CD job that makes the row possible.
# --------------------------------------------------------------------------

def test_the_cd_verify_job_installs_the_app():
    """Without this, `ai_bot_posture` SKIPS on every deploy and the battery
    reports green having compared nothing — in the ONE job where a real proxy
    sits in the path. CI's battery runs against a bare container and can never
    see an injected block, so this is not a duplicate of CI's install."""
    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "cd.yml").read_text())
    verify = next(
        job for name, job in workflow["jobs"].items()
        if "verify" in name or "verify" in str(job.get("name", ""))
    )
    scripts = "\n".join(step.get("run", "") for step in verify["steps"])

    assert "pip install -r requirements.txt" in scripts, (
        "cd.yml's verify job does not install the app — ai_bot_posture will "
        "skip forever and read green"
    )
    assert "network_smoke" in scripts, "the verify job does not run the battery"


def test_the_trap_is_in_the_kit():
    kit = re.sub(r"\s+", " ", (REPO / ".claude" / "CLAUDE.md").read_text()).lower()
    assert "a proxied robots.txt is not your robots.txt" in kit
