"""v0.31c downstream-task-bridge example — public-surface, schema, and
claim-boundary tests.

The example composes v0.31b1's ``run_pysindy_pde_task`` and v0.31b2's
``inspect_pysindy_weak_pde_library`` into a single JSON-only demonstration
runner. This module verifies:

- the runner is importable from ``pdelie.examples`` (submodule-only surface);
- the composed payload is strict-JSON safe and matches the frozen shape;
- neither underlying schema drifted (22-key discovery_task_result;
  27-key pdelie_weak_pde_library_diagnostic; diagnostic_only=True);
- backend versions are recorded verbatim from the installed distributions;
- the interpretation prose carries no WSINDy / noise-robustness claim;
- the example uses no private / internal PDELie module;
- the example is deterministic under the frozen seed and configuration;
- the CLI (``python -m pdelie.examples.downstream_discovery_task_bridge``)
  emits parseable JSON on stdout only.

The clean-wheel install path (test 13) and the missing-extra ImportError
path (test 14) are covered adversarially at the module-attribute level; the
end-to-end wheel smoke is exercised in the v0.31c release-close workflow.
"""

from __future__ import annotations

import ast
import importlib
import importlib.metadata as _importlib_metadata
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import pdelie

pysindy = pytest.importorskip(
    "pysindy",
    reason=(
        "pysindy is required by pdelie.examples.downstream_discovery_task_bridge; "
        "v0.31c tests are skipped when the [downstream] extra is not installed."
    ),
)


_REPO_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = "pdelie.examples.downstream_discovery_task_bridge"
_RUNNER_NAME = "run_downstream_discovery_task_bridge_example"

_EXPECTED_TOP_LEVEL_KEYS = {
    "backend_versions",
    "interpretation",
    "pde_library_task",
    "scope_boundaries",
    "summary_schema_version",
    "summary_type",
    "weak_pde_library_diagnostic",
}

_DISCOVERY_TASK_RESULT_KEY_COUNT = 22
_WEAK_DIAGNOSTIC_KEY_COUNT = 27

_FORBIDDEN_CLAIM_SUBSTRINGS = (
    "wsindy benchmark",
    "noise robustness",
    "robust to noise",
    "validated weak recovery",
)


# ---------------------------------------------------------------------------
# Shared: one live invocation (module scope) reused by most tests.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def example_payload() -> dict[str, Any]:
    from pdelie.examples import run_downstream_discovery_task_bridge_example

    return run_downstream_discovery_task_bridge_example()


# ---------------------------------------------------------------------------
# 1. Example runner is importable from pdelie.examples.
# ---------------------------------------------------------------------------


def test_v0_31c_example_runner_is_importable_from_pdelie_examples() -> None:
    module = importlib.import_module("pdelie.examples")
    assert hasattr(module, _RUNNER_NAME)
    assert _RUNNER_NAME in module.__all__
    submodule = importlib.import_module(_MODULE_PATH)
    assert hasattr(submodule, _RUNNER_NAME)


# ---------------------------------------------------------------------------
# 2. Root pdelie does not export the example runner.
# ---------------------------------------------------------------------------


def test_v0_31c_root_pdelie_does_not_export_example_runner() -> None:
    assert not hasattr(pdelie, _RUNNER_NAME)
    assert not hasattr(pdelie, "downstream_discovery_task_bridge")


# ---------------------------------------------------------------------------
# 3. CLI emits JSON only.
# ---------------------------------------------------------------------------


def test_v0_31c_cli_emits_json_only() -> None:
    result = subprocess.run(
        [sys.executable, "-m", _MODULE_PATH],
        capture_output=True,
        text=True,
        check=False,
        cwd=_REPO_ROOT,
    )
    assert result.returncode == 0, (
        f"CLI exit={result.returncode}; stderr tail:\n{result.stderr[-2000:]}"
    )
    payload = json.loads(result.stdout)
    assert payload["summary_type"] == "downstream_discovery_task_bridge_example"


# ---------------------------------------------------------------------------
# 4. summary_type is exact.
# ---------------------------------------------------------------------------


def test_v0_31c_summary_type_is_exact(example_payload: dict[str, Any]) -> None:
    assert example_payload["summary_type"] == "downstream_discovery_task_bridge_example"
    assert set(example_payload.keys()) == _EXPECTED_TOP_LEVEL_KEYS


def test_v0_31c_summary_schema_version_is_exact(example_payload: dict[str, Any]) -> None:
    assert example_payload["summary_schema_version"] == "0.1"


# ---------------------------------------------------------------------------
# 5. PDELibrary child has summary_type = "discovery_task_result".
# ---------------------------------------------------------------------------


def test_v0_31c_pde_library_child_is_discovery_task_result(
    example_payload: dict[str, Any],
) -> None:
    pde_task = example_payload["pde_library_task"]
    assert pde_task["summary_type"] == "discovery_task_result"
    assert len(pde_task) == _DISCOVERY_TASK_RESULT_KEY_COUNT, (
        f"discovery_task_result 22-key schema drifted; got {len(pde_task)} keys"
    )


# ---------------------------------------------------------------------------
# 6. Weak child has summary_type = "pdelie_weak_pde_library_diagnostic".
# ---------------------------------------------------------------------------


def test_v0_31c_weak_child_is_weak_pde_library_diagnostic(
    example_payload: dict[str, Any],
) -> None:
    weak = example_payload["weak_pde_library_diagnostic"]
    assert weak["summary_type"] == "pdelie_weak_pde_library_diagnostic"
    assert len(weak) == _WEAK_DIAGNOSTIC_KEY_COUNT, (
        f"pdelie_weak_pde_library_diagnostic 27-key schema drifted; "
        f"got {len(weak)} keys"
    )


# ---------------------------------------------------------------------------
# 7. Weak child diagnostic_only is true.
# ---------------------------------------------------------------------------


def test_v0_31c_weak_child_diagnostic_only_is_true(
    example_payload: dict[str, Any],
) -> None:
    assert example_payload["weak_pde_library_diagnostic"]["diagnostic_only"] is True


# ---------------------------------------------------------------------------
# 8. Entire output passes json.dumps(..., allow_nan=False).
# ---------------------------------------------------------------------------


def test_v0_31c_full_payload_is_strict_json(example_payload: dict[str, Any]) -> None:
    payload_text = json.dumps(example_payload, allow_nan=False)
    roundtrip = json.loads(payload_text)
    assert roundtrip == example_payload


# ---------------------------------------------------------------------------
# 9. Example records exact backend versions.
# ---------------------------------------------------------------------------


def test_v0_31c_backend_versions_are_exact(example_payload: dict[str, Any]) -> None:
    backend_versions = example_payload["backend_versions"]
    installed_pysindy = _importlib_metadata.version("pysindy")
    installed_pdelie = _importlib_metadata.version("pdelie")
    installed_sklearn = _importlib_metadata.version("scikit-learn")
    installed_scipy = _importlib_metadata.version("scipy")
    installed_numpy = _importlib_metadata.version("numpy")
    assert backend_versions["pysindy"] == installed_pysindy
    assert backend_versions["pdelie"] == installed_pdelie
    assert backend_versions["sklearn"] == installed_sklearn
    assert backend_versions["scipy"] == installed_scipy
    assert backend_versions["numpy"] == installed_numpy


# ---------------------------------------------------------------------------
# 10. Scope-boundary language contains no WSINDy/noise robustness claim.
# ---------------------------------------------------------------------------


def test_v0_31c_no_wsindy_or_noise_robustness_claim(
    example_payload: dict[str, Any],
) -> None:
    text = json.dumps(example_payload).lower()
    for forbidden in _FORBIDDEN_CLAIM_SUBSTRINGS:
        # The interpretation prose IS allowed to state that these claims are
        # NOT made; e.g. "does not establish WSINDy performance". So we look
        # for the forbidden phrase without the negation guardrail.
        if forbidden in text:
            # Verify each occurrence sits under a negation.
            for line in text.split("\n"):
                if forbidden in line:
                    assert (
                        "does not" in line
                        or "not " in line
                        or "no " in line
                        or forbidden.replace(" ", "_") not in line
                    ), (
                        f"forbidden phrase {forbidden!r} appears without a "
                        f"negation guardrail in line:\n{line}"
                    )

    scope_boundaries = example_payload["scope_boundaries"]
    assert scope_boundaries["wsindy_benchmark_claimed"] is False
    assert scope_boundaries["noise_robustness_claimed"] is False
    assert scope_boundaries["nonperiodic_discovery_claimed"] is False


# ---------------------------------------------------------------------------
# 11. Example uses no private/internal PDELie module.
# ---------------------------------------------------------------------------


def test_v0_31c_example_imports_only_public_pdelie_submodules() -> None:
    module_path = (
        _REPO_ROOT
        / "src"
        / "pdelie"
        / "examples"
        / "downstream_discovery_task_bridge.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if not module.startswith("pdelie"):
                continue
            parts = module.split(".")
            for part in parts[1:]:  # skip "pdelie"
                assert not part.startswith("_"), (
                    f"example imports from a private pdelie submodule: {module!r}"
                )
            for alias in node.names:
                assert not alias.name.startswith("_"), (
                    f"example imports a private symbol: {module}.{alias.name}"
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("pdelie"):
                    parts = alias.name.split(".")
                    for part in parts[1:]:
                        assert not part.startswith("_"), (
                            f"example imports a private pdelie submodule: "
                            f"{alias.name!r}"
                        )


# ---------------------------------------------------------------------------
# 12. Example is deterministic under the frozen seed/config.
# ---------------------------------------------------------------------------


def test_v0_31c_example_is_deterministic_under_frozen_seed() -> None:
    from pdelie.examples import run_downstream_discovery_task_bridge_example

    first = run_downstream_discovery_task_bridge_example()
    second = run_downstream_discovery_task_bridge_example()

    # Ephemeral fields (timing, random provenance ids) MUST NOT exist —
    # both runs should compare equal under strict JSON.
    first_text = json.dumps(first, sort_keys=True, allow_nan=False)
    second_text = json.dumps(second, sort_keys=True, allow_nan=False)
    assert first_text == second_text, (
        "example is not deterministic; runs differ under the frozen seed"
    )


# ---------------------------------------------------------------------------
# 13. Clean-wheel installed example executes successfully.
# ---------------------------------------------------------------------------


def test_v0_31c_example_smoke_from_current_environment(
    example_payload: dict[str, Any],
) -> None:
    """Substitutes for a full-wheel smoke by validating the same invariants a
    fresh-venv smoke would check: import, execute, strict-JSON, exact
    summary_type. The full clean-wheel smoke is exercised by the v0.31b3
    wheel-smoke gate and the v0.31c release-close manual smoke.
    """
    assert example_payload["summary_type"] == "downstream_discovery_task_bridge_example"
    assert example_payload["pde_library_task"]["summary_type"] == "discovery_task_result"
    assert (
        example_payload["weak_pde_library_diagnostic"]["summary_type"]
        == "pdelie_weak_pde_library_diagnostic"
    )
    json.dumps(example_payload, allow_nan=False)


# ---------------------------------------------------------------------------
# 14. Core-only environment without downstream extra raises the documented
# actionable ImportError.
# ---------------------------------------------------------------------------


def test_v0_31c_missing_pysindy_raises_actionable_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulate a core-only install by making the runtime pysindy import fail.

    ``_build_caller_configured_sindy`` performs a lazy ``import pysindy`` and
    is expected to re-raise with a message that names the ``[downstream]``
    extra and the reinstall command.
    """
    from pdelie.examples import downstream_discovery_task_bridge as module_under_test

    # Force the local `import pysindy` in _build_caller_configured_sindy to
    # fail even though pysindy is installed in this test environment.
    original_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def _blocked_import(
        name: str,
        globals_: Any = None,
        locals_: Any = None,
        fromlist: Any = (),
        level: int = 0,
    ) -> Any:
        if name == "pysindy" or name.startswith("pysindy."):
            raise ImportError("simulated: pysindy not installed")
        return original_import(name, globals_, locals_, fromlist, level)

    monkeypatch.setattr("builtins.__import__", _blocked_import)

    with pytest.raises(ImportError, match=r"pdelie\[downstream\]"):
        module_under_test._build_caller_configured_sindy()
