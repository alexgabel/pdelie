from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from typing import Any

import numpy as np

from pdelie import GeneratorFamily, InvariantMapSpec
from pdelie.contracts import FieldBatch, _translation_generator_basis_spec
from pdelie.data import generate_heat_1d_field_batch, generate_kdv_1d_field_batch
from pdelie.invariants import InvariantApplier
from pdelie.residuals import HeatResidualEvaluator, KdVResidualEvaluator, ResidualEvaluator


_SUMMARY_SCHEMA_VERSION = "0.1"
_DOMAIN_LENGTH = 2.0 * np.pi
_GRID_POINTS = 64
_COVERAGE_SHIFTS = (0.0, _DOMAIN_LENGTH / 4.0, _DOMAIN_LENGTH / 2.0, 3.0 * _DOMAIN_LENGTH / 4.0)
_TRANSFORM_SHIFTS = (0.0, _DOMAIN_LENGTH / _GRID_POINTS, _DOMAIN_LENGTH / 8.0, -_DOMAIN_LENGTH / 8.0, _DOMAIN_LENGTH)


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


def _relative_l2(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(left) - np.asarray(right)) / (np.linalg.norm(np.asarray(right)) + 1e-12))


def _rms(values: np.ndarray) -> float:
    normalized = np.asarray(values, dtype=float)
    return float(np.sqrt(np.mean(np.square(normalized))))


def _translation_generator() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


def _translation_spec(shift: float) -> InvariantMapSpec:
    return InvariantMapSpec(
        generator_metadata=_translation_generator().to_dict(),
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": float(shift)},
        domain_validity="global",
        inverse_available=True,
        diagnostics={"source": "v0.12_m4_orbit_coverage_feasibility"},
    )


def _periodic_window_mask(x: np.ndarray, *, start: float, width: float, domain_length: float) -> np.ndarray:
    normalized = (np.asarray(x, dtype=float) - float(start)) % float(domain_length)
    return normalized < float(width)


def _coverage_case(*, case_name: str, window_width: float) -> dict[str, object]:
    x = np.linspace(0.0, _DOMAIN_LENGTH, _GRID_POINTS, endpoint=False, dtype=float)
    base_windows = [{"start": 0.0, "width": float(window_width)}]
    coverage_counts = np.zeros(_GRID_POINTS, dtype=int)

    for window in base_windows:
        for shift in _COVERAGE_SHIFTS:
            coverage_counts += _periodic_window_mask(
                x,
                start=float(window["start"]) + float(shift),
                width=float(window["width"]),
                domain_length=_DOMAIN_LENGTH,
            ).astype(int)

    covered = int(np.count_nonzero(coverage_counts))
    zero_runs = _zero_run_lengths(coverage_counts)
    return _json_safe(
        {
            "case_name": case_name,
            "domain_length": _DOMAIN_LENGTH,
            "grid_points": _GRID_POINTS,
            "base_windows": base_windows,
            "shifts": list(_COVERAGE_SHIFTS),
            "covered_grid_point_count": covered,
            "coverage_fraction": float(covered / _GRID_POINTS),
            "min_coverage_count": int(np.min(coverage_counts)),
            "max_coverage_count": int(np.max(coverage_counts)),
            "mean_coverage_count": float(np.mean(coverage_counts)),
            "max_uncovered_run_points": int(max(zero_runs, default=0)),
        }
    )


def _zero_run_lengths(counts: np.ndarray) -> list[int]:
    uncovered = np.asarray(counts) == 0
    if not np.any(uncovered):
        return []
    doubled = np.concatenate([uncovered, uncovered])
    runs: list[int] = []
    current = 0
    for value in doubled:
        if value:
            current += 1
        elif current:
            runs.append(min(current, uncovered.size))
            current = 0
    if current:
        runs.append(min(current, uncovered.size))
    return runs


def _residual_rms(field: FieldBatch, evaluator: ResidualEvaluator) -> float:
    return _rms(evaluator.evaluate(field).residual)


def _transform_consistency_case(
    *,
    field_name: str,
    field: FieldBatch,
    evaluator: ResidualEvaluator,
) -> dict[str, object]:
    applier = InvariantApplier()
    before_rms = _residual_rms(field, evaluator)
    shift_reports: list[dict[str, object]] = []

    for shift in _TRANSFORM_SHIFTS:
        transformed = applier.apply(field, _translation_spec(float(shift)))
        inverted = applier.apply(transformed, _translation_spec(-float(shift)))
        period_wrapped = applier.apply(field, _translation_spec(float(shift) + _DOMAIN_LENGTH))
        after_rms = _residual_rms(transformed, evaluator)
        relative_delta = abs(after_rms - before_rms) / (abs(before_rms) + 1e-12)
        provenance = transformed.preprocess_log[-1]
        shift_reports.append(
            _json_safe(
                {
                    "shift": float(shift),
                    "dims_preserved": transformed.dims == field.dims,
                    "coords_preserved": all(
                        np.allclose(transformed.coords[name], field.coords[name], rtol=0.0, atol=1e-12)
                        for name in field.coords
                    ),
                    "var_names_preserved": transformed.var_names == field.var_names,
                    "metadata_preserved": transformed.metadata == field.metadata,
                    "mask_preserved": (
                        transformed.mask is None
                        if field.mask is None
                        else np.array_equal(transformed.mask, field.mask)
                    ),
                    "inverse_relative_l2_error": _relative_l2(inverted.values, field.values),
                    "period_wrap_relative_l2_error": _relative_l2(period_wrapped.values, transformed.values),
                    "residual_rms_before": before_rms,
                    "residual_rms_after": after_rms,
                    "residual_relative_rms_delta": float(relative_delta),
                    "provenance_operation": provenance["operation"],
                    "provenance_construction_method": provenance["construction_method"],
                    "preprocess_log_length_delta": len(transformed.preprocess_log) - len(field.preprocess_log),
                }
            )
        )

    return _json_safe(
        {
            "field_name": field_name,
            "equation": field.metadata["parameter_tags"].get("equation", "heat_1d"),
            "shifts": list(_TRANSFORM_SHIFTS),
            "shift_reports": shift_reports,
        }
    )


def run_orbit_coverage_feasibility() -> dict[str, object]:
    heat = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=_GRID_POINTS, seed=1201)
    kdv = generate_kdv_1d_field_batch(batch_size=2, num_times=17, num_points=_GRID_POINTS, seed=1202)

    return _json_safe(
        {
            "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
            "summary_type": "orbit_coverage_feasibility",
            "coverage_cases": [
                _coverage_case(case_name="half_coverage_quarter_shifts", window_width=_DOMAIN_LENGTH / 8.0),
                _coverage_case(case_name="full_coverage_quarter_shifts", window_width=_DOMAIN_LENGTH / 4.0),
            ],
            "transform_consistency_cases": [
                _transform_consistency_case(
                    field_name="heat_default",
                    field=heat,
                    evaluator=HeatResidualEvaluator(),
                ),
                _transform_consistency_case(
                    field_name="kdv_default",
                    field=kdv,
                    evaluator=KdVResidualEvaluator(),
                ),
            ],
        }
    )


@lru_cache(maxsize=1)
def _cached_orbit_coverage_feasibility() -> dict[str, object]:
    return run_orbit_coverage_feasibility()


def cached_orbit_coverage_feasibility() -> dict[str, object]:
    return deepcopy(_cached_orbit_coverage_feasibility())
