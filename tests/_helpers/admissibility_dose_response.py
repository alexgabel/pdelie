"""v0.33d admissibility dose-response: spec, measurement, and regeneration CLI.

The v0.33d crash test is a binary CI gate (``residual_l2 >= 10x``). This module
pins the underlying *dose-response curve* -- how the constant-coefficient
method's ``residual_l2`` grows with the amplitude of the variable-coefficient
perturbation -- so the claim can be cited rather than merely asserted.

Profile family::

    nu_alpha(x) = nu_0 * (1 + alpha * sin(2*pi*x/L))

``alpha = 0.0`` is the control: the profile is a constant array, so it routes
through the RK4 variable-coefficient path rather than the closed-form
constant-coefficient path. Its ratio isolates integrator error from the
variable-coefficient effect -- a ratio near 1.0 means the measured growth at
``alpha > 0`` is attributable to x-dependence and not to having switched
numerical schemes.

This is a separate fixture from ``v0_33e_golden_numbers.json`` by design: the
dose-response *requires* the v0.33d generators, so it cannot live in a v0.33e
artifact that pins the constant-coefficient pipeline. The v0.33e fixture, its
schema, and its regeneration CLI are left untouched.

Regeneration::

    python -m tests._helpers.admissibility_dose_response --reason "<named cause>"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from pdelie.data import (
    generate_advection_diffusion_1d_field_batch,
    generate_burgers_1d_field_batch,
    generate_heat_1d_field_batch,
)
from pdelie.data.heat_1d import DEFAULT_DOMAIN_LENGTH
from pdelie.residuals import (
    AdvectionDiffusionResidualEvaluator,
    BurgersResidualEvaluator,
    HeatResidualEvaluator,
)
from pdelie.symmetry.methods.polynomial_translation_svd import PolynomialTranslationSvdMethod

_REPO_ROOT = Path(__file__).resolve().parents[2]
DOSE_RESPONSE_FIXTURE_PATH = (
    _REPO_ROOT / "tests" / "fixtures" / "v0_33d_admissibility_dose_response.json"
)

SUMMARY_SCHEMA_VERSION = "0.1"
SUMMARY_TYPE = "pdelie_admissibility_dose_response_fixture"

NUM_POINTS = 64
SEED = 0

#: Perturbation amplitudes. 0.0 is the integrator control; 0.5 is the frozen
#: crash-test profile.
DOSE_RESPONSE_ALPHAS: tuple[float, ...] = (0.0, 0.1, 0.25, 0.5, 0.75)

#: Same cross-BLAS reasoning as the v0.33e gate: aggregate scalars only, never
#: bit-exact comparison.
DOSE_RESPONSE_RTOL = 1e-6
DOSE_RESPONSE_ATOL = 1e-12

_PDE_SPECS = (
    ("heat_1d", generate_heat_1d_field_batch,
     {"batch_size": 1, "num_times": 17, "num_points": NUM_POINTS, "seed": SEED},
     0.1, lambda: HeatResidualEvaluator(diffusivity=0.1)),
    ("burgers_1d", generate_burgers_1d_field_batch,
     {"batch_size": 1, "num_times": 33, "num_points": NUM_POINTS, "seed": SEED},
     0.1, lambda: BurgersResidualEvaluator(diffusivity=0.1)),
    ("advection_diffusion_1d", generate_advection_diffusion_1d_field_batch,
     {"batch_size": 1, "num_times": 65, "num_points": NUM_POINTS, "seed": SEED},
     0.05, lambda: AdvectionDiffusionResidualEvaluator(advection_speed=0.75, diffusivity=0.05)),
)

DOSE_RESPONSE_PDE_NAMES: tuple[str, ...] = tuple(spec[0] for spec in _PDE_SPECS)


def _profile(base: float, alpha: float) -> np.ndarray:
    x = np.linspace(0.0, DEFAULT_DOMAIN_LENGTH, NUM_POINTS, endpoint=False, dtype=float)
    return base * (1.0 + alpha * np.sin(2.0 * np.pi * x / DEFAULT_DOMAIN_LENGTH))


def measure_dose_response() -> list[dict[str, Any]]:
    method = PolynomialTranslationSvdMethod()
    entries: list[dict[str, Any]] = []
    for name, generator, kwargs, base, evaluator in _PDE_SPECS:
        reference = method.fit(
            generator(**kwargs), residual_evaluator=evaluator()
        ).method_scores["residual_l2"]
        points = []
        for alpha in DOSE_RESPONSE_ALPHAS:
            field = generator(**kwargs, diffusivity_profile=_profile(base, alpha))
            residual_l2 = method.fit(field, residual_evaluator=evaluator()).method_scores["residual_l2"]
            points.append(
                {
                    "alpha": float(alpha),
                    "residual_l2": float(residual_l2),
                    "ratio_to_constant_reference": float(residual_l2 / reference),
                }
            )
        entries.append(
            {
                "name": name,
                "constant_reference_residual_l2": float(reference),
                "dose_response": points,
            }
        )
    return entries


def build_payload(*, reason: str) -> dict[str, Any]:
    return {
        "summary_schema_version": SUMMARY_SCHEMA_VERSION,
        "summary_type": SUMMARY_TYPE,
        "profile_family": "nu_0*(1+alpha*sin(2*pi*x/L))",
        "diffusivity_form": "conservative_divergence",
        "generator_seed": SEED,
        "num_points": NUM_POINTS,
        "alphas": list(DOSE_RESPONSE_ALPHAS),
        "last_regeneration_reason": reason,
        "pdes": measure_dose_response(),
    }


def load_fixture() -> dict[str, Any]:
    with DOSE_RESPONSE_FIXTURE_PATH.open(encoding="utf-8") as handle:
        payload: dict[str, Any] = json.load(handle)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tests._helpers.admissibility_dose_response",
        description="Regenerate the v0.33d admissibility dose-response fixture.",
    )
    parser.add_argument("--reason", required=True, help="Named cause for the change.")
    args = parser.parse_args(argv)

    if not args.reason.strip():
        raise ValueError("A non-empty --reason is required.")

    payload = build_payload(reason=args.reason)
    DOSE_RESPONSE_FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOSE_RESPONSE_FIXTURE_PATH.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {DOSE_RESPONSE_FIXTURE_PATH.relative_to(_REPO_ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
