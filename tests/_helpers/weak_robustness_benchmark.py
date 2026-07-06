from __future__ import annotations

import importlib
from collections.abc import Callable

import numpy as np

from pdelie import FieldBatch, GeneratorFamily
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import (
    add_gaussian_noise,
    from_numpy,
    generate_burgers_1d_field_batch,
    generate_heat_1d_field_batch,
    subsample_time,
    subsample_x,
)
from pdelie.residuals import (
    BurgersResidualEvaluator,
    HeatResidualEvaluator,
    evaluate_weak_burgers_residual,
    evaluate_weak_heat_residual,
)
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.parameterization.polynomial_translation import (
    DEFAULT_TRANSLATION_SPAN_TOLERANCE,
    _coerce_translation_coefficients,
    translation_reference_coefficients,
    translation_span_distance,
)
from pdelie.verification import DEFAULT_EPSILON_VALUES, verify_translation_generator
from tests._helpers.weak_contract_integration import (
    fit_translation_generator_from_weak_reports,
    verify_translation_generator_from_weak_reports,
)

WrongReportEvaluator = Callable[[FieldBatch], dict[str, object]]

M4_BENCHMARK_CONFIG: dict[str, object] = {
    "train_batch_size": 4,
    "heldout_batch_size": 3,
    "num_times": 33,
    "num_points": 64,
    "noise_std_fraction": 1e-3,
    "coarse_time_stride": 2,
    "coarse_x_stride": 2,
    "heat_train_seed": 8401,
    "heat_heldout_seed": 8402,
    "heat_train_noise_seed": 8403,
    "heat_heldout_noise_seed": 8404,
    "burgers_train_seed": 8501,
    "burgers_heldout_seed": 8502,
    "burgers_train_noise_seed": 8503,
    "burgers_heldout_noise_seed": 8504,
    "wrong_generator_coefficients": [0.0, 0.0, 1.0, 0.0],
    "wrong_generator_description": "x-basis affine non-translation control",
}

PATH_SUMMARY_STRUCTURAL_KEYS = (
    "path",
    "pde",
    "condition",
    "fit_mode",
    "reference_fallback_used",
    "fallback_reason",
    "contract_mode",
    "contract_stable",
    "transform_mode",
    "deterministic",
    "wrong_generator_description",
)
_RAW_PATH_SUMMARY_STRUCTURAL_KEYS = tuple(
    key for key in PATH_SUMMARY_STRUCTURAL_KEYS if key not in {"contract_stable", "deterministic"}
)
PATH_SUMMARY_FLOAT_KEYS = (
    "selected_span_distance",
    "first_epsilon",
    "first_epsilon_fitted_error",
    "first_epsilon_wrong_error",
    "first_epsilon_wrong_to_fitted_ratio",
)
IMPORTED_PARITY_STRUCTURAL_KEYS = (
    "fit_mode",
    "reference_fallback_used",
    "fallback_reason",
    "contract_mode",
    "contract_stable",
    "transform_mode",
    "wrong_generator_description",
)
IMPORTED_PARITY_FLOAT_KEYS = (
    "selected_span_distance",
    "first_epsilon",
    "first_epsilon_fitted_error",
    "first_epsilon_wrong_error",
    "first_epsilon_wrong_to_fitted_ratio",
)
COMPARISON_SUMMARY_KEYS = (
    "weak_contract_mode",
    "strong_contract_mode",
    "weak_contract_stable",
    "strong_contract_stable",
    "weak_ratio",
    "strong_ratio",
    "robustness_signal_source",
    "weak_has_robustness_signal",
)

_NATIVE_CONDITIONS = ("clean", "noisy", "coarse")
_IMPORTED_CASES = (("heat", "noisy"), ("burgers", "coarse"))


def _make_wrong_generator() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.asarray(M4_BENCHMARK_CONFIG["wrong_generator_coefficients"], dtype=float).reshape(1, -1),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


def _field_factory_for_pde(pde_name: str) -> Callable[..., FieldBatch]:
    if pde_name == "heat":
        return generate_heat_1d_field_batch
    if pde_name == "burgers":
        return generate_burgers_1d_field_batch
    raise ValueError(f"Unsupported PDE name {pde_name!r}.")


def _strong_evaluator_for_pde(pde_name: str) -> HeatResidualEvaluator | BurgersResidualEvaluator:
    if pde_name == "heat":
        return HeatResidualEvaluator()
    if pde_name == "burgers":
        return BurgersResidualEvaluator()
    raise ValueError(f"Unsupported PDE name {pde_name!r}.")


def _weak_evaluator_for_pde(pde_name: str) -> WrongReportEvaluator:
    if pde_name == "heat":
        return evaluate_weak_heat_residual
    if pde_name == "burgers":
        return evaluate_weak_burgers_residual
    raise ValueError(f"Unsupported PDE name {pde_name!r}.")


def _coarse_field(field: FieldBatch) -> FieldBatch:
    return subsample_x(
        subsample_time(field, stride=int(M4_BENCHMARK_CONFIG["coarse_time_stride"])),
        stride=int(M4_BENCHMARK_CONFIG["coarse_x_stride"]),
    )


def _apply_condition(
    field: FieldBatch,
    *,
    condition: str,
    noise_seed: int,
) -> FieldBatch:
    if condition == "clean":
        return field
    if condition == "noisy":
        return add_gaussian_noise(
            field,
            std_fraction=float(M4_BENCHMARK_CONFIG["noise_std_fraction"]),
            seed=noise_seed,
        )
    if condition == "coarse":
        return _coarse_field(field)
    raise ValueError(f"Unsupported condition {condition!r}.")


def _build_native_case(pde_name: str, condition: str) -> tuple[FieldBatch, FieldBatch]:
    factory = _field_factory_for_pde(pde_name)
    train_seed = int(M4_BENCHMARK_CONFIG[f"{pde_name}_train_seed"])
    heldout_seed = int(M4_BENCHMARK_CONFIG[f"{pde_name}_heldout_seed"])
    train_noise_seed = int(M4_BENCHMARK_CONFIG[f"{pde_name}_train_noise_seed"])
    heldout_noise_seed = int(M4_BENCHMARK_CONFIG[f"{pde_name}_heldout_noise_seed"])

    training = factory(
        seed=train_seed,
        batch_size=int(M4_BENCHMARK_CONFIG["train_batch_size"]),
        num_times=int(M4_BENCHMARK_CONFIG["num_times"]),
        num_points=int(M4_BENCHMARK_CONFIG["num_points"]),
    )
    heldout = factory(
        seed=heldout_seed,
        batch_size=int(M4_BENCHMARK_CONFIG["heldout_batch_size"]),
        num_times=int(M4_BENCHMARK_CONFIG["num_times"]),
        num_points=int(M4_BENCHMARK_CONFIG["num_points"]),
    )
    return (
        _apply_condition(training, condition=condition, noise_seed=train_noise_seed),
        _apply_condition(heldout, condition=condition, noise_seed=heldout_noise_seed),
    )


def _import_from_numpy(field: FieldBatch) -> FieldBatch:
    mask = None if field.mask is None else field.mask[..., 0]
    return from_numpy(
        field.values[..., 0],
        dims=("batch", "time", "x"),
        coords={"time": field.coords["time"], "x": field.coords["x"]},
        var_name=field.var_names[0],
        metadata=field.metadata,
        mask=mask,
        preprocess_log=field.preprocess_log,
    )


def _import_from_xarray(field: FieldBatch) -> FieldBatch:
    xr = importlib.import_module("xarray")
    from_xarray = importlib.import_module("pdelie.data").from_xarray
    coords = {
        "batch": np.arange(field.values.shape[0], dtype=int),
        "time": field.coords["time"],
        "x": field.coords["x"],
    }
    data_array = xr.DataArray(
        field.values[..., 0],
        dims=("batch", "time", "x"),
        coords=coords,
        name=field.var_names[0],
    )
    mask = None
    if field.mask is not None:
        mask = xr.DataArray(
            field.mask[..., 0],
            dims=("batch", "time", "x"),
            coords=coords,
        )
    return from_xarray(
        data_array,
        metadata=field.metadata,
        mask=mask,
        preprocess_log=field.preprocess_log,
    )


def _import_field(field: FieldBatch, *, importer_name: str) -> FieldBatch:
    if importer_name == "from_numpy":
        return _import_from_numpy(field)
    if importer_name == "from_xarray":
        return _import_from_xarray(field)
    raise ValueError(f"Unsupported importer {importer_name!r}.")


def _build_imported_case(pde_name: str, condition: str, *, importer_name: str) -> tuple[FieldBatch, FieldBatch]:
    native_training, native_heldout = _build_native_case(pde_name, condition)
    return _import_field(native_training, importer_name=importer_name), _import_field(
        native_heldout,
        importer_name=importer_name,
    )


def _compute_ratio(*, fitted_error: float, wrong_error: float) -> float:
    if fitted_error == 0.0:
        return float("inf")
    return float(wrong_error / fitted_error)


def _contract_mode(
    coefficients: np.ndarray,
    *,
    reference_fallback_used: bool,
) -> str:
    reference = translation_reference_coefficients()
    if reference_fallback_used and np.allclose(coefficients, reference, rtol=0.0, atol=1e-12):
        return "canonical_fallback"
    if translation_span_distance(coefficients) <= DEFAULT_TRANSLATION_SPAN_TOLERANCE:
        return "in_tolerance_fit"
    return "out_of_tolerance"


def _summaries_match(first: dict[str, object], second: dict[str, object]) -> bool:
    for key in _RAW_PATH_SUMMARY_STRUCTURAL_KEYS:
        if first[key] != second[key]:
            return False
    for key in PATH_SUMMARY_FLOAT_KEYS:
        # This benchmark calls SVD-backed fitting twice and records a deterministic
        # bit. LAPACK-level final-digit jitter is not a contract failure here; the
        # robustness signal and frozen thresholds operate at much wider margins.
        if not np.allclose(float(first[key]), float(second[key]), rtol=1e-8, atol=1e-12):
            return False
    return True


def _run_strong_case_once(
    pde_name: str,
    condition: str,
    training: FieldBatch,
    heldout: FieldBatch,
) -> tuple[dict[str, object], dict[str, object]]:
    evaluator = _strong_evaluator_for_pde(pde_name)
    generator = fit_translation_generator(training, evaluator, epsilon=1e-4)
    fitted_report = verify_translation_generator(heldout, generator, evaluator)
    wrong_report = verify_translation_generator(heldout, _make_wrong_generator(), evaluator)

    coefficients = _coerce_translation_coefficients(generator.coefficients)
    reference_fallback_used = bool(generator.diagnostics["reference_fallback_used"])
    contract_mode = _contract_mode(coefficients, reference_fallback_used=reference_fallback_used)
    first_epsilon = float(np.asarray(fitted_report.epsilon_values, dtype=float)[0])
    fitted_error = float(np.asarray(fitted_report.error_curve, dtype=float)[0])
    wrong_error = float(np.asarray(wrong_report.error_curve, dtype=float)[0])

    return (
        {
            "path": "strong",
            "pde": pde_name,
            "condition": condition,
            "fit_mode": str(generator.diagnostics["fit_mode"]),
            "reference_fallback_used": reference_fallback_used,
            "fallback_reason": generator.diagnostics["fallback_reason"],
            "selected_span_distance": float(translation_span_distance(coefficients)),
            "contract_mode": contract_mode,
            "transform_mode": str(fitted_report.diagnostics["transform_mode"]),
            "first_epsilon": first_epsilon,
            "first_epsilon_fitted_error": fitted_error,
            "first_epsilon_wrong_error": wrong_error,
            "first_epsilon_wrong_to_fitted_ratio": _compute_ratio(fitted_error=fitted_error, wrong_error=wrong_error),
            "wrong_generator_description": str(M4_BENCHMARK_CONFIG["wrong_generator_description"]),
        },
        {
            "verification_classification": fitted_report.classification,
        },
    )


def _run_weak_case_once(
    pde_name: str,
    condition: str,
    training: FieldBatch,
    heldout: FieldBatch,
) -> tuple[dict[str, object], dict[str, object]]:
    evaluator = _weak_evaluator_for_pde(pde_name)
    fit_result = fit_translation_generator_from_weak_reports(training, evaluator, epsilon=1e-4)
    fitted_report = verify_translation_generator_from_weak_reports(heldout, fit_result["generator"], evaluator)
    wrong_report = verify_translation_generator_from_weak_reports(heldout, _make_wrong_generator(), evaluator)

    coefficients = _coerce_translation_coefficients(fit_result["generator"].coefficients)
    reference_fallback_used = bool(fit_result["reference_fallback_used"])
    contract_mode = _contract_mode(coefficients, reference_fallback_used=reference_fallback_used)
    first_epsilon = float(np.asarray(fitted_report["relative_to_field_norm_error_curve"], dtype=float)[0:1][0])
    wrong_error = float(np.asarray(wrong_report["relative_to_field_norm_error_curve"], dtype=float)[0:1][0])

    return (
        {
            "path": "weak",
            "pde": pde_name,
            "condition": condition,
            "fit_mode": str(fit_result["fit_mode"]),
            "reference_fallback_used": reference_fallback_used,
            "fallback_reason": fit_result["fallback_reason"],
            "selected_span_distance": float(fit_result["selected_span_distance"]),
            "contract_mode": contract_mode,
            "transform_mode": str(fitted_report["transform_mode"]),
            "first_epsilon": float(np.asarray(DEFAULT_EPSILON_VALUES, dtype=float)[0]),
            "first_epsilon_fitted_error": first_epsilon,
            "first_epsilon_wrong_error": wrong_error,
            "first_epsilon_wrong_to_fitted_ratio": _compute_ratio(fitted_error=first_epsilon, wrong_error=wrong_error),
            "wrong_generator_description": str(M4_BENCHMARK_CONFIG["wrong_generator_description"]),
        },
        {},
    )


def _finalize_strong_summary(
    summary: dict[str, object],
    internal: dict[str, object],
    *,
    deterministic: bool,
) -> dict[str, object]:
    contract_stable = (
        deterministic
        and summary["contract_mode"] != "out_of_tolerance"
        and summary["transform_mode"] == "uniform_translation"
        and internal["verification_classification"] != "failed"
    )
    return {
        **summary,
        "contract_stable": contract_stable,
        "deterministic": deterministic,
    }


def _finalize_weak_summary(
    summary: dict[str, object],
    *,
    deterministic: bool,
) -> dict[str, object]:
    contract_stable = (
        deterministic
        and summary["contract_mode"] != "out_of_tolerance"
        and summary["transform_mode"] == "uniform_translation"
    )
    return {
        **summary,
        "contract_stable": contract_stable,
        "deterministic": deterministic,
    }


def _comparison_summary(
    strong: dict[str, object],
    weak: dict[str, object],
) -> dict[str, object]:
    strong_ratio = float(strong["first_epsilon_wrong_to_fitted_ratio"])
    weak_ratio = float(weak["first_epsilon_wrong_to_fitted_ratio"])

    robustness_signal_source = "none"
    if bool(weak["deterministic"]) and bool(weak["contract_stable"]) and not bool(strong["contract_stable"]):
        robustness_signal_source = "contract_stability_signal"
    elif bool(weak["deterministic"]) and weak_ratio >= 1.5 * strong_ratio and weak_ratio >= 3.0:
        robustness_signal_source = "separation_signal"

    return {
        "weak_contract_mode": str(weak["contract_mode"]),
        "strong_contract_mode": str(strong["contract_mode"]),
        "weak_contract_stable": bool(weak["contract_stable"]),
        "strong_contract_stable": bool(strong["contract_stable"]),
        "weak_ratio": weak_ratio,
        "strong_ratio": strong_ratio,
        "robustness_signal_source": robustness_signal_source,
        "weak_has_robustness_signal": robustness_signal_source != "none",
    }


def _run_case_once(
    pde_name: str,
    condition: str,
    *,
    importer_name: str | None,
) -> dict[str, object]:
    if importer_name is None:
        training, heldout = _build_native_case(pde_name, condition)
    else:
        training, heldout = _build_imported_case(pde_name, condition, importer_name=importer_name)
    strong_summary, strong_internal = _run_strong_case_once(pde_name, condition, training, heldout)
    weak_summary, weak_internal = _run_weak_case_once(pde_name, condition, training, heldout)
    return {
        "strong_summary": strong_summary,
        "strong_internal": strong_internal,
        "weak_summary": weak_summary,
        "weak_internal": weak_internal,
    }


def _run_matrix_once(
    *,
    importer_name: str | None,
    cases: tuple[tuple[str, str], ...],
) -> dict[str, dict[str, dict[str, object]]]:
    matrix: dict[str, dict[str, dict[str, object]]] = {}
    for pde_name, condition in cases:
        matrix.setdefault(pde_name, {})[condition] = _run_case_once(
            pde_name,
            condition,
            importer_name=importer_name,
        )
    return matrix


def _finalize_matrix(
    first: dict[str, dict[str, dict[str, object]]],
    second: dict[str, dict[str, dict[str, object]]],
) -> dict[str, dict[str, dict[str, object]]]:
    finalized: dict[str, dict[str, dict[str, object]]] = {}
    for pde_name, condition_map in first.items():
        finalized[pde_name] = {}
        for condition, first_case in condition_map.items():
            second_case = second[pde_name][condition]
            strong_deterministic = _summaries_match(
                first_case["strong_summary"],
                second_case["strong_summary"],
            )
            weak_deterministic = _summaries_match(
                first_case["weak_summary"],
                second_case["weak_summary"],
            )
            strong = _finalize_strong_summary(
                dict(first_case["strong_summary"]),
                dict(first_case["strong_internal"]),
                deterministic=strong_deterministic,
            )
            weak = _finalize_weak_summary(
                dict(first_case["weak_summary"]),
                deterministic=weak_deterministic,
            )
            finalized[pde_name][condition] = {
                "strong": strong,
                "weak": weak,
                "comparison": _comparison_summary(strong, weak),
            }
    return finalized


def run_native_weak_robustness_benchmark() -> dict[str, dict[str, dict[str, object]]]:
    cases = tuple((pde_name, condition) for pde_name in ("heat", "burgers") for condition in _NATIVE_CONDITIONS)
    # Warm the internal fitting / verification stack once so the reproducibility
    # bit reflects steady-state behavior rather than first-call startup drift.
    _run_matrix_once(importer_name=None, cases=cases)
    first = _run_matrix_once(importer_name=None, cases=cases)
    second = _run_matrix_once(importer_name=None, cases=cases)
    return _finalize_matrix(first, second)


def run_imported_weak_robustness_benchmark(*, importer_name: str) -> dict[str, dict[str, dict[str, object]]]:
    if importer_name not in {"from_numpy", "from_xarray"}:
        raise ValueError("importer_name must be 'from_numpy' or 'from_xarray'.")
    _run_matrix_once(importer_name=importer_name, cases=_IMPORTED_CASES)
    first = _run_matrix_once(importer_name=importer_name, cases=_IMPORTED_CASES)
    second = _run_matrix_once(importer_name=importer_name, cases=_IMPORTED_CASES)
    return _finalize_matrix(first, second)


__all__ = [
    "COMPARISON_SUMMARY_KEYS",
    "IMPORTED_PARITY_FLOAT_KEYS",
    "IMPORTED_PARITY_STRUCTURAL_KEYS",
    "M4_BENCHMARK_CONFIG",
    "PATH_SUMMARY_FLOAT_KEYS",
    "PATH_SUMMARY_STRUCTURAL_KEYS",
    "run_imported_weak_robustness_benchmark",
    "run_native_weak_robustness_benchmark",
]
