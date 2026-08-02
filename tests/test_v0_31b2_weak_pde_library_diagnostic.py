"""v0.31b2 tests for the ``pdelie.tasks.weak_pde_library`` diagnostic wrapper.

This suite implements the full 31-test plan for the v0.31b2 diagnostic
wrapper: happy-path introspection, scope-rejection matrix, adversarial
strict-JSON boundary rejections, and composition-boundary invariants.

The tests deliberately import ``pysindy`` via ``pytest.importorskip`` because
the wrapper is only meaningful when the optional PySINDy backend is
installed. Warning filters are scoped narrowly (per-test) to avoid the
non-fatal ``numpy.product`` DeprecationWarning cascade documented in the
v0.31b2 preflight.
"""

from __future__ import annotations

import copy
import importlib
import importlib.metadata as _importlib_metadata
import inspect as _inspect
import json
import math
import sys
import warnings
from unittest.mock import MagicMock

import numpy as np
import pytest

pytest.importorskip(
    "pysindy",
    reason=(
        "pysindy is an optional backend; v0.31b2 diagnostic tests are "
        "skipped when unavailable."
    ),
)

import pdelie
from pdelie.contracts import FieldBatch
from pdelie.data import generate_heat_1d_field_batch
from pdelie.discovery import to_pysindy_trajectories
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.reporting.summaries import summarize_weak_form_supportability
from pdelie.tasks import (
    PySINDyDiscoveryUnsupportedBoundaryError,
    WeakPDELibraryDiagnostic,
    inspect_pysindy_weak_pde_library,
    run_pysindy_pde_task,
    summarize_discovery_task_result,
    summarize_pysindy_weak_pde_library_diagnostic,
)
from pdelie.tasks import weak_pde_library as _weak_pde_library

# ---------------------------------------------------------------------------
# Deterministic fixtures
# ---------------------------------------------------------------------------


def _build_heat_field() -> FieldBatch:
    # The grid must satisfy the K-scaled defensive lower bound
    # max(8, 4 * num_domain_centers_K); the default diagnostic uses K=16, so
    # 64 samples on each axis is the minimum compliant fixture.
    return generate_heat_1d_field_batch(
        batch_size=1,
        num_times=64,
        num_points=64,
        seed=3120,
    )


def _run_default_diagnostic() -> dict[str, object]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        warnings.simplefilter("ignore", category=DeprecationWarning)
        return inspect_pysindy_weak_pde_library(
            _build_heat_field(),
            task_name="v0_31b2_happy_path_smoke",
            library_configuration=WeakPDELibraryDiagnostic(
                polynomial_degree=2,
                derivative_order=2,
                num_domain_centers_K=16,
            ),
        seed=13)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_1_installed_pysindy_version_recorded_in_summary_provenance() -> None:
    """Provenance echoes the installed PySINDy distribution version."""
    summary = _run_default_diagnostic()

    provenance = summary["provenance"]
    assert isinstance(provenance, dict)
    installed_version = _importlib_metadata.version("pysindy")
    assert provenance["pysindy_version"] == installed_version
    assert summary["backend_version"]["pysindy"] == installed_version


def test_5_summary_type_is_pdelie_weak_pde_library_diagnostic() -> None:
    """A periodic scalar 1D manufactured Heat input yields the frozen summary_type."""
    summary = _run_default_diagnostic()
    assert summary["summary_type"] == "pdelie_weak_pde_library_diagnostic"


def test_6_diagnostic_only_is_exactly_true() -> None:
    """The load-bearing diagnostic_only marker is exactly True (not truthy-1)."""
    summary = _run_default_diagnostic()
    assert summary["diagnostic_only"] is True


def test_7_method_family_is_frozen_string() -> None:
    """method_family matches the design-frozen identifier verbatim."""
    summary = _run_default_diagnostic()
    assert summary["method_family"] == "pysindy_weak_pde_library_polynomial_gauss_v1"


def test_8_backend_version_includes_pdelie_and_pysindy() -> None:
    """backend_version dict contains pdelie, pysindy; sklearn/scipy when installed."""
    summary = _run_default_diagnostic()
    backend_version = summary["backend_version"]

    assert isinstance(backend_version, dict)
    assert "pdelie" in backend_version
    assert "pysindy" in backend_version
    for key, value in backend_version.items():
        assert isinstance(key, str) and key
        assert isinstance(value, str) and value

    for optional_dist_name, optional_key in (("scikit-learn", "sklearn"), ("scipy", "scipy")):
        try:
            _importlib_metadata.version(optional_dist_name)
        except _importlib_metadata.PackageNotFoundError:
            continue
        assert optional_key in backend_version, (
            f"{optional_key!r} should be recorded when its distribution is installed"
        )


def test_9_weak_feature_names_deterministic_across_two_constructions() -> None:
    """Two independent runs on the same input yield identical feature-name ordering."""
    first = _run_default_diagnostic()
    second = _run_default_diagnostic()
    assert first["weak_feature_names"] == second["weak_feature_names"]
    assert len(set(first["weak_feature_names"])) == len(first["weak_feature_names"])


def test_10_weak_matrix_shape_and_target_shape_are_internally_consistent() -> None:
    """The matrix's row count matches the target's row count; column count matches feature count."""
    summary = _run_default_diagnostic()
    matrix_shape = summary["weak_matrix_shape"]
    target_shape = summary["weak_target_shape"]
    feature_names = summary["weak_feature_names"]

    assert isinstance(matrix_shape, list) and len(matrix_shape) == 2
    assert isinstance(target_shape, list) and len(target_shape) == 2
    # (K, num_features) vs (K, num_targets=1) — row counts must match.
    assert matrix_shape[0] == target_shape[0]
    assert matrix_shape[1] == len(feature_names)


def test_13_strict_json_roundtrip_with_allow_nan_false_succeeds() -> None:
    """The composed payload is strict-JSON safe (no NaN/Inf leak through)."""
    summary = _run_default_diagnostic()
    encoded = json.dumps(summary, allow_nan=False)
    decoded = json.loads(encoded)
    assert decoded == summary


def test_14_dirichlet_nonperiodic_field_is_rejected() -> None:
    """A Dirichlet (nonperiodic-in-x) FieldBatch raises the runtime BC guard."""
    field = _build_heat_field()

    # Deep-copy and mutate the boundary condition to Dirichlet with unspecified faces.
    mutated_metadata = copy.deepcopy(field.metadata)
    mutated_metadata["boundary_conditions"]["x"] = {
        "type": "dirichlet",
        "left": {"value": None, "time_dependent": False, "source": "inferred_unspecified"},
        "right": {"value": None, "time_dependent": False, "source": "inferred_unspecified"},
        "specified": False,
        "notes": None,
    }
    dirichlet_field = FieldBatch(
        values=field.values,
        dims=field.dims,
        coords=field.coords,
        var_names=field.var_names,
        metadata=mutated_metadata,
        preprocess_log=list(field.preprocess_log),
    )

    with pytest.raises(PySINDyDiscoveryUnsupportedBoundaryError):
        inspect_pysindy_weak_pde_library(
            dirichlet_field,
            task_name="v0_31b2_dirichlet_rejection",
        seed=13)


def test_25_no_root_pdelie_export_for_diagnostic_names() -> None:
    """None of the b2 diagnostic public names leak into the root pdelie namespace."""
    forbidden = (
        "WeakPDELibraryDiagnostic",
        "summarize_pysindy_weak_pde_library_diagnostic",
        "inspect_pysindy_weak_pde_library",
        "weak_pde_library",
        "PySINDyDiscoveryUnsupportedBoundaryError",
    )
    for name in forbidden:
        assert not hasattr(pdelie, name), (
            f"pdelie unexpectedly exports {name!r} at the root — v0.31 is "
            "submodule-only for the task-bridge surface."
        )


def test_26_new_summary_type_cannot_pass_as_discovery_task_result() -> None:
    """The diagnostic summary_type is strictly distinct from discovery_task_result."""
    summary = _run_default_diagnostic()

    assert summary["summary_type"] != "discovery_task_result"
    # And no key in the diagnostic summary mimics the underlying_discovery_result
    # container from v0.31b1.
    assert "underlying_discovery_result" not in summary
    # And feeding the diagnostic payload into summarize_discovery_task_result
    # should not silently pass off as a discovery TaskResult — the assembler
    # requires kwargs, not a single dict, so the mismatch is structural.
    assert callable(summarize_discovery_task_result)


def test_27_no_wsindy_or_noise_robustness_claims_in_output_or_module() -> None:
    """No output field or module docstring claims WSINDy / noise robustness / validated weak recovery."""
    summary = _run_default_diagnostic()
    encoded = json.dumps(summary).lower()

    forbidden_substrings = (
        "wsindy benchmark",
        "noise robustness",
        "robust to noise",
        "validated weak recovery",
    )
    for phrase in forbidden_substrings:
        assert phrase not in encoded, (
            f"emitted summary must not claim {phrase!r}; observed in output"
        )

    module_docstring = (_weak_pde_library.__doc__ or "").lower()
    for phrase in forbidden_substrings:
        assert phrase not in module_docstring, (
            f"module docstring must not claim {phrase!r}"
        )

    # Also check the public function docstrings.
    for func in (
        inspect_pysindy_weak_pde_library,
        summarize_pysindy_weak_pde_library_diagnostic,
    ):
        doc = (_inspect.getdoc(func) or "").lower()
        for phrase in forbidden_substrings:
            assert phrase not in doc, (
                f"{func.__name__} docstring must not claim {phrase!r}"
            )


def test_30_v0_31b0_golden_fixture_still_works() -> None:
    """The v0.31b0 golden bridge fixture (to_pysindy_trajectories) still runs cleanly.

    This anchors the b2 wrapper against silent regressions in the bridge
    surface it (independently) also builds upon.
    """
    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=5, num_points=16, seed=310
    )
    trajectories, time_values, feature_names = to_pysindy_trajectories(field)
    assert isinstance(trajectories, list) and len(trajectories) == 1
    assert time_values.shape == (5,)
    assert len(feature_names) == 16
    for idx, name in enumerate(feature_names):
        assert name == f"u__x_index_{idx}"


def test_31_v0_31b1_discovery_task_runtime_still_works() -> None:
    """The v0.31b1 ``run_pysindy_pde_task`` composed TaskResult still assembles cleanly."""
    import pysindy  # local import — already gated by module-level importorskip

    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=5, num_points=16, seed=3110
    )
    optimizer = pysindy.STLSQ(threshold=0.1, alpha=0.05, max_iter=20)
    feature_library = pysindy.PolynomialLibrary(degree=2, include_bias=True)
    differentiation_method = pysindy.FiniteDifference()
    model = pysindy.SINDy(
        optimizer=optimizer,
        feature_library=feature_library,
        differentiation_method=differentiation_method,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        warnings.simplefilter("ignore", category=DeprecationWarning)
        task_result = run_pysindy_pde_task(
            field,
            task_name="v0_31b1_regression_smoke",
            pysindy_model=model,
        )

    assert task_result["summary_type"] == "discovery_task_result"
    assert task_result["backend_name"] == "pysindy"
    assert task_result["pysindy_bridge_variant"] == "periodic_only_v1"


# ---------------------------------------------------------------------------
# 2-4. Preflight / API compatibility tests
# ---------------------------------------------------------------------------


def test_2_pysindy_is_imported_lazily_not_at_module_scope() -> None:
    """The wrapper module must not eagerly bind ``pysindy`` at import time.

    The wrapper is optional-dependency guarded; importing
    ``pdelie.tasks.weak_pde_library`` MUST not require ``pysindy`` to be
    installed. This is enforced structurally: ``pysindy`` is not a
    module-level name in the wrapper's namespace.
    """
    assert "pysindy" not in vars(_weak_pde_library), (
        "pdelie.tasks.weak_pde_library must import pysindy lazily inside "
        "the runtime, not at module scope; found a module-level pysindy "
        "binding which would eagerly require the optional extra."
    )


def test_3_missing_pysindy_raises_actionable_scope_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When PySINDy is not importable, the wrapper raises ScopeValidationError.

    The runtime catches ``ImportError`` from ``import pysindy`` and re-raises
    a ``ScopeValidationError`` (optional-extra pattern). We simulate the
    missing dependency by shadowing ``sys.modules['pysindy']`` with ``None``,
    which turns ``import pysindy`` into an ``ImportError``.
    """
    field = _build_heat_field()
    monkeypatch.setitem(sys.modules, "pysindy", None)  # type: ignore[arg-type]

    with pytest.raises(ScopeValidationError), warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        warnings.simplefilter("ignore", category=DeprecationWarning)
        inspect_pysindy_weak_pde_library(
            field,
            task_name="v0_31b2_missing_pysindy",
        seed=13)


def test_4_unsupported_weak_pde_library_signature_raises_scope_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A drifted WeakPDELibrary signature must surface as ScopeValidationError.

    We monkeypatch ``pysindy.WeakPDELibrary`` with a stub whose constructor
    only accepts an empty kwargs set. The wrapper passes kwargs like
    ``derivative_order=`` and ``spatiotemporal_grid=``, so the stub raises
    ``TypeError``. The runtime must catch that and raise a
    ``ScopeValidationError`` rather than silently degrade or crash with a
    raw ``TypeError``.
    """
    import pysindy  # local — gated by module-level importorskip

    class _StubWeakPDELibrary:
        def __init__(self) -> None:
            raise TypeError(
                "stub_weak_pde_library_takes_no_kwargs (v0.31b2 signature-drift test)"
            )

    monkeypatch.setattr(pysindy, "WeakPDELibrary", _StubWeakPDELibrary, raising=True)

    field = _build_heat_field()
    with pytest.raises(ScopeValidationError), warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        warnings.simplefilter("ignore", category=DeprecationWarning)
        inspect_pysindy_weak_pde_library(
            field,
            task_name="v0_31b2_signature_drift",
        seed=13)


# ---------------------------------------------------------------------------
# 11-12. Positive diagnostic invariants
# ---------------------------------------------------------------------------


def test_11_retained_plus_skipped_rows_equals_attempted_row_count() -> None:
    """``retained_weak_rows + skipped_weak_rows`` accounts for every attempted row.

    Under a healthy periodic Heat 1D input the WeakPDELibrary emits K
    subdomain rows and none are skipped. The invariant is:
    ``retained + skipped == weak_matrix_shape[0]``. If the API does not
    expose the counts (both None) we assert a warning was emitted instead.
    """
    summary = _run_default_diagnostic()
    retained = summary["retained_weak_rows"]
    skipped = summary["skipped_weak_rows"]
    matrix_rows = int(summary["weak_matrix_shape"][0])  # type: ignore[index]

    if retained is None or skipped is None:
        # Fallback path: the underlying API does not expose row-inventory.
        assert retained is None and skipped is None, (
            "retained/skipped row counts must both be None if either is; "
            f"got retained={retained!r}, skipped={skipped!r}."
        )
        assert isinstance(summary["warnings"], list) and summary["warnings"], (
            "when retained/skipped are unavailable the wrapper must emit at "
            "least one warning explaining the coarser accounting."
        )
    else:
        assert isinstance(retained, int) and isinstance(skipped, int)
        assert retained + skipped == matrix_rows, (
            "retained_weak_rows + skipped_weak_rows must equal the attempted "
            f"row count (weak_matrix_shape[0]={matrix_rows}); got "
            f"{retained} + {skipped} = {retained + skipped}."
        )
        assert retained >= 0 and skipped >= 0


def test_12_all_emitted_numeric_fields_are_finite_or_none() -> None:
    """Nested walk: every int/float in the payload is finite or ``None``.

    The wrapper's contract is that NaN/Inf are NEVER surfaced. They are
    converted to ``None`` with an accompanying warnings entry before the
    strict-JSON boundary. This test walks the entire payload tree to
    confirm.
    """
    summary = _run_default_diagnostic()

    def _walk(value: object, path: str) -> None:
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            assert math.isfinite(float(value)), (
                f"non-finite numeric value at {path!r}: {value!r}"
            )
            return
        if isinstance(value, dict):
            for key, item in value.items():
                _walk(item, f"{path}.{key}")
            return
        if isinstance(value, (list, tuple)):
            for idx, item in enumerate(value):
                _walk(item, f"{path}[{idx}]")
            return
        # str / None / other JSON-safe scalar — nothing to check.

    _walk(summary, "summary")


# ---------------------------------------------------------------------------
# 15-19. Scope rejection matrix
# ---------------------------------------------------------------------------


def _mutate_coord_to_nonuniform(field: FieldBatch, dim: str) -> FieldBatch:
    """Post-construction mutation: rewrite ``coords[dim]`` to a nonuniform grid.

    ``FieldBatch.validate()`` rejects nonuniform spatial coords at
    construction time. This helper bypasses that check by mutating the
    dataclass instance's coords dict in place, so that downstream
    consumers (like the b2 wrapper's own ``_is_uniform_1d`` guard) can be
    tested against a nonuniform grid.
    """
    coord = np.asarray(field.coords[dim], dtype=float).copy()
    # Perturb one interior sample to make the spacing non-uniform.
    coord[len(coord) // 2] += 0.37
    field.coords[dim] = coord
    return field


def test_15_nonuniform_x_grid_rejected() -> None:
    """A FieldBatch with a nonuniform x-grid is rejected by the wrapper."""
    field = _build_heat_field()
    _mutate_coord_to_nonuniform(field, "x")
    with pytest.raises(ScopeValidationError):
        inspect_pysindy_weak_pde_library(
            field, task_name="v0_31b2_nonuniform_x_rejection", seed=13
        )


def test_16_nonuniform_t_grid_rejected() -> None:
    """A FieldBatch with a nonuniform t-grid is rejected by the wrapper."""
    field = _build_heat_field()
    _mutate_coord_to_nonuniform(field, "time")
    with pytest.raises(ScopeValidationError):
        inspect_pysindy_weak_pde_library(
            field, task_name="v0_31b2_nonuniform_t_rejection", seed=13
        )


def test_17_multivariable_input_rejected() -> None:
    """A FieldBatch with more than one scalar var is rejected."""
    base = _build_heat_field()
    # Stack a second channel by duplicating the primary variable.
    duplicated = np.concatenate([base.values, base.values], axis=-1)
    field = FieldBatch(
        values=duplicated,
        dims=base.dims,
        coords={str(k): np.asarray(v, dtype=float).copy() for k, v in base.coords.items()},
        var_names=["u", "v"],
        metadata=copy.deepcopy(base.metadata),
        preprocess_log=list(base.preprocess_log),
    )
    with pytest.raises(ScopeValidationError):
        inspect_pysindy_weak_pde_library(
            field, task_name="v0_31b2_multivariable_rejection", seed=13
        )


def test_18_two_dimensional_field_batch_rejected() -> None:
    """A 2D+time FieldBatch (``dims`` includes ``y``) is rejected."""
    num_times = 12
    num_x = 12
    num_y = 12
    values = np.zeros((1, num_times, num_x, num_y, 1), dtype=float)
    x_coord = np.linspace(0.0, 2 * math.pi, num_x, endpoint=False, dtype=float)
    y_coord = np.linspace(0.0, 2 * math.pi, num_y, endpoint=False, dtype=float)
    t_coord = np.linspace(0.0, 0.6, num_times, dtype=float)
    field = FieldBatch(
        values=values,
        dims=("batch", "time", "x", "y", "var"),
        coords={"time": t_coord, "x": x_coord, "y": y_coord},
        var_names=["u"],
        metadata={
            "boundary_conditions": {"x": "periodic", "y": "periodic"},
            "coordinate_system": "cartesian",
            "grid_regularity": "uniform",
            "grid_type": "rectilinear",
            "parameter_tags": {},
        },
        preprocess_log=[],
    )
    with pytest.raises(ScopeValidationError):
        inspect_pysindy_weak_pde_library(
            field, task_name="v0_31b2_two_dimensional_rejection", seed=13
        )


def test_19_too_small_grid_rejected_with_actionable_message() -> None:
    """A grid that is too small for K subdomains raises with an actionable message."""
    field = generate_heat_1d_field_batch(
        batch_size=1,
        num_times=32,
        num_points=6,  # under the wrapper's 8-x-sample lower bound
        seed=1919,
    )
    with pytest.raises(ScopeValidationError) as excinfo, warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        warnings.simplefilter("ignore", category=DeprecationWarning)
        inspect_pysindy_weak_pde_library(
            field,
            task_name="v0_31b2_too_small_grid",
            library_configuration=WeakPDELibraryDiagnostic(
                polynomial_degree=2,
                derivative_order=2,
                num_domain_centers_K=16,
            ),
        seed=13)
    message = str(excinfo.value).lower()
    # The message must mention the deficient dimension AND a concrete lower bound.
    assert "x-samples" in message or "x samples" in message, message
    assert "8" in message, message


# ---------------------------------------------------------------------------
# 20-23. Adversarial strict-JSON boundary tests
# ---------------------------------------------------------------------------


def _minimal_valid_summarizer_kwargs() -> dict[str, object]:
    """Build a minimal, strict-JSON-safe kwargs bundle for the summarizer.

    The bundle passes the composition-boundary check on its own so any
    single-field mutation in tests 20-22 is the sole reason the summarizer
    fails.
    """
    return {
        "backend_version": {"pdelie": "0.31.0", "pysindy": "1.7.5"},
        "library_configuration": {
            "polynomial_degree": 2,
            "derivative_order": 2,
            "include_bias": False,
            "include_interaction": True,
            "interaction_only": True,
            "num_domain_centers_K": 16,
            "test_function_polynomial_degree_p": 4,
            "library_function_names": ["x0", "x0^2"],
            "notes": None,
            "extra": {},
        },
        "spatiotemporal_grid_shape": [32, 32, 2],
        "input_field_shape": [32, 32, 1],
        "weak_feature_names": ["x0", "x0^2"],
        "weak_matrix_shape": [16, 2],
        "weak_target_shape": [16, 1],
        "retained_weak_rows": 16,
        "skipped_weak_rows": 0,
        "skipped_row_reasons": [],
        "finite_value_status": "all_finite",
        "column_norms": {"x0": 1.0, "x0^2": 2.0},
        "matrix_rank": 2,
        "matrix_condition_number": 3.5,
        "warnings": [],
        "compatibility_notes": [],
        "provenance": {
            "backend_name": "pysindy",
            "task_name": "v0_31b2_boundary_probe",
            "diagnostic_only": True,
            "pysindy_version": "1.7.5",
        },
    }


def test_20_nan_in_column_norms_rejected_by_strict_json_boundary() -> None:
    """A NaN in ``column_norms`` is rejected by the strict-JSON boundary."""
    kwargs = _minimal_valid_summarizer_kwargs()
    kwargs["column_norms"] = {"x0": float("nan"), "x0^2": 2.0}
    with pytest.raises(SchemaValidationError):
        summarize_pysindy_weak_pde_library_diagnostic(**kwargs)  # type: ignore[arg-type]


def test_21_plus_inf_in_matrix_condition_number_rejected() -> None:
    """A ``+Inf`` in ``matrix_condition_number`` is rejected."""
    kwargs = _minimal_valid_summarizer_kwargs()
    kwargs["matrix_condition_number"] = float("inf")
    with pytest.raises(SchemaValidationError):
        summarize_pysindy_weak_pde_library_diagnostic(**kwargs)  # type: ignore[arg-type]


def test_22_nan_in_provenance_or_backend_version_rejected() -> None:
    """A NaN nested inside provenance or backend_version is rejected."""
    # (a) provenance carries a NaN.
    kwargs_prov = _minimal_valid_summarizer_kwargs()
    provenance = dict(kwargs_prov["provenance"])  # type: ignore[arg-type]
    provenance["mystery_metric"] = float("nan")
    kwargs_prov["provenance"] = provenance
    with pytest.raises(SchemaValidationError):
        summarize_pysindy_weak_pde_library_diagnostic(**kwargs_prov)  # type: ignore[arg-type]

    # (b) backend_version carries a NaN (routed through str() by the
    # summarizer, so the guaranteed leak path is via provenance; but a
    # non-stringifiable NaN dict value must still be caught in the general
    # payload walk). We use a dict field that isn't str-coerced: the
    # library_configuration.extra bag.
    kwargs_extra = _minimal_valid_summarizer_kwargs()
    library_configuration = dict(kwargs_extra["library_configuration"])  # type: ignore[arg-type]
    library_configuration["extra"] = {"suspect_scalar": float("nan")}
    kwargs_extra["library_configuration"] = library_configuration
    with pytest.raises(SchemaValidationError):
        summarize_pysindy_weak_pde_library_diagnostic(**kwargs_extra)  # type: ignore[arg-type]


def test_23_validate_strict_json_compatible_called_exactly_once_at_composition_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The composition boundary invokes the strict validator exactly once.

    The runtime may perform intermediate strict-JSON checks (e.g. inside
    ``WeakPDELibraryDiagnostic.as_dict``) but the load-bearing invariant is
    that the *fully composed summary payload* passes through
    ``_validate_strict_json_compatible`` exactly once. The composition
    boundary call is uniquely identified by the ``name`` kwarg
    ``"pysindy weak pde library diagnostic summary"``.
    """
    real_validator = _weak_pde_library._validate_strict_json_compatible
    spy = MagicMock(side_effect=real_validator)
    monkeypatch.setattr(
        _weak_pde_library, "_validate_strict_json_compatible", spy, raising=True
    )

    field = _build_heat_field()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        warnings.simplefilter("ignore", category=DeprecationWarning)
        result = inspect_pysindy_weak_pde_library(
            field,
            task_name="v0_31b2_composition_boundary_spy",
        seed=13)

    composition_boundary_calls = [
        call
        for call in spy.call_args_list
        if call.kwargs.get("name") == "pysindy weak pde library diagnostic summary"
    ]
    assert len(composition_boundary_calls) == 1, (
        "the fully composed summary payload must pass through "
        "_validate_strict_json_compatible exactly once; observed "
        f"{len(composition_boundary_calls)} composition-boundary call(s) out "
        f"of {spy.call_count} total call(s)."
    )
    passed_payload = composition_boundary_calls[0].args[0]
    assert passed_payload == result, (
        "the payload handed to _validate_strict_json_compatible at the "
        "composition boundary must be byte-for-byte the returned summary."
    )


# ---------------------------------------------------------------------------
# 24. Relationship boundary — weak_1d must remain importable and stable
# ---------------------------------------------------------------------------


def test_24_pdelie_residuals_weak_1d_module_stays_importable_and_stable() -> None:
    """pdelie.residuals.weak_1d imports cleanly and its identifier strings stay pdelie-native.

    weak_1d is guaranteed through v0.32 close; v0.31b2 must not remove or
    re-scope it. We assert the module imports, that its two public entry
    points remain callable, and that its pinned identifier strings
    (src/pdelie/residuals/weak_1d.py:20-22) are the pdelie-native ones,
    distinct from the b2 ``pysindy_weak_pde_library_*`` provenance labels.
    """
    weak_1d = importlib.import_module("pdelie.residuals.weak_1d")

    # Public entry points must still exist and be callable.
    for public_fn_name in (
        "evaluate_weak_heat_residual",
        "evaluate_weak_burgers_residual",
    ):
        assert hasattr(weak_1d, public_fn_name), (
            f"pdelie.residuals.weak_1d must still expose {public_fn_name!r}; "
            "v0.31b2 does not remove weak_1d."
        )
        assert callable(getattr(weak_1d, public_fn_name))

    # Pinned identifier strings (source-level constants) must remain the
    # pdelie-native ones, distinct from the b2 pysindy_-prefixed labels.
    identifier_attrs = {
        "_METHOD_FAMILY": "local_separable_quartic_bump_trapezoid_v1",
        "_QUADRATURE": "composite_tensor_product_trapezoidal_native_window",
        "_TEST_FUNCTION": "separable_quartic_bump_beta",
    }
    for attr, expected in identifier_attrs.items():
        assert hasattr(weak_1d, attr), (
            f"pdelie.residuals.weak_1d must retain the {attr!r} identifier "
            "constant."
        )
        value = getattr(weak_1d, attr)
        assert value == expected, (
            f"weak_1d.{attr} drifted: expected {expected!r}, got {value!r}. "
            "weak_1d identifier strings are pinned through v0.32 close."
        )
        assert not value.startswith("pysindy_"), (
            f"weak_1d.{attr}={value!r} must NOT carry a pysindy_-prefixed "
            "identifier; that prefix belongs to the b2 diagnostic surface."
        )


# ---------------------------------------------------------------------------
# 28-29. Supportability policy assertions
# ---------------------------------------------------------------------------


def test_28_supportability_policy_reports_supports_pysindy_weak_library_diagnostic_true() -> None:
    """The reporting policy exposes ``supports_pysindy_weak_library_diagnostic == True``.

    The frozen spec places this key in
    ``src/pdelie/reporting/summaries.py::summarize_weak_form_supportability``
    policy dict alongside the pre-existing ``supports_weak_derivative_backend``
    flag.
    """
    summary = summarize_weak_form_supportability()
    policy = summary["policy"]
    assert isinstance(policy, dict)
    assert policy.get("supports_pysindy_weak_library_diagnostic") is True, (
        "the reporting policy dict must expose "
        "supports_pysindy_weak_library_diagnostic=True as a stable public "
        "flag for the v0.31b2 diagnostic surface; got "
        f"{policy.get('supports_pysindy_weak_library_diagnostic')!r}."
    )


def test_29_supports_weak_derivative_backend_still_scoped_to_weak_1d() -> None:
    """``supports_weak_derivative_backend`` remains False and still refers to weak_1d.

    The flag must NOT have been silently repurposed to cover the b2
    PySINDy diagnostic surface — the two flags are load-bearing distinct.
    """
    summary = summarize_weak_form_supportability()
    policy = summary["policy"]
    assert policy.get("supports_weak_derivative_backend") is False, (
        "supports_weak_derivative_backend must stay False in v0.31b2; the "
        "b2 wrapper does not promote the public weak-derivative-backend "
        "surface."
    )

    # The source-level comment must still name weak_1d so future readers
    # understand which surface the flag refers to.
    source = _inspect.getsource(summarize_weak_form_supportability)
    assert "weak_1d" in source, (
        "the summarize_weak_form_supportability implementation must retain "
        "an explicit reference to weak_1d so supports_weak_derivative_backend "
        "cannot be silently re-scoped."
    )
    # And the two flags must be documented as distinct.
    assert "supports_pysindy_weak_library_diagnostic" in source, (
        "supports_pysindy_weak_library_diagnostic must be declared alongside "
        "supports_weak_derivative_backend in the same policy dict."
    )


# --- v0.36e: three-state seed semantics -------------------------------------


def test_v0_38_the_seeded_report_keeps_the_v0_31b2_schema() -> None:
    """Replaces two v0.36e tests whose subject -- the omitted-seed path -- is gone.

    They asserted that omitting the seed still produced the 27-key schema and
    that legacy nondeterminism was retained. v0.38 makes the seed required, so
    neither has a subject any more. What still matters, and is checked here, is
    that requiring the seed did not disturb the frozen v0.31b2 shape.
    """
    import warnings as _warnings

    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=64, num_points=64, seed=3120
    )
    with _warnings.catch_warnings(record=True) as captured:
        _warnings.simplefilter("always")
        report = inspect_pysindy_weak_pde_library(
            field, task_name="v0_31b2_seeded", seed=13
        )

    assert len(set(report)) == 27
    assert not [item for item in captured if issubclass(item.category, FutureWarning)], (
        "the transition FutureWarning survives a change that has now happened"
    )

    provenance = report["provenance"]["seed_provenance"]
    assert provenance["seed"] == 13
    assert provenance["seed_was_omitted"] is False
    assert provenance["nondeterministic_requested"] is False
