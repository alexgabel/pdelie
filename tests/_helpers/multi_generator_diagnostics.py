from __future__ import annotations

from typing import Any

import numpy as np

from pdelie import GeneratorFamily
from pdelie.symmetry import compare_generator_spans


_FIT_PROBE_SEEDS = (2701, 2702, 2703)


def _x_basis_spec() -> dict[str, object]:
    return {
        "variables": ["x"],
        "component_names": ["xi"],
        "basis_terms": [
            {"label": "1", "powers": [0]},
            {"label": "x", "powers": [1]},
        ],
        "component_ordering": ["xi"],
        "term_ordering": ["1", "x"],
        "layout": "component_major",
    }


def _family(coefficients: np.ndarray, *, name: str) -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="internal_multi_generator_fit_probe",
        coefficients=np.asarray(coefficients, dtype=float),
        basis_spec=_x_basis_spec(),
        normalization="runtime_fixture",
        generator_names=[f"{name}_{index}" for index in range(int(coefficients.shape[0]))],
        diagnostics={"visibility": "internal_test_only"},
    )


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def run_internal_multi_generator_fit_probe() -> dict[str, object]:
    """Return deterministic, internal-only span-recoverability diagnostics.

    The probe uses a frozen linear design surrogate whose row space is the
    target two-generator affine span. It is deliberately test-only and does
    not define a public fitting algorithm.
    """

    reference = _family(np.eye(2, dtype=float), name="reference_affine_x")
    cases: list[dict[str, object]] = []
    for seed in _FIT_PROBE_SEEDS:
        rng = np.random.default_rng(seed)
        mixing = rng.normal(size=(5, 2))
        design_matrix = mixing @ np.asarray(reference.coefficients, dtype=float)
        _, singular_values, vh = np.linalg.svd(design_matrix, full_matrices=False)
        candidate = _family(vh[:2], name=f"probe_seed_{seed}")
        span_report = compare_generator_spans(reference, candidate)
        passed = (
            span_report["comparison_status"] == "passed"
            and float(span_report["projection_residual"]["summary"]) <= 1e-12
        )
        cases.append(
            {
                "seed": seed,
                "design_shape": list(design_matrix.shape),
                "singular_values": singular_values.tolist(),
                "span_report": span_report,
                "passed": bool(passed),
            }
        )

    passed = all(bool(case["passed"]) for case in cases)
    return _json_safe(
        {
            "summary_schema_version": "0.1",
            "summary_type": "multi_generator_fit_probe",
            "visibility": "internal_test_only",
            "label": "fit_probe_diagnostic_only",
            "passed": passed,
            "future_promotion_candidate": False,
            "public_api_promoted": False,
            "probe_policy": {
                "no_public_import_path": True,
                "no_runtime_example": True,
                "no_best_of_sweep_promotion": True,
            },
            "cases": cases,
        }
    )
