"""v0.36a-alpha: export stage bundles from the LEGACY pdelie (v0.22.0).

Runs INSIDE the legacy virtualenv. It imports ``pdelie`` -- the *legacy* one --
and the standard library. It does **not** import ``pdelie.audit``: that module
exists only in the modern tree, and importing it here would silently make the
two sides share a serializer, which is the one thing this design forbids.

Legacy environment, measured rather than assumed
================================================

* CPython **3.11** is mandatory. ``v0.22.0`` gates ``pysindy`` and
  ``scikit-learn`` behind the marker ``python_version < '3.12'``, so on 3.12+
  they are silently absent and the discovery stages cannot run.
* ``pysindy``/``scikit-learn`` live in the ``[downstream]`` extra, not in the
  core dependencies. Install ``pdelie[downstream]``, not bare ``pdelie``.
* Build the wheel with ``setuptools>=68`` and ``wheel==0.38.4``.

  The v0.36 plan proposed ``setuptools==65.5.0``. That fails: ``v0.22.0``'s own
  ``[build-system]`` declares ``requires = ["setuptools>=68"]``, so 65.5.0 is
  below its floor and the build aborts with ``Missing dependencies:
  setuptools>=68``. Measured working combination: ``setuptools==68.2.2``,
  ``wheel==0.38.4``, CPython 3.11.14 -- which also means the Docker fallback in
  the plan is not required.

Resolved legacy runtime: pdelie 0.22.0, numpy 1.26.4, pysindy 1.7.5,
scikit-learn 1.2.2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

SCHEMA_VERSION = "0.1"


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False
        ).stdout.strip()
    except OSError:
        return ""


def build_provenance(wheel_path: Path | None, stage_type: str) -> dict[str, object]:
    """Provenance for exit gate A-alpha-0.

    ``source_dirty`` is a required bool, not an optional nicety: a wheel built
    from a dirty tree is not the tag it claims to be, and "unknown" is not an
    answer an audit can use.
    """
    import importlib.metadata as md

    wheel_sha256 = ""
    if wheel_path is not None and Path(wheel_path).is_file():
        wheel_sha256 = hashlib.sha256(Path(wheel_path).read_bytes()).hexdigest()

    return {
        "wheel_sha256": wheel_sha256,
        "package_version": md.version("pdelie"),
        "git_commit": _git("rev-parse", "HEAD"),
        "source_dirty": bool(_git("status", "--porcelain")),
        "python_version": ".".join(str(part) for part in sys.version_info[:3]),
        "numpy_version": np.__version__,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "side": "legacy",
        "stage_type": stage_type,
    }


def write_bundle(
    directory: Path,
    stage_id: str,
    arrays: dict[str, np.ndarray],
    provenance: dict[str, object],
    parent_stage_ids: list[str],
    comparison_class: str,
) -> None:
    """Standalone bundle writer.

    Deliberately duplicated from ``pdelie.audit.stage_bundle`` rather than
    imported: the legacy side must not depend on the modern package. The format
    is the contract; the code is not shared. ``tests/`` asserts both writers
    produce byte-identical ``stage.json`` for the same inputs.
    """
    target = Path(directory) / stage_id
    target.mkdir(parents=True, exist_ok=True)

    entries = []
    for index, name in enumerate(sorted(arrays)):
        array = np.asarray(arrays[name])
        relative = f"array_{index:03d}.npy"
        path = target / relative
        np.save(path, array, allow_pickle=False)
        entries.append(
            {
                "name": name,
                "path": relative,
                "shape": [int(dim) for dim in array.shape],
                "dtype": str(array.dtype),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "stage_id": stage_id,
        "stage_type": provenance.get("stage_type", "unspecified"),
        "parent_stage_ids": list(parent_stage_ids),
        "comparison_class": comparison_class,
        "arrays": entries,
        "provenance": provenance,
    }
    (target / "stage.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Paper-critical stages 2-16.
#
# Stages 9-16 build the design matrix from the DerivativeBatch directly rather
# than routing through PySINDy. That is deliberate: PySINDy 1.7.5 and 2.1.x are
# a known, separately-documented contract change, and running the comparison
# through them would confound "did the numerics survive the migration" with
# "did PySINDy change". The design matrix, its Gram matrix, and a least-squares
# solve are computable identically on both sides from quantities each version
# already produces.
# ---------------------------------------------------------------------------

TRAIN_FRACTION = 0.7
SUPPORT_THRESHOLD = 1e-3


def _feature_matrix(derivatives, values):
    """[u, u_x, u_xx, u*u_x, u*u_xx] flattened over (batch, time, x)."""
    u = values.reshape(-1)
    u_x = np.asarray(derivatives["u_x"], dtype=float).reshape(-1)
    u_xx = np.asarray(derivatives["u_xx"], dtype=float).reshape(-1)
    return np.column_stack([u, u_x, u_xx, u * u_x, u * u_xx])


def export_remaining_stages(directory, wheel_path, field, values, derivatives, residual_l2):
    def prov(kind):
        return build_provenance(wheel_path, kind)

    n_batch, n_time, n_x = values.shape[0], values.shape[1], values.shape[2]

    write_bundle(directory, "trajectory_ids",
                 {"trajectory_ids": np.arange(n_batch, dtype=np.int64)},
                 prov("identifiers"), ["generated_field_statistics"], "exact_discrete")

    n_train = round(TRAIN_FRACTION * n_time)
    membership = np.zeros(n_time, dtype=np.int64)
    membership[n_train:] = 1
    write_bundle(directory, "split_membership", {"split_membership": membership},
                 prov("split"), ["trajectory_ids"], "exact_discrete")

    observation = np.ones((n_batch, n_time, n_x), dtype=bool)
    write_bundle(directory, "observation_mask", {"mask": observation},
                 prov("mask"), ["trajectory_ids"], "exact_discrete")

    # Periodic spectral differentiation wraps, so no stencil erosion occurs and
    # the derivative-validity mask equals the observation mask. On nonperiodic
    # or masked data these differ by the stencil half-width; that regime is beta
    # scope, and this stage agrees here because the situation is trivial rather
    # than because the migration preserved an erosion rule.
    write_bundle(directory, "derivative_validity_mask", {"mask": observation.copy()},
                 prov("mask"), ["observation_mask"], "exact_discrete")

    regression = observation.copy()
    regression[:, n_train:, :] = False
    write_bundle(directory, "regression_row_mask", {"mask": regression},
                 prov("mask"), ["derivative_validity_mask", "observation_mask"],
                 "exact_discrete")

    write_bundle(directory, "residuals", {"residual": residual_l2},
                 prov("residuals"), ["derivatives"], "tolerance_numeric")

    features = _feature_matrix(derivatives, values)
    rows = regression.reshape(-1)
    design = features[rows]
    target = np.asarray(derivatives["u_t"], dtype=float).reshape(-1)[rows]

    write_bundle(directory, "design_matrix_x", {"design_matrix": design},
                 prov("matrix"), ["derivatives", "regression_row_mask"],
                 "tolerance_numeric")
    write_bundle(directory, "target_y", {"target": target},
                 prov("vector"), ["derivatives", "regression_row_mask"],
                 "tolerance_numeric")

    gram = design.T @ design
    write_bundle(directory, "gram_matrix", {"gram": gram},
                 prov("matrix"), ["design_matrix_x"], "tolerance_numeric")

    coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
    write_bundle(directory, "coefficients", {"coefficients": coefficients},
                 prov("vector"), ["gram_matrix", "target_y"], "tolerance_numeric")

    scale = float(np.abs(coefficients).max()) or 1.0
    support = (np.abs(coefficients) / scale >= SUPPORT_THRESHOLD).astype(np.int64)
    write_bundle(directory, "selected_support", {"support": support},
                 prov("support"), ["coefficients"], "exact_discrete")

    prediction = design @ coefficients
    per_seed = np.array([
        float(np.linalg.norm(prediction - target)),
        float(np.linalg.norm(prediction - target) / max(np.linalg.norm(target), 1e-300)),
    ], dtype=float)
    write_bundle(directory, "per_seed_metrics", {"metrics": per_seed},
                 prov("metrics"), ["coefficients", "split_membership"],
                 "tolerance_numeric")

    aggregate = np.array([per_seed.mean(), per_seed.max()], dtype=float)
    write_bundle(directory, "aggregate_metrics", {"metrics": aggregate},
                 prov("metrics"), ["per_seed_metrics"], "tolerance_numeric")


def export(config_path: Path, output_dir: Path, wheel_path: Path | None) -> int:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    kwargs = config["field_generator_kwargs"]

    from pdelie.data import (
        generate_burgers_1d_field_batch,
        generate_heat_1d_field_batch,
    )
    from pdelie.derivatives import compute_spectral_fd_derivatives

    generators = {
        "pdelie.data.generate_burgers_1d_field_batch": generate_burgers_1d_field_batch,
        "pdelie.data.generate_heat_1d_field_batch": generate_heat_1d_field_batch,
    }
    generator = generators[config["field_generator"]]
    field = generator(**kwargs)
    values = np.asarray(field.values, dtype=float)

    # Stage 1 -- generated field statistics.
    write_bundle(
        output_dir,
        "generated_field_statistics",
        {
            "statistics": np.array(
                [values.mean(), values.std(), float(np.linalg.norm(values))], dtype=float
            ),
            "shape": np.array(values.shape, dtype=np.int64),
        },
        build_provenance(wheel_path, "statistics"),
        [],
        "qualitative_invariant",
    )

    # Stage 7 -- derivatives. Legacy entry point; see the module docstring.
    derivatives = compute_spectral_fd_derivatives(field)
    write_bundle(
        output_dir,
        "derivatives",
        {name: np.asarray(value, dtype=float) for name, value in derivatives.derivatives.items()},
        build_provenance(wheel_path, "derivatives"),
        ["observation_mask"],
        "tolerance_numeric",
    )


    # Stage 8 uses the residual evaluator each version ships. The constructor is
    # contract-identical across the gap: both take `diffusivity`.
    from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator

    evaluator = (
        BurgersResidualEvaluator(diffusivity=1.0)
        if "burgers" in config["field_generator"]
        else HeatResidualEvaluator(diffusivity=1.0)
    )
    residual_batch = evaluator.evaluate(field)
    residual_l2 = np.asarray(residual_batch.residual, dtype=float)

    export_remaining_stages(
        output_dir, wheel_path, field, values, derivatives.derivatives, residual_l2
    )

    print(f"legacy exporter wrote bundles to {output_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export legacy stage bundles.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--wheel", type=Path, default=None)
    args = parser.parse_args(argv)
    return export(args.config, args.output_dir, args.wheel)


if __name__ == "__main__":
    raise SystemExit(main())
