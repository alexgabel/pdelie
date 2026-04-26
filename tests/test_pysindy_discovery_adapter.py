from __future__ import annotations

import importlib

import numpy as np
import pytest

from pdelie import SchemaValidationError, ScopeValidationError
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.discovery import fit_pysindy_discovery, to_pysindy_trajectories


def _adapter_module():
    return importlib.import_module("pdelie.discovery.pysindy_adapter")


def _small_bridge_from_field(field):
    trajectories, time_values, feature_names = to_pysindy_trajectories(field)
    return trajectories, time_values, feature_names


@pytest.mark.parametrize(
    ("field_factory", "seed"),
    (
        (generate_heat_1d_field_batch, 901),
        (generate_burgers_1d_field_batch, 902),
    ),
)
def test_fit_pysindy_discovery_succeeds_on_tiny_representative_bridge(field_factory, seed: int) -> None:
    try:
        _adapter_module()._require_discovery_dependencies()
    except ImportError as exc:
        pytest.skip(str(exc))

    field = field_factory(batch_size=2, num_times=9, num_points=4, seed=seed)
    trajectories, time_values, feature_names = _small_bridge_from_field(field)

    result = fit_pysindy_discovery(trajectories, time_values, feature_names)

    assert result["status"] == "success"
    assert result["backend"] == "pysindy"
    assert result["feature_names"] == feature_names
    assert result["fit_config"]["coefficient_threshold"] == pytest.approx(1e-8)
    assert result["fit_diagnostics"]["terms_are_backend_native"] is True
    assert result["fit_diagnostics"]["canonicalized"] is False
    assert result["fit_diagnostics"]["num_trajectories"] == len(trajectories)
    assert result["fit_diagnostics"]["num_times"] == len(time_values)

    coefficients = result["coefficients"]
    library_feature_names = result["library_feature_names"]
    assert isinstance(library_feature_names, list)
    assert coefficients.shape == (len(feature_names), len(library_feature_names))
    assert np.all(np.isfinite(coefficients))

    assert set(result["equation_terms"]) == set(feature_names)
    assert set(result["equation_strings"]) == set(feature_names)
    for name in feature_names:
        assert isinstance(result["equation_terms"][name], dict)
        assert isinstance(result["equation_strings"][name], str)


def test_fit_pysindy_discovery_freezes_row_orientation_for_extraction() -> None:
    adapter_module = _adapter_module()

    equation_terms, equation_strings, nonzero_term_counts = adapter_module._extract_backend_terms(
        np.asarray([[0.0, 1.0, 0.0], [2.0, 0.0, -3.0]], dtype=float),
        feature_names=["lhs0", "lhs1"],
        library_feature_names=["1", "a", "b"],
        coefficient_threshold=1e-8,
    )

    assert equation_terms == {
        "lhs0": {"a": 1.0},
        "lhs1": {"1": 2.0, "b": -3.0},
    }
    assert equation_strings == {
        "lhs0": "1*a",
        "lhs1": "2*1 - 3*b",
    }
    assert nonzero_term_counts == {"lhs0": 1, "lhs1": 2}


def test_fit_pysindy_discovery_real_backend_orientation_is_rows_by_feature() -> None:
    try:
        _adapter_module()._require_discovery_dependencies()
    except ImportError as exc:
        pytest.skip(str(exc))

    time_values = np.linspace(0.0, 0.9, 10)
    trajectories = [np.column_stack((time_values, 2.0 * time_values))]
    feature_names = ["a", "b"]

    result = fit_pysindy_discovery(trajectories, time_values, feature_names)

    assert result["status"] == "success"
    assert result["coefficients"].shape[0] == 2
    assert list(result["equation_terms"]) == ["a", "b"]
    assert result["fit_diagnostics"]["num_state_features"] == 2


def test_fit_pysindy_discovery_rejects_non_none_config() -> None:
    with pytest.raises(ScopeValidationError, match="only supports config=None"):
        fit_pysindy_discovery(
            [np.ones((4, 2), dtype=float)],
            np.linspace(0.0, 0.3, 4),
            ["a", "b"],
            config={},
        )


@pytest.mark.parametrize(
    ("trajectories", "match"),
    (
        ([], "non-empty list or tuple"),
        ([np.ones(4, dtype=float)], "each trajectory must be a 2D finite numeric array"),
        ([np.ones((4, 2), dtype=float), np.ones((5, 2), dtype=float)], "must share identical shape"),
        ([np.array([[1.0, np.nan]])], "must contain only finite values"),
    ),
)
def test_fit_pysindy_discovery_rejects_invalid_trajectories(trajectories, match: str) -> None:
    with pytest.raises(SchemaValidationError, match=match):
        fit_pysindy_discovery(trajectories, np.linspace(0.0, 0.3, 4), ["a", "b"])


@pytest.mark.parametrize(
    ("time_values", "match"),
    (
        (np.ones((4, 1), dtype=float), "one-dimensional"),
        (np.array([0.0, 0.1]), "at least 3 entries"),
        (np.array([0.0, 0.2, 0.1, 0.3]), "strictly increasing"),
        (np.array([0.0, 0.1, np.nan, 0.3]), "contain only finite values"),
        (np.linspace(0.0, 0.2, 3), "length must match"),
    ),
)
def test_fit_pysindy_discovery_rejects_invalid_time_values(time_values, match: str) -> None:
    with pytest.raises(SchemaValidationError, match=match):
        fit_pysindy_discovery([np.ones((4, 2), dtype=float)], time_values, ["a", "b"])


@pytest.mark.parametrize(
    ("feature_names", "match"),
    (
        ("ab", "sequence of unique non-empty strings"),
        (["a"], "length must match"),
        (["a", ""], "non-empty strings"),
        (["a", "a"], "must be unique"),
    ),
)
def test_fit_pysindy_discovery_rejects_invalid_feature_names(feature_names, match: str) -> None:
    with pytest.raises(SchemaValidationError, match=match):
        fit_pysindy_discovery([np.ones((4, 2), dtype=float)], np.linspace(0.0, 0.3, 4), feature_names)


def test_fit_pysindy_discovery_raises_clear_import_error_when_dependency_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter_module = _adapter_module()
    real_import_module = importlib.import_module

    def _fake_import_module(name: str, package: str | None = None):
        if name == "pysindy":
            raise ModuleNotFoundError("No module named 'pysindy'")
        return real_import_module(name, package)

    monkeypatch.setattr(adapter_module.importlib, "import_module", _fake_import_module)

    with pytest.raises(ImportError, match=r"pdelie\[downstream\] or pdelie\[test\]"):
        fit_pysindy_discovery(
            [np.ones((4, 2), dtype=float)],
            np.linspace(0.0, 0.3, 4),
            ["a", "b"],
        )


def test_fit_pysindy_discovery_converts_backend_fit_exception_to_failed_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter_module = _adapter_module()

    class _FailingModel:
        def fit(self, *args, **kwargs):
            raise RuntimeError("synthetic backend failure")

    try:
        adapter_module._require_discovery_dependencies()
    except ImportError as exc:
        pytest.skip(str(exc))

    monkeypatch.setattr(adapter_module, "_build_pysindy_model", lambda *args, **kwargs: _FailingModel())

    result = fit_pysindy_discovery(
        [np.ones((4, 2), dtype=float)],
        np.linspace(0.0, 0.3, 4),
        ["a", "b"],
    )

    assert result["status"] == "failed"
    assert result["backend"] == "pysindy"
    assert result["feature_names"] == ["a", "b"]
    assert result["library_feature_names"] == []
    assert result["coefficients"] is None
    assert result["equation_terms"] == {}
    assert result["equation_strings"] == {}
    assert result["failure_reason"] == "backend_fit_failed"
    assert result["fit_diagnostics"]["exception_type"] == "RuntimeError"
    assert "synthetic backend failure" in result["fit_diagnostics"]["exception_message"]
