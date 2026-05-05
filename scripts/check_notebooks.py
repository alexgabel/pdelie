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


def _code_cells(notebook: dict[str, object]) -> list[dict[str, object]]:
    cells = notebook.get("cells", [])
    if not isinstance(cells, list):
        raise AssertionError("notebook cells must be a list")
    return [
        cell
        for cell in cells
        if isinstance(cell, dict) and cell.get("cell_type") == "code"
    ]


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

        code_cells = _code_cells(notebook)
        if not code_cells:
            failures.append(f"{path}: missing code cells")
            continue
        unexecuted = [
            index
            for index, cell in enumerate(code_cells)
            if cell.get("execution_count") is None
        ]
        if unexecuted:
            failures.append(f"{path}: code cells without execution counts: {unexecuted}")
        output_count = 0
        error_cells: list[int] = []
        for index, cell in enumerate(code_cells):
            outputs = cell.get("outputs", [])
            if not isinstance(outputs, list):
                failures.append(f"{path}: code cell {index} outputs must be a list")
                continue
            output_count += len(outputs)
            if any(isinstance(output, dict) and output.get("output_type") == "error" for output in outputs):
                error_cells.append(index)
        if output_count == 0:
            failures.append(f"{path}: missing saved cell outputs for GitHub rendering")
        if error_cells:
            failures.append(f"{path}: saved error outputs in code cells: {error_cells}")

    if failures:
        print("\n".join(failures))
        raise SystemExit(1)

    print(f"validated {len(notebooks)} notebooks")


if __name__ == "__main__":
    main()
