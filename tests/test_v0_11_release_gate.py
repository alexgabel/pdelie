from __future__ import annotations

import importlib
import re
from pathlib import Path

import numpy as np

import pdelie
from pdelie.data import generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from tests._helpers.ks_vertical_slice import cached_ks_vertical_slice_summary


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def test_v0_11_release_gate_order4_derivative_api_is_public_and_documented() -> None:
    derivatives_module = importlib.import_module("pdelie.derivatives")
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=11011)

    assert hasattr(derivatives_module, "compute_spectral_fd_derivatives")
    assert not hasattr(pdelie, "compute_spectral_fd_derivatives")

    default = compute_spectral_fd_derivatives(field)
    order4 = compute_spectral_fd_derivatives(field, max_spatial_order=4)

    assert set(default.derivatives) == {"u_t", "u_x", "u_xx"}
    assert "spatial_max_order" not in default.config
    assert set(order4.derivatives) == {"u_t", "u_x", "u_xx", "u_xxx", "u_xxxx"}
    assert order4.config["spatial_max_order"] == 4
    assert np.all(np.isfinite(order4.derivatives["u_xxxx"]))

    assert "pdelie.derivatives.compute_spectral_fd_derivatives(field, *, max_spatial_order=4)" in api_stability
    assert "this derivative extension does not add a stable public Kuramoto-Sivashinsky data generator or residual evaluator" in api_stability
    assert "pdelie.data.generate_ks_1d_field_batch" not in api_stability
    assert "pdelie.residuals.KSResidualEvaluator" not in api_stability


def test_v0_11_release_gate_no_public_ks_runtime_surface() -> None:
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")
    examples_module = importlib.import_module("pdelie.examples")
    forbidden_names = {
        "generate_ks_1d_field_batch",
        "generate_ks_feasibility_field_batch",
        "KSResidualEvaluator",
        "KuramotoSivashinskyResidualEvaluator",
        "run_ks_vertical_slice_example",
        "evaluate_weak_ks_residual",
        "evaluate_weak_kuramoto_sivashinsky_residual",
        "WeakKSResidualEvaluator",
    }

    for module in [pdelie, data_module, residuals_module, examples_module]:
        for name in sorted(forbidden_names):
            assert not hasattr(module, name), f"{module.__name__}.{name}"


def test_v0_11_release_gate_ks_closeout_remains_reference_fallback_no_go() -> None:
    summary = cached_ks_vertical_slice_summary()

    assert summary["evidence_label"] == "reference_fallback"
    assert summary["reference_fallback_used"] is True
    assert isinstance(summary["fallback_reason"], str)
    assert summary["fallback_reason"]
    assert summary["selected_span_distance"] <= 1e-1
    assert summary["svd_span_distance"] is not None
    assert summary["svd_span_distance"] > 1e-1
    assert summary["classification"] != "failed"


def test_v0_11_release_gate_metadata_docs_and_ci_are_aligned() -> None:
    workflow = _repo_text(".github/workflows/ci.yml")
    readiness = _repo_text("docs/releases/V0_11_RELEASE_READINESS.md")
    readme = _repo_text("README.md")
    changelog = _repo_text("CHANGELOG.md")
    publishing = _repo_text("docs/releases/PUBLISHING.md")
    release_gate_jobs = re.findall(r"^  (v0_\d+-release-gate):", workflow, flags=re.MULTILINE)

    assert release_gate_jobs == ["v0_16-release-gate"]
    assert "python -m pytest tests/test_v0_16_release_gate.py" in workflow

    assert "## 0.11.0" in changelog
    assert "V0.16" in readme
    assert "stable KS runtime" in readme
    assert "package version: `0.11.0`" in readiness
    assert "git tag: `v0.11.0`" in readiness
    assert "no-go/defer" in readiness
    assert "Do not run TestPyPI or PyPI publishing for `v0.11`" in readiness
    assert "including `v0.16.0`" in publishing
