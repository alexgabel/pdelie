from __future__ import annotations

import importlib

import numpy as np
import pytest

from pdelie import FieldBatch, GeneratorFamily, InvariantMapSpec, SchemaValidationError, ScopeValidationError
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import generate_heat_1d_field_batch
from pdelie.discovery import (
    build_translation_canonical_discovery_inputs,
    fit_pysindy_discovery,
    to_pysindy_trajectories,
)
from pdelie.portability import coerce_generator_family, export_generator_family_manifest
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator


def _make_translation_generator() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]]),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


def _make_nonconstant_translation_generator() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[0.0, 1.0, 0.0, 0.0]]),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


def _make_template(
    *,
    parameters: dict[str, object] | None = None,
    generator_metadata: dict[str, object] | None = None,
) -> InvariantMapSpec:
    return InvariantMapSpec(
        generator_metadata=_make_translation_generator().to_dict() if generator_metadata is None else generator_metadata,
        construction_method="uniform_translation",
        parameters={} if parameters is None else parameters,
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )


def _make_multi_var_field(field: FieldBatch) -> FieldBatch:
    return FieldBatch(
        values=np.concatenate((field.values, field.values), axis=-1),
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=["u", "v"],
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None,
    )


def _make_reduced_field(field: FieldBatch) -> FieldBatch:
    return FieldBatch(
        values=field.values[:, 0, :, :].copy(),
        dims=("batch", "x", "var"),
        coords={"x": field.coords["x"].copy()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None,
    )


def _make_masked_field(field: FieldBatch) -> FieldBatch:
    return FieldBatch(
        values=field.values.copy(),
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=np.zeros_like(field.values, dtype=bool),
    )


def _adapter_module():
    return importlib.import_module("pdelie.discovery.pysindy_adapter")


def test_known_translation_family_path_succeeds_and_preserves_field_contracts() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=17, num_points=16, seed=1001)
    generator = _make_translation_generator()

    result = build_translation_canonical_discovery_inputs(field, generator_family=generator)
    transformed = result["transformed_field"]

    transformed.validate()
    assert result["generator_metadata"] == generator.to_dict()
    assert result["construction_method"] == "uniform_translation"
    assert result["provenance"] == {
        "input_mode": "generator_family",
        "bridge": "to_pysindy_trajectories",
        "runtime_only": True,
    }
    assert transformed.dims == field.dims
    assert transformed.var_names == field.var_names
    assert transformed.metadata == field.metadata
    assert list(transformed.coords) == list(field.coords)
    np.testing.assert_allclose(transformed.coords["x"], field.coords["x"])
    np.testing.assert_allclose(transformed.coords["time"], field.coords["time"])
    assert len(transformed.preprocess_log) == len(field.preprocess_log) + 1
    assert transformed.preprocess_log[-1]["operation"] == "translation_canonical_discovery_inputs"
    assert transformed.preprocess_log[-1]["input_mode"] == "generator_family"
    assert transformed.preprocess_log[-1]["construction_method"] == "uniform_translation"
    assert transformed.preprocess_log[-1]["alignment_policy"]["kind"] == "heuristic_peak_alignment"
    assert transformed.preprocess_log[-1]["alignment_shifts"] == result["alignment_shifts"]


def test_imported_coerced_translation_family_path_succeeds() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=1002)
    manifest = export_generator_family_manifest(_make_translation_generator())
    coerced = coerce_generator_family(manifest)

    result = build_translation_canonical_discovery_inputs(field, generator_family=coerced)

    assert result["generator_metadata"] == coerced.to_dict()
    assert result["provenance"]["input_mode"] == "generator_family"
    assert len(result["alignment_shifts"]) == field.values.shape[0]


def test_discovered_translation_family_path_succeeds_within_span_tolerance() -> None:
    training = generate_heat_1d_field_batch(batch_size=4, num_times=17, num_points=16, seed=1003)
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=17, num_points=16, seed=1004)
    discovered = fit_translation_generator(training, HeatResidualEvaluator(), epsilon=1e-4)

    result = build_translation_canonical_discovery_inputs(heldout, generator_family=discovered)

    assert result["generator_metadata"]["parameterization"] == "polynomial_translation_affine"
    assert result["provenance"]["input_mode"] == "generator_family"


def test_nonconstant_translation_family_is_rejected() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=1005)

    with pytest.raises(ScopeValidationError, match="translation-span tolerance"):
        build_translation_canonical_discovery_inputs(field, generator_family=_make_nonconstant_translation_generator())


def test_invariant_spec_template_path_succeeds() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=1006)
    template = _make_template(parameters={"axis": "x"})

    result = build_translation_canonical_discovery_inputs(field, invariant_spec_template=template)

    assert result["generator_metadata"] == _make_translation_generator().to_dict()
    assert result["provenance"]["input_mode"] == "invariant_spec_template"


def test_invariant_spec_template_rejects_fixed_shift() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=1007)
    template = _make_template(parameters={"axis": "x", "shift": 0.25})

    with pytest.raises(SchemaValidationError, match="must not include 'shift'"):
        build_translation_canonical_discovery_inputs(field, invariant_spec_template=template)


def test_invariant_spec_template_rejects_unsupported_parameter_keys() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=1008)
    template = _make_template(parameters={"mode": "bad"})

    with pytest.raises(SchemaValidationError, match="unsupported keys"):
        build_translation_canonical_discovery_inputs(field, invariant_spec_template=template)


def test_invariant_spec_template_rejects_non_translation_generator_metadata() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=1009)
    template = _make_template(
        generator_metadata={
            "schema_version": "0.2",
            "parameterization": "polynomial_scaling_affine",
            "coefficients": [[1.0]],
            "basis_spec": {
                "variables": ["t", "x", "u"],
                "component_names": ["xi"],
                "basis_terms": [{"label": "1", "powers": [0, 0, 0]}],
                "component_ordering": ["xi"],
                "term_ordering": ["1"],
                "layout": "component_major",
            },
            "normalization": "l2_unit",
            "diagnostics": {},
        }
    )

    with pytest.raises(ScopeValidationError, match="polynomial_translation_affine"):
        build_translation_canonical_discovery_inputs(field, invariant_spec_template=template)


def test_requires_exactly_one_input_mode() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=1010)
    generator = _make_translation_generator()
    template = _make_template()

    with pytest.raises(SchemaValidationError, match="Exactly one"):
        build_translation_canonical_discovery_inputs(field)
    with pytest.raises(SchemaValidationError, match="Exactly one"):
        build_translation_canonical_discovery_inputs(
            field,
            generator_family=generator,
            invariant_spec_template=template,
        )


def test_rejects_wrong_input_types() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=1011)

    with pytest.raises(SchemaValidationError, match="GeneratorFamily"):
        build_translation_canonical_discovery_inputs(field, generator_family={"bad": "type"})  # type: ignore[arg-type]
    with pytest.raises(SchemaValidationError, match="InvariantMapSpec"):
        build_translation_canonical_discovery_inputs(field, invariant_spec_template={"bad": "type"})  # type: ignore[arg-type]


def test_rejects_masked_fields() -> None:
    field = _make_masked_field(generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=1012))

    with pytest.raises(ScopeValidationError, match="does not support masked fields"):
        build_translation_canonical_discovery_inputs(field, generator_family=_make_translation_generator())


def test_rejects_non_periodic_wrong_dims_and_multi_variable_fields() -> None:
    base = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=1013)
    non_periodic = FieldBatch(
        values=base.values.copy(),
        dims=base.dims,
        coords={name: coord.copy() for name, coord in base.coords.items()},
        var_names=list(base.var_names),
        metadata={**base.metadata, "boundary_conditions": {"x": "dirichlet"}},
        preprocess_log=list(base.preprocess_log),
        mask=None,
    )

    with pytest.raises(ScopeValidationError, match="requires periodic boundary conditions in x"):
        build_translation_canonical_discovery_inputs(non_periodic, generator_family=_make_translation_generator())
    with pytest.raises(ScopeValidationError, match="only supports dims"):
        build_translation_canonical_discovery_inputs(_make_reduced_field(base), generator_family=_make_translation_generator())
    with pytest.raises(ScopeValidationError, match="single scalar variable"):
        build_translation_canonical_discovery_inputs(_make_multi_var_field(base), generator_family=_make_translation_generator())


def test_alignment_is_deterministic_for_flat_and_repeated_maxima() -> None:
    base = generate_heat_1d_field_batch(batch_size=2, num_times=5, num_points=4, seed=1014)
    values = np.zeros_like(base.values)
    values[0, :, :, 0] = 1.0
    values[1, :, :, 0] = np.array(
        [
            [0.0, 3.0, 3.0, 1.0],
            [0.0, 3.0, 3.0, 1.0],
            [0.0, 3.0, 3.0, 1.0],
            [0.0, 3.0, 3.0, 1.0],
            [0.0, 3.0, 3.0, 1.0],
        ],
        dtype=float,
    )
    field = FieldBatch(
        values=values,
        dims=base.dims,
        coords={name: coord.copy() for name, coord in base.coords.items()},
        var_names=list(base.var_names),
        metadata=dict(base.metadata),
        preprocess_log=list(base.preprocess_log),
        mask=None,
    )

    result = build_translation_canonical_discovery_inputs(field, generator_family=_make_translation_generator())
    x = field.coords["x"]

    assert result["alignment_policy"]["kind"] == "heuristic_peak_alignment"
    assert result["alignment_policy"]["tie_break"] == "first_index"
    assert result["alignment_shifts"] == [pytest.approx(0.0), pytest.approx(float(x[1] - x[0]))]


def test_bridge_outputs_match_direct_bridge_on_transformed_field() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=1015)

    result = build_translation_canonical_discovery_inputs(field, generator_family=_make_translation_generator())
    expected_trajectories, expected_time_values, expected_feature_names = to_pysindy_trajectories(
        result["transformed_field"]
    )

    assert result["feature_names"] == expected_feature_names
    np.testing.assert_allclose(result["time_values"], expected_time_values)
    assert len(result["trajectories"]) == len(expected_trajectories)
    for actual, expected in zip(result["trajectories"], expected_trajectories):
        np.testing.assert_allclose(actual, expected)


def test_tiny_pysindy_integration_smoke_is_structural_only() -> None:
    try:
        _adapter_module()._require_discovery_dependencies()
    except ImportError as exc:
        pytest.skip(str(exc))

    field = generate_heat_1d_field_batch(batch_size=2, num_times=9, num_points=4, seed=1016)
    discovery_inputs = build_translation_canonical_discovery_inputs(
        field,
        generator_family=_make_translation_generator(),
    )

    result = fit_pysindy_discovery(
        discovery_inputs["trajectories"],
        discovery_inputs["time_values"],
        discovery_inputs["feature_names"],
    )

    assert result["status"] == "success"
    assert result["backend"] == "pysindy"
    assert isinstance(result["library_feature_names"], list)
    assert result["coefficients"].shape == (
        len(discovery_inputs["feature_names"]),
        len(result["library_feature_names"]),
    )
    assert np.all(np.isfinite(result["coefficients"]))
