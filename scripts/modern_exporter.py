"""v0.36a-alpha: export stage bundles from the MODERN pdelie.

Runs INSIDE the modern virtualenv and uses ``pdelie.audit.stage_bundle`` for
serialization -- the shared utilities are available on this side by definition.

The legacy counterpart deliberately does not import this module. The interchange
*format* is the contract; the code that writes it is not shared, so a change to
the modern serializer cannot silently redefine what a legacy bundle means.
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

from pdelie.audit.stage_bundle import STAGE_BUNDLE_SCHEMA_VERSION, write_stage_bundle


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout.strip()
    except OSError:
        return ""


def build_provenance(wheel_path: Path | None, stage_type: str) -> dict[str, object]:
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
        "side": "modern",
        "stage_type": stage_type,
    }


def write_bundle(directory, stage_id, arrays, provenance, parent_stage_ids, comparison_class):
    """Adapter onto the modern writer.

    The stage bodies below are byte-identical to the legacy exporter's on
    purpose -- the two sides must produce the same format from independent code.
    This adapter is the single point where the modern side uses
    ``pdelie.audit.stage_bundle``, which the legacy side cannot import.
    """
    write_stage_bundle(
        directory,
        stage_id,
        STAGE_BUNDLE_SCHEMA_VERSION,
        arrays,
        provenance,
        list(parent_stage_ids),
        comparison_class,
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


# ---------------------------------------------------------------------------
# v0.36a-beta: the PySINDy-routed stages.
#
# alpha deliberately routed stages 9-16 around PySINDy so its numerical baseline
# would not be confounded by the PySINDy 1.7.5 -> 2.1.x version delta. beta MUST
# audit that path -- see the beta preconditions in
# docs/planning/V0_36A_ALPHA_TO_BETA_RUNBOOK.md. Any delta found here, given
# alpha's clean close, is attributable to the PySINDy version delta rather than
# to migration numerical drift.
#
# The stage ids are suffixed `_pysindy` so they never collide with alpha's
# DerivativeBatch-routed stages, and both can appear in one report.
# ---------------------------------------------------------------------------


def export_pysindy_stages(directory, wheel_path, field):
    """Export the PySINDy-routed design matrix, coefficients and support."""
    from pdelie.discovery import fit_pysindy_discovery, to_pysindy_trajectories

    def prov(kind):
        return build_provenance(wheel_path, kind)

    trajectories, time_values, feature_names = to_pysindy_trajectories(field)

    write_bundle(directory, "pysindy_trajectories",
                 {"trajectory_0": np.asarray(trajectories[0], dtype=float),
                  "time_values": np.asarray(time_values, dtype=float)},
                 prov("matrix"), ["generated_field_statistics"], "tolerance_numeric")

    result = fit_pysindy_discovery(
        trajectories=trajectories, time_values=time_values,
        feature_names=feature_names, config=None,
    )
    coefficients = np.asarray(result["coefficients"], dtype=float)
    write_bundle(directory, "pysindy_coefficients", {"coefficients": coefficients},
                 prov("matrix"), ["pysindy_trajectories"], "tolerance_numeric")

    scale = float(np.abs(coefficients).max()) or 1.0
    support = (np.abs(coefficients) / scale >= SUPPORT_THRESHOLD).astype(np.int64)
    write_bundle(directory, "pysindy_selected_support", {"support": support},
                 prov("support"), ["pysindy_coefficients"], "exact_discrete")

    # The library feature-name list is the surface most likely to move between
    # PySINDy majors. Exported as a length so a change is visible without
    # embedding a version-specific naming scheme in the comparison.
    library_names = result.get("library_feature_names") or []
    write_bundle(directory, "pysindy_library_size",
                 {"library_feature_count": np.array([len(library_names)], dtype=np.int64)},
                 prov("metrics"), ["pysindy_coefficients"], "exact_discrete")


def export(config_path: Path, output_dir: Path, wheel_path: Path | None) -> int:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    kwargs = config["field_generator_kwargs"]

    from pdelie.data import (
        generate_advection_diffusion_1d_field_batch,
        generate_burgers_1d_field_batch,
        generate_heat_1d_field_batch,
        generate_kdv_1d_field_batch,
        generate_reaction_diffusion_1d_field_batch,
    )
    from pdelie.derivatives import compute_derivatives

    generators = {
        "pdelie.data.generate_advection_diffusion_1d_field_batch":
            generate_advection_diffusion_1d_field_batch,
        "pdelie.data.generate_burgers_1d_field_batch": generate_burgers_1d_field_batch,
        "pdelie.data.generate_heat_1d_field_batch": generate_heat_1d_field_batch,
        "pdelie.data.generate_kdv_1d_field_batch": generate_kdv_1d_field_batch,
        "pdelie.data.generate_reaction_diffusion_1d_field_batch":
            generate_reaction_diffusion_1d_field_batch,
    }
    field = generators[config["field_generator"]](**kwargs)
    values = np.asarray(field.values, dtype=float)

    write_stage_bundle(
        output_dir,
        "generated_field_statistics",
        STAGE_BUNDLE_SCHEMA_VERSION,
        {
            "statistics": np.array(
                [values.mean(), values.std(), float(np.linalg.norm(values))], dtype=float
            ),
            "shape": np.array(values.shape, dtype=np.int64),
        },
        build_provenance(wheel_path, "statistics"),
        [],
        # tolerance_numeric, not qualitative_invariant. These are unique-valued
        # floats, which the portability taxonomy classes tolerance_numeric. The
        # previous 'sign' invariant asserted one sign bit of a mean measured at
        # -4.18e-17 -- numerical zero for a field of L2 38 -- so it tested
        # rounding noise and would fail wherever that noise landed positive.
        "tolerance_numeric",
    )

    # Modern entry point. The rename from compute_spectral_fd_derivatives is a
    # known contract change from v0.30d backend dispatch; the config carries the
    # note and the comparison policy must supply the release-note link.
    derivatives = compute_derivatives(field)
    write_stage_bundle(
        output_dir,
        "derivatives",
        STAGE_BUNDLE_SCHEMA_VERSION,
        {name: np.asarray(value, dtype=float) for name, value in derivatives.derivatives.items()},
        build_provenance(wheel_path, "derivatives"),
        ["observation_mask"],
        "tolerance_numeric",
    )


    # Stage 8 uses the residual evaluator each version ships. The constructor is
    # contract-identical across the gap: both take `diffusivity`.
    import pdelie.residuals as _residuals

    _EVALUATORS = {
        "burgers": ("BurgersResidualEvaluator", {"diffusivity": 1.0}),
        "kdv": ("KdVResidualEvaluator", {}),
        "reaction_diffusion": ("ReactionDiffusionResidualEvaluator", {}),
        "advection_diffusion": ("AdvectionDiffusionResidualEvaluator", {"diffusivity": 1.0}),
        "heat": ("HeatResidualEvaluator", {"diffusivity": 1.0}),
    }
    _generator_name = config["field_generator"]
    for _key, (_cls, _kwargs) in _EVALUATORS.items():
        if _key in _generator_name:
            evaluator = getattr(_residuals, _cls)(**_kwargs)
            break
    else:
        evaluator = _residuals.HeatResidualEvaluator(diffusivity=1.0)
    residual_batch = evaluator.evaluate(field)
    residual_l2 = np.asarray(residual_batch.residual, dtype=float)

    export_remaining_stages(
        output_dir, wheel_path, field, values, derivatives.derivatives, residual_l2
    )

    if config.get("include_pysindy_path", False):
        export_pysindy_stages(output_dir, wheel_path, field)

    print(f"modern exporter wrote bundles to {output_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export modern stage bundles.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--wheel", type=Path, default=None)
    args = parser.parse_args(argv)
    return export(args.config, args.output_dir, args.wheel)


if __name__ == "__main__":
    raise SystemExit(main())
