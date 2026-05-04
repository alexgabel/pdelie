from __future__ import annotations

import json

from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.reporting import summarize_weak_form_supportability
from pdelie.residuals import (
    BurgersResidualEvaluator,
    HeatResidualEvaluator,
    evaluate_weak_burgers_residual,
    evaluate_weak_heat_residual,
)


_SUMMARY_SCHEMA_VERSION = "0.1"


def _static_fisher_kpp_feasibility() -> dict[str, object]:
    return {
        "summary_schema_version": "0.1",
        "summary_type": "weak_reaction_diffusion_feasibility",
        "visibility": "internal_diagnostic_only",
        "pde": "reaction_diffusion_fisher_kpp",
        "equation_form": "u_t = nu*u_xx + rho*u*(1-u)",
        "quadrature_rule": "identity_first_internal_feasibility_only",
        "conclusion": "diagnostic_only",
        "identity_tests": {
            "constant_field": "not_run_in_runtime_example",
            "pure_time_sign": "not_run_in_runtime_example",
            "pure_space_fourier_integration_by_parts": "not_run_in_runtime_example",
            "manufactured_fisher_kpp_smooth_field": "not_run_in_runtime_example",
        },
        "public_api": {
            "exports_weak_reaction_diffusion": False,
            "exports_weak_derivative_backend": False,
            "exports_wsindy_design_matrix": False,
        },
        "interpretation": "static_runtime_marker_for_internal_test_only_feasibility",
    }


def run_weak_form_supportability_example() -> dict[str, object]:
    heat = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=32, seed=24001)
    burgers = generate_burgers_1d_field_batch(batch_size=2, num_times=17, num_points=32, seed=24002)

    heat_strong = HeatResidualEvaluator().evaluate(heat, compute_spectral_fd_derivatives(heat))
    burgers_strong = BurgersResidualEvaluator().evaluate(burgers, compute_spectral_fd_derivatives(burgers))
    heat_weak = evaluate_weak_heat_residual(heat)
    burgers_weak = evaluate_weak_burgers_residual(burgers)

    heat_supportability = summarize_weak_form_supportability(
        weak_report=heat_weak,
        strong_residual=heat_strong,
        thresholds={
            "finite_required": True,
            "min_weak_rows": 1,
            "max_skipped_fraction": 0.0,
        },
        extra_metrics={"case_name": "heat_weak_public_slice"},
    )
    burgers_supportability = summarize_weak_form_supportability(
        weak_report=burgers_weak,
        strong_residual=burgers_strong,
        thresholds={
            "finite_required": True,
            "min_weak_rows": 1,
            "max_skipped_fraction": 0.0,
        },
        extra_metrics={"case_name": "burgers_weak_public_slice"},
    )
    fisher_feasibility = summarize_weak_form_supportability(
        feasibility=_static_fisher_kpp_feasibility(),
        extra_metrics={"case_name": "fisher_kpp_internal_feasibility_marker"},
    )

    return {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "weak_form_supportability_example",
        "cases": [
            {"case_name": "heat_weak_public_slice", "supportability": heat_supportability},
            {"case_name": "burgers_weak_public_slice", "supportability": burgers_supportability},
            {
                "case_name": "fisher_kpp_internal_feasibility_marker",
                "supportability": fisher_feasibility,
            },
        ],
        "extra_metrics": {
            "example_name": "weak_form_supportability",
            "supportability_labels": [
                heat_supportability["supportability_label"],
                burgers_supportability["supportability_label"],
                fisher_feasibility["supportability_label"],
            ],
            "interpretation": "weak_supportability_reports_not_wsindy_or_weak_backend",
        },
    }


def main() -> None:
    print(json.dumps(run_weak_form_supportability_example(), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
