"""v0.30.1 polynomial_translation_svd built-in adapter tests."""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.contracts import FieldBatch, GeneratorFamily
from pdelie.data import generate_heat_1d_field_batch
from pdelie.errors import ScopeValidationError
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry import (
    SymmetryCandidate,
    SymmetryMethodResult,
    run_symmetry_method,
    summarize_symmetry_method_result,
)


def _small_periodic_heat_field() -> FieldBatch:
    return generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=32, seed=42
    )


# ---------------------------------------------------------------------------
# 1. Output is SymmetryCandidate, not raw GeneratorFamily.
# ---------------------------------------------------------------------------


def test_adapter_returns_symmetry_candidate_not_generator_family() -> None:
    result = run_symmetry_method(
        "polynomial_translation_svd",
        _small_periodic_heat_field(),
        residual_evaluator=HeatResidualEvaluator(),
    )
    assert isinstance(result, SymmetryMethodResult)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert isinstance(candidate, SymmetryCandidate)
    # The candidate WRAPS the GeneratorFamily; the return is not the
    # raw GeneratorFamily.
    assert isinstance(candidate.payload, GeneratorFamily)


# ---------------------------------------------------------------------------
# 2. representation_type is generator_family.
# ---------------------------------------------------------------------------


def test_adapter_representation_type_is_generator_family() -> None:
    result = run_symmetry_method(
        "polynomial_translation_svd",
        _small_periodic_heat_field(),
        residual_evaluator=HeatResidualEvaluator(),
    )
    assert result.candidates[0].representation_type == "generator_family"


# ---------------------------------------------------------------------------
# 3. method_scores finite or None.
# ---------------------------------------------------------------------------


def test_adapter_method_scores_are_finite_or_none() -> None:
    result = run_symmetry_method(
        "polynomial_translation_svd",
        _small_periodic_heat_field(),
        residual_evaluator=HeatResidualEvaluator(),
    )
    # v0.32b: frozen four score names. See
    # docs/design/GENERATOR_CONFIDENCE_ADDITIVE_FIELDS.md.
    assert set(result.method_scores.keys()) == {
        "span_distance",
        "residual_l2",
        "error_curve_max",
        "svd_condition_number",
    }
    for key, value in result.method_scores.items():
        assert value is None or isinstance(value, float), (
            f"method_scores[{key!r}] must be finite float or None; got "
            f"{type(value).__name__}"
        )
        if value is not None:
            assert np.isfinite(value)


# ---------------------------------------------------------------------------
# 4. reference_fallback_used remains bool.
# ---------------------------------------------------------------------------


def test_adapter_reference_fallback_used_is_bool() -> None:
    result = run_symmetry_method(
        "polynomial_translation_svd",
        _small_periodic_heat_field(),
        residual_evaluator=HeatResidualEvaluator(),
    )
    reference_fallback = result.fit_diagnostics["reference_fallback_used"]
    # STRICT bool check — must not be coerced to 0/1 or "true".
    assert type(reference_fallback) is bool


# ---------------------------------------------------------------------------
# 5. Runtime and provenance recorded.
# ---------------------------------------------------------------------------


def test_adapter_records_runtime_and_provenance() -> None:
    result = run_symmetry_method(
        "polynomial_translation_svd",
        _small_periodic_heat_field(),
        residual_evaluator=HeatResidualEvaluator(),
    )
    assert result.runtime_seconds is not None
    assert result.runtime_seconds > 0
    assert result.provenance["residual_evaluator"] == "HeatResidualEvaluator"
    assert result.provenance["method_version"] == "0.1"
    assert result.provenance["field_schema_version"] == "0.2"
    assert result.provenance["config"] == {"epsilon": 1e-4}


def test_adapter_records_backend_versions() -> None:
    result = run_symmetry_method(
        "polynomial_translation_svd",
        _small_periodic_heat_field(),
        residual_evaluator=HeatResidualEvaluator(),
    )
    assert "pdelie" in result.backend_versions
    assert "numpy" in result.backend_versions


# ---------------------------------------------------------------------------
# 6. Deterministic repeated result under same field/config.
# ---------------------------------------------------------------------------


def test_adapter_is_deterministic_under_same_field_and_config() -> None:
    field = _small_periodic_heat_field()
    evaluator = HeatResidualEvaluator()
    first = run_symmetry_method(
        "polynomial_translation_svd",
        field,
        residual_evaluator=evaluator,
    )
    second = run_symmetry_method(
        "polynomial_translation_svd",
        field,
        residual_evaluator=evaluator,
    )
    assert first.deterministic is True
    assert second.deterministic is True
    # The wrapped GeneratorFamily coefficients must match byte-for-byte.
    np.testing.assert_array_equal(
        first.candidates[0].payload.coefficients,
        second.candidates[0].payload.coefficients,
    )
    # The method_scores must match byte-for-byte.
    assert first.method_scores == second.method_scores


# ---------------------------------------------------------------------------
# 7. No verification report fabricated.
# ---------------------------------------------------------------------------


def test_adapter_does_not_fabricate_verification_report() -> None:
    """The adapter must not attach a VerificationReport to the summary.

    v0.30.1 architectural rule: candidate generation and verification
    are distinct stages. The adapter emits a candidate but does NOT run
    verification.
    """
    result = run_symmetry_method(
        "polynomial_translation_svd",
        _small_periodic_heat_field(),
        residual_evaluator=HeatResidualEvaluator(),
    )
    for key in ("verification_report", "verification", "verified"):
        assert key not in result.provenance
        assert key not in result.fit_diagnostics
    for key in ("verification_report", "verification", "verified"):
        assert key not in result.candidates[0].provenance


def test_adapter_result_carries_no_best_property() -> None:
    """SymmetryMethodResult has no ``best`` accessor by design."""
    result = run_symmetry_method(
        "polynomial_translation_svd",
        _small_periodic_heat_field(),
        residual_evaluator=HeatResidualEvaluator(),
    )
    assert not hasattr(result, "best")


def test_adapter_result_carries_no_method_confidence_field() -> None:
    """No method-native scalar may be called ``confidence`` by v0.30.1
    policy — the field is called ``method_scores``.
    """
    result = run_symmetry_method(
        "polynomial_translation_svd",
        _small_periodic_heat_field(),
        residual_evaluator=HeatResidualEvaluator(),
    )
    assert not hasattr(result, "method_confidence")
    assert "method_confidence" not in result.fit_diagnostics
    assert "confidence" not in result.method_scores


# ---------------------------------------------------------------------------
# 8. Periodic-only guard preserved.
# ---------------------------------------------------------------------------


def test_adapter_rejects_nonperiodic_field() -> None:
    """Build a nonperiodic FieldBatch by directly rewriting the boundary
    metadata (bypasses the constructor's periodic default) and confirm the
    adapter's ``is_x_periodic`` guard fires before any expensive work.
    """
    field = _small_periodic_heat_field()
    field.metadata["boundary_conditions"] = {
        "x": {
            "type": "dirichlet",
            "left": {"value": 0.0, "source": "user_supplied"},
            "right": {"value": 0.0, "source": "user_supplied"},
            "specified": True,
        }
    }
    with pytest.raises(ScopeValidationError, match="periodic"):
        run_symmetry_method(
            "polynomial_translation_svd",
            field,
            residual_evaluator=HeatResidualEvaluator(),
        )


def test_adapter_rejects_missing_residual_evaluator() -> None:
    with pytest.raises(ScopeValidationError, match="residual_evaluator"):
        run_symmetry_method(
            "polynomial_translation_svd",
            _small_periodic_heat_field(),
            residual_evaluator=None,
        )


# ---------------------------------------------------------------------------
# 9. Strict JSON summary passes.
# ---------------------------------------------------------------------------


def test_adapter_summary_is_strict_json_serializable() -> None:
    result = run_symmetry_method(
        "polynomial_translation_svd",
        _small_periodic_heat_field(),
        residual_evaluator=HeatResidualEvaluator(),
    )
    summary = summarize_symmetry_method_result(result)
    # allow_nan=False roundtrip is the canonical strict-JSON assertion.
    text = json.dumps(summary, allow_nan=False)
    roundtrip = json.loads(text)
    assert roundtrip == summary
    assert summary["summary_type"] == "pdelie_symmetry_method_result"
    assert summary["method_name"] == "polynomial_translation_svd"
    assert summary["deterministic"] is True
    # No NaN or Inf anywhere in the summary.
    assert "NaN" not in text
    assert "Infinity" not in text


# ---------------------------------------------------------------------------
# 10. Config knob honored: epsilon.
# ---------------------------------------------------------------------------


def test_adapter_honors_epsilon_config() -> None:
    """Different epsilon values produce (potentially) different results,
    but both are strict-JSON.
    """
    field = _small_periodic_heat_field()
    evaluator = HeatResidualEvaluator()
    result_default = run_symmetry_method(
        "polynomial_translation_svd", field, residual_evaluator=evaluator
    )
    result_custom = run_symmetry_method(
        "polynomial_translation_svd",
        field,
        residual_evaluator=evaluator,
        config={"epsilon": 1e-5},
    )
    assert result_default.provenance["config"]["epsilon"] == 1e-4
    assert result_custom.provenance["config"]["epsilon"] == 1e-5


def test_adapter_rejects_nonpositive_epsilon() -> None:
    with pytest.raises(ScopeValidationError, match="epsilon"):
        run_symmetry_method(
            "polynomial_translation_svd",
            _small_periodic_heat_field(),
            residual_evaluator=HeatResidualEvaluator(),
            config={"epsilon": -1.0},
        )
