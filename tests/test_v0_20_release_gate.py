from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import pdelie
from pdelie.data import generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.examples import run_generator_confidence_report_example
from pdelie.reporting import summarize_generator_confidence
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def test_v0_20_release_gate_metadata_docs_and_ci_are_aligned() -> None:
    pyproject = tomllib.loads(_repo_text("pyproject.toml"))
    workflow = _repo_text(".github/workflows/ci.yml")
    readiness = _repo_text("docs/releases/V0_22_RELEASE_READINESS.md")
    readme = _repo_text("README.md")
    changelog = _repo_text("CHANGELOG.md")
    publishing = _repo_text("docs/releases/PUBLISHING.md")
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_20_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    release_gate_jobs = re.findall(r"^  (v0_\d+-release-gate):", workflow, flags=re.MULTILINE)

    assert pyproject["project"]["version"] == "0.22.0"
    assert release_gate_jobs == ["v0_22-release-gate"]
    assert "python -m pytest tests/test_v0_22_release_gate.py" in workflow
    assert "v0_20-release-gate" not in workflow

    assert "## 0.22.0" in changelog
    assert "V0.22" in readme
    assert "summarize_generator_confidence" in readme
    assert "package version: `0.22.0`" in readiness
    assert "git tag: `v0.22.0`" in readiness
    assert "Do not publish to TestPyPI or PyPI for `v0.22.0`" in readiness
    assert "including `v0.22.0`" in publishing
    assert "Milestone 6: COMPLETE" in plan
    assert "Milestone 6: COMPLETE" in scope
    assert "`v0.21` - External data readiness reports" in roadmap
    assert "**Status:** Completed" in roadmap


def test_v0_20_release_gate_confidence_api_is_documented_and_submodule_only() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    reporting_module = importlib.import_module("pdelie.reporting")
    examples_module = importlib.import_module("pdelie.examples")

    assert hasattr(reporting_module, "summarize_generator_confidence")
    assert hasattr(examples_module, "run_generator_confidence_report_example")
    assert not hasattr(pdelie, "summarize_generator_confidence")
    assert not hasattr(pdelie, "run_generator_confidence_report_example")
    assert "pdelie.reporting.summarize_generator_confidence" in api_stability
    assert "summary_type = \"generator_confidence\"" in api_stability
    assert "strong" in api_stability
    assert "insufficient_evidence" in api_stability
    assert "no root `pdelie` exports" in api_stability


def test_v0_20_release_gate_confidence_report_is_strong_for_direct_svd_heat() -> None:
    training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=20020)
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=20021)
    evaluator = HeatResidualEvaluator()
    derivatives = compute_spectral_fd_derivatives(training)
    residual = evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, evaluator, epsilon=1e-4)
    verification = verify_translation_generator(heldout, generator, evaluator)

    confidence = summarize_generator_confidence(
        residual=residual,
        generator=generator,
        verification=verification,
        thresholds={
            "residual_max_abs": 1e-3,
            "residual_rms": 1e-4,
            "verification_first_error": 1e-5,
            "verification_max_error": 1e-4,
        },
    )

    assert json.loads(json.dumps(confidence)) == confidence
    assert confidence["summary_type"] == "generator_confidence"
    assert confidence["confidence_label"] == "strong"
    assert confidence["component_statuses"]["residual"]["status"] == "passed"
    assert confidence["component_statuses"]["fit"]["status"] == "passed"
    assert confidence["component_statuses"]["verification"]["status"] == "passed"
    assert confidence["fit_diagnostics"]["evidence_label"] == "direct_svd_in_tolerance"
    assert "candidate_validation" in confidence["missing_evidence"]


def test_v0_20_release_gate_example_outputs_confidence_reports() -> None:
    result = run_generator_confidence_report_example()

    assert json.loads(json.dumps(result)) == result
    assert result["summary_type"] == "generator_confidence_report_example"
    assert result["extra_metrics"]["confidence_labels"] == ["strong", "qualified"]
    cases = {case["case_name"]: case["confidence"] for case in result["cases"]}
    assert cases["heat_direct_svd"]["summary_type"] == "generator_confidence"
    assert cases["heat_direct_svd"]["confidence_label"] == "strong"
    assert cases["formula_candidate_partial_validation"]["confidence_label"] == "qualified"
    assert (
        cases["formula_candidate_partial_validation"]["candidate_validation"]["conclusion"]
        == "partially_validated"
    )


def test_v0_20_release_gate_no_deferred_surface_leaked() -> None:
    root_forbidden = {
        "run_generator_confidence_report_example",
        "summarize_generator_confidence",
    }
    deferred_forbidden = {
        "CallableGeneratorFamily",
        "compute_confidence_score",
        "compute_weak_derivatives",
        "evaluate_weak_advection_diffusion_residual",
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
        "split_orbit_train_heldout",
        "summarize_generator_confidence_score",
        "train_test_translation_orbit_split",
        "WeakAdvectionDiffusionResidualEvaluator",
        "WeakKSResidualEvaluator",
        "WeakReactionDiffusionResidualEvaluator",
    }

    for name in sorted(root_forbidden | deferred_forbidden):
        assert not hasattr(pdelie, name), f"pdelie.{name}"

    modules = [
        importlib.import_module("pdelie.data"),
        importlib.import_module("pdelie.invariants"),
        importlib.import_module("pdelie.residuals"),
        importlib.import_module("pdelie.reporting"),
        importlib.import_module("pdelie.examples"),
        importlib.import_module("pdelie.discovery"),
        importlib.import_module("pdelie.symmetry"),
    ]
    for module in modules:
        for name in sorted(deferred_forbidden):
            assert not hasattr(module, name), f"{module.__name__}.{name}"
