"""Component prop tables from an installed Dash component package (1.6.38).

A Dash component package ships ``metadata.json`` next to its ``__init__``
(react-docgen output: one entry per component source file with
``displayName`` and ``props`` → ``{type, required, description,
defaultValue}``), and every generated component class carries the same
props in its docstring. ``metadata.json`` is the one machine-readable
source, so this reads it; the classes exist in the package namespace and
are used only to confirm a component is exported. (The drop named
``_prop_names``; Dash 4 no longer sets it on generated classes — the
docstring and metadata.json are what remain.)
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path


def _type_name(t) -> str:
    if not isinstance(t, dict):
        return str(t or "")
    name = t.get("name") or ""
    if name == "enum" and isinstance(t.get("value"), list):
        vals = [str(v.get("value", v)) for v in t["value"]]
        return "one of " + ", ".join(vals[:8]) + (" …" if len(vals) > 8 else "")
    if name == "union" and isinstance(t.get("value"), list):
        return " | ".join(_type_name(v) for v in t["value"])
    if name == "arrayOf":
        return f"list of {_type_name(t.get('value'))}"
    if name in ("shape", "exact"):
        return "dict"
    return name or "any"


def _default(prop) -> str:
    d = prop.get("defaultValue")
    if isinstance(d, dict):
        return str(d.get("value", ""))
    return "" if d is None else str(d)


# THIS FORK'S ONE ADDITION to the template's file, and the reason is a fact
# about this repo the template has no equivalent of: `dash_leaflet2/
# metadata.json` is a 27 MB react-docgen build artifact that is BOTH
# .gitignored (DIVERGENCES 12) and `exclude`d from the wheel (MANIFEST.in) —
# it is a build input, never a runtime file. So on Render, and for anyone who
# `pip install dash-leaflet2`, it is simply absent and /api would render an
# empty page while every local check passed.
#
# `scripts/build_api_metadata.py` distils it to the 64 KB this page actually
# needs and commits THAT. metadata.json still wins when present, so a
# developer who has just re-run `npm run build:backends` sees the new props
# before the slim file is regenerated.
SLIM_METADATA = "api_metadata.json"


def load_package(package: str) -> list[dict]:
    """``[{name, description, props: [{name, type, required, default, description}]}]``
    for every component the package exports, sorted by name. Raises
    ImportError if the package is not installed; returns [] if it ships no
    metadata.json (not a Dash component package)."""
    mod = importlib.import_module(package)
    pkg_dir = Path(mod.__file__).resolve().parent
    meta_path = pkg_dir / "metadata.json"
    if not meta_path.is_file():
        slim = pkg_dir / SLIM_METADATA
        if slim.is_file():
            # Already in this function's OUTPUT shape — nothing left to do.
            return json.loads(slim.read_text(encoding="utf-8"))["components"]
        return []
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    out = []
    for entry in meta.values():
        name = entry.get("displayName") or ""
        if not name or not hasattr(mod, name):
            continue
        props = []
        for pname, p in (entry.get("props") or {}).items():
            if pname in ("setProps", "loading_state"):
                continue
            props.append({
                "name": pname,
                "type": _type_name(p.get("type") or p.get("flowType") or p.get("tsType")),
                "required": bool(p.get("required")),
                "default": _default(p),
                "description": (p.get("description") or "").strip(),
            })
        props.sort(key=lambda p: (p["name"] != "id", p["name"]))
        out.append({"name": name, "description": (entry.get("description") or "").strip(), "props": props})
    out.sort(key=lambda c: c["name"])
    return out


def load_packages(packages) -> list[dict]:
    """Every package's components, in declaration order; a missing package
    is reported as one entry with an ``error`` rather than raising — the
    page must render on a host whose extra is not installed."""
    out = []
    for pkg in packages:
        try:
            out.append({"package": pkg, "components": load_package(pkg)})
        except Exception as exc:  # noqa: BLE001
            out.append({"package": pkg, "components": [], "error": f"{type(exc).__name__}: {exc}"})
    return out


def as_markdown(packages) -> str:
    """The same tables as Markdown — the page's LLMS_DOC."""
    lines = ["# API reference", ""]
    for pkg in load_packages(packages):
        lines += [f"## {pkg['package']}", ""]
        if pkg.get("error"):
            lines += [f"_not installed: {pkg['error']}_", ""]
        for c in pkg["components"]:
            lines += [f"### {c['name']}", ""]
            if c["description"]:
                lines += [c["description"], ""]
            lines += ["| prop | type | default | description |", "|---|---|---|---|"]
            for p in c["props"]:
                desc = p["description"].replace("\n", " ").replace("|", "\\|")
                lines.append(f"| `{p['name']}`{' *' if p['required'] else ''} | {p['type']} | {p['default']} | {desc} |")
            lines.append("")
    return "\n".join(lines)


def slim_generated_on(package: str) -> str | None:
    """The date `scripts/build_api_metadata.py` last regenerated the committed
    props extract, or None.

    This is /api's `lastmod`, and it is honest for the same reason a docs
    page's frontmatter date is: it changes exactly when the CONTENT changes,
    because the script that writes it is what regenerates the content — and
    it is committed, so a Docker rebuild cannot reset it the way an mtime
    would. (The template registers /api with no lastmod; this repo's
    tests/test_seo_icons.py fails a sitemap entry without one.)
    """
    try:
        mod = importlib.import_module(package)
        slim = Path(mod.__file__).resolve().parent / SLIM_METADATA
        return json.loads(slim.read_text(encoding="utf-8")).get("generated")
    except Exception:
        return None
