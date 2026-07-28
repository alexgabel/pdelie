"""v0.34c conditioning-ratio fixture: spec, measurement, and regeneration CLI.

Why this fixture exists in the shape it does
--------------------------------------------

The v0.34 plan carried three headline figures for column normalization: an 87x
column-scale ratio and a condition number of 111.8 falling to 3.77. Measurement
during the v0.34c prototype could not reproduce them on any of 48 swept
configurations, and the reason turned out to be structural rather than a
mis-recorded number:

``pysindy.WeakPDELibrary`` places its ``K`` domain centers by drawing from the
global NumPy RNG and exposes **no seed parameter**. The weak diagnostic was
therefore nondeterministic run-to-run -- back-to-back default calls produced
``matrix_condition_number`` of 7.69 and 11.42. Across 12 unseeded draws of the
canonical fixture, ``condition_number_before_normalization`` ranged 5.03-14.44
and ``column_scale_ratio`` ranged 3.93-6.64. The planned figures were one draw
from a distribution, not a fixed quantity.

v0.34c added ``inspect_pysindy_weak_pde_library(..., seed=...)`` so the
diagnostic can be made reproducible. Every number in this fixture is measured at
that fixed seed and is stable; without it, nothing here could be pinned.

What the numbers actually say
-----------------------------

Column normalization improves conditioning on every fixture and every draw, so
the *direction* of the original claim holds. The *magnitude* is strongly
fixture-dependent: at the pinned seed the improvement ranges 1.79x (canonical)
to 48.34x (advection-diffusion), median 4.51x. The canonical fixture -- the one
a reader is most likely to assume the headline figure describes -- improves by
under 2x.

Consequently the gate asserted by
``tests/test_v0_34c_column_normalized_weak_stlsq.py`` is **not** a single
threshold. It is (a) a universal invariant that normalization never *worsens*
conditioning, and (b) per-fixture pinned values. A single headline threshold
would either be unmeetable on the canonical fixture or chosen to pass on a
fixture that clears it.

Regeneration::

    python -m tests._helpers.conditioning_ratios --reason "<named cause>"
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Any

from pdelie.data import (
    generate_advection_diffusion_1d_field_batch,
    generate_burgers_1d_field_batch,
    generate_heat_1d_field_batch,
)
from pdelie.tasks.weak_pde_library import (
    WeakPDELibraryDiagnostic,
    inspect_pysindy_weak_pde_library,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
CONDITIONING_FIXTURE_PATH = (
    _REPO_ROOT / "tests" / "fixtures" / "v0_34c_conditioning_ratios.json"
)

SUMMARY_SCHEMA_VERSION = "0.1"
SUMMARY_TYPE = "pdelie_column_normalization_conditioning_fixture"

#: Fixed seed for the whole fixture. Changing it invalidates every pinned value.
CONDITIONING_SEED = 20340

#: Cross-BLAS tolerance, matching the v0.33e gate's reasoning: aggregate scalars
#: only, never bit-exact comparison.
CONDITIONING_RTOL = 1e-6
CONDITIONING_ATOL = 1e-12

#: The universal invariant. Normalization must never make conditioning worse.
#: This is the only threshold asserted across every fixture; per-fixture
#: magnitudes are pinned individually rather than collapsed into one number.
MINIMUM_IMPROVEMENT_RATIO = 1.0

PINNED_METRIC_NAMES: tuple[str, ...] = (
    "column_scale_ratio",
    "condition_number_before_normalization",
    "condition_number_after_normalization",
    "condition_number_improvement_ratio",
)

_CANONICAL_CONFIG = WeakPDELibraryDiagnostic(
    polynomial_degree=2, derivative_order=2, num_domain_centers_K=16
)


def _fixture_specs() -> list[tuple[str, Any, WeakPDELibraryDiagnostic]]:
    return [
        (
            "canonical",
            generate_heat_1d_field_batch(batch_size=1, num_times=64, num_points=64, seed=3120),
            _CANONICAL_CONFIG,
        ),
        (
            "heat_short_horizon",
            generate_heat_1d_field_batch(
                batch_size=1, num_times=64, num_points=64, seed=7, max_time=0.05
            ),
            _CANONICAL_CONFIG,
        ),
        (
            "heat_degree3",
            generate_heat_1d_field_batch(batch_size=1, num_times=64, num_points=64, seed=3120),
            WeakPDELibraryDiagnostic(
                polynomial_degree=3, derivative_order=2, num_domain_centers_K=16
            ),
        ),
        (
            "heat_derivative4",
            generate_heat_1d_field_batch(batch_size=1, num_times=64, num_points=64, seed=3120),
            WeakPDELibraryDiagnostic(
                polynomial_degree=2, derivative_order=4, num_domain_centers_K=16
            ),
        ),
        (
            "burgers",
            generate_burgers_1d_field_batch(batch_size=1, num_times=64, num_points=64, seed=3120),
            _CANONICAL_CONFIG,
        ),
        (
            "advection_diffusion",
            generate_advection_diffusion_1d_field_batch(
                batch_size=1, num_times=64, num_points=64, seed=3120
            ),
            _CANONICAL_CONFIG,
        ),
    ]


CONDITIONING_FIXTURE_NAMES: tuple[str, ...] = tuple(
    name for name, _field, _config in _fixture_specs()
)


def measure_conditioning() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for name, field, config in _fixture_specs():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            report = inspect_pysindy_weak_pde_library(
                field,
                task_name="v0_34c_conditioning",
                library_configuration=config,
                column_normalize=True,
                seed=CONDITIONING_SEED,
            )
        block = report["column_normalization"]
        entry: dict[str, Any] = {"name": name}
        entry.update({metric: float(block[metric]) for metric in PINNED_METRIC_NAMES})
        entry["scaling_zero_column_count"] = int(block["scaling_zero_column_count"])
        entries.append(entry)
    return entries


def build_payload(*, reason: str) -> dict[str, Any]:
    return {
        "summary_schema_version": SUMMARY_SCHEMA_VERSION,
        "summary_type": SUMMARY_TYPE,
        "seed": CONDITIONING_SEED,
        "seed_is_required_for_reproducibility": True,
        "seed_rationale": (
            "pysindy.WeakPDELibrary draws its K domain centers from the global "
            "NumPy RNG and exposes no seed parameter; without an explicit seed "
            "the diagnostic is nondeterministic and none of these values can be "
            "pinned."
        ),
        "minimum_improvement_ratio": MINIMUM_IMPROVEMENT_RATIO,
        "last_regeneration_reason": reason,
        "fixtures": measure_conditioning(),
    }


def load_fixture() -> dict[str, Any]:
    with CONDITIONING_FIXTURE_PATH.open(encoding="utf-8") as handle:
        payload: dict[str, Any] = json.load(handle)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tests._helpers.conditioning_ratios",
        description="Regenerate the v0.34c conditioning-ratio fixture.",
    )
    parser.add_argument("--reason", required=True, help="Named cause for the change.")
    args = parser.parse_args(argv)
    if not args.reason.strip():
        raise ValueError("A non-empty --reason is required.")

    payload = build_payload(reason=args.reason)
    CONDITIONING_FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONDITIONING_FIXTURE_PATH.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {CONDITIONING_FIXTURE_PATH.relative_to(_REPO_ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
