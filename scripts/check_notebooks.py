from __future__ import annotations

import json
from pathlib import Path


NOTEBOOK_DIR = Path(__file__).resolve().parents[1] / "notebooks"
REQUIRED_PHRASES = (
    "What you will learn",
    "Required extras",
    "Expected runtime",
)
REQUIRED_SCOPE_PHRASES = ("Out of scope", "Limitations")
STALE_MARKERS = ("v0.17 quickstart", "tutorial-v0.17")


def _cell_source(cell: dict[str, object]) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(str(item) for item in source)
    return str(source)


def _markdown_text(notebook: dict[str, object]) -> str:
    cells = notebook.get("cells", [])
    if not isinstance(cells, list):
        raise AssertionError("notebook cells must be a list")
    return "\n".join(
        _cell_source(cell)
        for cell in cells
        if isinstance(cell, dict) and cell.get("cell_type") == "markdown"
    )


def _first_markdown_title(notebook: dict[str, object]) -> str | None:
    cells = notebook.get("cells", [])
    if not isinstance(cells, list):
        raise AssertionError("notebook cells must be a list")
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("cell_type") != "markdown":
            continue
        for line in _cell_source(cell).splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return None


def main() -> None:
    failures: list[str] = []
    notebooks = sorted(NOTEBOOK_DIR.glob("*.ipynb"))
    if not notebooks:
        raise SystemExit("no notebooks found")

    for path in notebooks:
        try:
            notebook = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path}: invalid JSON: {exc}")
            continue

        title = _first_markdown_title(notebook)
        if not title:
            failures.append(f"{path}: missing top-level markdown title")

        text = _markdown_text(notebook)
        for phrase in REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"{path}: missing '{phrase}'")
        if not any(phrase in text for phrase in REQUIRED_SCOPE_PHRASES):
            failures.append(f"{path}: missing 'Out of scope' or 'Limitations'")
        if "V0.28" not in text and "v0.28" not in text:
            failures.append(f"{path}: should mention current V0.28 surface")
        for marker in STALE_MARKERS:
            if marker in text:
                failures.append(f"{path}: stale marker '{marker}'")

    if failures:
        print("\n".join(failures))
        raise SystemExit(1)

    print(f"validated {len(notebooks)} notebooks")


if __name__ == "__main__":
    main()
