from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import numpy as np

import pdelie
from pdelie import GeneratorFamily, InvariantMapSpec
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import generate_heat_1d_field_batch
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry import validate_symmetry_candidate


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def _translation_generator(coefficients: list[float] | None = None) -> GeneratorFamily:
    coefficients = [1.0, 0.0, 0.0, 0.0] if coefficients is None else coefficients
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.asarray([coefficients], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


def _translation_spec(generator: GeneratorFamily) -> InvariantMapSpec:
    return InvariantMapSpec(
        generator_metadata=generator.to_dict(),
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": 0.125},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )


def test_v0_16_release_gate_metadata_docs_and_ci_are_aligned() -> None:
    pyproject = tomllib.loads(_repo_text("pyproject.toml"))
    workflow = _repo_text(".github/workflows/ci.yml")
    readiness = _repo_text("docs/releases/V0_23_RELEASE_READINESS.md")
    readme = _repo_text("README.md")
    changelog = _repo_text("CHANGELOG.md")
    publishing = _repo_text("docs/releases/PUBLISHING.md")
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_16_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    release_gate_jobs = re.findall(r"^  (v0_\d+-release-gate):", workflow, flags=re.MULTILINE)

    assert pyproject["project"]["version"] == "0.23.0"
    assert release_gate_jobs == ["v0_23-release-gate"]
    assert "python -m pytest tests/test_v0_23_release_gate.py" in workflow
    assert "v0_16-release-gate" not in workflow

    assert "## 0.16.0" in changelog
    assert "V0.23" in readme
    assert "validate_symmetry_candidate" in readme
    assert "package version: `0.23.0`" in readiness
    assert "git tag: `v0.23.0`" in readiness
    assert "Do not publish to TestPyPI or PyPI for `v0.23.0`" in readiness
    assert "including `v0.23.0`" in publishing
    assert "Milestone 6: COMPLETE" in plan
    assert "Milestone 6: COMPLETE" in scope
    assert "`v0.16` - External symmetry-candidate validation" in roadmap
    assert "**Status:** Completed" in roadmap


def test_v0_16_release_gate_validation_api_is_documented_and_submodule_only() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    symmetry_module = importlib.import_module("pdelie.symmetry")

    assert hasattr(symmetry_module, "validate_symmetry_candidate")
    assert not hasattr(pdelie, "validate_symmetry_candidate")
    assert "pdelie.symmetry.validate_symmetry_candidate" in api_stability
    assert "candidate_kind = \"generator_family\"" in api_stability
    assert "candidate_kind = \"invariant_map_spec\"" in api_stability
    assert "not a mathematical proof of symmetry" in api_stability
    assert "this API has no root `pdelie` export" in api_stability


def test_v0_16_release_gate_representative_candidates_validate_and_fail_as_expected() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=7, num_points=16, seed=16016)
    generator = _translation_generator()
    spec = _translation_spec(generator)
    wrong = _translation_generator([0.0, 0.0, 1.0, 0.0])

    generator_report = validate_symmetry_candidate(
        field,
        generator.to_dict(),
        residual_evaluator=HeatResidualEvaluator(),
        reference_generator=generator,
        source_candidate_id="v0_16_generator",
    )
    spec_report = validate_symmetry_candidate(
        field,
        spec.to_dict(),
        residual_evaluator=HeatResidualEvaluator(),
        source_candidate_id="v0_16_spec",
    )
    failed_report = validate_symmetry_candidate(field, wrong, residual_evaluator=HeatResidualEvaluator())

    assert json.loads(json.dumps(generator_report)) == generator_report
    assert json.loads(json.dumps(spec_report)) == spec_report
    assert json.loads(json.dumps(failed_report)) == failed_report
    assert generator_report["candidate_kind"] == "generator_family"
    assert generator_report["conclusion"] == "validated"
    assert generator_report["check_reports"]["finite_transform_verification"]["status"] == "passed"
    assert generator_report["check_reports"]["reference_span_comparison"]["status"] == "passed"
    assert spec_report["candidate_kind"] == "invariant_map_spec"
    assert spec_report["conclusion"] == "validated"
    assert spec_report["check_reports"]["residual_stability"]["status"] == "passed"
    assert spec_report["check_reports"]["inverse_consistency"]["status"] == "passed"
    assert failed_report["candidate_kind"] == "generator_family"
    assert failed_report["conclusion"] == "failed"
    assert failed_report["check_reports"]["finite_transform_verification"]["status"] == "failed"


def test_v0_16_release_gate_no_deferred_surface_leaked() -> None:
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
        "augment_translation_orbit",
        "build_translation_orbit_dataset",
        "build_translation_orbit_views",
        "CallableGeneratorFamily",
        "compute_coverage_diagnostics",
        "compute_weak_derivatives",
        "diagnose_time_translation_consistency",
        "evaluate_weak_ks_residual",
        "from_pdebench",
        "from_the_well",
        "generate_ks_1d_field_batch",
        "generate_ks_feasibility_field_batch",
        "KSResidualEvaluator",
        "KuramotoSivashinskyResidualEvaluator",
        "load_pdebench",
        "load_the_well",
        "materialize_uniform_translation_orbit",
        "run_ks_vertical_slice_example",
        "split_orbit_train_heldout",
        "train_test_translation_orbit_split",
        "validate_generator_candidate",
        "WeakKSResidualEvaluator",
    }

    for module in modules:
        for name in sorted(forbidden_names):
            assert not hasattr(module, name), f"{module.__name__}.{name}"
