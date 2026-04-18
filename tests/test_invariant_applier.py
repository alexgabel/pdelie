from __future__ import annotations

import numpy as np
import pytest

from pdelie import FieldBatch, GeneratorFamily, InvariantMapSpec, SchemaValidationError, ScopeValidationError
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.invariants import InvariantApplier
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator


def make_translation_generator() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([1.0, 0.0, 0.0, 0.0]),
        normalization="l2_unit",
        diagnostics={"basis": ["1", "t", "x", "u"]},
    )


def make_invariant_map_spec(
    *,
    shift: float = 0.25,
    domain_validity: str = "global",
    diagnostics: dict[str, object] | None = None,
) -> InvariantMapSpec:
    return InvariantMapSpec(
        generator_metadata=make_translation_generator().to_dict(),
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": shift},
        domain_validity=domain_validity,
        inverse_available=True,
        diagnostics={} if diagnostics is None else diagnostics,
    )


def test_invariant_applier_returns_valid_field_batch_and_appends_provenance() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=60)
    spec = make_invariant_map_spec(shift=float(field.coords["x"][1]))

    transformed = InvariantApplier().apply(field, spec)

    transformed.validate()
    np.testing.assert_allclose(transformed.coords["x"], field.coords["x"])
    np.testing.assert_allclose(transformed.coords["time"], field.coords["time"])
    assert transformed.dims == field.dims
    assert transformed.var_names == field.var_names
    assert transformed.metadata == field.metadata
    assert len(transformed.preprocess_log) == len(field.preprocess_log) + 1
    assert transformed.preprocess_log[-1]["operation"] == "invariant_apply"
    assert transformed.preprocess_log[-1]["construction_method"] == "uniform_translation"
    assert transformed.preprocess_log[-1]["domain_validity"] == "global"
    assert transformed.preprocess_log[-1]["parameters"]["shift"] == pytest.approx(float(field.coords["x"][1]))
    assert field.preprocess_log == []

    derivatives = compute_spectral_fd_derivatives(transformed)
    residual = HeatResidualEvaluator().evaluate(transformed, derivatives)
    assert residual.residual.shape == transformed.values.shape


def test_invariant_applier_is_reproducible_and_preserves_diagnostics() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=61)
    spec = make_invariant_map_spec(diagnostics={"source": "test"})
    applier = InvariantApplier()

    first = applier.apply(field, spec)
    second = applier.apply(field, spec)

    np.testing.assert_allclose(first.values, second.values)
    assert first.preprocess_log[-1] == second.preprocess_log[-1]
    assert first.preprocess_log[-1]["diagnostics"] == {"source": "test"}


def test_invariant_applier_rejects_non_global_specs() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=62)
    spec = make_invariant_map_spec(
        domain_validity="local",
        diagnostics={"validity_note": "Only small shifts are supported in this local chart."},
    )

    with pytest.raises(ScopeValidationError, match="only supports global invariant specs"):
        InvariantApplier().apply(field, spec)


def test_invariant_applier_rejects_approximate_specs() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=67)
    spec = make_invariant_map_spec(
        diagnostics={
            "approximate": True,
            "approximation_note": "The invariant is only approximate under this fitted construction.",
        }
    )

    with pytest.raises(ScopeValidationError, match="does not support approximate invariant specs"):
        InvariantApplier().apply(field, spec)


def test_invariant_applier_rejects_unsupported_parameterizations() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=68)
    spec = InvariantMapSpec(
        generator_metadata={
            "schema_version": "0.1",
            "parameterization": "polynomial_scaling_affine",
            "coefficients": [1.0],
            "normalization": "l2_unit",
            "diagnostics": {},
        },
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": 0.25},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )

    with pytest.raises(ScopeValidationError, match="only supports polynomial_translation_affine generators"):
        InvariantApplier().apply(field, spec)


def test_invariant_applier_rejects_unsupported_construction_methods() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=69)
    spec = InvariantMapSpec(
        generator_metadata=make_translation_generator().to_dict(),
        construction_method="pointwise_translation",
        parameters={"axis": "x", "shift": 0.25},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )

    with pytest.raises(ScopeValidationError, match="only supports the 'uniform_translation' construction_method"):
        InvariantApplier().apply(field, spec)


def test_invariant_applier_rejects_unsupported_axes() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=70)
    spec = InvariantMapSpec(
        generator_metadata=make_translation_generator().to_dict(),
        construction_method="uniform_translation",
        parameters={"axis": "y", "shift": 0.25},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )

    with pytest.raises(ScopeValidationError, match="only supports translation along x"):
        InvariantApplier().apply(field, spec)


def test_invariant_applier_rejects_missing_shift_parameter() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=71)
    spec = InvariantMapSpec(
        generator_metadata=make_translation_generator().to_dict(),
        construction_method="uniform_translation",
        parameters={"axis": "x"},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )

    with pytest.raises(SchemaValidationError, match="must include 'shift'"):
        InvariantApplier().apply(field, spec)


def test_invariant_applier_rejects_non_numeric_shift_parameter() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=72)
    spec = InvariantMapSpec(
        generator_metadata=make_translation_generator().to_dict(),
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": "abc"},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )

    with pytest.raises(SchemaValidationError, match="must be numeric"):
        InvariantApplier().apply(field, spec)


def test_invariant_applier_rejects_non_finite_shift_parameter() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=73)
    spec = InvariantMapSpec(
        generator_metadata=make_translation_generator().to_dict(),
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": np.nan},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )

    with pytest.raises(SchemaValidationError, match="must be finite"):
        InvariantApplier().apply(field, spec)


def test_invariant_applier_rejects_non_periodic_fields() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=74)
    field.metadata["boundary_conditions"] = {"x": "dirichlet"}
    spec = make_invariant_map_spec()

    with pytest.raises(ScopeValidationError, match="requires periodic boundary conditions in x"):
        InvariantApplier().apply(field, spec)


def test_invariant_applier_rejects_unsupported_dims() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=75)
    reduced_field = FieldBatch(
        values=field.values[:, 0, :, :],
        dims=("batch", "x", "var"),
        coords={"x": field.coords["x"].copy()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None if field.mask is None else field.mask[:, 0, :, :].copy(),
    )

    with pytest.raises(ScopeValidationError, match="only supports dims"):
        InvariantApplier().apply(reduced_field, make_invariant_map_spec())


def test_invariant_applier_rejects_multi_variable_fields() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=76)
    stacked_values = np.concatenate((field.values, field.values), axis=-1)
    multi_var_field = FieldBatch(
        values=stacked_values,
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=["u", "v"],
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None if field.mask is None else np.concatenate((field.mask, field.mask), axis=-1),
    )

    with pytest.raises(ScopeValidationError, match="only supports a single scalar variable"):
        InvariantApplier().apply(multi_var_field, make_invariant_map_spec())


def test_heat_and_burgers_stable_symmetry_paths_remain_exact() -> None:
    heat_training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=63)
    heat_heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=64)
    burgers_training = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=65)
    burgers_heldout = generate_burgers_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=66)

    heat_generator = fit_translation_generator(heat_training, HeatResidualEvaluator(), epsilon=1e-4)
    burgers_generator = fit_translation_generator(burgers_training, BurgersResidualEvaluator(), epsilon=1e-4)

    heat_report = verify_translation_generator(heat_heldout, heat_generator, HeatResidualEvaluator())
    burgers_report = verify_translation_generator(burgers_heldout, burgers_generator, BurgersResidualEvaluator())

    assert heat_report.classification == "exact"
    assert burgers_report.classification == "exact"
