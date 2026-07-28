"""
Backend selection helper for the Dash documentation boilerplate.

Dash **4.2+** supports pluggable backends:
    app = Dash(backend="flask"  | "fastapi" | "quart")

NOTE the floor. Dash's own notes suggest 4.1, but `Dash.__init__` in 4.1.0 has
no `backend` parameter at all and raises TypeError — verified against two
separate 4.1.0 installs by scripts/compat_matrix.py. `run.py` catches that and
falls back to the bundled Flask backend, so the site still boots on 4.1.

This module owns the single source of truth for which backend the app is
running on, so both `run.py` and UI components (e.g. the navbar badge) stay
in sync.

Backend is selected via the ``DASH_BACKEND`` environment variable. Falls back
to ``flask`` if unset or invalid.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BackendName = Literal["flask", "fastapi", "quart"]

SUPPORTED_BACKENDS: tuple[BackendName, ...] = ("flask", "fastapi", "quart")
DEFAULT_BACKEND: BackendName = "flask"


@dataclass(frozen=True)
class BackendInfo:
    name: BackendName
    label: str
    color: str          # DMC color name
    icon: str           # iconify icon id
    description: str
    is_async: bool


_BACKEND_INFO: dict[str, BackendInfo] = {
    "flask": BackendInfo(
        name="flask",
        label="Flask",
        color="gray",
        icon="simple-icons:flask",
        description="WSGI backend. Default. Full feature parity with Dash 3.x.",
        is_async=False,
    ),
    "fastapi": BackendInfo(
        name="fastapi",
        label="FastAPI",
        color="teal",
        icon="simple-icons:fastapi",
        description="ASGI backend. Adds websocket callbacks, async support and MCP-friendly transport.",
        is_async=True,
    ),
    "quart": BackendInfo(
        name="quart",
        label="Quart",
        color="violet",
        icon="simple-icons:python",
        description="ASGI backend with a Flask-compatible API surface.",
        is_async=True,
    ),
}


def resolve_backend(name: str | None = None) -> BackendName:
    """Resolve the backend to use.

    Reads ``DASH_BACKEND`` env var when ``name`` is not given. Unknown values
    fall back to the default backend rather than raising — the docs site
    should always boot.
    """
    raw = (name or os.environ.get("DASH_BACKEND") or DEFAULT_BACKEND).strip().lower()
    if raw not in SUPPORTED_BACKENDS:
        return DEFAULT_BACKEND
    return raw  # type: ignore[return-value]


def get_backend_info(name: str | None = None) -> BackendInfo:
    return _BACKEND_INFO[resolve_backend(name)]
