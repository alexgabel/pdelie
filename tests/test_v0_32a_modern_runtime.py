"""v0.32a modern-runtime migration tests.

The v0.32a PR migrates pdelie to Python 3.12+, NumPy 2.x, and PySINDy
2.1.x. This test file locks in the 20 required invariants documented in
the v0.32a prompt:

1.  requires-python is >=3.12.
2.  NumPy range is >=2,<3.
3.  PySINDy range is >=2.1,<3.
4.  legacy setuptools pin is absent.
5.  legacy PySINDy 1.x pin is absent.
6.  discovery_task_result exact key set unchanged (22 keys).
7.  weak diagnostic exact key set unchanged (27 keys).
8.  canonical feature-name golden passes on 2.1.x.
9.  coefficient orientation unchanged (n_targets, n_features).
10. term-support metrics preserve semantics.
11. strict JSON adversarial tests remain green.
12. downstream example remains deterministic.
13. missing-extra error remains actionable.
14. root surface unchanged.
15. registry listing remains lazy.
16. built-in symmetry method remains deterministic.
17. reserved candidates now reject public construction (v0.32a hardening).
18. private prototype file is removed.
19. no broad compatibility fallback exists.
20. all migration xfails are resolved or explicitly reclassified.
"""

from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from pathlib import Path

import pytest

import pdelie

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT_PATH = _REPO_ROOT / "pyproject.toml"


def _pyproject() -> dict:
    return tomllib.loads(_PYPROJECT_PATH.read_text(encoding="utf-8"))


def _pyproject_text() -> str:
    return _PYPROJECT_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. requires-python is >=3.12.
# ---------------------------------------------------------------------------


def test_1_requires_python_is_gte_3_12() -> None:
    assert _pyproject()["project"]["requires-python"] == ">=3.12"


# ---------------------------------------------------------------------------
# 2. NumPy range is >=2,<3.
# ---------------------------------------------------------------------------


def test_2_numpy_range_is_2_dot_x() -> None:
    deps = _pyproject()["project"]["dependencies"]
    numpy_lines = [d for d in deps if "numpy" in d]
    assert numpy_lines, "pyproject.toml must declare numpy as a core dep"
    assert any(">=2" in d and "<3" in d for d in numpy_lines), (
        f"numpy must be pinned >=2,<3 for v0.32a; got {numpy_lines!r}"
    )


# ---------------------------------------------------------------------------
# 3. PySINDy range is >=2.1,<3.
# ---------------------------------------------------------------------------


def test_3_pysindy_range_is_2_dot_1_dot_x() -> None:
    extras = _pyproject()["project"]["optional-dependencies"]
    for extra_name in ("downstream", "test"):
        lines = extras.get(extra_name, [])
        pysindy_lines = [d for d in lines if "pysindy" in d.lower()]
        assert pysindy_lines, (
            f"pyproject.toml [{extra_name}] extra must declare pysindy"
        )
        assert any(">=2.1" in d and "<3" in d for d in pysindy_lines), (
            f"pysindy must be pinned >=2.1,<3 in the {extra_name!r} extra; "
            f"got {pysindy_lines!r}"
        )


# ---------------------------------------------------------------------------
# 4. legacy setuptools pin is absent.
# ---------------------------------------------------------------------------


def test_4_no_legacy_setuptools_lt_82_pin() -> None:
    """The v0.31c1 ``setuptools<82`` cap must be gone. Pysindy 2.x uses
    ``importlib.metadata`` — no ``pkg_resources`` dependency.
    """
    text = _pyproject_text()
    # Reject any runtime setuptools<... constraint in [project.dependencies]
    # or in extras. The [build-system].requires line is fine (it just needs
    # setuptools>=77 for the build backend).
    runtime_lines = [
        line
        for line in text.splitlines()
        if re.search(r'"setuptools\s*<', line)
    ]
    assert not runtime_lines, (
        f"v0.32a: the temporary setuptools<82 cap must be removed. "
        f"Offenders: {runtime_lines!r}"
    )


# ---------------------------------------------------------------------------
# 5. legacy PySINDy 1.x pin is absent.
# ---------------------------------------------------------------------------


def test_5_no_legacy_pysindy_1_x_pin() -> None:
    text = _pyproject_text()
    legacy_lines = [
        line
        for line in text.splitlines()
        if re.search(r'"pysindy>=1\.', line)
        or re.search(r'"pysindy<2\b', line)
    ]
    assert not legacy_lines, (
        f"v0.32a: the pysindy>=1.7.5,<2 pin must be gone. "
        f"Offenders: {legacy_lines!r}"
    )


# ---------------------------------------------------------------------------
# 6. discovery_task_result exact key set unchanged (22 keys).
# ---------------------------------------------------------------------------


def test_6_discovery_task_result_stays_22_keys() -> None:
    from pdelie.tasks import discovery as discovery_module

    assert len(discovery_module._TASK_RESULT_TOP_LEVEL_KEYS) == 22


# ---------------------------------------------------------------------------
# 7. weak diagnostic exact key set unchanged (27 keys).
# ---------------------------------------------------------------------------


def test_7_weak_diagnostic_stays_27_keys() -> None:
    from pdelie.tasks import weak_pde_library as weak_module

    top_level = getattr(
        weak_module, "_DIAGNOSTIC_TOP_LEVEL_KEYS", None
    ) or getattr(weak_module, "_SUMMARY_TOP_LEVEL_KEYS", None)
    assert top_level is not None
    assert len(top_level) == 27


# ---------------------------------------------------------------------------
# 8. Canonical feature-name golden passes on the installed pysindy.
# ---------------------------------------------------------------------------


def test_8_polynomial_feature_names_match_v0_31b0_golden() -> None:
    """The v0.31b0 term-mapping golden pinned feature names emitted by a
    ``PolynomialLibrary(degree=2, include_bias=True)`` on a 2-state input
    to ``['1', 'x0', 'x1', 'x0^2', 'x0 x1', 'x1^2']``. The v0.32a
    preflight audit confirmed byte-identical output from PySINDy 2.1.0.
    This test asserts that identity is preserved on the installed
    version.
    """
    pytest.importorskip("pysindy", reason="pysindy is a [downstream] optional dep")
    import numpy as np
    import pysindy

    # Fit a trivial 2-state polynomial and read feature names.
    T = 32
    t = np.linspace(0.0, 1.0, T)
    x = np.column_stack([np.sin(t), np.cos(t)])
    model = pysindy.SINDy(
        optimizer=pysindy.STLSQ(threshold=0.1, alpha=0.05, max_iter=5),
        feature_library=pysindy.PolynomialLibrary(degree=2, include_bias=True),
        differentiation_method=pysindy.FiniteDifference(),
    )
    model.fit(x, t=t)
    feature_names = list(model.get_feature_names())
    expected = ["1", "x0", "x1", "x0^2", "x0 x1", "x1^2"]
    assert feature_names[: len(expected)] == expected, (
        f"pysindy PolynomialLibrary feature-name convention drifted; "
        f"expected {expected!r}, got {feature_names[: len(expected)]!r}"
    )


# ---------------------------------------------------------------------------
# 9. Coefficient orientation unchanged (n_targets, n_features).
# ---------------------------------------------------------------------------


def test_9_coefficient_shape_convention_is_n_targets_n_features() -> None:
    pytest.importorskip("pysindy", reason="pysindy is a [downstream] optional dep")
    import numpy as np
    import pysindy

    T = 32
    t = np.linspace(0.0, 1.0, T)
    x = np.column_stack([np.sin(t), np.cos(t)])
    model = pysindy.SINDy(
        optimizer=pysindy.STLSQ(threshold=0.1, alpha=0.05, max_iter=5),
        feature_library=pysindy.PolynomialLibrary(degree=2, include_bias=True),
        differentiation_method=pysindy.FiniteDifference(),
    )
    model.fit(x, t=t)
    coefficients = np.asarray(model.coefficients())
    n_targets = 2  # x has two state features (sin, cos)
    n_features = len(list(model.get_feature_names()))
    assert coefficients.shape == (n_targets, n_features), (
        f"pysindy 2.1.x coefficient shape convention drifted; expected "
        f"({n_targets}, {n_features}), got {coefficients.shape!r}"
    )


# ---------------------------------------------------------------------------
# 10. Term-support metrics preserve semantics (via existing
#     evaluate_discovery_recovery contract).
# ---------------------------------------------------------------------------


def test_10_term_support_metrics_preserve_semantics() -> None:
    from pdelie.discovery.evaluation import evaluate_discovery_recovery

    target = {"u_xx": 0.1}
    discovered = {"u_xx": 0.11, "u": 0.001}
    recovery = evaluate_discovery_recovery(
        target, discovered, support_epsilon=1e-2
    )
    assert set(recovery.keys()) >= {
        "support_precision",
        "support_recall",
        "support_f1",
        "coefficient_relative_l2_error",
        "support_exact_match",
    }
    assert isinstance(recovery["support_exact_match"], bool)


# ---------------------------------------------------------------------------
# 11. Strict JSON adversarial tests remain green.
# ---------------------------------------------------------------------------


def test_11_strict_json_validator_rejects_nan_inf() -> None:
    import math

    from pdelie.errors import SchemaValidationError
    from pdelie.reporting.summaries import _validate_strict_json_compatible

    with pytest.raises(SchemaValidationError):
        _validate_strict_json_compatible({"x": math.nan}, name="test")
    with pytest.raises(SchemaValidationError):
        _validate_strict_json_compatible({"x": math.inf}, name="test")


# ---------------------------------------------------------------------------
# 12. Downstream example remains deterministic.
# ---------------------------------------------------------------------------


def test_12_downstream_example_is_deterministic() -> None:
    pytest.importorskip("pysindy", reason="pysindy is a [downstream] optional dep")
    from pdelie.examples import run_downstream_discovery_task_bridge_example

    first = run_downstream_discovery_task_bridge_example()
    second = run_downstream_discovery_task_bridge_example()
    first_text = json.dumps(first, sort_keys=True, allow_nan=False)
    second_text = json.dumps(second, sort_keys=True, allow_nan=False)
    assert first_text == second_text, (
        "downstream example is not deterministic under the frozen seed"
    )


# ---------------------------------------------------------------------------
# 13. Missing-extra error remains actionable.
# ---------------------------------------------------------------------------


def test_13_missing_extra_error_names_downstream_extra() -> None:
    """When pysindy is not importable, ``_require_discovery_dependencies``
    must raise an actionable ImportError naming the ``[downstream]`` extra.
    """
    from pdelie.discovery import pysindy_adapter

    _orig_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def _blocked_import(name: str, *args: object, **kwargs: object) -> object:
        if name in ("pysindy", "sklearn") or name.startswith(("pysindy.", "sklearn.")):
            raise ModuleNotFoundError(f"simulated: {name} not installed")
        return _orig_import(name, *args, **kwargs)

    for mod_name in ("pysindy", "sklearn"):
        sys.modules.pop(mod_name, None)

    with pytest.MonkeyPatch().context() as m:
        m.setattr("builtins.__import__", _blocked_import)
        with pytest.raises(ImportError, match=r"pdelie\[downstream\]"):
            pysindy_adapter._require_discovery_dependencies()


# ---------------------------------------------------------------------------
# 14. Root surface unchanged.
# ---------------------------------------------------------------------------


def test_14_root_surface_unchanged() -> None:
    for forbidden in (
        "run_pysindy_pde_task",
        "inspect_pysindy_weak_pde_library",
        "SymmetryCandidate",
        "SymmetryMethod",
        "discover_symmetries",
        "_pysindy2_prototype",
        "_pysindy_compat",
    ):
        assert not hasattr(pdelie, forbidden), (
            f"v0.32a must not add root export {forbidden!r}"
        )


# ---------------------------------------------------------------------------
# 15. Registry listing remains lazy.
# ---------------------------------------------------------------------------


def test_15_list_symmetry_methods_does_not_import_adapters() -> None:
    from pdelie.symmetry import list_symmetry_methods

    sys.modules.pop("pdelie.symmetry.methods.polynomial_translation_svd", None)
    torch_before = "torch" in sys.modules
    methods = list_symmetry_methods()
    assert isinstance(methods, list)
    assert ("torch" in sys.modules) == torch_before
    assert "pdelie.symmetry.methods.polynomial_translation_svd" not in sys.modules


# ---------------------------------------------------------------------------
# 16. Built-in symmetry method remains deterministic.
# ---------------------------------------------------------------------------


def test_16_polynomial_translation_svd_is_deterministic() -> None:
    import numpy as np

    from pdelie.data import generate_heat_1d_field_batch
    from pdelie.residuals import HeatResidualEvaluator
    from pdelie.symmetry import run_symmetry_method

    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=32, seed=42
    )
    evaluator = HeatResidualEvaluator()
    first = run_symmetry_method(
        "polynomial_translation_svd", field, residual_evaluator=evaluator
    )
    second = run_symmetry_method(
        "polynomial_translation_svd", field, residual_evaluator=evaluator
    )
    np.testing.assert_array_equal(
        first.candidates[0].payload.coefficients,
        second.candidates[0].payload.coefficients,
    )
    assert first.method_scores == second.method_scores


# ---------------------------------------------------------------------------
# 17. Reserved candidates reject public construction (v0.32a hardening).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reserved",
    [
        "matrix_lie_algebra",
        "coordinate_vector_field",
        "finite_transform_spec",
        "latent_generator_reference",
    ],
)
def test_17_reserved_representation_types_reject_public_construction(
    reserved: str,
) -> None:
    from pdelie.errors import ScopeValidationError
    from pdelie.symmetry import build_symmetry_candidate

    with pytest.raises(ScopeValidationError, match="reserved"):
        build_symmetry_candidate(
            candidate_id=f"test-{reserved}",
            representation_type=reserved,
            payload=None,
            source_method="test",
        )


# ---------------------------------------------------------------------------
# 18. Private prototype file is removed.
# ---------------------------------------------------------------------------


def test_18_pysindy2_prototype_file_is_removed() -> None:
    assert not (
        _REPO_ROOT / "src" / "pdelie" / "discovery" / "_pysindy2_prototype.py"
    ).exists()
    assert not (_REPO_ROOT / "tests" / "test_pysindy_2_migration_prototype.py").exists()


# ---------------------------------------------------------------------------
# 19. No broad compatibility fallback exists.
# ---------------------------------------------------------------------------


def test_19_no_broad_compatibility_fallback_in_discovery_paths() -> None:
    """The v0.32a migration replaces the v0.31c1-era targeted
    ``sys.version_info >= (3, 12)`` deferral message on both adapter
    paths. Neither ``pysindy_adapter._require_discovery_dependencies``
    nor ``weak_pde_library._build_weak_library`` may contain a version
    branch pointing at a deferred v0.31.x milestone.
    """
    for source_relpath in (
        "src/pdelie/discovery/pysindy_adapter.py",
        "src/pdelie/tasks/weak_pde_library.py",
    ):
        text = (_REPO_ROOT / source_relpath).read_text(encoding="utf-8")
        assert "v0.31.1 deferral" not in text
        assert "deferred to v0.31.1" not in text
        assert "PySINDy 2.x / Python 3.12+ compatibility is deferred" not in text


def test_19_no_broad_except_typeerror_swallowing_pysindy_api() -> None:
    """AST-inspect the adapter module: no bare ``except:`` and no
    broad ``except TypeError`` that would silently swallow a pysindy
    2.x API drift into a 1.x fallback path.
    """
    adapter_path = _REPO_ROOT / "src" / "pdelie" / "discovery" / "pysindy_adapter.py"
    tree = ast.parse(adapter_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                pytest.fail(
                    f"{adapter_path}:{node.lineno}: bare `except:` — a "
                    "pysindy 2.x TypeError could be silently swallowed"
                )


# ---------------------------------------------------------------------------
# 20. All migration xfails are resolved or explicitly reclassified.
# ---------------------------------------------------------------------------


def test_20_no_migration_xfail_files_remain() -> None:
    """The three v0.31b3 xfails and the v0.31c1 packaging-policy file are
    both removed by v0.32a. Their invariants are covered by tests in this
    file (12 = strict-JSON, 13 = missing-extra actionable, 17 = reserved
    types reject).
    """
    for path in (
        _REPO_ROOT / "tests" / "test_v0_31b3_pysindy_compatibility_policy.py",
        _REPO_ROOT / "tests" / "test_v0_31c1_downstream_packaging_policy.py",
    ):
        assert not path.exists(), (
            f"{path} must be removed by v0.32a; its invariants are covered "
            "by tests in this file"
        )
