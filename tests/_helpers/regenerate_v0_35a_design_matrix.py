"""Regenerate the v0.35a canonical design-matrix fixture.

Why this exists
===============

The v0.35 plan named "the canonical matrix from the v0.34c fixture" as v0.35a's
realistic test input. That matrix does not exist on disk: the v0.34c fixture
(``tests/fixtures/v0_34c_conditioning_ratios.json``) stores *scalars*.

It cannot simply be rebuilt on demand either. ``pysindy.WeakPDELibrary`` draws
its domain centers from the global NumPy RNG and exposes no seed parameter, so
an unseeded rebuild returns a different matrix every time -- measured condition
numbers of 5232.86 at seed 20340 and 5945.46 at seed 20341 on otherwise
identical inputs.

So v0.35a stores the matrix. Once stored, every diagnostic test loads an array
instead of re-running a nondeterministic third-party library, and v0.35c
inherits a pinned input rather than drawing its own.

Regeneration is deliberate and named
====================================

    python -m tests._helpers.regenerate_v0_35a_design_matrix --reason "..."

``--reason`` is required. The fixture pins numbers that tests compare against;
regenerating without recording why is how a silent numerical change gets
committed as a fixture update.
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Any

import numpy as np

from pdelie.data import generate_heat_1d_field_batch
from pdelie.tasks.weak_pde_library import (
    WeakPDELibraryDiagnostic,
    _build_weak_library,
    _seeded_global_numpy_random,
)

#: Inherited from v0.34c. Changing it invalidates every pinned value here and in
#: ``tests/fixtures/v0_34c_conditioning_ratios.json``.
DESIGN_MATRIX_SEED = 20340

#: The v0.34c "canonical" fixture parameters, reproduced exactly.
FIELD_KWARGS: dict[str, Any] = {
    "batch_size": 1,
    "num_times": 64,
    "num_points": 64,
    "seed": 3120,
}
LIBRARY_CONFIG = WeakPDELibraryDiagnostic(
    polynomial_degree=2, derivative_order=2, num_domain_centers_K=16
)

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "v0_35a_canonical_design_matrix.npz"

#: Aggregate properties pinned alongside the array. Cross-BLAS reproducibility
#: is asserted on these at ``rtol=1e-6``; the array itself is exact on reload.
PINNED_PROPERTY_NAMES = (
    "condition_number",
    "matrix_rank",
    "max_column_norm",
    "min_column_norm",
)


def build_design_matrix() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Build the canonical weak-form design matrix under the pinned seed."""
    field = generate_heat_1d_field_batch(**FIELD_KWARGS)
    x_coord = np.asarray(field.coords["x"], dtype=float)
    t_coord = np.asarray(field.coords["time"], dtype=float)
    num_times = int(FIELD_KWARGS["num_times"])
    num_points = int(FIELD_KWARGS["num_points"])
    u_input = np.asarray(field.values, dtype=float)[0].reshape(num_times, num_points, 1)

    with _seeded_global_numpy_random(DESIGN_MATRIX_SEED), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        library, _grid = _build_weak_library(
            LIBRARY_CONFIG, x_coord=x_coord, t_coord=t_coord
        )
        library.fit(u_input)
        design_matrix = np.asarray(library.transform(u_input), dtype=float)
        target = np.asarray(library.convert_u_dot_integral(u_input), dtype=float)
        feature_names = list(library.get_feature_names())

    return design_matrix, target, feature_names


def matrix_properties(design_matrix: np.ndarray) -> dict[str, float | int]:
    """Aggregate properties pinned alongside the array."""
    column_norms = np.linalg.norm(design_matrix, axis=0)
    return {
        "condition_number": float(np.linalg.cond(design_matrix)),
        "matrix_rank": int(np.linalg.matrix_rank(design_matrix)),
        "max_column_norm": float(column_norms.max()),
        "min_column_norm": float(column_norms.min()),
    }


def build_payload(*, reason: str) -> dict[str, Any]:
    design_matrix, target, feature_names = build_design_matrix()
    return {
        "design_matrix": design_matrix,
        "target": target,
        "feature_names": np.array(feature_names, dtype=object),
        "provenance": np.array(
            json.dumps(
                {
                    "reason": reason,
                    "seed": DESIGN_MATRIX_SEED,
                    "seed_is_required_for_reproducibility": True,
                    "seed_rationale": (
                        "pysindy.WeakPDELibrary draws domain centers from the "
                        "global NumPy RNG and exposes no seed parameter; without "
                        "an explicit seed the matrix differs on every build."
                    ),
                    "field_kwargs": FIELD_KWARGS,
                    "library_configuration": {
                        "polynomial_degree": LIBRARY_CONFIG.polynomial_degree,
                        "derivative_order": LIBRARY_CONFIG.derivative_order,
                        "num_domain_centers_K": LIBRARY_CONFIG.num_domain_centers_K,
                    },
                    "feature_names": feature_names,
                    "properties": matrix_properties(design_matrix),
                },
                indent=2,
                sort_keys=True,
                allow_nan=False,
            ),
            dtype=object,
        ),
    }


def load_fixture() -> dict[str, Any]:
    with np.load(FIXTURE_PATH, allow_pickle=True) as archive:
        return {
            "design_matrix": np.asarray(archive["design_matrix"], dtype=float),
            "target": np.asarray(archive["target"], dtype=float),
            "feature_names": [str(name) for name in archive["feature_names"]],
            "provenance": json.loads(str(archive["provenance"].item())),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the v0.35a canonical design-matrix fixture. Requires an "
            "explicit --reason; the fixture pins numbers that tests assert against."
        )
    )
    parser.add_argument(
        "--reason",
        required=True,
        help="Why this regeneration is happening; recorded in the fixture.",
    )
    args = parser.parse_args(argv)

    payload = build_payload(reason=args.reason)
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(FIXTURE_PATH, **payload)

    properties = matrix_properties(payload["design_matrix"])
    print(f"wrote {FIXTURE_PATH}")
    print(f"  shape      : {payload['design_matrix'].shape}")
    print(f"  properties : {properties}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
