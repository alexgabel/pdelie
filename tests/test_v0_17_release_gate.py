from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import numpy as np

import pdelie
from pdelie.data import generate_heat_1d_field_batch
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry import FormulaGeneratorFamily, validate_symmetry_candidate


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def _formula_translation(*, finite_transform: bool = False) -> FormulaGeneratorFamily:
    finite_transform_spec = None
    if finite_transform:
        from pdelie import GeneratorFamily, InvariantMapSpec
        from pdelie.contracts import _translation_generator_basis_spec

        generator = GeneratorFamily(
            parameterization="polynomial_translation_affine",
            coefficients=np.asarray([[1.0, 0.0, 0.0, 0.0]], dtype=float),
            basis_spec=_translation_generator_basis_spec(),
            normalization="l2_unit",
            diagnostics={},
        )
        finite_transform_spec = InvariantMapSpec(
            generator_metadata=generator.to_dict(),
            construction_method="uniform_translation",
            parameters={"axis": "x", "shift": 0.125},
            domain_validity="global",
            inverse_available=True,
            diagnostics={},
        ).to_dict()

    return FormulaGeneratorFamily(
        formula_generators=[
            {
                "name": "formula_translation",
                "components": {
                    "tau": {"node": "const", "value": 0.0},
                    "xi": {"node": "const", "value": 1.0},
                    "phi": {"node": "const", "value": 0.0},
                },
            }
        ],
        finite_transform_spec=finite_transform_spec,
    )


def test_v0_17_release_gate_metadata_docs_and_ci_are_aligned() -> None:
    pyproject = tomllib.loads(_repo_text("pyproject.toml"))
    workflow = _repo_text(".github/workflows/ci.yml")
    readiness = _repo_text("docs/releases/V0_27_RELEASE_READINESS.md")
    readme = _repo_text("README.md")
    changelog = _repo_text("CHANGELOG.md")
    publishing = _repo_text("docs/releases/PUBLISHING.md")
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_17_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    release_gate_jobs = re.findall(r"^  (v0_\d+-release-gate):", workflow, flags=re.MULTILINE)

    assert pyproject["project"]["version"] == "0.27.0"
    assert release_gate_jobs == ["v0_27-release-gate"]
    assert "python -m pytest tests/test_v0_27_release_gate.py" in workflow
    assert "v0_16-release-gate" not in workflow

    assert "## 0.27.0" in changelog
    assert "V0.27" in readme
    assert "FormulaGeneratorFamily" in readme
    assert "package version: `0.27.0`" in readiness
    assert "git tag: `v0.27.0`" in readiness
    assert "Do not publish to TestPyPI or PyPI for `v0.27.0`" in readiness
    assert "including `v0.27.0`" in publishing
    assert "Milestone 6: COMPLETE" in plan
    assert "Milestone 6: COMPLETE" in scope
    assert "`v0.18` - Stable Fisher-KPP reaction-diffusion strong path" in roadmap
    assert "**Status:** Completed" in roadmap


def test_v0_17_release_gate_formula_api_is_documented_and_submodule_only() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    symmetry_module = importlib.import_module("pdelie.symmetry")
    reporting_module = importlib.import_module("pdelie.reporting")

    assert hasattr(symmetry_module, "FormulaGeneratorFamily")
    assert hasattr(symmetry_module, "validate_symmetry_candidate")
    assert hasattr(reporting_module, "summarize_formula_generator_family")
    assert not hasattr(pdelie, "FormulaGeneratorFamily")
    assert not hasattr(pdelie, "summarize_formula_generator_family")
    assert "pdelie.symmetry.FormulaGeneratorFamily" in api_stability
    assert "pdelie.reporting.summarize_formula_generator_family" in api_stability
    assert "candidate_kind = \"formula_generator_family\"" in api_stability
    assert "safe JSON AST" in api_stability
    assert "these APIs have no root `pdelie` exports" in api_stability


def test_v0_17_release_gate_formula_candidates_validate_and_fail_as_expected() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=7, num_points=16, seed=17017)

    partial_report = validate_symmetry_candidate(
        field,
        _formula_translation().to_dict(),
        residual_evaluator=HeatResidualEvaluator(),
        source_candidate_id="v0_17_formula",
    )
    validated_report = validate_symmetry_candidate(
        field,
        _formula_translation(finite_transform=True),
        residual_evaluator=HeatResidualEvaluator(),
        source_candidate_id="v0_17_formula_transform",
    )
    failed_report = validate_symmetry_candidate(
        field,
        FormulaGeneratorFamily(
            formula_generators=[
                {
                    "name": "failed_formula",
                    "components": {
                        "tau": {"node": "const", "value": 0.0},
                        "xi": {"node": "reciprocal", "arg": {"node": "const", "value": 0.0}},
                        "phi": {"node": "const", "value": 0.0},
                    },
                }
            ]
        ),
        residual_evaluator=HeatResidualEvaluator(),
    )

    assert json.loads(json.dumps(partial_report)) == partial_report
    assert json.loads(json.dumps(validated_report)) == validated_report
    assert json.loads(json.dumps(failed_report)) == failed_report
    assert partial_report["candidate_kind"] == "formula_generator_family"
    assert partial_report["conclusion"] == "partially_validated"
    assert partial_report["check_reports"]["formula_evaluation_diagnostics"]["status"] == "passed"
    assert validated_report["candidate_kind"] == "formula_generator_family"
    assert validated_report["conclusion"] == "validated"
    assert validated_report["check_reports"]["finite_transform_residual_stability"]["status"] == "passed"
    assert failed_report["candidate_kind"] == "formula_generator_family"
    assert failed_report["conclusion"] == "failed"
    assert failed_report["check_reports"]["formula_evaluation_diagnostics"]["status"] == "failed"


def test_v0_17_release_gate_no_deferred_surface_leaked() -> None:
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
