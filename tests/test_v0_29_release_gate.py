from __future__ import annotations

import importlib
import json
from pathlib import Path

import pdelie


EXPECTED_COLUMNS = [
    "pde",
    "generator",
    "residual",
    "vertical_slice",
    "candidate_validation",
    "weak_support",
    "external_data_readiness",
]
EXPECTED_ROWS = [
    {
        "pde": "Heat",
        "generator": "yes",
        "residual": "yes",
        "vertical_slice": "yes",
        "candidate_validation": "yes",
        "weak_support": "frozen weak slice",
        "external_data_readiness": "yes",
    },
    {
        "pde": "Burgers",
        "generator": "yes",
        "residual": "yes",
        "vertical_slice": "yes",
        "candidate_validation": "yes",
        "weak_support": "frozen weak slice",
        "external_data_readiness": "yes",
    },
    {
        "pde": "KdV",
        "generator": "normalized short-horizon only",
        "residual": "yes",
        "vertical_slice": "yes",
        "candidate_validation": "yes",
        "weak_support": "no",
        "external_data_readiness": "yes",
    },
    {
        "pde": "Fisher-KPP",
        "generator": "yes",
        "residual": "yes",
        "vertical_slice": "yes",
        "candidate_validation": "yes",
        "weak_support": "internal weak diagnostic only",
        "external_data_readiness": "yes",
    },
    {
        "pde": "Advection-diffusion",
        "generator": "yes",
        "residual": "yes",
        "vertical_slice": "yes",
        "candidate_validation": "yes",
        "weak_support": "no",
        "external_data_readiness": "yes",
    },
    {
        "pde": "KS",
        "generator": "no public runtime",
        "residual": "no",
        "vertical_slice": "no",
        "candidate_validation": "diagnostic/no-go",
        "weak_support": "no",
        "external_data_readiness": "no",
    },
]


def _repo_path(path: str) -> Path:
    return Path(__file__).resolve().parents[1] / path


def _repo_text(path: str) -> str:
    return _repo_path(path).read_text(encoding="utf-8")


def _repo_json(path: str) -> dict[str, object]:
    return json.loads(_repo_text(path))


def test_v0_29_release_gate_support_matrix_is_exact_and_json_compatible() -> None:
    matrix = _repo_json("docs/specs/support_matrix.v0_29.json")
    markdown = _repo_text("docs/specs/SUPPORT_MATRIX.md")

    assert json.loads(json.dumps(matrix, allow_nan=False)) == matrix
    assert matrix["summary_schema_version"] == "0.1"
    assert matrix["summary_type"] == "pdelie_support_matrix"
    assert matrix["release"] == "0.29.0"
    assert matrix["release_decision"] == "workflow_recipes_and_support_matrix_complete_no_new_numerical_scope"
    assert matrix["columns"] == EXPECTED_COLUMNS
    assert matrix["pdes"] == EXPECTED_ROWS

    assert "support_matrix.v0_29.json" in markdown
    for row in EXPECTED_ROWS:
        markdown_row = (
            f"| {row['pde']} | {row['generator']} | {row['residual']} | "
            f"{row['vertical_slice']} | {row['candidate_validation']} | "
            f"{row['weak_support']} | {row['external_data_readiness']} |"
        )
        assert markdown_row in markdown


def test_v0_29_release_gate_workflow_docs_are_in_sphinx_navigation() -> None:
    docs_index = _repo_text("docs/index.rst")
    workflows_index = _repo_text("docs/workflows/index.rst")
    tutorials_index = _repo_text("docs/tutorials/index.rst")

    assert "workflows/index" in docs_index
    for page in [
        "data_readiness",
        "candidate_validation",
        "downstream_export_provenance",
        "end_to_end_dataset_to_downstream",
        "candidate_to_split_provenance",
    ]:
        assert page in workflows_index
        text = _repo_text(f"docs/workflows/{page}.md")
        assert "V0.29" in text or "v0.29" in text
        assert "new runtime API" not in text

    assert "12_dataset_to_downstream_workflow" in tutorials_index
    assert "13_candidate_to_split_provenance_workflow" in tutorials_index
    assert "../../notebooks/12_dataset_to_downstream_workflow.ipynb" in _repo_text(
        "docs/tutorials/12_dataset_to_downstream_workflow.nblink"
    )
    assert "../../notebooks/13_candidate_to_split_provenance_workflow.ipynb" in _repo_text(
        "docs/tutorials/13_candidate_to_split_provenance_workflow.nblink"
    )


def test_v0_29_release_gate_new_notebooks_are_rendered_and_tutorial_like() -> None:
    for notebook_path in [
        "notebooks/12_dataset_to_downstream_workflow.ipynb",
        "notebooks/13_candidate_to_split_provenance_workflow.ipynb",
    ]:
        notebook = _repo_json(notebook_path)
        cells = notebook["cells"]
        markdown = "\n".join(
            "".join(cell.get("source", []))
            for cell in cells
            if cell.get("cell_type") == "markdown"
        )
        code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
        output_count = sum(len(cell.get("outputs", [])) for cell in code_cells)

        assert "V0.29" in markdown
        assert "What you will learn" in markdown
        assert "Required extras" in markdown
        assert "Expected runtime" in markdown
        assert "Limitations" in markdown or "Out of scope" in markdown
        assert code_cells
        assert all(cell.get("execution_count") is not None for cell in code_cells)
        assert output_count > 0


def test_v0_29_release_gate_no_new_runtime_api_or_numerical_scope_landed() -> None:
    reporting_module = importlib.import_module("pdelie.reporting")
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")

    forbidden = {
        "summarize_workflow_readiness",
        "load_field_batch",
        "from_netcdf",
        "from_zarr",
        "from_pdebench",
        "from_the_well",
        "register_dataset_adapter",
        "infer_field_metadata",
        "resample_field_batch",
        "generate_ks_1d_field_batch",
        "KSResidualEvaluator",
        "KuramotoSivashinskyResidualEvaluator",
        "fit_multi_generator_family",
        "MultiGeneratorInvariantChart",
    }
    for name in sorted(forbidden):
        assert not hasattr(pdelie, name), name
        assert not hasattr(reporting_module, name), f"pdelie.reporting.{name}"
        assert not hasattr(data_module, name), f"pdelie.data.{name}"
        assert not hasattr(residuals_module, name), f"pdelie.residuals.{name}"
