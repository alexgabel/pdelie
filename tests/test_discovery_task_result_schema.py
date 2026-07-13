"""Design-only tests for the frozen v0.31a discovery TaskResult schema.

These tests exercise the *design* documented in
``docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md``. No runtime TaskResult
implementation exists yet — the runtime is deferred to v0.31b+. Nevertheless,
the tests are real and passing because they import the actual strict-JSON
helper from ``pdelie.reporting.summaries`` (the same helper the v0.31b runtime
will wire up) and prove it enforces the NaN-safety contract on a
representative composed payload.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pdelie.errors import SchemaValidationError
from pdelie.reporting.summaries import _validate_strict_json_compatible

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCOPE_CONFIG_PATH = _REPO_ROOT / "configs/planning/v0_31_discovery_task_bridge_scope.json"


def _load_planned_schema() -> dict[str, object]:
    return json.loads(_SCOPE_CONFIG_PATH.read_text(encoding="utf-8"))["planned_task_result_schema"]


def _build_minimal_task_result_payload(*, target_convention: str = "pde_library") -> dict[str, object]:
    """Build a minimal, valid TaskResult payload matching the design doc.

    This mirrors what ``pdelie.tasks.discovery.run_pysindy_pde_task`` will
    produce in v0.31b. Numbers are chosen to be strictly finite so the payload
    round-trips through ``json.dumps(..., allow_nan=False)``.
    """

    weak_contract: dict[str, object] | None
    if target_convention == "weak_pde_library":
        weak_contract = {
            "method_family": "pysindy_weak_pde_library_polynomial_gauss_v1",
            "test_function_family": "pysindy_weak_pde_library_polynomial_bump_v1",
            "quadrature_rule": "pysindy_weak_pde_library_composite_gauss_v1",
            "diagnostic_only": True,
        }
    else:
        weak_contract = None

    return {
        "summary_schema_version": "0.1",
        "summary_type": "discovery_task_result",
        "task_name": "heat_pysindy_pde_task_smoke",
        "backend_name": "pysindy",
        "backend_version": {"pysindy": "1.7.5", "sklearn": "1.4.0", "pdelie": "0.30.0"},
        "target_convention": target_convention,
        "derivative_backend": "FiniteDifference",
        "input_layout": "scalar_1d_uniform",
        "library_feature_names": ["u", "u_x", "u_xx", "u*u_x"],
        "selected_terms": {"x0": {"u_xx": 0.1}},
        "coefficients": None,
        "support_precision": 1.0,
        "support_recall": 1.0,
        "support_f1": 1.0,
        "exact_support": True,
        "coefficient_relative_l2": 0.0,
        "train_residual": {"size": 128, "l2_norm": 0.01, "rms": 0.001, "max_abs": 0.002},
        "heldout_residual": None,
        "weak_contract": weak_contract,
        "warnings": [],
        "underlying_discovery_result": {
            "summary_schema_version": "0.1",
            "summary_type": "discovery_result",
            "status": "success",
            "backend": "pysindy",
            "feature_names": ["x0"],
            "library_feature_names": ["u", "u_x", "u_xx", "u*u_x"],
            "equation_terms": {"x0": {"u_xx": 0.1}},
            "equation_strings": {"x0": "0.100 u_xx"},
            "coefficient_summary": {
                "present": True,
                "shape": [1, 4],
                "finite": True,
                "l2_norm": 0.1,
                "linf_norm": 0.1,
                "nonzero_count": 1,
            },
            "support_epsilon": 1e-8,
            "fit_diagnostics": {},
            "fit_config": {},
            "failure_reason": None,
            "residuals": {"train": None, "heldout": None},
            "recovery": None,
            "returns_coefficients": False,
        },
    }


def test_valid_task_result_payload_passes_strict_json_check() -> None:
    """A well-formed TaskResult payload with only finite numbers must pass strict JSON."""
    payload = _build_minimal_task_result_payload()
    validated = _validate_strict_json_compatible(payload, name="discovery_task_result summary")
    assert json.loads(json.dumps(validated, allow_nan=False)) == validated


def test_task_result_schema_literal_invariants_match_design_doc() -> None:
    """The design-doc literal fields (schema version, summary type) hold at construction."""
    payload = _build_minimal_task_result_payload()
    assert payload["summary_schema_version"] == "0.1"
    assert payload["summary_type"] == "discovery_task_result"
    assert payload["backend_name"] == "pysindy"
    assert payload["target_convention"] in {"pde_library", "weak_pde_library"}
    assert payload["input_layout"] == "scalar_1d_uniform"


def test_weak_contract_trigger_predicate_documented_in_design() -> None:
    """weak_contract is non-null iff target_convention == 'weak_pde_library'."""
    pde = _build_minimal_task_result_payload(target_convention="pde_library")
    weak = _build_minimal_task_result_payload(target_convention="weak_pde_library")
    assert pde["weak_contract"] is None
    assert isinstance(weak["weak_contract"], dict)
    assert weak["weak_contract"]["diagnostic_only"] is True


def test_weak_wrapper_identifiers_distinct_from_pdelie_native_weak_1d() -> None:
    """WeakPDELibrary wrapper strings must not collide with pdelie-native weak_1d identifiers.

    The pdelie-native ``weak_1d`` module publishes:
        method_family    = "local_separable_quartic_bump_trapezoid_v1"
        test_function    = "separable_quartic_bump_beta"
        quadrature       = "composite_tensor_product_trapezoidal_native_window"

    at ``src/pdelie/residuals/weak_1d.py:20-22``. The wrapper strings must
    differ so downstream consumers can disambiguate provenance.
    """
    weak = _build_minimal_task_result_payload(target_convention="weak_pde_library")
    contract = weak["weak_contract"]
    assert isinstance(contract, dict)
    assert contract["method_family"] != "local_separable_quartic_bump_trapezoid_v1"
    assert contract["test_function_family"] != "separable_quartic_bump_beta"
    assert contract["quadrature_rule"] != "composite_tensor_product_trapezoidal_native_window"


def test_nan_adversarial_in_top_level_residual_is_rejected() -> None:
    """NaN in ``train_residual.l2_norm`` must be rejected by the strict-JSON check."""
    payload = _build_minimal_task_result_payload()
    assert isinstance(payload["train_residual"], dict)
    payload["train_residual"]["l2_norm"] = float("nan")
    with pytest.raises(SchemaValidationError):
        _validate_strict_json_compatible(payload, name="discovery_task_result summary")


def test_nan_adversarial_in_embedded_discovery_result_is_rejected() -> None:
    """NaN embedded in the underlying discovery_result summary must be rejected.

    This is the load-bearing test the peer-memo review flagged as absent: the
    strict-JSON contract must catch NaN that leaked in through the embedded
    ``underlying_discovery_result`` sub-summary, not only NaN placed at the
    TaskResult top level. This is the exact leak path the permissive
    ``_summary_payload`` funnel would allow through, so the v0.31b runtime
    MUST route the composed payload through ``_validate_strict_json_compatible``
    at the composition boundary.
    """
    payload = _build_minimal_task_result_payload()
    embedded = payload["underlying_discovery_result"]
    assert isinstance(embedded, dict)
    # Inject NaN into a nested coefficient-summary field of the embedded result.
    coefficient_summary = embedded["coefficient_summary"]
    assert isinstance(coefficient_summary, dict)
    coefficient_summary["l2_norm"] = float("nan")
    with pytest.raises(SchemaValidationError):
        _validate_strict_json_compatible(payload, name="discovery_task_result summary")


def test_nan_adversarial_in_weak_contract_is_rejected() -> None:
    """NaN inside the weak_contract subtree must also be rejected under the strict check."""
    payload = _build_minimal_task_result_payload(target_convention="weak_pde_library")
    contract = payload["weak_contract"]
    assert isinstance(contract, dict)
    contract["quadrature_relative_error"] = float("nan")
    with pytest.raises(SchemaValidationError):
        _validate_strict_json_compatible(payload, name="discovery_task_result summary")


def test_inf_adversarial_is_rejected() -> None:
    """Positive infinity in a residual field must also be rejected."""
    payload = _build_minimal_task_result_payload()
    assert isinstance(payload["train_residual"], dict)
    payload["train_residual"]["max_abs"] = float("inf")
    with pytest.raises(SchemaValidationError):
        _validate_strict_json_compatible(payload, name="discovery_task_result summary")


def test_planned_schema_matches_design_document_shape() -> None:
    """The manifest's ``planned_task_result_schema`` mirrors the fields the design doc names."""
    planned = _load_planned_schema()
    fields = planned["fields"]
    for required_field in (
        "task_name",
        "backend_name",
        "backend_version",
        "target_convention",
        "derivative_backend",
        "input_layout",
        "library_feature_names",
        "selected_terms",
        "coefficients",
        "support_precision",
        "support_recall",
        "support_f1",
        "exact_support",
        "coefficient_relative_l2",
        "train_residual",
        "heldout_residual",
        "weak_contract",
        "warnings",
        "underlying_discovery_result",
    ):
        assert required_field in fields, f"missing planned field: {required_field}"
