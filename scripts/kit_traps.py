#!/usr/bin/env python3
"""Count the fleet-class traps in a `.claude/CLAUDE.md` traps section.

1.6.44 item 14. A fork's traps section can sit fifteen entries behind the
template's — 7 against 22 on emojimart, whose HEAD trap still carried the
diagnosis 1.6.32 had corrected. The kit is contract-class, so no sync ever
copies it, and until this script nothing printed the gap.

ADAPTED FOR A FORK, and the adaptation is the whole point of shipping it here.
The template's copy resolves its reference kit as `REPO_ROOT/.claude/CLAUDE.md`
— which on the template IS the reference. Run unchanged in a fork, that
compares this repo's kit against ITSELF and reports a perfect score forever,
which is worse than not having the script. So the reference is resolved
separately:

    1. an explicit second argument, or
    2. $TEMPLATE_KIT, or
    3. the sibling checkout at ../dash-documentation-boilerplate.

If none resolves, the script says so and reports this repo's own count only —
a clone has no template beside it, and a tool that invented a comparison there
would be reporting a number it could not have measured.

Matching is by the first sentence of each entry, lower-cased and squeezed —
NOT by exact text, because a fork is EXPECTED to merge a trap into its own
wording, and adding a host-specific clause must not read as absence. This repo
does exactly that (its HEAD trap carries its own FastAPI measurement), so a
strict check would report this fork's correct adaptations as missing traps and
train it to paste over them — the opposite of what the item asks for.

    python3 scripts/kit_traps.py                  # this repo vs the template
    python3 scripts/kit_traps.py <fork-kit>       # another fork vs the template
    python3 scripts/kit_traps.py <fork> <template>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HEADING = "### Verification traps"
REPO_ROOT = Path(__file__).resolve().parent.parent
OWN_KIT = REPO_ROOT / ".claude" / "CLAUDE.md"

# Where the TEMPLATE's kit lives, from a fork's point of view. Never
# `OWN_KIT` — see the module docstring.
SIBLING_TEMPLATE = REPO_ROOT.parent / "dash-documentation-boilerplate"


def resolve_template(explicit: str | None = None) -> Path | None:
    """The reference kit, or None when this checkout has no template beside it."""
    import os

    for candidate in (explicit, os.getenv("TEMPLATE_KIT")):
        if candidate:
            path = Path(candidate)
            return path if path.is_file() else None
    guess = SIBLING_TEMPLATE / ".claude" / "CLAUDE.md"
    return guess if guess.is_file() else None


def traps_section(text: str) -> str:
    """The traps section, or "" when the file has none."""
    if HEADING not in text:
        return ""
    after = text.split(HEADING, 1)[1]
    # The section runs to the next `## ` heading, or to end of file.
    return re.split(r"^## ", after, maxsplit=1, flags=re.M)[0]


def trap_entries(text: str) -> list[str]:
    """One entry per top-level `- ` bullet, continuation lines folded in."""
    section = traps_section(text)
    entries, current = [], None
    for line in section.splitlines():
        if line.startswith("- "):
            if current is not None:
                entries.append(" ".join(current))
            current = [line[2:].strip()]
        elif current is not None and line.startswith("  "):
            current.append(line.strip())
        elif current is not None and not line.strip():
            continue
    if current is not None:
        entries.append(" ".join(current))
    return entries


def key(entry: str) -> str:
    """A readable identity for printing: the first sentence, normalised."""
    first = re.split(r"(?<=[.:])\s", entry, maxsplit=1)[0]
    first = re.sub(r"[`*_\"']", "", first)
    return re.sub(r"\s+", " ", first).strip().lower()[:60]


def _tokens(entry: str) -> set:
    """Content words of the first sentence, for overlap matching."""
    first = re.split(r"(?<=[.:])\s", entry, maxsplit=1)[0]
    words = re.findall(r"[a-z0-9_./>=-]+", first.lower())
    return {w for w in words if len(w) > 2}


# How much of a template trap's opening sentence a fork entry must share to
# count as the same trap. Deliberately loose: a fork is EXPECTED to merge a
# trap into its own wording and to add host-specific clauses, and a check
# that reported those as absence would train forks to paste over their own
# adaptations — the opposite of what item 14 asks for.
OVERLAP = 0.6


def _present(template_entry: str, fork_entries: list) -> bool:
    wanted = _tokens(template_entry)
    if not wanted:
        return True
    for candidate in fork_entries:
        shared = wanted & _tokens(candidate)
        if len(shared) / len(wanted) >= OVERLAP:
            return True
    return False


def compare(fork_text: str, template_text: str):
    """(fork count, template count, template entries the fork is missing)."""
    fork = trap_entries(fork_text)
    template = trap_entries(template_text)
    missing = [e for e in template if not _present(e, fork)]
    return len(fork), len(template), missing


def main(argv: list[str]) -> int:
    fork_path = Path(argv[1]) if len(argv) > 1 else OWN_KIT
    template_path = resolve_template(argv[2] if len(argv) > 2 else None)

    fork_text = fork_path.read_text()
    if template_path is None:
        count = len(trap_entries(fork_text))
        print(f"{fork_path}: {count} trap entries")
        print("  no template kit to compare against — pass one, set "
              "$TEMPLATE_KIT, or place the template beside this checkout")
        return 0 if count else 1

    fork_n, template_n, missing = compare(fork_text, template_path.read_text())
    print(f"{fork_path}: fork {fork_n} / template {template_n}")
    for entry in missing:
        print(f"  MISSING: {key(entry)}…")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
