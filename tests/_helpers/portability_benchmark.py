from __future__ import annotations

import numpy as np

from pdelie import GeneratorFamily, InvariantMapSpec
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import generate_heat_1d_field_batch
from pdelie.discovery import to_pysindy_trajectories
from pdelie.invariants import InvariantApplier
from pdelie.portability import coerce_generator_family, export_generator_family_manifest
from pdelie.symmetry import (
    compare_generator_spans,
    diagnose_generator_family_closure,
    render_generator_family,
)


PORTABILITY_BENCHMARK_BRANCHES = ("in_memory", "canonical_payload", "manifest")
PORTABILITY_BENCHMARK_CONFIG: dict[str, object] = {
    "heat_seed": 510,
    "num_times": 17,
    "num_points": 16,
    "translation_shift_rule": "shift = x[1]",
}


def _make_translation_family() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={"source": "portability_benchmark"},
    )


def _x_basis_spec(*, labels: list[str], powers: list[list[int]]) -> dict[str, object]:
    return {
        "variables": ["x"],
        "component_names": ["xi"],
        "basis_terms": [
            {"label": label, "powers": power}
            for label, power in zip(labels, powers)
        ],
        "component_ordering": ["xi"],
        "term_ordering": list(labels),
        "layout": "component_major",
    }


def _velocity_basis_spec(labels: list[str]) -> dict[str, object]:
    return {
        "variables": ["x"],
        "component_names": ["velocity"],
        "basis_terms": [
            {"label": labels[0], "powers": [0]},
            {"label": labels[1], "powers": [1]},
        ],
        "component_ordering": ["velocity"],
        "term_ordering": list(labels),
        "layout": "component_major",
    }


def _make_polynomial_family(
    coefficients: np.ndarray,
    *,
    basis_spec: dict[str, object],
    normalization: str = "runtime_fixture",
    parameterization: str = "polynomial_point_family",
) -> GeneratorFamily:
    return GeneratorFamily(
        parameterization=parameterization,
        coefficients=np.asarray(coefficients, dtype=float),
        basis_spec=basis_spec,
        normalization=normalization,
        diagnostics={},
    )


def _legacy_translation_payload() -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "parameterization": "polynomial_translation_affine",
        "coefficients": [1.0, 0.0, 0.0, 0.0],
        "normalization": "l2_unit",
        "diagnostics": {},
    }


def _make_branch_families(canonical: GeneratorFamily) -> dict[str, GeneratorFamily]:
    return {
        "in_memory": canonical,
        "canonical_payload": coerce_generator_family(canonical.to_dict()),
        "manifest": coerce_generator_family(export_generator_family_manifest(canonical)),
    }


def _make_invariant_spec(generator_metadata: dict[str, object], shift: float) -> InvariantMapSpec:
    return InvariantMapSpec(
        generator_metadata=generator_metadata,
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": shift},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )


def _make_downstream_branch_result(
    generator: GeneratorFamily,
    *,
    shift: float,
) -> dict[str, object]:
    field = generate_heat_1d_field_batch(
        batch_size=1,
        num_times=int(PORTABILITY_BENCHMARK_CONFIG["num_times"]),
        num_points=int(PORTABILITY_BENCHMARK_CONFIG["num_points"]),
        seed=int(PORTABILITY_BENCHMARK_CONFIG["heat_seed"]),
    )
    transformed = InvariantApplier().apply(field, _make_invariant_spec(generator.to_dict(), shift))
    trajectories, time_values, feature_names = to_pysindy_trajectories(transformed)
    return {
        "transformed": transformed,
        "trajectories": trajectories,
        "time_values": np.asarray(time_values, dtype=float),
        "feature_names": list(feature_names),
    }


def run_portability_benchmark() -> dict[str, object]:
    translation_family = _make_translation_family()
    translation_branches = _make_branch_families(translation_family)
    legacy_translation = coerce_generator_family(_legacy_translation_payload())

    span_family = _make_polynomial_family(
        np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(labels=["1", "x", "x^2"], powers=[[0], [1], [2]]),
    )
    span_branches = _make_branch_families(span_family)

    closure_family = _make_polynomial_family(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_velocity_basis_spec(["offset", "linear"]),
    )
    closure_branches = _make_branch_families(closure_family)

    base_field = generate_heat_1d_field_batch(
        batch_size=1,
        num_times=int(PORTABILITY_BENCHMARK_CONFIG["num_times"]),
        num_points=int(PORTABILITY_BENCHMARK_CONFIG["num_points"]),
        seed=int(PORTABILITY_BENCHMARK_CONFIG["heat_seed"]),
    )
    shift = float(base_field.coords["x"][1])

    return {
        "settings": dict(PORTABILITY_BENCHMARK_CONFIG),
        "branch_names": list(PORTABILITY_BENCHMARK_BRANCHES),
        "translation": {
            "families": translation_branches,
            "rendered": {
                branch: render_generator_family(generator)
                for branch, generator in translation_branches.items()
            },
            "legacy_family": legacy_translation,
            "legacy_rendered": render_generator_family(legacy_translation),
        },
        "span": {
            "reference_family": span_family,
            "branches": span_branches,
            "reports": {
                branch: compare_generator_spans(span_family, generator)
                for branch, generator in span_branches.items()
            },
        },
        "closure": {
            "reference_family": closure_family,
            "branches": closure_branches,
            "reports": {
                branch: diagnose_generator_family_closure(
                    generator,
                    component_targets={"velocity": "x"},
                    computation_mode="auto",
                )
                for branch, generator in closure_branches.items()
            },
        },
        "downstream": {
            "shift": shift,
            "base_field": base_field,
            "branches": {
                branch: _make_downstream_branch_result(generator, shift=shift)
                for branch, generator in translation_branches.items()
            },
            "legacy": _make_downstream_branch_result(legacy_translation, shift=shift),
        },
    }
