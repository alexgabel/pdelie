from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import pdelie
from pdelie.data import generate_reaction_diffusion_1d_field_batch, split_batch_train_heldout
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.examples import run_reaction_diffusion_vertical_slice_example
from pdelie.residuals import ReactionDiffusionResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def test_v0_18_release_gate_metadata_docs_and_ci_are_aligned() -> None:
    pyproject = tomllib.loads(_repo_text("pyproject.toml"))
    workflow = _repo_text(".github/workflows/ci.yml")
    readiness = _repo_text("docs/releases/V0_23_RELEASE_READINESS.md")
    readme = _repo_text("README.md")
    changelog = _repo_text("CHANGELOG.md")
    publishing = _repo_text("docs/releases/PUBLISHING.md")
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_18_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    release_gate_jobs = re.findall(r"^  (v0_\d+-release-gate):", workflow, flags=re.MULTILINE)

    assert pyproject["project"]["version"] == "0.23.0"
    assert release_gate_jobs == ["v0_23-release-gate"]
    assert "python -m pytest tests/test_v0_23_release_gate.py" in workflow
    assert "v0_17-release-gate" not in workflow

    assert "## 0.23.0" in changelog
    assert "V0.23" in readme
    assert "reaction_diffusion_fisher_kpp" in readme
    assert "package version: `0.23.0`" in readiness
    assert "git tag: `v0.23.0`" in readiness
    assert "Do not publish to TestPyPI or PyPI for `v0.23.0`" in readiness
    assert "including `v0.23.0`" in publishing
    assert "Milestone 6: COMPLETE" in plan
    assert "Milestone 6: COMPLETE" in scope
    assert "`v0.18` - Stable Fisher-KPP reaction-diffusion strong path" in roadmap
    assert "**Status:** Completed" in roadmap


def test_v0_18_release_gate_reaction_diffusion_api_is_documented_and_submodule_only() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")
    examples_module = importlib.import_module("pdelie.examples")

    assert hasattr(data_module, "generate_reaction_diffusion_1d_field_batch")
    assert hasattr(residuals_module, "ReactionDiffusionResidualEvaluator")
    assert hasattr(examples_module, "run_reaction_diffusion_vertical_slice_example")
    assert not hasattr(pdelie, "generate_reaction_diffusion_1d_field_batch")
    assert not hasattr(pdelie, "ReactionDiffusionResidualEvaluator")
    assert not hasattr(pdelie, "run_reaction_diffusion_vertical_slice_example")
    assert "pdelie.data.generate_reaction_diffusion_1d_field_batch" in api_stability
    assert "pdelie.residuals.ReactionDiffusionResidualEvaluator" in api_stability
    assert "pdelie.examples.run_reaction_diffusion_vertical_slice_example" in api_stability
    assert "reaction_diffusion_fisher_kpp" in api_stability
    assert "these APIs have no root `pdelie` exports" in api_stability


def test_v0_18_release_gate_reaction_diffusion_vertical_slice_is_direct_svd() -> None:
    field = generate_reaction_diffusion_1d_field_batch(batch_size=5, seed=18018)
    training, heldout = split_batch_train_heldout(field, train_size=2, seed=18019)
    derivatives = compute_spectral_fd_derivatives(training)
    evaluator = ReactionDiffusionResidualEvaluator()
    residual = evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, evaluator, epsilon=1e-4)
    verification = verify_translation_generator(heldout, generator, evaluator)

    assert residual.diagnostics["max_abs_residual"] < 5e-4
    assert residual.diagnostics["rms_residual"] < 5e-5
    assert generator.diagnostics["evidence_label"] == "direct_svd_in_tolerance"
    assert generator.diagnostics["reference_fallback_used"] is False
    assert generator.diagnostics["svd_span_distance"] <= 5e-2
    assert verification.classification != "failed"
    assert float(verification.error_curve[0]) < 5e-4


def test_v0_18_release_gate_example_outputs_nested_summary() -> None:
    result = run_reaction_diffusion_vertical_slice_example()

    assert json.loads(json.dumps(result)) == result
    assert result["summary_type"] == "vertical_slice"
    assert result["extra_metrics"]["equation"] == "reaction_diffusion_fisher_kpp"
    assert result["derivative_keys"] == ["u_t", "u_x", "u_xx"]
    assert result["residual"]["summary_type"] == "residual_batch"
    assert result["generator"]["summary_type"] == "generator_family"
    assert result["verification"]["summary_type"] == "verification_report"
    assert result["generator"]["reference_fallback_used"] is False
    assert result["verification"]["classification"] != "failed"


def test_v0_18_release_gate_no_deferred_surface_leaked() -> None:
    modules = [
        pdelie,
        importlib.import_module("pdelie.data"),
        importlib.import_module("pdelie.invariants"),
        importlib.import_module("pdelie.residuals"),
        importlib.import_module("pdelie.reporting"),
        importlib.import_module("pdelie.examples"),
        importlib.import_module("pdelie.discovery"),
        importlib.import_module("pdelie.symmetry"),
    ]
    forbidden_names = {
        "CallableGeneratorFamily",
        "compute_weak_derivatives",
        "evaluate_weak_ks_residual",
        "evaluate_weak_reaction_diffusion_residual",
        "from_pdebench",
        "from_the_well",
        "generate_ks_1d_field_batch",
        "generate_ks_feasibility_field_batch",
        "KSResidualEvaluator",
        "KuramotoSivashinskyResidualEvaluator",
        "load_pdebench",
        "load_the_well",
        "sample_reaction_diffusion_initial_conditions",
        "WeakKSResidualEvaluator",
        "WeakReactionDiffusionResidualEvaluator",
    }

    for module in modules:
        for name in sorted(forbidden_names):
            assert not hasattr(module, name), f"{module.__name__}.{name}"
