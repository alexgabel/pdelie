from __future__ import annotations

import importlib
import json
import re
import tomllib
from copy import deepcopy
from pathlib import Path

import numpy as np
import xarray as xr

import pdelie
from pdelie.data import from_xarray, from_xarray_dataset, generate_heat_1d_field_batch
from pdelie.examples import run_data_ecosystem_feasibility_example
from pdelie.reporting import summarize_field_batch_readiness, summarize_xarray_dataset_readiness


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def _heat_dataset():
    source = generate_heat_1d_field_batch(batch_size=1, num_times=9, num_points=16, seed=28028)
    metadata = deepcopy(source.metadata)
    metadata["parameter_tags"]["equation"] = "heat_1d"
    dataset = xr.Dataset(
        {"u": (source.dims, source.values)},
        coords={"time": source.coords["time"], "x": source.coords["x"]},
        attrs={"source": "v0.28-release-gate"},
    )
    return source, dataset, metadata


def test_v0_28_release_gate_metadata_docs_and_ci_are_aligned() -> None:
    pyproject = tomllib.loads(_repo_text("pyproject.toml"))
    workflow = _repo_text(".github/workflows/ci.yml")
    readiness = _repo_text("docs/releases/V0_28_RELEASE_READINESS.md")
    readme = _repo_text("README.md")
    changelog = _repo_text("CHANGELOG.md")
    publishing = _repo_text("docs/releases/PUBLISHING.md")
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_28_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    release_gate_jobs = re.findall(r"^  (v0_\d+-release-gate):", workflow, flags=re.MULTILINE)

    assert pyproject["project"]["version"] == "0.28.0"
    assert release_gate_jobs == ["v0_28-release-gate"]
    assert "python -m pytest tests/test_v0_28_release_gate.py" in workflow
    assert "docs-build:" in workflow
    assert "sphinx-build -b html -W --keep-going docs docs/_build/html" in workflow
    assert 'pdelie[xarray] @ ${wheel_uri}' in workflow
    assert "python -m pdelie.examples.data_ecosystem_feasibility" in workflow
    assert "v0_27-release-gate" not in workflow

    assert "## 0.28.0" in changelog
    assert "V0.28" in readme
    assert "narrow data-ecosystem feasibility release" in readme
    assert "package version: `0.28.0`" in readiness
    assert "git tag: `v0.28.0`" in readiness
    assert "Do not publish to TestPyPI or PyPI for `v0.28.0`" in readiness
    assert "including `v0.28.0`" in publishing
    assert "Milestone 6: COMPLETE" in plan
    assert "Milestone 6: COMPLETE" in scope
    assert "`v0.28` - Narrow xarray Dataset ingestion" in roadmap


def test_v0_28_release_gate_dataset_conversion_and_readiness_are_stable() -> None:
    _source, dataset, metadata = _heat_dataset()

    dataset_readiness = summarize_xarray_dataset_readiness(
        dataset,
        metadata=metadata,
        expected_equation="heat_1d",
    )
    imported = from_xarray_dataset(dataset, metadata=metadata)
    direct = from_xarray(dataset["u"], var_name="u", metadata=metadata)
    field_readiness = summarize_field_batch_readiness(imported, expected_equation="heat_1d")

    assert json.loads(json.dumps(dataset_readiness, allow_nan=False)) == dataset_readiness
    assert dataset_readiness["summary_type"] == "xarray_dataset_readiness"
    assert dataset_readiness["readiness_label"] == "ready"
    assert dataset_readiness["selected_data_var"] == "u"
    assert dataset_readiness["conversion_preflight"]["field_readiness"]["summary_type"] == "field_batch_readiness"
    assert field_readiness["readiness_label"] == "ready"
    np.testing.assert_allclose(imported.values, direct.values)
    np.testing.assert_allclose(imported.coords["time"], direct.coords["time"])
    np.testing.assert_allclose(imported.coords["x"], direct.coords["x"])
    assert imported.dims == direct.dims
    assert imported.var_names == direct.var_names
    assert imported.metadata == direct.metadata
    assert imported.preprocess_log[-2]["operation"] == "from_xarray_dataset"
    assert imported.preprocess_log[-1]["operation"] == "from_xarray"


def test_v0_28_release_gate_example_records_data_ecosystem_decision() -> None:
    result = run_data_ecosystem_feasibility_example()

    assert json.loads(json.dumps(result, allow_nan=False)) == result
    assert result["summary_type"] == "data_ecosystem_feasibility_example"
    assert result["release_decision"] == "xarray_dataset_scalar_slice_supported_file_loaders_deferred"
    assert result["dataset_readiness"]["summary_type"] == "xarray_dataset_readiness"
    assert result["dataset_readiness"]["readiness_label"] == "ready"
    assert result["field_readiness"]["summary_type"] == "field_batch_readiness"
    assert result["field_readiness"]["readiness_label"] == "ready"
    assert result["deferred_scope"]["file_loaders"] is False
    assert result["deferred_scope"]["metadata_inference_engine"] is False


def test_v0_28_release_gate_new_api_is_submodule_only_and_deferred_surfaces_absent() -> None:
    data_module = importlib.import_module("pdelie.data")
    reporting_module = importlib.import_module("pdelie.reporting")
    examples_module = importlib.import_module("pdelie.examples")

    assert hasattr(data_module, "from_xarray_dataset")
    assert hasattr(reporting_module, "summarize_xarray_dataset_readiness")
    assert hasattr(examples_module, "run_data_ecosystem_feasibility_example")

    for name in [
        "from_xarray_dataset",
        "summarize_xarray_dataset_readiness",
        "run_data_ecosystem_feasibility_example",
        "load_field_batch",
        "from_netcdf",
        "from_zarr",
        "from_pdebench",
        "from_the_well",
        "register_dataset_adapter",
        "infer_field_metadata",
        "resample_field_batch",
    ]:
        assert not hasattr(pdelie, name), name
    for name in [
        "load_field_batch",
        "from_netcdf",
        "from_zarr",
        "from_pdebench",
        "from_the_well",
        "register_dataset_adapter",
        "infer_field_metadata",
        "resample_field_batch",
    ]:
        assert not hasattr(data_module, name), name
