"""Bootstrap that runs the smoke suite under a foreign interpreter.

Used by ``compat_matrix.py --local``. The target interpreter supplies **Dash**
(the thing under test); this project's own virtualenv supplies the docs-site
libraries that Dash version does not have installed.

Import order is the whole trick:

1. ``import dash`` FIRST, so it resolves from the target interpreter's own
   ``site-packages`` and lands in ``sys.modules``.
2. Only then append the donor ``site-packages``. Because Dash is already
   imported and cached, nothing appended afterwards can shadow it — and because
   the donor path goes on the END of ``sys.path``, the target's own copies of
   anything else still win.

Env:
    DL2_EXTRA_SITE   donor site-packages directory
    DL2_SMOKE_ARGS   arguments to forward to smoke_test.py, newline-separated
"""
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 1. Pin Dash from the TARGET interpreter before anything else can pull one in.
import dash  # noqa: E402,F401

_resolved = dash.__version__
_origin = Path(dash.__file__).resolve()

# 2. Now lend the target the docs-site libraries it is missing.
extra = os.environ.get("DL2_EXTRA_SITE")
if extra and extra not in sys.path:
    sys.path.append(extra)

# Report what actually got used, so a silently-wrong measurement is visible.
print(f"[runner] dash {_resolved} from {_origin.parent.parent.parent.parent}")
print(f"[runner] donor site-packages: {extra or '(none)'}")

sys.argv = ["smoke_test.py"] + [
    a for a in (os.environ.get("DL2_SMOKE_ARGS") or "").split("\n") if a
]
runpy.run_path(str(ROOT / "scripts" / "smoke_test.py"), run_name="__main__")
