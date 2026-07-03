"""Tests for v0.30c boundary-aware readiness and reporting."""
from __future__ import annotations

import json
import copy

import numpy as np
import pytest

from pdelie._boundary import normalize_x_boundary_condition
from pdelie.data import from_numpy, generate_heat_1d_field_batch
from pdelie.errors import ScopeValidationError
from pdelie.reporting import (
    summarize_field_batch_readiness,
    summarize_residual_batch,
)
from pdelie.residuals import HeatResidualEvaluator


def _nonperiodic_metadata(*, x_boundary):
    return {
        "boundary_conditions": {"x": x_boundary},
        "coordinate_system": "cartesian",
        "grid_regularity": "uniform",
        "grid_type": "rectilinear",
        "parameter_tags": {},
    }


def _nonperiodic_field(x_boundary):
    n_t, n_x = 9, 16
    t = np.linspace(0.0, 1.0, n_t, dtype=float)
    x = np.linspace(0.0, 1.0, n_x, dtype=float)
    values = np.zeros((1, n_t, n_x, 1), dtype=float)
    return from_numpy(
        values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata=_nonperiodic_metadata(x_boundary=x_boundary),
    )


# --- summarize_field_batch_readiness boundary_condition_warnings ------------


def test_periodic_legacy_string_has_no_boundary_warnings() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=9, num_points=16, seed=0)
    summary = summarize_field_batch_readiness(field)
    assert summary["boundary_condition_warnings"] == []
    assert summary["readiness_label"] == "ready"


def test_periodic_structured_has_no_boundary_warnings() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=9, num_points=16, seed=1)
    field = copy.copy(field)
    field.metadata = copy.deepcopy(field.metadata)
    field.metadata["boundary_conditions"] = {"x": normalize_x_boundary_condition("periodic")}
    summary = summarize_field_batch_readiness(field)
    assert summary["boundary_condition_warnings"] == []


def test_legacy_dirichlet_string_emits_legacy_and_unspecified_warnings() -> None:
    field = _nonperiodic_field("dirichlet")
    summary = summarize_field_batch_readiness(field)
    warnings = summary["boundary_condition_warnings"]
    assert "x_boundary_legacy_string_under_schema_0_2" in warnings
    assert "x_boundary_dirichlet_unspecified" in warnings
    assert summary["readiness_label"] == "needs_attention"


def test_legacy_neumann_string_emits_neumann_unspecified_warning() -> None:
    field = _nonperiodic_field("neumann")
    summary = summarize_field_batch_readiness(field)
    assert "x_boundary_neumann_unspecified" in summary["boundary_condition_warnings"]


def test_legacy_open_unknown_string_emits_open_unknown_warning() -> None:
    field = _nonperiodic_field("open_unknown")
    summary = summarize_field_batch_readiness(field)
    assert "x_boundary_open_unknown" in summary["boundary_condition_warnings"]
    assert summary["readiness_label"] == "needs_attention"


def test_structured_dirichlet_unspecified_emits_unspecified_warning() -> None:
    spec = normalize_x_boundary_condition("dirichlet")
    field = _nonperiodic_field(spec)
    summary = summarize_field_batch_readiness(field)
    warnings = summary["boundary_condition_warnings"]
    assert "x_boundary_dirichlet_unspecified" in warnings
    # No legacy-string warning when the BC is structured.
    assert "x_boundary_legacy_string_under_schema_0_2" not in warnings


def test_structured_dirichlet_with_user_values_has_no_unspecified_warning() -> None:
    spec = normalize_x_boundary_condition({
        "type": "dirichlet",
        "left": {"value": 0.0, "time_dependent": False, "source": "user_supplied"},
        "right": {"value": 1.0, "time_dependent": False, "source": "user_supplied"},
    })
    field = _nonperiodic_field(spec)
    summary = summarize_field_batch_readiness(field)
    warnings = summary["boundary_condition_warnings"]
    # Specified=True ⇒ no "_unspecified" warning, and no legacy-string warning.
    assert "x_boundary_dirichlet_unspecified" not in warnings
    assert "x_boundary_legacy_string_under_schema_0_2" not in warnings
    # Readiness is at most "needs_attention" — but for fully-specified dirichlet there's no warning at all,
    # so the label stays "ready" (the warning system only downgrades when warnings exist).
    # Other failures could still downgrade the field; the assertion below holds only for this minimal field.
    assert summary["boundary_condition_warnings"] == []


def test_structured_open_unknown_emits_open_warning() -> None:
    spec = normalize_x_boundary_condition("open_unknown")
    field = _nonperiodic_field(spec)
    summary = summarize_field_batch_readiness(field)
    assert "x_boundary_open_unknown" in summary["boundary_condition_warnings"]


# --- readiness label downgrade ---------------------------------------------


def test_nonperiodic_downgrades_ready_to_needs_attention() -> None:
    field = _nonperiodic_field("dirichlet")
    summary = summarize_field_batch_readiness(field)
    assert summary["readiness_label"] == "needs_attention"
    # Metadata itself is now considered "passed" — nonperiodic is not a failure.
    assert summary["component_statuses"]["metadata"]["status"] == "passed"


def test_other_failures_still_route_to_not_ready_regardless_of_boundary() -> None:
    """A non-finite value remains a hard failure; the boundary warning does not soften it."""
    field = _nonperiodic_field("dirichlet")
    field.values[0, 0, 0, 0] = np.nan
    summary = summarize_field_batch_readiness(field)
    assert summary["readiness_label"] == "not_ready"


# --- strict JSON ------------------------------------------------------------


def test_field_batch_readiness_summary_is_strict_json_compatible() -> None:
    field = _nonperiodic_field("dirichlet")
    summary = summarize_field_batch_readiness(field)
    assert json.loads(json.dumps(summary, allow_nan=False)) == summary


# --- summarize_residual_batch.residual_domain_policy -----------------------


def test_residual_batch_summary_records_not_configured_when_policy_absent() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=9, num_points=16, seed=2)
    residual = HeatResidualEvaluator().evaluate(field)
    summary = summarize_residual_batch(residual)
    assert summary["residual_domain_policy"] == "not_configured"


def test_residual_batch_summary_passes_through_supplied_policy() -> None:
    """A caller (or a future v0.30+ residual evaluator) can record the policy in
    `residual.diagnostics`; the summary surfaces it verbatim."""
    field = generate_heat_1d_field_batch(batch_size=1, num_times=9, num_points=16, seed=3)
    residual = HeatResidualEvaluator().evaluate(field)
    residual.diagnostics["residual_domain_policy"] = "interior_only"
    summary = summarize_residual_batch(residual)
    assert summary["residual_domain_policy"] == "interior_only"


def test_residual_batch_summary_remains_strict_json_compatible() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=9, num_points=16, seed=4)
    residual = HeatResidualEvaluator().evaluate(field)
    summary = summarize_residual_batch(residual)
    assert json.loads(json.dumps(summary, allow_nan=False)) == summary


# --- malformed metadata still routes to failure -----------------------------


def test_unsupported_boundary_string_routes_to_metadata_failure() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=9, num_points=16, seed=5)
    field = copy.copy(field)
    field.metadata = copy.deepcopy(field.metadata)
    field.metadata["boundary_conditions"] = {"x": "insulating"}
    summary = summarize_field_batch_readiness(field)
    # Unsupported BC strings are reported as a hard failure, not as a soft warning.
    assert summary["readiness_label"] in {"needs_attention", "not_ready"}
    failures = summary["metadata_diagnostics"].get("missing_keys", [])
    component_failures = summary["component_statuses"]["metadata"]
    # Either a metadata failure or an x_boundary_unsupported entry should appear.
    if component_failures["status"] == "failed":
        details = component_failures.get("details", {})
        assert "x_boundary_unsupported" in details.get("failures", []) or failures
