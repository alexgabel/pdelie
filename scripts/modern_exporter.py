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


def export(config_path: Path, output_dir: Path, wheel_path: Path | None) -> int:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    kwargs = config["field_generator_kwargs"]

    from pdelie.data import (
        generate_burgers_1d_field_batch,
        generate_heat_1d_field_batch,
    )
    from pdelie.derivatives import compute_derivatives

    generators = {
        "pdelie.data.generate_burgers_1d_field_batch": generate_burgers_1d_field_batch,
        "pdelie.data.generate_heat_1d_field_batch": generate_heat_1d_field_batch,
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
        "qualitative_invariant",
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
