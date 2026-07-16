"""v0.32d PDEBench 1D Burgers readiness cookbook (JSON-only, submodule-only).

Loads exactly one frozen PDEBench 1D Burgers slice — pinned by filename,
MD5 checksum, HDF5 dataset paths, axis layout, viscosity parameter, and
periodic-in-x boundary condition per
``configs/external_data/pdebench_burgers_1d_readiness.json`` — and emits a
strict-JSON ``pdelie_external_data_readiness`` report.

This module is a narrow readiness cookbook, NOT a general PDEBench adapter.
It does not implement dataset-name inference, an adapter registry, a broad
``from_pdebench`` API, or any recovery benchmark. It reads exactly one
dataset shard, verifies its provenance, and reports whether a
scalar-1D-uniform :class:`FieldBatch` can be constructed from it.

Non-goals:

- no broad PDEBench support claim;
- no model training, no FNO/U-Net/PINN comparison;
- no automatic dataset-name inference;
- no train/test policy invented on the caller's behalf;
- no root ``pdelie`` re-export.

Optional dependency: ``h5py``. Users install it directly
(``pip install h5py``) — v0.32d does NOT add a broad ``pdelie[pdebench]``
extra, because doing so would imply broad PDEBench support, which is
explicitly out of scope. On a plain install, calling the loader with a
real cached file raises a helpful ``ImportError``. All other readiness
paths (config validation, checksum enforcement,
unavailable-no-cached-dataset) work without ``h5py``.
"""

from __future__ import annotations

import hashlib
import importlib.metadata as _importlib_metadata
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from pdelie.contracts import FieldBatch
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.reporting import summarize_field_batch_readiness

_SUMMARY_TYPE = "pdelie_external_data_readiness"
_SUMMARY_SCHEMA_VERSION = "0.1"

_CONFIG_PATH = (
    Path(__file__).resolve().parent
    / "_external_data"
    / "pdebench_burgers_1d_readiness.json"
)

_READINESS_CONCLUSIONS = frozenset(
    {
        "ready_scalar_1d_readiness_only",
        "ready_residual_preflight_only",
        "blocked_boundary_metadata_unverified",
        "blocked_parameter_convention_mismatch",
        "blocked_nonuniform_grid",
        "blocked_schema_mismatch",
        "blocked_multichannel_required",
        "blocked_download_or_checksum_failure",
        "unavailable_no_cached_dataset",
    }
)


def load_pdebench_burgers_1d_readiness_config() -> dict[str, Any]:
    """Return the frozen v0.32d PDEBench Burgers config as a strict-JSON dict."""
    payload: dict[str, Any] = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    encoded = json.dumps(payload, allow_nan=False)
    if json.loads(encoded) != payload:
        raise SchemaValidationError(
            "pdebench_burgers_1d_readiness config is not strict-JSON."
        )
    return payload


def _resolve_backend_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for dist_name, key in (
        ("pdelie", "pdelie"),
        ("numpy", "numpy"),
        ("h5py", "h5py"),
    ):
        try:
            versions[key] = _importlib_metadata.version(dist_name)
        except _importlib_metadata.PackageNotFoundError:
            continue
    return versions


def _compute_md5(path: Path, *, chunk_size: int = 1 << 20) -> str:
    hasher = hashlib.md5()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _stage_unavailable(config: Mapping[str, Any]) -> dict[str, Any]:
    payload = _base_payload(config)
    payload["field_batch_readiness"] = None
    payload["derivative_readiness"] = {"stage_run": False, "reason": "no_cached_dataset"}
    payload["residual_readiness"] = {"stage_run": False, "reason": "no_cached_dataset"}
    payload["split_metadata"] = _split_metadata_default(config)
    payload["warnings"] = ["cached_dataset_path_not_provided"]
    payload["conclusion"] = "unavailable_no_cached_dataset"
    return _finalize(payload)


def _stage_checksum_failure(
    config: Mapping[str, Any],
    *,
    actual_checksum: str,
    expected_checksum: str,
    algorithm: str,
) -> dict[str, Any]:
    payload = _base_payload(config)
    payload["field_batch_readiness"] = None
    payload["derivative_readiness"] = {
        "stage_run": False,
        "reason": "checksum_mismatch",
    }
    payload["residual_readiness"] = {
        "stage_run": False,
        "reason": "checksum_mismatch",
    }
    payload["split_metadata"] = _split_metadata_default(config)
    payload["warnings"] = [
        f"checksum_mismatch:{algorithm}:{actual_checksum}!={expected_checksum}"
    ]
    payload["conclusion"] = "blocked_download_or_checksum_failure"
    return _finalize(payload)


def _base_payload(config: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": _SUMMARY_TYPE,
        "source_project": config["source_project"],
        "dataset_identifier": (
            f"{config['dataset_family']}/{config['source_file']}"
        ),
        "dataset_version": config["dataset_version"],
        "data_doi_or_record": config["data_doi_or_record"],
        "license": config["license"],
        "citation": config["citation"],
        "source_file": config["source_file"],
        "source_checksum": dict(config["source_checksum"]),
        "variable_mapping": dict(config["variable_mapping"]),
        "axis_mapping": dict(config["axis_mapping"]),
        "input_layout": config["array_layout"],
        "grid_uniformity": config["grid_uniformity"],
        "coordinate_ranges": {
            k: list(v) for k, v in config["coordinate_ranges"].items()
        },
        "boundary_condition_evidence": dict(config["boundary_condition_evidence"]),
        "parameter_evidence": dict(config["parameter_evidence"]),
        "equation_tag_candidate": config["equation_tag_candidate"],
        "provenance": {
            "config_slug": "pdebench_burgers_1d_readiness",
            "backend_versions": _resolve_backend_versions(),
        },
    }


def _split_metadata_default(config: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "in_file": bool(config["train_test_split_semantics"]["in_file"]),
        "policy": str(config["train_test_split_semantics"]["policy"]),
        "invented_by_cookbook": False,
        "pdelie_policy": str(
            config["train_test_split_semantics"]["pdelie_policy"]
        ),
    }


def _finalize(payload: Mapping[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload, allow_nan=False)
    validated: dict[str, Any] = json.loads(encoded)
    if validated["conclusion"] not in _READINESS_CONCLUSIONS:
        raise SchemaValidationError(
            f"conclusion must be one of {sorted(_READINESS_CONCLUSIONS)}; "
            f"got {validated['conclusion']!r}."
        )
    return validated


def _load_h5py() -> Any:
    try:
        import h5py
    except ImportError as exc:  # pragma: no cover — surfaced via test
        raise ImportError(
            "pdelie.examples.pdebench_burgers_1d_readiness requires h5py "
            "for reading the PDEBench HDF5 shard. Install it directly with "
            "`pip install h5py`. v0.32d does not add a broad "
            "pdelie[pdebench] extra."
        ) from exc
    return h5py


def _validate_hdf5_shape(
    tensor_shape: tuple[int, ...],
    x_shape: tuple[int, ...],
    t_shape: tuple[int, ...],
) -> None:
    if len(tensor_shape) != 3:
        raise SchemaValidationError(
            "PDEBench 1D_Burgers tensor dataset must have rank 3 "
            f"(n_traj, T, X); got shape {tensor_shape!r}."
        )
    if len(x_shape) != 1:
        raise SchemaValidationError(
            "PDEBench 1D_Burgers x-coordinate must be 1-D; "
            f"got shape {x_shape!r}."
        )
    if len(t_shape) != 1:
        raise SchemaValidationError(
            "PDEBench 1D_Burgers t-coordinate must be 1-D; "
            f"got shape {t_shape!r}."
        )
    _n_traj, t_size, x_size = tensor_shape
    if t_shape[0] != t_size:
        raise SchemaValidationError(
            f"tensor time axis {t_size} must match t-coordinate length "
            f"{t_shape[0]}."
        )
    if x_shape[0] != x_size:
        raise SchemaValidationError(
            f"tensor space axis {x_size} must match x-coordinate length "
            f"{x_shape[0]}."
        )


def _is_uniform(coord: np.ndarray[Any, Any]) -> bool:
    if coord.size < 2:
        return True
    dx = np.diff(coord)
    if dx.size == 0:
        return True
    # PDEBench 1D_Burgers is stored as float32; the linspace-generated
    # coordinate arrays carry ~1e-7 float32 quantization noise that rtol
    # must accommodate. Tightening this below rtol=1e-5 would false-positive
    # on the real file.
    return bool(np.allclose(dx, dx[0], rtol=1e-5, atol=1e-8))


def _build_field_batch_from_hdf5(
    tensor: np.ndarray[Any, Any],
    x_coord: np.ndarray[Any, Any],
    t_coord: np.ndarray[Any, Any],
    *,
    nu: float,
    max_trajectories: int,
) -> FieldBatch:
    n_traj = tensor.shape[0]
    take = min(n_traj, int(max_trajectories))
    if take <= 0:
        raise ScopeValidationError(
            "max_trajectories must be a positive integer."
        )
    subset = np.asarray(tensor[:take], dtype=float)
    values = subset[..., None]  # add trailing var axis
    return FieldBatch(
        values=values,
        dims=("batch", "time", "x", "var"),
        coords={
            "time": np.asarray(t_coord, dtype=float).copy(),
            "x": np.asarray(x_coord, dtype=float).copy(),
        },
        var_names=["u"],
        metadata={
            "grid_type": "rectilinear",
            "grid_regularity": "uniform",
            "coordinate_system": "cartesian",
            "boundary_conditions": {"x": "periodic"},
            "parameter_tags": {"equation": "burgers_1d", "nu": float(nu)},
        },
        preprocess_log=[
            {
                "operation": "pdebench_burgers_1d_cookbook_load",
                "trajectories_taken": int(take),
                "trajectories_available": int(n_traj),
            }
        ],
    )


def run_pdebench_burgers_1d_readiness_cookbook(
    *,
    cached_file_path: str | Path | None = None,
    residual_preflight: bool = False,
    max_trajectories: int = 4,
) -> dict[str, Any]:
    """Run the frozen PDEBench 1D Burgers readiness cookbook.

    Parameters
    ----------
    cached_file_path:
        Absolute or relative path to a locally cached copy of the exact
        expected file (`1D_Burgers_Sols_Nu0.001.hdf5`). If ``None``, the
        cookbook returns a ``unavailable_no_cached_dataset`` report and
        skips every read.
    residual_preflight:
        If ``True`` AND a valid cached file is present AND all metadata
        checks pass, run the Burgers residual evaluator on the loaded
        FieldBatch and record interior-only + full-grid diagnostics. Set
        to ``False`` (default) for readiness-only reports.
    max_trajectories:
        Number of trajectories to slice for the FieldBatch construction.
        Kept small so the cookbook stays cheap even on the full shard.
    """
    config = load_pdebench_burgers_1d_readiness_config()

    if cached_file_path is None:
        return _stage_unavailable(config)

    path = Path(cached_file_path).expanduser()
    if not path.is_file():
        payload = _base_payload(config)
        payload["field_batch_readiness"] = None
        payload["derivative_readiness"] = {
            "stage_run": False,
            "reason": "cached_file_not_found",
        }
        payload["residual_readiness"] = {
            "stage_run": False,
            "reason": "cached_file_not_found",
        }
        payload["split_metadata"] = _split_metadata_default(config)
        payload["warnings"] = [f"cached_file_not_found:{path.name}"]
        payload["conclusion"] = "unavailable_no_cached_dataset"
        return _finalize(payload)

    if path.name != config["source_file"]:
        raise SchemaValidationError(
            f"cached_file_path filename {path.name!r} does not match the "
            f"frozen expected filename {config['source_file']!r}."
        )

    expected_checksum = config["source_checksum"]["value"]
    algorithm = str(config["source_checksum"]["algorithm"]).lower()
    if algorithm != "md5":
        raise SchemaValidationError(
            f"cookbook only supports MD5 checksums (DaRUS-published); "
            f"got algorithm {algorithm!r}."
        )
    actual_checksum = _compute_md5(path)
    if actual_checksum != expected_checksum:
        return _stage_checksum_failure(
            config,
            actual_checksum=actual_checksum,
            expected_checksum=expected_checksum,
            algorithm=algorithm,
        )

    h5py = _load_h5py()

    with h5py.File(str(path), "r") as fp:
        for required_path in (
            config["hdf5_dataset_paths"]["field"],
            config["hdf5_dataset_paths"]["x_coordinate"],
            config["hdf5_dataset_paths"]["t_coordinate"],
        ):
            if required_path.strip("/") not in fp:
                raise SchemaValidationError(
                    f"HDF5 file is missing required dataset {required_path!r}. "
                    "The v0.32d cookbook only reads the exact frozen schema."
                )
        tensor = np.asarray(
            fp[config["hdf5_dataset_paths"]["field"]], dtype=float
        )
        x_coord = np.asarray(
            fp[config["hdf5_dataset_paths"]["x_coordinate"]], dtype=float
        )
        t_coord = np.asarray(
            fp[config["hdf5_dataset_paths"]["t_coordinate"]], dtype=float
        )

    _validate_hdf5_shape(tensor.shape, x_coord.shape, t_coord.shape)

    if not (_is_uniform(x_coord) and _is_uniform(t_coord)):
        payload = _base_payload(config)
        payload["field_batch_readiness"] = None
        payload["derivative_readiness"] = {
            "stage_run": False,
            "reason": "nonuniform_grid",
        }
        payload["residual_readiness"] = {
            "stage_run": False,
            "reason": "nonuniform_grid",
        }
        payload["split_metadata"] = _split_metadata_default(config)
        payload["warnings"] = ["nonuniform_grid_detected"]
        payload["conclusion"] = "blocked_nonuniform_grid"
        return _finalize(payload)

    field = _build_field_batch_from_hdf5(
        tensor,
        x_coord,
        t_coord,
        nu=float(config["parameter_evidence"]["nu"]),
        max_trajectories=max_trajectories,
    )
    readiness = summarize_field_batch_readiness(field)

    payload = _base_payload(config)
    payload["field_batch_readiness"] = readiness
    payload["split_metadata"] = _split_metadata_default(config)
    payload["warnings"] = []

    if not residual_preflight:
        payload["derivative_readiness"] = {
            "stage_run": False,
            "reason": "residual_preflight_not_requested",
        }
        payload["residual_readiness"] = {
            "stage_run": False,
            "reason": "residual_preflight_not_requested",
        }
        payload["conclusion"] = "ready_scalar_1d_readiness_only"
        return _finalize(payload)

    # Residual preflight: gate on the readiness label.
    readiness_label = readiness.get("readiness_label")
    if readiness_label != "ready":
        payload["derivative_readiness"] = {
            "stage_run": False,
            "reason": f"field_batch_readiness_label:{readiness_label}",
        }
        payload["residual_readiness"] = {
            "stage_run": False,
            "reason": f"field_batch_readiness_label:{readiness_label}",
        }
        payload["conclusion"] = "ready_scalar_1d_readiness_only"
        return _finalize(payload)

    from pdelie.derivatives import compute_derivatives
    from pdelie.residuals import BurgersResidualEvaluator

    derivatives = compute_derivatives(field, backend="spectral_fd")
    residual = BurgersResidualEvaluator().evaluate(field, derivatives=derivatives)
    residual_array = np.asarray(residual.residual, dtype=float)
    interior_slice = residual_array[:, 1:-1, 1:-1, :]
    full_l2 = float(np.linalg.norm(residual_array.reshape(-1)))
    interior_l2 = float(np.linalg.norm(interior_slice.reshape(-1)))
    payload["derivative_readiness"] = {
        "stage_run": True,
        "backend": derivatives.backend,
        "derivative_keys": sorted(str(k) for k in derivatives.derivatives),
    }
    payload["residual_readiness"] = {
        "stage_run": True,
        "diagnostic_only": True,
        "evaluator": type(residual.residual_evaluator).__name__
        if hasattr(residual, "residual_evaluator")
        else "BurgersResidualEvaluator",
        "full_grid_residual_l2": full_l2,
        "interior_only_residual_l2": interior_l2,
        "source_discretization_limitation_note": (
            "PDEBench 1D_Burgers is stored on the source discretization; "
            "PDELie derivative reconstruction and residual evaluation are "
            "narrower than the original solver's operator, so residual "
            "magnitudes are diagnostic only and NOT a recovery benchmark."
        ),
    }
    payload["conclusion"] = "ready_residual_preflight_only"
    return _finalize(payload)


def main() -> None:
    print(
        json.dumps(
            run_pdebench_burgers_1d_readiness_cookbook(),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
