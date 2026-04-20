from __future__ import annotations

import importlib
from types import ModuleType

_MATPLOTLIB_IMPORT_ERROR = "Matplotlib is required for pdelie.viz. Install pdelie[viz] or pdelie[test]."


def require_pyplot() -> ModuleType:
    try:
        return importlib.import_module("matplotlib.pyplot")
    except ModuleNotFoundError as exc:
        missing_name = exc.name or ""
        if missing_name == "matplotlib" or missing_name.startswith("matplotlib."):
            raise ImportError(_MATPLOTLIB_IMPORT_ERROR) from exc
        raise


__all__ = ["require_pyplot"]
