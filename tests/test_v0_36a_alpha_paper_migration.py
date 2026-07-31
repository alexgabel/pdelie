"""v0.36a-alpha: contract tests for the migration audit.

**Contract tests only.** The actual audit builds two wheels across a major
Python/NumPy boundary and runs both pipelines; it executes via
``workflow_dispatch`` (``.github/workflows/alpha_migration.yml``) and produces a
downloadable report. What is asserted here is that the machinery is correct:
bundles round-trip, hashes are verified, comparators assign the labels their
evidence supports, and nothing pickles.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from pdelie.audit import (
    COMPARATOR_ASSIGNABLE_LABELS,
    COMPARISON_CLASSES,
    MIGRATION_LABELS,
    PRINCIPAL_ANGLE_RESOLUTION_FLOOR_RAD,
    QUALITATIVE_INVARIANTS,
    PipelineMigrationComparisonPolicy,
    StagePolicy,
    compare_exact,
    compare_numeric,
    compare_pipeline_stages,
    compare_qualitative,
    compare_selected_rows_by_objective,
    compare_subspaces,
    principal_angles,
    read_stage_bundle,
    write_stage_bundle,
)
from pdelie.errors import ScopeValidationError, ShapeValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]

PROVENANCE = {
    "wheel_sha256": "0" * 64,
    "package_version": "0.22.0",
    "git_commit": "abc1234",
    "source_dirty": False,
    "python_version": "3.11.14",
    "numpy_version": "1.26.4",
    "stage_type": "mask",
}


def write(tmp_path: Path, stage_id: str, arrays, cls="exact_discrete", parents=()) -> Path:
    write_stage_bundle(tmp_path, stage_id, "0.1", arrays, PROVENANCE, list(parents), cls)
    return tmp_path


# --- stage bundle round-trip ------------------------------------------------


def test_stage_bundle_round_trips(tmp_path: Path) -> None:
    arrays = {"mask": np.array([[True, False], [False, True]]), "ids": np.arange(4)}
    write(tmp_path, "regression_row_mask", arrays, parents=["observation_mask"])
    bundle = read_stage_bundle(tmp_path, "regression_row_mask")

    assert bundle.stage_id == "regression_row_mask"
    assert bundle.comparison_class == "exact_discrete"
    assert bundle.parent_stage_ids == ("observation_mask",)
    assert bundle.array_names() == ("ids", "mask")
    for name, original in arrays.items():
        assert np.array_equal(bundle.arrays[name], original)


def test_stage_json_is_strict_json_and_records_content_hashes(tmp_path: Path) -> None:
    write(tmp_path, "observation_mask", {"mask": np.ones((2, 3), dtype=bool)})
    manifest = json.loads((tmp_path / "observation_mask/stage.json").read_text())
    encoded = json.dumps(manifest, allow_nan=False)
    assert "NaN" not in encoded and "Infinity" not in encoded
    for entry in manifest["arrays"]:
        assert len(entry["sha256"]) == 64
        assert entry["path"].startswith("array_") and entry["path"].endswith(".npy")


def test_tampered_array_is_detected_at_read_time(tmp_path: Path) -> None:
    """A bundle whose bytes changed is not evidence about anything."""
    write(tmp_path, "observation_mask", {"mask": np.ones((2, 3), dtype=bool)})
    target = tmp_path / "observation_mask/array_000.npy"
    np.save(target, np.zeros((2, 3), dtype=bool), allow_pickle=False)

    with pytest.raises(ScopeValidationError, match="content hash mismatch"):
        read_stage_bundle(tmp_path, "observation_mask")


def test_object_dtype_is_refused_because_it_would_pickle(tmp_path: Path) -> None:
    with pytest.raises(ScopeValidationError, match="dtype=object"):
        write(tmp_path, "bad", {"values": np.array([{"a": 1}, {"b": 2}], dtype=object)})


def test_no_pickle_anywhere_in_the_bundle(tmp_path: Path) -> None:
    """np.save writes a pickle header for object arrays; assert none is present."""
    write(tmp_path, "derivatives", {"u_xx": np.linspace(0, 1, 8)}, cls="tolerance_numeric")
    for path in (tmp_path / "derivatives").rglob("*.npy"):
        header = path.read_bytes()[:128]
        assert b"pickle" not in header.lower()
        # allow_pickle=False arrays never carry the object dtype descriptor.
        assert b"'descr': '|O'" not in header


def test_missing_provenance_key_is_refused(tmp_path: Path) -> None:
    incomplete = {key: value for key, value in PROVENANCE.items() if key != "source_dirty"}
    with pytest.raises(ScopeValidationError, match="source_dirty"):
        write_stage_bundle(
            tmp_path, "s", "0.1", {"a": np.ones(2)}, incomplete, [], "exact_discrete"
        )


def test_source_dirty_must_be_a_bool_not_a_string(tmp_path: Path) -> None:
    provenance = {**PROVENANCE, "source_dirty": "unknown"}
    with pytest.raises(ScopeValidationError, match="must be a bool"):
        write_stage_bundle(
            tmp_path, "s", "0.1", {"a": np.ones(2)}, provenance, [], "exact_discrete"
        )


def test_unknown_comparison_class_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ScopeValidationError, match="not one of"):
        write(tmp_path, "s", {"a": np.ones(2)}, cls="approximately_fine")


def test_stage_cannot_be_its_own_parent(tmp_path: Path) -> None:
    with pytest.raises(ScopeValidationError, match="cannot be its own parent"):
        write(tmp_path, "s", {"a": np.ones(2)}, parents=["s"])


# --- comparators ------------------------------------------------------------


def test_compare_exact_labels_identical_arrays_preserved() -> None:
    a = np.arange(10)
    result = compare_exact(a, a.copy())
    assert result.label == "exactly_preserved"
    assert result.max_absolute_deviation == 0.0


def test_compare_exact_labels_any_difference_a_regression() -> None:
    a = np.arange(10)
    b = a.copy()
    b[3] = 99
    result = compare_exact(a, b)
    assert result.label == "unexplained_regression"
    assert result.drift_breakdown["mismatched_elements"] == 1
    assert result.drift_breakdown["first_mismatch_index"] == [3]


def test_compare_numeric_requires_both_tolerances() -> None:
    a = np.ones(4)
    with pytest.raises(TypeError):
        compare_numeric(a, a)  # type: ignore[call-arg]


def test_compare_numeric_accepts_drift_inside_tolerance() -> None:
    a = np.linspace(1.0, 2.0, 16)
    b = a * (1 + 1e-12)
    result = compare_numeric(a, b, rtol=1e-6, atol=1e-12)
    assert result.label == "numerically_equivalent_within_tolerance"
    assert result.max_relative_deviation < 1e-9


def test_compare_numeric_rejects_drift_outside_tolerance() -> None:
    a = np.linspace(1.0, 2.0, 16)
    b = a * 1.01
    result = compare_numeric(a, b, rtol=1e-6, atol=1e-12)
    assert result.label == "unexplained_regression"
    assert "deviation_exceeds_supplied_tolerance" in result.warnings


def test_compare_numeric_refuses_boolean_input() -> None:
    mask = np.ones(4, dtype=bool)
    with pytest.raises(ScopeValidationError, match="use compare_exact"):
        compare_numeric(mask, mask, rtol=1e-6, atol=1e-12)


def test_shape_change_is_refused_rather_than_compared() -> None:
    with pytest.raises(ShapeValidationError, match="different shape"):
        compare_exact(np.ones(4), np.ones(5))


@pytest.mark.parametrize("invariant", QUALITATIVE_INVARIANTS)
def test_every_qualitative_invariant_is_checkable(invariant: str) -> None:
    a = np.array([[1.0, 2.0], [3.0, 4.0]])
    result = compare_qualitative(a, a.copy(), invariant=invariant)
    assert result.label == "qualitatively_preserved"


def test_unknown_invariant_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="not one of"):
        compare_qualitative(np.ones(4), np.ones(4), invariant="vibes")


def test_subspace_comparison_ignores_column_sign() -> None:
    """The reason principal angles exist: sign is not a property of a subspace.

    The tolerance is the arccos resolution floor, not a round number. arccos is
    ill-conditioned near 1 -- ``arccos(1 - eps) ~ sqrt(2 eps)`` -- so identical
    subspaces report an angle of order ``sqrt(machine eps)``. Measured: 0.0 on
    macOS and 1.49e-08 on Linux for these same two bases. An earlier revision of
    this test asserted ``abs=1e-12`` and passed locally while failing CI, which
    is the mistake the portability classes exist to prevent.
    """
    rng = np.random.default_rng(20360)
    basis = np.linalg.qr(rng.standard_normal((6, 2)))[0]
    flipped = basis * np.array([1.0, -1.0])
    angles = principal_angles(basis, flipped)
    assert float(angles.max()) <= PRINCIPAL_ANGLE_RESOLUTION_FLOOR_RAD
    assert compare_subspaces(
        basis, flipped, max_principal_angle_rad=PRINCIPAL_ANGLE_RESOLUTION_FLOOR_RAD
    ).label == "qualitatively_preserved"


def test_principal_angle_resolution_floor_is_sqrt_machine_epsilon() -> None:
    """Pins the floor so a future edit cannot tighten it into a flaky assertion."""
    assert PRINCIPAL_ANGLE_RESOLUTION_FLOOR_RAD == pytest.approx(1.4901161e-08, rel=1e-6)


def test_row_selection_compared_by_objective_not_by_permutation() -> None:
    """v0.35c measured SciPy pivoting the same matrix differently per LAPACK."""
    same = compare_selected_rows_by_objective(140080.0, 140080.0000001, rtol=1e-6)
    assert same.label == "qualitatively_preserved"
    different = compare_selected_rows_by_objective(140080.0, 200000.0, rtol=1e-6)
    assert different.label == "unexplained_regression"


def test_comparators_can_only_assign_evidence_backed_labels() -> None:
    """The three judgement labels are policy decisions, not comparator outputs."""
    assert set(COMPARATOR_ASSIGNABLE_LABELS) < set(MIGRATION_LABELS)
    for judgement in (
        "intentional_contract_change",
        "platform_specific_difference",
        "blocked_missing_legacy_dependency",
    ):
        assert judgement not in COMPARATOR_ASSIGNABLE_LABELS


# --- policy -----------------------------------------------------------------


def test_intentional_contract_change_requires_a_release_note() -> None:
    with pytest.raises(ScopeValidationError, match="requires a linked release note"):
        StagePolicy(
            stage_id="derivatives",
            override_label="intentional_contract_change",
            justification="v0.30d backend dispatch added two config keys",
        )


def test_policy_override_requires_a_justification() -> None:
    with pytest.raises(ScopeValidationError, match="requires a justification"):
        StagePolicy(stage_id="derivatives", override_label="platform_specific_difference")


def test_policy_cannot_override_into_a_preserved_label() -> None:
    """A policy may explain a difference; it may not manufacture agreement."""
    with pytest.raises(ScopeValidationError, match="cannot be overridden into a preserved"):
        StagePolicy(
            stage_id="derivatives",
            override_label="exactly_preserved",
            justification="looks fine to me",
        )


# --- report -----------------------------------------------------------------


def _two_bundle_trees(tmp_path: Path, modern_arrays) -> tuple[Path, Path]:
    legacy_root = tmp_path / "legacy"
    modern_root = tmp_path / "modern"
    base = {"mask": np.array([[True, False], [True, True]])}
    write_stage_bundle(
        legacy_root, "observation_mask", "0.1", base, PROVENANCE, [], "exact_discrete"
    )
    write_stage_bundle(
        modern_root, "observation_mask", "0.1", modern_arrays,
        {**PROVENANCE, "side": "modern"}, [], "exact_discrete",
    )
    return legacy_root, modern_root


def test_report_is_strict_json_and_hashes_its_own_verdicts(tmp_path: Path) -> None:
    base = {"mask": np.array([[True, False], [True, True]])}
    legacy_root, modern_root = _two_bundle_trees(tmp_path, base)
    config = {
        "experiment_id": "unit",
        "stages": [{"stage_id": "observation_mask", "comparison_class": "exact_discrete"}],
    }

    report = compare_pipeline_stages(
        legacy_bundle_dir=legacy_root,
        modern_bundle_dir=modern_root,
        experiment_config=config,
        comparison_policy=PipelineMigrationComparisonPolicy(policy_id="unit"),
    )
    assert report["summary_type"] == "pdelie_pipeline_migration_report"
    assert report["label_counts"]["exactly_preserved"] == 1
    assert report["all_stages_explained"] is True
    assert len(report["report_semantic_hash"]) == 64
    json.dumps(report, allow_nan=False)


def test_missing_legacy_bundle_is_blocked_not_a_regression(tmp_path: Path) -> None:
    modern_root = tmp_path / "modern"
    write_stage_bundle(
        modern_root, "coefficients", "0.1", {"c": np.ones(3)},
        PROVENANCE, [], "tolerance_numeric",
    )
    (tmp_path / "legacy").mkdir()
    config = {
        "experiment_id": "unit",
        "stages": [{"stage_id": "coefficients", "comparison_class": "tolerance_numeric"}],
    }

    report = compare_pipeline_stages(
        legacy_bundle_dir=tmp_path / "legacy",
        modern_bundle_dir=modern_root,
        experiment_config=config,
        comparison_policy=PipelineMigrationComparisonPolicy(policy_id="unit"),
    )
    assert report["label_counts"]["blocked_missing_legacy_dependency"] == 1
    assert report["unexplained_regression_stage_ids"] == []


def test_tolerance_stage_without_tolerances_is_refused(tmp_path: Path) -> None:
    """The freeze process forbids a defaulted tolerance; so does the code."""
    arrays = {"c": np.ones(3)}
    for root in ("legacy", "modern"):
        write_stage_bundle(
            tmp_path / root, "coefficients", "0.1", arrays,
            PROVENANCE, [], "tolerance_numeric",
        )
    config = {
        "experiment_id": "unit",
        "stages": [{"stage_id": "coefficients", "comparison_class": "tolerance_numeric"}],
    }

    with pytest.raises(ScopeValidationError, match="required and are set by the pilot"):
        compare_pipeline_stages(
            legacy_bundle_dir=tmp_path / "legacy",
            modern_bundle_dir=tmp_path / "modern",
            experiment_config=config,
            comparison_policy=PipelineMigrationComparisonPolicy(policy_id="unit"),
        )


# --- configs and scope ------------------------------------------------------


@pytest.mark.parametrize("name", ["burgers_experiment", "hard_heat_experiment"])
def test_experiment_config_declares_sixteen_paper_critical_stages(name: str) -> None:
    config = json.loads((REPO_ROOT / f"configs/alpha_migration/{name}.json").read_text())
    stages = config["stages"]
    assert len(stages) == 16
    assert config["contains_paper_table_numbers"] is False
    for stage in stages:
        assert stage["comparison_class"] in COMPARISON_CLASSES
        assert stage["tolerance"] is None, "tolerances are set by the pilot, not the config"


def test_legacy_exporter_does_not_import_the_modern_audit_package() -> None:
    """The two sides share a format, never a serializer."""
    source = (REPO_ROOT / "scripts/legacy_exporter.py").read_text()
    for line in source.splitlines():
        stripped = line.strip()
        assert not stripped.startswith("from pdelie.audit")
        assert not stripped.startswith("import pdelie.audit")


def test_no_pickle_import_in_any_audit_module() -> None:
    for path in (REPO_ROOT / "src/pdelie/audit").rglob("*.py"):
        for line in path.read_text().splitlines():
            stripped = line.strip()
            assert not stripped.startswith(("import pickle", "from pickle"))


def test_audit_is_not_exported_from_the_root_namespace() -> None:
    import pdelie

    assert "audit" not in pdelie.__all__
    for name in ("compare_pipeline_stages", "write_stage_bundle", "StageBundle"):
        assert name not in pdelie.__all__


# --- policy and report branches --------------------------------------------


def test_policy_id_must_be_non_empty() -> None:
    with pytest.raises(ScopeValidationError, match="policy_id must be"):
        PipelineMigrationComparisonPolicy(policy_id="  ")


def test_stage_policy_key_must_match_its_stage_id() -> None:
    with pytest.raises(ScopeValidationError, match="does not match"):
        PipelineMigrationComparisonPolicy(
            policy_id="unit",
            stage_policies={"derivatives": StagePolicy(stage_id="residuals")},
        )


def test_comparison_class_disagreement_between_sides_is_refused(tmp_path: Path) -> None:
    """The class is a property of the stage; the two sides must agree."""
    arrays = {"a": np.ones(3)}
    write_stage_bundle(
        tmp_path / "legacy", "s", "0.1", arrays, PROVENANCE, [], "exact_discrete"
    )
    write_stage_bundle(
        tmp_path / "modern", "s", "0.1", arrays, PROVENANCE, [], "tolerance_numeric"
    )
    config = {"experiment_id": "unit", "stages": [{"stage_id": "s"}]}
    with pytest.raises(ScopeValidationError, match="declares comparison_class"):
        compare_pipeline_stages(
            legacy_bundle_dir=tmp_path / "legacy",
            modern_bundle_dir=tmp_path / "modern",
            experiment_config=config,
            comparison_policy=PipelineMigrationComparisonPolicy(policy_id="unit"),
        )


def test_differing_array_name_sets_is_a_regression(tmp_path: Path) -> None:
    write_stage_bundle(
        tmp_path / "legacy", "s", "0.1", {"a": np.ones(3)}, PROVENANCE, [], "exact_discrete"
    )
    write_stage_bundle(
        tmp_path / "modern", "s", "0.1", {"b": np.ones(3)}, PROVENANCE, [], "exact_discrete"
    )
    report = compare_pipeline_stages(
        legacy_bundle_dir=tmp_path / "legacy",
        modern_bundle_dir=tmp_path / "modern",
        experiment_config={"experiment_id": "unit", "stages": [{"stage_id": "s"}]},
        comparison_policy=PipelineMigrationComparisonPolicy(policy_id="unit"),
    )
    detail = report["stages"][0]["detail"]
    assert report["stages"][0]["label"] == "unexplained_regression"
    assert detail["only_in_legacy"] == ["a"]
    assert detail["only_in_modern"] == ["b"]


def test_platform_specific_diagnostic_stage_is_reported_never_asserted(tmp_path: Path) -> None:
    for root, value in (("legacy", 1.0), ("modern", 2.0)):
        write_stage_bundle(
            tmp_path / root, "blas", "0.1", {"threads": np.array([value])},
            PROVENANCE, [], "platform_specific_diagnostic",
        )
    report = compare_pipeline_stages(
        legacy_bundle_dir=tmp_path / "legacy",
        modern_bundle_dir=tmp_path / "modern",
        experiment_config={"experiment_id": "unit", "stages": [{"stage_id": "blas"}]},
        comparison_policy=PipelineMigrationComparisonPolicy(policy_id="unit"),
    )
    assert report["stages"][0]["label"] == "platform_specific_difference"
    assert report["unexplained_regression_stage_ids"] == []


def test_policy_override_relabels_a_failure_with_its_justification(tmp_path: Path) -> None:
    """The real v0.30d case: the entry point moved and config gained two keys."""
    write_stage_bundle(
        tmp_path / "legacy", "derivatives", "0.1", {"u_xx": np.ones(4)},
        PROVENANCE, [], "tolerance_numeric",
    )
    write_stage_bundle(
        tmp_path / "modern", "derivatives", "0.1", {"u_xx": np.full(4, 5.0)},
        PROVENANCE, [], "tolerance_numeric",
    )
    policy = PipelineMigrationComparisonPolicy(
        policy_id="unit",
        stage_policies={
            "derivatives": StagePolicy(
                stage_id="derivatives", rtol=1e-9, atol=1e-12,
                override_label="intentional_contract_change",
                justification="v0.30d added boundary-condition backend dispatch",
                release_note="docs/releases/V0_33_RELEASE_READINESS.md",
            )
        },
    )
    report = compare_pipeline_stages(
        legacy_bundle_dir=tmp_path / "legacy",
        modern_bundle_dir=tmp_path / "modern",
        experiment_config={"experiment_id": "unit", "stages": [{"stage_id": "derivatives"}]},
        comparison_policy=policy,
    )
    stage = report["stages"][0]
    assert stage["label"] == "intentional_contract_change"
    assert stage["detail"]["overridden_from"] == "unexplained_regression"
    assert stage["detail"]["release_note"].endswith(".md")
    assert report["all_stages_explained"] is True


def test_missing_modern_bundle_is_a_regression_not_blocked(tmp_path: Path) -> None:
    write_stage_bundle(
        tmp_path / "legacy", "s", "0.1", {"a": np.ones(3)}, PROVENANCE, [], "exact_discrete"
    )
    (tmp_path / "modern").mkdir()
    report = compare_pipeline_stages(
        legacy_bundle_dir=tmp_path / "legacy",
        modern_bundle_dir=tmp_path / "modern",
        experiment_config={"experiment_id": "unit", "stages": [{"stage_id": "s"}]},
        comparison_policy=PipelineMigrationComparisonPolicy(policy_id="unit"),
    )
    assert report["stages"][0]["label"] == "unexplained_regression"
    assert report["stages"][0]["detail"]["reason"] == "modern bundle absent"


def test_missing_bundle_directory_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ScopeValidationError, match="is not a directory"):
        compare_pipeline_stages(
            legacy_bundle_dir=tmp_path / "nope",
            modern_bundle_dir=tmp_path,
            experiment_config={"experiment_id": "u", "stages": [{"stage_id": "s"}]},
            comparison_policy=PipelineMigrationComparisonPolicy(policy_id="u"),
        )


def test_empty_stage_list_is_refused(tmp_path: Path) -> None:
    (tmp_path / "legacy").mkdir()
    (tmp_path / "modern").mkdir()
    with pytest.raises(ScopeValidationError, match="non-empty 'stages'"):
        compare_pipeline_stages(
            legacy_bundle_dir=tmp_path / "legacy",
            modern_bundle_dir=tmp_path / "modern",
            experiment_config={"experiment_id": "u", "stages": []},
            comparison_policy=PipelineMigrationComparisonPolicy(policy_id="u"),
        )


def test_qualitative_stage_without_a_named_invariant_is_refused(tmp_path: Path) -> None:
    arrays = {"a": np.ones(3)}
    for root in ("legacy", "modern"):
        write_stage_bundle(
            tmp_path / root, "stats", "0.1", arrays, PROVENANCE, [], "qualitative_invariant"
        )
    with pytest.raises(ScopeValidationError, match="names no invariant"):
        compare_pipeline_stages(
            legacy_bundle_dir=tmp_path / "legacy",
            modern_bundle_dir=tmp_path / "modern",
            experiment_config={"experiment_id": "u", "stages": [{"stage_id": "stats"}]},
            comparison_policy=PipelineMigrationComparisonPolicy(policy_id="u"),
        )


# --- validation branches ----------------------------------------------------


@pytest.mark.parametrize("bad_id", ["", "  ", "a/b", "..", 7])
def test_invalid_stage_id_is_refused(tmp_path: Path, bad_id: object) -> None:
    with pytest.raises(ScopeValidationError):
        write_stage_bundle(
            tmp_path, bad_id, "0.1", {"a": np.ones(2)}, PROVENANCE, [], "exact_discrete"  # type: ignore[arg-type]
        )


def test_empty_or_non_mapping_arrays_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ScopeValidationError, match="non-empty mapping"):
        write_stage_bundle(tmp_path, "s", "0.1", {}, PROVENANCE, [], "exact_discrete")
    with pytest.raises(ScopeValidationError, match="non-empty mapping"):
        write_stage_bundle(
            tmp_path, "s", "0.1", ["not", "a", "mapping"], PROVENANCE, [], "exact_discrete"  # type: ignore[arg-type]
        )


def test_empty_array_and_blank_array_name_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ShapeValidationError, match="is empty"):
        write_stage_bundle(
            tmp_path, "s", "0.1", {"a": np.array([])}, PROVENANCE, [], "exact_discrete"
        )
    with pytest.raises(ScopeValidationError, match="non-empty string"):
        write_stage_bundle(
            tmp_path, "s", "0.1", {"": np.ones(2)}, PROVENANCE, [], "exact_discrete"
        )


def test_non_mapping_or_non_json_provenance_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ScopeValidationError, match="must be a mapping"):
        write_stage_bundle(
            tmp_path, "s", "0.1", {"a": np.ones(2)}, "nope", [], "exact_discrete"  # type: ignore[arg-type]
        )
    with pytest.raises(ScopeValidationError, match="strict-JSON"):
        write_stage_bundle(
            tmp_path, "s", "0.1", {"a": np.ones(2)},
            {**PROVENANCE, "nan": float("nan")}, [], "exact_discrete",
        )


def test_blank_schema_version_and_duplicate_parents_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ScopeValidationError, match="schema_version"):
        write_stage_bundle(
            tmp_path, "s", "  ", {"a": np.ones(2)}, PROVENANCE, [], "exact_discrete"
        )
    with pytest.raises(ScopeValidationError, match="must not repeat"):
        write_stage_bundle(
            tmp_path, "s", "0.1", {"a": np.ones(2)}, PROVENANCE, ["p", "p"], "exact_discrete"
        )


def test_reading_a_missing_or_corrupt_bundle_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ScopeValidationError, match="no stage.json"):
        read_stage_bundle(tmp_path, "absent")

    write_stage_bundle(
        tmp_path, "s", "0.1", {"a": np.ones(2)}, PROVENANCE, [], "exact_discrete"
    )
    (tmp_path / "s/array_000.npy").unlink()
    with pytest.raises(ScopeValidationError, match="is missing"):
        read_stage_bundle(tmp_path, "s")


def test_reading_a_bundle_with_an_unknown_class_is_refused(tmp_path: Path) -> None:
    write_stage_bundle(
        tmp_path, "s", "0.1", {"a": np.ones(2)}, PROVENANCE, [], "exact_discrete"
    )
    manifest_path = tmp_path / "s/stage.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["comparison_class"] = "vibes"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ScopeValidationError, match="not one of"):
        read_stage_bundle(tmp_path, "s")


@pytest.mark.parametrize("bad", [-1.0, "1e-6", True])
def test_negative_or_non_numeric_tolerances_are_refused(bad: object) -> None:
    a = np.ones(4)
    with pytest.raises(ScopeValidationError, match="non-negative real"):
        compare_numeric(a, a, rtol=bad, atol=1e-12)  # type: ignore[arg-type]
    with pytest.raises(ScopeValidationError, match="non-negative real"):
        compare_numeric(a, a, rtol=1e-6, atol=bad)  # type: ignore[arg-type]


def test_non_finite_values_are_reported_not_silently_compared() -> None:
    a = np.array([1.0, np.nan, 3.0])
    b = np.array([1.0, np.nan, 3.0])
    result = compare_numeric(a, b, rtol=1e-6, atol=1e-12)
    assert "non_finite_values_present_and_excluded_from_deviation" in result.warnings

    allnan = np.array([np.nan, np.nan])
    empty = compare_numeric(allnan, allnan, rtol=1e-6, atol=1e-12)
    assert empty.label == "unexplained_regression"
    assert "no_finite_elements_to_compare" in empty.warnings


def test_principal_angles_validates_its_inputs() -> None:
    with pytest.raises(ShapeValidationError, match="two-dimensional"):
        principal_angles(np.ones(4), np.ones(4))
    with pytest.raises(ShapeValidationError, match="same ambient dimension"):
        principal_angles(np.ones((4, 2)), np.ones((5, 2)))


def test_subspace_and_objective_comparators_validate_thresholds() -> None:
    basis = np.linalg.qr(np.random.default_rng(1).standard_normal((5, 2)))[0]
    with pytest.raises(ScopeValidationError, match="non-negative real"):
        compare_subspaces(basis, basis, max_principal_angle_rad=-1.0)
    with pytest.raises(ScopeValidationError, match="must be a real number"):
        compare_selected_rows_by_objective("1.0", 1.0, rtol=1e-6)  # type: ignore[arg-type]


def test_qualitative_invariants_detect_a_genuine_violation() -> None:
    assert compare_qualitative(
        np.array([1.0, -1.0]), np.array([1.0, 1.0]), invariant="sign"
    ).label == "unexplained_regression"
    assert compare_qualitative(
        np.array([[1.0, 0.0], [0.0, 1.0]]), np.array([[1.0, 1.0], [1.0, 1.0]]), invariant="rank"
    ).label == "unexplained_regression"
    assert compare_qualitative(
        np.array([1, 1, 0]), np.array([0, 1, 0]), invariant="support_containment"
    ).label == "unexplained_regression"


def test_summarize_labels_counts_every_vocabulary_entry() -> None:
    from pdelie.audit import summarize_labels

    counts = summarize_labels([compare_exact(np.ones(2), np.ones(2))])
    assert set(counts) == set(MIGRATION_LABELS)
    assert counts["exactly_preserved"] == 1
