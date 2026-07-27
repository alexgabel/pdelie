"""v0.33e golden-numbers fixture: frozen spec, metric computation, and regeneration CLI.

This module is the single source of truth for the golden-numbers regression
gate. Both :mod:`tests.test_v0_33e_golden_numbers_regression_gate` and the
regeneration CLI read the same :data:`GOLDEN_PDE_SPECS` table, so the fixture
can never drift from the configuration the gate replays.

Regeneration flow (release-close only)::

    python -m tests._helpers.regenerate_golden_fixture --all \\
        --reason "v0.30d FD-backend stencil widened to 4th order"

    python -m tests._helpers.regenerate_golden_fixture --pde kdv_1d \\
        --reason "KdV dealiasing cutoff changed from N/3 to 2N/5"

``--reason`` is mandatory: every regeneration records a named cause in the
fixture's ``last_regeneration_reason`` field, and the release-close CHANGELOG
must carry the same cause. No unnamed drift is permitted.

For cross-cutting numerical changes (FD backend, residual formulas, generator
schemes), use ``--all`` so every PDE lands on the new code state atomically. Use
``--pde <name>`` only for isolated changes to a single PDE's generator or
evaluator. If unsure, use ``--all`` -- a full regeneration is cheap.

Only aggregate norms are pinned -- never element-wise values. BLAS reduction
order differs across the Linux and macOS wheels, so element-wise equality is
not a portable invariant while aggregate norms at ``rtol=1e-6`` are.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path
from typing import Any

import numpy as np

from pdelie._boundary import get_x_boundary_type
from pdelie.contracts import FieldBatch
from pdelie.data import (
    generate_advection_diffusion_1d_field_batch,
    generate_burgers_1d_field_batch,
    generate_heat_1d_field_batch,
    generate_kdv_1d_field_batch,
    generate_reaction_diffusion_1d_field_batch,
)
from pdelie.derivatives import compute_derivatives
from pdelie.residuals import (
    AdvectionDiffusionResidualEvaluator,
    BurgersResidualEvaluator,
    HeatResidualEvaluator,
    KdVResidualEvaluator,
    ReactionDiffusionResidualEvaluator,
    ResidualEvaluator,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_FIXTURE_PATH = _REPO_ROOT / "tests" / "fixtures" / "v0_33e_golden_numbers.json"

SUMMARY_SCHEMA_VERSION = "0.1"
SUMMARY_TYPE = "pdelie_golden_numbers_fixture"

#: Frozen grid shared by every pinned PDE. Changing any of these three values
#: invalidates the whole fixture and requires a full ``--all`` regeneration.
GENERATOR_SEED = 20330
BATCH_SIZE = 1
NUM_TIMES = 33
NUM_POINTS = 64

#: Tolerances for the regression gate. ``rtol`` is a cross-BLAS margin: the
#: fixture is generated on macOS and replayed on the Linux CI runners, where the
#: worst observed relative deviation on an unchanged pipeline is 1.5e-9 (~650x
#: of headroom). Within one platform the reproduction is bit-exact across py3.12
#: and py3.13; across platforms it is not, so no pinned metric is ever compared
#: with ``==``. ``atol`` keeps near-zero metrics (e.g. residuals of
#: exactly-integrated fields) above float64 denormal-and-cancellation noise. The
#: pipeline is float64 throughout (``_to_numpy`` -> ``dtype=float``); these are
#: not float32 quantization limits.
GOLDEN_RTOL = 1e-6
GOLDEN_ATOL = 1e-12

#: The six pinned metrics, in fixture order.
PINNED_METRIC_NAMES: tuple[str, ...] = (
    "residual_l2_norm",
    "residual_rms",
    "residual_max_abs",
    "derivative_u_x_l2_norm",
    "derivative_u_xx_l2_norm",
    "derivative_u_t_l2_norm",
)

#: Keys every fixture PDE entry carries, in fixture order.
PDE_ENTRY_KEYS: tuple[str, ...] = (
    "name",
    "generator_kwargs",
    "max_spatial_order",
    "boundary_condition_x",
    *PINNED_METRIC_NAMES,
)


@dataclass(frozen=True)
class GoldenPdeSpec:
    """One pinned PDE: how to build its field, and how to differentiate it.

    ``generator_kwargs`` carries only the per-PDE parameters that differ from
    the shared grid -- ``max_time`` is numerically load-bearing and differs by
    an order of magnitude across PDEs (KdV is short-horizon-only at 0.03, Heat
    runs to 0.6), so it cannot live in the shared fixture header.

    ``max_spatial_order`` is per-PDE because ``compute_derivatives`` defaults to
    2 while ``KdVResidualEvaluator`` requires ``u_xxx``.
    """

    name: str
    generator: Callable[..., FieldBatch]
    evaluator: Callable[[], ResidualEvaluator]
    max_spatial_order: int
    generator_kwargs: dict[str, Any] = dataclass_field(default_factory=dict)

    def build_field(self) -> FieldBatch:
        return self.generator(
            batch_size=BATCH_SIZE,
            num_times=NUM_TIMES,
            num_points=NUM_POINTS,
            seed=GENERATOR_SEED,
            **self.generator_kwargs,
        )


#: The five distinct PDE generators with public runtime support.
#:
#: Fisher-KPP is *not* a separate entry: ``generate_reaction_diffusion_1d_field_batch``
#: stamps ``parameter_tags["equation"] == "reaction_diffusion_fisher_kpp"``, and
#: ``docs/specs/SUPPORT_MATRIX.md`` carries a single Fisher-KPP row for it. KS has
#: no public runtime and is excluded by the same matrix.
GOLDEN_PDE_SPECS: tuple[GoldenPdeSpec, ...] = (
    GoldenPdeSpec(
        name="heat_1d",
        generator=generate_heat_1d_field_batch,
        evaluator=HeatResidualEvaluator,
        max_spatial_order=2,
        generator_kwargs={"max_time": 0.6},
    ),
    GoldenPdeSpec(
        name="burgers_1d",
        generator=generate_burgers_1d_field_batch,
        evaluator=BurgersResidualEvaluator,
        max_spatial_order=2,
        generator_kwargs={"max_time": 0.25},
    ),
    GoldenPdeSpec(
        name="kdv_1d",
        generator=generate_kdv_1d_field_batch,
        evaluator=KdVResidualEvaluator,
        max_spatial_order=3,
        generator_kwargs={"max_time": 0.03},
    ),
    GoldenPdeSpec(
        name="advection_diffusion_1d",
        generator=generate_advection_diffusion_1d_field_batch,
        evaluator=AdvectionDiffusionResidualEvaluator,
        max_spatial_order=2,
        generator_kwargs={"max_time": 0.4},
    ),
    GoldenPdeSpec(
        name="reaction_diffusion_1d",
        generator=generate_reaction_diffusion_1d_field_batch,
        evaluator=ReactionDiffusionResidualEvaluator,
        max_spatial_order=2,
        generator_kwargs={"max_time": 0.3},
    ),
)

GOLDEN_PDE_NAMES: tuple[str, ...] = tuple(spec.name for spec in GOLDEN_PDE_SPECS)


def compute_golden_entry(spec: GoldenPdeSpec) -> dict[str, Any]:
    """Replay one PDE through the derivative + residual pipeline and pin its metrics."""
    field = spec.build_field()
    derivatives = compute_derivatives(
        field, backend="auto", max_spatial_order=spec.max_spatial_order
    )
    residual_batch = spec.evaluator().evaluate(field, derivatives)
    residual = np.asarray(residual_batch.residual, dtype=float)

    entry: dict[str, Any] = {
        "name": spec.name,
        "generator_kwargs": dict(spec.generator_kwargs),
        "max_spatial_order": spec.max_spatial_order,
        "boundary_condition_x": get_x_boundary_type(field),
        "residual_l2_norm": float(np.linalg.norm(residual)),
        "residual_rms": float(np.sqrt(np.mean(np.square(residual)))),
        "residual_max_abs": float(np.max(np.abs(residual))),
    }
    for derivative_name in ("u_x", "u_xx", "u_t"):
        array = np.asarray(derivatives.derivatives[derivative_name], dtype=float)
        entry[f"derivative_{derivative_name}_l2_norm"] = float(np.linalg.norm(array))
    return entry


def build_fixture_payload(*, reason: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "summary_schema_version": SUMMARY_SCHEMA_VERSION,
        "summary_type": SUMMARY_TYPE,
        "generator_seed": GENERATOR_SEED,
        "batch_size": BATCH_SIZE,
        "num_times": NUM_TIMES,
        "num_points": NUM_POINTS,
        "last_regeneration_reason": reason,
        "pdes": entries,
    }


def load_fixture() -> dict[str, Any]:
    with GOLDEN_FIXTURE_PATH.open(encoding="utf-8") as handle:
        payload: dict[str, Any] = json.load(handle)
    return payload


def _write_fixture(payload: dict[str, Any]) -> None:
    GOLDEN_FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=False, allow_nan=False)
    GOLDEN_FIXTURE_PATH.write_text(serialized + "\n", encoding="utf-8")


def regenerate(*, reason: str, pde_names: list[str] | None = None) -> dict[str, Any]:
    """Regenerate the fixture, either wholly or for a named subset of PDEs.

    When ``pde_names`` is given, entries for the other PDEs are carried over from
    the existing fixture verbatim so a targeted regeneration cannot silently
    re-pin unrelated numbers.
    """
    if not reason.strip():
        raise ValueError("A non-empty --reason is required; unnamed drift is not permitted.")

    if pde_names is None:
        entries = [compute_golden_entry(spec) for spec in GOLDEN_PDE_SPECS]
        return build_fixture_payload(reason=reason, entries=entries)

    unknown = sorted(set(pde_names) - set(GOLDEN_PDE_NAMES))
    if unknown:
        raise ValueError(f"Unknown PDE name(s): {unknown}. Known: {list(GOLDEN_PDE_NAMES)}.")

    existing = {entry["name"]: entry for entry in load_fixture()["pdes"]}
    entries = [
        compute_golden_entry(spec) if spec.name in set(pde_names) else existing[spec.name]
        for spec in GOLDEN_PDE_SPECS
    ]
    return build_fixture_payload(reason=reason, entries=entries)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tests._helpers.regenerate_golden_fixture",
        description="Regenerate the v0.33e golden-numbers fixture with a named cause.",
        epilog=(
            "For cross-cutting numerical changes (FD backend, residual formulas, generator "
            "schemes), use --all so every PDE lands on the new code state atomically. Use "
            "--pde <name> only for isolated changes to a single PDE's generator or evaluator. "
            "If unsure, use --all -- a full regeneration is cheap."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--pde",
        action="append",
        dest="pdes",
        choices=GOLDEN_PDE_NAMES,
        help="Regenerate only this PDE (repeatable). Other entries are carried over verbatim.",
    )
    target.add_argument("--all", action="store_true", help="Regenerate every PDE entry.")
    parser.add_argument(
        "--reason",
        required=True,
        help="Named cause for the drift. Must also appear in the release-close CHANGELOG.",
    )
    args = parser.parse_args(argv)

    payload = regenerate(reason=args.reason, pde_names=None if args.all else args.pdes)
    _write_fixture(payload)

    regenerated = "all PDEs" if args.all else ", ".join(args.pdes)
    print(f"Wrote {GOLDEN_FIXTURE_PATH.relative_to(_REPO_ROOT)} ({regenerated}).")
    print(f"Recorded reason: {args.reason}")
    print("Reminder: the same cause must appear in the release-close CHANGELOG entry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
