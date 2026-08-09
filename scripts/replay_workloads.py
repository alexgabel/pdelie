"""Emit the v0.38b/c/d measurements the Gate F closure plan owes.

The existing replay lane runs ``run_admissibility_benchmark`` only, so the
`tolerance_numeric` values frozen from single-platform pilots -- v0.38b's
conditioning, v0.38c's quadrature, v0.38d's reference errors -- have never been
measured on a second platform. This produces them.

Scope comes from ``configs/gate_f_replay_scope.json`` and is **not restated
here**. Run 31278210299 swept derivative order 4, which the v0.38b confirmatory
freeze explicitly disclaims -- and five of its seven cross-platform
disagreements were at d=4, measured against a bound that was never established.
A harness that invents its own scope will do that again.

The row count is **derived** from the scope artifact. "286 rows" was an
invariant of the superseded design and is deliberately not preserved: removing
d=4 from the gate population changes it, and a count asserted from memory would
have hidden that.

CI tooling, not library API
===========================

Deliberately in ``scripts/`` and not in ``src/pdelie/``. It exercises the
library; it is not part of it, and the v0.38 public API freeze
(``docs/specs/public_api_freeze.v0_38.json``) should not grow to accommodate a
measurement harness.

Every row carries its ``error_metric_spec_id``
==============================================

Closure-plan section 5: the paired comparison must call
``require_matching_metric`` before quoting a relative gap. A row that does not
say which metric its number is in cannot be compared safely -- that is the
v0.37c pilot-1 defect, and carrying the id on every row is what makes it
impossible rather than discouraged.
"""

from __future__ import annotations

import json
import platform
import sys
from math import factorial
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from replay_contracts import (
    ReplayRowSpec,
    declaration_for,
)

from pdelie.contracts.error_metric_spec import ErrorMetricSpec
from pdelie.differentiation.error_reference import (
    measure_derivative_error,
)
from pdelie.differentiation.fornberg import (
    describe_grid_regularity,
    fornberg_weights,
)
from pdelie.residuals.irregular_weak import (
    nonuniform_trapezoidal_weights,
    validate_quadrature_weights,
)

LINF = ErrorMetricSpec(metric_spec_id="replay_linf_absolute", quantity="absolute", norm="linf")

#: Fixed, so both runners generate byte-identical node sets. A seeded RNG is
#: used only where the plan calls for irregular spacing, never for anything the
#: comparison depends on being the same.
_SEED = 20380


def _row(workload: str, label: str, *, order: int | None = None, **fields: Any) -> dict[str, Any]:
    """One measurement row, built from a typed spec.

    ``order`` is NOT optional metadata a caller may forget. If the workload's
    family is order-parameterised, :class:`ReplayRowSpec` refuses to construct
    without it -- so a call site that omits it fails loudly at build time
    rather than emitting a row with ``derivative_order: None`` that the gate
    then silently accepts.

    That omission, on ten ``deriv_ref_signal_regime_*`` rows, is exactly why the
    confirmatory replay `31326189317` could not close Gate F.
    """
    family, order_parameterized = declaration_for(workload)
    spec = ReplayRowSpec(
        workload_id=workload,
        workload_family=family,
        order_parameterized=order_parameterized,
        derivative_order=order,
        portability_class=_SCOPE["portability_classes"][workload],
        gate_use=(
            "exploratory_only"
            if order is not None and order not in _ORDERS
            else "gate_evidence"
        ),
        label=label,
    )
    return spec.as_row(**fields)


def _stretched(count: int, ratio: float) -> np.ndarray:
    """Nodes with an approximate max/min spacing ratio. Deterministic."""
    t = np.linspace(0.0, 1.0, count)
    if ratio <= 1.0:
        return t
    return (t ** (1.0 + np.log(ratio) / 3.0)) / (1.0 ** (1.0 + np.log(ratio) / 3.0))


# ---------------------------------------------------------------------------
# v0.38b -- 183 rows
# ---------------------------------------------------------------------------

def _scope() -> dict[str, Any]:
    """The single source of scope. Neither script keeps its own copy."""
    path = Path(__file__).resolve().parents[1] / "configs/gate_f_replay_scope.json"
    return json.loads(path.read_text())


_SCOPE = _scope()

#: Orders the v0.38b freeze establishes a claim for. Gate rows use only these.
_ORDERS = tuple(_SCOPE["supported_derivative_orders"])

#: Emitted, labelled, and excluded from any gate decision. Retained because
#: deleting a real measurement to make a gate pass is the wrong repair.
_EXPLORATORY_ORDERS = tuple(_SCOPE["exploratory_derivative_orders"])


def v0_38b_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    # 4 orders x 3 stencil sizes x 5 nodes = 60
    nodes_pool = np.array([0.0, 0.31, 1.07, 1.13, 2.71, 4.02, 4.15, 6.4, 7.1, 8.3, 9.0, 10.4, 11.9])
    for order in _ORDERS + _EXPLORATORY_ORDERS:
        for stencil in (order + 2, order + 4, order + 6):
            stencil = min(stencil, 13)
            for node_index in range(5):
                nodes = nodes_pool[node_index : node_index + stencil]
                if nodes.size < stencil:
                    nodes = nodes_pool[-stencil:]
                point = float(nodes[0] + 0.37 * (nodes[-1] - nodes[0]))
                w = fornberg_weights(nodes, point, order)
                degree = stencil - 1
                exact = (
                    factorial(degree) / factorial(degree - order) * point ** (degree - order)
                    if degree >= order
                    else 0.0
                )
                approx = float(np.dot(w.weights, nodes**degree))
                scale = max(abs(exact), 1.0)
                rows.append(
                    _row(
                        "fornberg_uniform_polynomial_exactness",
                        f"n{stencil}_i{node_index}",
                        order=order,
                        formal_accuracy=w.formal_accuracy,
                        absolute_error=abs(approx - exact),
                        reference_scale=scale,
                        error_metric_spec_id=LINF.metric_spec_id,
                        portability_class="tolerance_numeric",
                    )
                )

    # 4 orders x 5 grids x 3 refinements = 60
    for order in _ORDERS + _EXPLORATORY_ORDERS:
        for grid_index, ratio in enumerate((1.0, 2.0, 4.0, 7.0, 10.0)):
            for refinement, count in enumerate((81, 121, 161)):
                x = _stretched(count, ratio) * 2.0 * np.pi
                u = np.sin(2.0 * x)
                i = int(0.37 * count)
                half = 5
                lo = max(0, i - half)
                hi = min(count, lo + 11)
                lo = hi - 11
                w = fornberg_weights(x[lo:hi], x[i], order)
                approx = float(np.dot(w.weights, u[lo:hi]))
                exact = float(
                    {1: 2 * np.cos(2 * x[i]), 2: -4 * np.sin(2 * x[i]),
                     3: -8 * np.cos(2 * x[i]), 4: 16 * np.sin(2 * x[i])}[order]
                )
                rows.append(
                    _row(
                        "fornberg_perturbed_uniform_spacing_ratio_1_to_10",
                        f"g{grid_index}_r{refinement}",
                        order=order,
                        absolute_error=abs(approx - exact),
                        reference_scale=float(2.0**order),
                        spacing_ratio=describe_grid_regularity(x).spacing_ratio,
                        error_metric_spec_id=LINF.metric_spec_id,
                        portability_class="tolerance_numeric",
                    )
                )

    # 4 orders x 8 grids = 32
    for order in _ORDERS + _EXPLORATORY_ORDERS:
        for grid_index, ratio in enumerate((10.0, 40.0, 1e2, 1e3, 1e4, 1e5, 1e6, 1e8)):
            count = 121
            x = _stretched(count, ratio) * 2.0 * np.pi
            u = np.sin(2.0 * x)
            i = int(0.37 * count)
            lo = max(0, i - 5)
            hi = min(count, lo + 11)
            lo = hi - 11
            w = fornberg_weights(x[lo:hi], x[i], order)
            approx = float(np.dot(w.weights, u[lo:hi]))
            exact = float(
                {1: 2 * np.cos(2 * x[i]), 2: -4 * np.sin(2 * x[i]),
                 3: -8 * np.cos(2 * x[i]), 4: 16 * np.sin(2 * x[i])}[order]
            )
            regularity = describe_grid_regularity(x)
            rows.append(
                _row(
                    "fornberg_pathological_spacing_ratio_10_to_1e8",
                    f"g{grid_index}",
                        order=order,
                    absolute_error=abs(approx - exact),
                    reference_scale=float(2.0**order),
                    spacing_ratio=regularity.spacing_ratio,
                    # exact_discrete: the verdict must agree, not just the number
                    g5_verdict=regularity.g5_verdict,
                    error_metric_spec_id=LINF.metric_spec_id,
                    portability_class="tolerance_numeric",
                )
            )

    # 5 node counts x 3 spans = 15
    for count in (17, 33, 129, 1024, 4096):
        for span_index, span in enumerate((2.0 * np.pi, 1.0, 1000.0)):
            regularity = describe_grid_regularity(np.linspace(0.0, span, count, endpoint=False))
            rows.append(
                _row(
                    "fornberg_fn_12_uniform_spacing_ratio",
                    f"n{count}_s{span_index}",
                    ratio_minus_one=regularity.spacing_ratio - 1.0,
                    uniformity_tolerance=count * float(np.finfo(float).eps),
                    is_uniform=regularity.is_uniform,
                    reference_scale=1.0,
                    error_metric_spec_id=LINF.metric_spec_id,
                    portability_class="tolerance_numeric",
                )
            )

    # 4 orders x 4 boundary positions = 16
    for order in _ORDERS + _EXPLORATORY_ORDERS:
        for position_index, offset in enumerate((0, 1, 2, 3)):
            count = 81
            x = _stretched(count, 4.0) * 2.0 * np.pi
            u = np.sin(2.0 * x)
            i = offset + 6
            w = fornberg_weights(x[i - 5 : i + 6], x[i], order)
            approx = float(np.dot(w.weights, u[i - 5 : i + 6]))
            exact = float(
                {1: 2 * np.cos(2 * x[i]), 2: -4 * np.sin(2 * x[i]),
                 3: -8 * np.cos(2 * x[i]), 4: 16 * np.sin(2 * x[i])}[order]
            )
            rows.append(
                _row(
                    "fornberg_boundary_stencils_second_order",
                    f"p{position_index}",
                        order=order,
                    absolute_error=abs(approx - exact),
                    reference_scale=float(2.0**order),
                    error_metric_spec_id=LINF.metric_spec_id,
                    portability_class="tolerance_numeric",
                )
            )
    return rows


# ---------------------------------------------------------------------------
# v0.38c -- 39 rows
# ---------------------------------------------------------------------------


def v0_38c_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ratios = (1.0, 4.0, 16.0, 40.0, 79.0)

    # 5 ratios x 3 node counts = 15
    for ratio_index, ratio in enumerate(ratios):
        for count_index, count in enumerate((21, 41, 81)):
            x = _stretched(count, ratio) * 3.0
            report = validate_quadrature_weights(
                nonuniform_trapezoidal_weights(x), x, rule="nonuniform_trapezoidal"
            )
            rows.append(
                _row(
                    "weak_constant_exactness_nonuniform_trapezoidal",
                    f"r{ratio_index}_n{count_index}",
                    absolute_error=report["constant_exactness_error"],
                    tolerance=report["constant_exactness_tolerance"],
                    reference_scale=report["interval_length"],
                    error_metric_spec_id=LINF.metric_spec_id,
                    portability_class="tolerance_numeric",
                )
            )

    # 4 pass + 4 fail = 8
    from pdelie.errors import ScopeValidationError

    for case_index in range(8):
        count = 21
        x = _stretched(count, 4.0) * 3.0
        weights = nonuniform_trapezoidal_weights(x)
        should_pass = case_index < 4
        if not should_pass:
            weights = weights * (1.0 + 0.01 * (case_index - 3))
        try:
            validate_quadrature_weights(weights, x, rule="user_supplied_validated_weights")
            accepted = True
        except ScopeValidationError:
            accepted = False
        rows.append(
            _row(
                "weak_user_supplied_validation",
                f"case{case_index}",
                # exact_discrete: acceptance must agree, not merely be close
                accepted=accepted,
                expected_accepted=should_pass,
                portability_class="exact_discrete",
            )
        )

    # 5 ratios x 2 window widths = 10
    for ratio_index, ratio in enumerate(ratios):
        for width_index, count in enumerate((21, 61)):
            x = _stretched(count, ratio) * 3.0
            report = validate_quadrature_weights(
                nonuniform_trapezoidal_weights(x), x, rule="nonuniform_trapezoidal"
            )
            rows.append(
                _row(
                    "weak_linear_exactness_report",
                    f"r{ratio_index}_w{width_index}",
                    linear_exactness_relative=report["linear_exactness_relative"],
                    reference_scale=report["interval_length"],
                    error_metric_spec_id=LINF.metric_spec_id,
                    # Reported, not gated -- the freeze says so.
                    portability_class="tolerance_numeric",
                )
            )

    # 6 pairings = 6
    from pdelie.design.lineage import DesignRowLineage
    from pdelie.residuals.irregular_weak import WeakWindow, weak_window_overlap_fraction

    identities = [
        DesignRowLineage(trajectory_id="t", source_coordinate_id=f"x{i}", mask_id="m").identity()
        for i in range(12)
    ]
    for pairing_index, (start, width) in enumerate(
        ((0, 4), (0, 6), (2, 4), (3, 5), (0, 3), (4, 4))
    ):
        windows = [
            WeakWindow(
                window_id=f"w{k}",
                support_start=float(k),
                support_end=float(k + width),
                sample_row_identities=tuple(identities[start + k : start + k + width]),
                quadrature_rule="nonuniform_trapezoidal",
            )
            for k in range(2)
        ]
        overlap = weak_window_overlap_fraction(windows)
        rows.append(
            _row(
                "weak_overlap_declaration",
                f"p{pairing_index}",
                overlap_fraction=overlap["overlap_fraction"],
                windows_are_independent=overlap["windows_are_independent"],
                portability_class="exact_discrete",
            )
        )
    return rows


# ---------------------------------------------------------------------------
# v0.38d -- 64 rows
# ---------------------------------------------------------------------------

_FUNCS = {
    "sin2x": (lambda x: np.sin(2 * x), {1: lambda x: 2 * np.cos(2 * x), 2: lambda x: -4 * np.sin(2 * x),
                                         3: lambda x: -8 * np.cos(2 * x), 4: lambda x: 16 * np.sin(2 * x)}, 16.0),
    "expx3": (lambda x: np.exp(x / 3), {k: (lambda x, k=k: np.exp(x / 3) / 3**k) for k in (1, 2, 3, 4)}, 8.0),
    # Derivatives written out rather than left None: an omitted entry silently
    # shrank this population from the 64 the closure plan declares to 52, which
    # the count check caught. g(x) = exp(-(x-3)^2), z = x-3.
    "gauss": (
        lambda x: np.exp(-((x - 3.0) ** 2)),
        {
            1: lambda x: -2 * (x - 3.0) * np.exp(-((x - 3.0) ** 2)),
            2: lambda x: (4 * (x - 3.0) ** 2 - 2) * np.exp(-((x - 3.0) ** 2)),
            3: lambda x: (-8 * (x - 3.0) ** 3 + 12 * (x - 3.0)) * np.exp(-((x - 3.0) ** 2)),
            4: lambda x: (16 * (x - 3.0) ** 4 - 48 * (x - 3.0) ** 2 + 12)
            * np.exp(-((x - 3.0) ** 2)),
        },
        12.0,
    ),
    "poly": (lambda x: x**4, {1: lambda x: 4 * x**3, 2: lambda x: 12 * x**2,
                              3: lambda x: 24 * x, 4: lambda x: 24 * np.ones_like(x)}, 1500.0),
    "cosx": (lambda x: np.cos(x), {1: lambda x: -np.sin(x), 2: lambda x: -np.cos(x),
                                   3: lambda x: np.sin(x), 4: lambda x: np.cos(x)}, 1.0),
}


def v0_38d_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    x = np.linspace(0.0, 2.0 * np.pi, 161)

    for kind_label, reference_kind in (("analytical", "analytical"), ("manufactured", "refined_grid")):
        for name, (f, ders, scale) in _FUNCS.items():
            for order in _ORDERS + _EXPLORATORY_ORDERS:
                if ders[order] is None:
                    continue
                i = int(0.37 * x.size)
                w = fornberg_weights(x[i - 5 : i + 6], x[i], order)
                computed = np.array([float(np.dot(w.weights, f(x[i - 5 : i + 6])))])
                reference = np.array([float(ders[order](x[i]))])
                report = measure_derivative_error(
                    computed, reference, metric=LINF,
                    reference_kind=reference_kind, reference_scale=scale,
                )
                rows.append(
                    _row(
                        f"deriv_ref_signal_regime_{kind_label}",
                        f"{name}",
                        order=order,
                        reporting_regime=report.reporting_regime,
                        absolute_error=report.absolute_error,
                        relative_error=report.relative_error,
                        reference_scale=scale,
                        error_metric_spec_id=LINF.metric_spec_id,
                        portability_class="tolerance_numeric",
                    )
                )

    # floor regime: evaluate where the reference is ~0
    for name, (f, ders, scale) in _FUNCS.items():
        for order in _ORDERS + _EXPLORATORY_ORDERS:
            if ders[order] is None:
                continue
            zeros = np.abs(ders[order](x))
            i = int(np.argmin(zeros[6 : x.size - 6])) + 6
            w = fornberg_weights(x[i - 5 : i + 6], x[i], order)
            computed = np.array([float(np.dot(w.weights, f(x[i - 5 : i + 6])))])
            reference = np.array([float(ders[order](x[i]))])
            report = measure_derivative_error(
                computed, reference, metric=LINF,
                reference_kind="analytical", reference_scale=scale,
            )
            rows.append(
                _row(
                    "deriv_ref_floor_regime",
                    f"{name}",
                    order=order,
                    reporting_regime=report.reporting_regime,
                    absolute_error=report.absolute_error,
                    relative_error=report.relative_error,
                    reference_scale=scale,
                    error_metric_spec_id=LINF.metric_spec_id,
                    portability_class="tolerance_numeric",
                )
            )

    for case_index in range(4):
        report = measure_derivative_error(
            np.array([float(case_index + 1)]), None, metric=LINF, reference_kind="none"
        )
        rows.append(
            _row(
                "deriv_ref_none_kind",
                f"case{case_index}",
                reference_kind=report.reference_kind,
                reporting_regime=report.reporting_regime,
                absolute_error=report.absolute_error,
                relative_error=report.relative_error,
                portability_class="exact_discrete",
            )
        )
    return rows


def main() -> None:
    b, c, d = v0_38b_rows(), v0_38c_rows(), v0_38d_rows()
    payload = {
        "summary_type": "pdelie_gate_f_closure_replay",
        "summary_schema_version": "0.1",
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "counts": {"v0_38b": len(b), "v0_38c": len(c), "v0_38d": len(d),
                   "total": len(b) + len(c) + len(d)},
        "rows": b + c + d,
    }
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "gate_f_replay.json")
    target.write_text(json.dumps(payload, indent=2, allow_nan=False, sort_keys=True))
    print(json.dumps({**payload["platform"], **payload["counts"]}, indent=2))


if __name__ == "__main__":
    main()
