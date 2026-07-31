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
