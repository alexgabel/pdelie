"""The release gate's own contract, asserted.

The documented release procedure had **never completed end to end**. Three of
its seven links failed on this repository, and each was found only by executing
it:

* ``mypy`` always exits 1 against the ratcheted baseline, so a gate keyed on its
  exit status is permanently red — and a permanently-red gate gets disabled.
* ``pip install --force-reinstall`` clobbers the editable install, so the next
  local test run silently measures the wheel instead of the tree.
* ``pdelie.__version__`` does not exist, so the chain's final command raises.

These tests keep each repair in place.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/release_gate_local.sh"


def _packaged_version() -> str:
    return tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]["version"]


def test_the_gate_script_exists_and_is_executable() -> None:
    assert SCRIPT.exists()
    import os

    assert os.access(SCRIPT, os.X_OK), "release_gate_local.sh is not executable"


def test_the_root_namespace_still_has_no_version_attribute() -> None:
    """Preserved deliberately.

    Adding ``pdelie.__version__`` would have made the documented chain work, and
    would have widened the root surface the v0.38 API freeze locks in order to
    satisfy a check. The gate reads installed metadata instead.
    """
    import pdelie

    assert not hasattr(pdelie, "__version__")
    assert "__version__" not in pdelie.__all__


def test_the_installed_distribution_reports_the_packaged_version() -> None:
    """``importlib.metadata`` is the canonical source, and it agrees."""
    import importlib.metadata

    assert importlib.metadata.version("pdelie") == _packaged_version()


def test_the_gate_checks_the_wheel_version_against_pyproject() -> None:
    """Not merely that the wheel imports."""
    text = SCRIPT.read_text()
    assert "importlib.metadata" in text
    assert "pyproject" in text.lower()
    assert "MISMATCH" in text, (
        "the install gate does not compare the wheel's version against "
        "pyproject; it would pass on a wheel carrying the wrong version"
    )


def test_the_gate_does_not_key_mypy_on_its_exit_status() -> None:
    """A permanently-red gate gets disabled, which is worse than no gate."""
    text = SCRIPT.read_text()
    assert "MYPY_BASELINE_ERRORS" in text
    assert "RATCHET BROKEN" in text


def test_the_mypy_baseline_matches_the_repository_fingerprint() -> None:
    """The script's baseline and the real fingerprint must not drift apart."""
    text = SCRIPT.read_text()
    errors = int(re.search(r"MYPY_BASELINE_ERRORS=(\d+)", text).group(1))
    files = int(re.search(r"MYPY_BASELINE_FILES=(\d+)", text).group(1))
    assert (errors, files) == (147, 29), (
        f"the script's baseline is {errors}/{files}. If the ratchet genuinely "
        f"improved, lower it here and in this assertion together."
    )


def test_the_gate_does_not_force_reinstall_into_the_working_environment() -> None:
    """That would replace the editable install and silently change what the
    next local test run measures."""
    # Executable lines only. The script *names* --force-reinstall in the
    # comment explaining why it is not used, and a check that cannot tell a
    # command from an explanation of why that command is wrong is the
    # disclaim-versus-claim defect this repository has caught seven times.
    executable = [
        line for line in SCRIPT.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    offending = [line.strip() for line in executable if "--force-reinstall" in line]
    assert not offending, f"the gate force-reinstalls: {offending}"
    assert any("venv" in line for line in executable), (
        "the wheel must be installed into a throwaway venv"
    )


def test_a_skipped_build_cannot_report_release_readiness() -> None:
    """``--skip-build`` must not produce a bare success.

    Otherwise the fast path becomes the habitual one and the release ritual
    silently stops exercising the artifact it ships.
    """
    text = SCRIPT.read_text()
    assert "PASSED WITH SKIPS" in text
    assert "not sufficient for a release tag" in text


def test_no_test_executes_the_gate_script() -> None:
    """Replaces a test that ran the gate script -- which runs this suite.

    That test recursed without bound: pytest -> gate -> pytest -> gate, seven
    levels deep before it was killed, each level loading numpy/scipy/pysindy.
    It exhausted system swap.

    The mistake was wanting to assert "the gate actually passes" from inside the
    thing the gate runs. That claim cannot be made here. It belongs in the
    release checklist, executed before tagging.
    """
    import ast
    from pathlib import Path

    offenders: list[str] = []
    for path in sorted(Path(__file__).resolve().parent.rglob("test_*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, "attr", None) or getattr(func, "id", None)
            if name not in {"run", "check_call", "check_output", "Popen", "call"}:
                continue
            # Any literal or Name mentioning the script inside a process-spawning
            # call is the pattern that recursed.
            for arg in ast.walk(node):
                mentions = (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and "release_gate_local" in arg.value
                ) or (isinstance(arg, ast.Name) and arg.id == "SCRIPT")
                if mentions:
                    offenders.append(f"{path.name}:{node.lineno}")
                    break

    assert not offenders, (
        f"{offenders} spawn release_gate_local.sh from inside the test suite. "
        f"The script runs this suite, so that recurses without bound."
    )


def test_the_script_guards_against_re_entry() -> None:
    """The structural fix, so the failure mode is impossible not merely absent."""
    text = SCRIPT.read_text()
    assert "PDELIE_RELEASE_GATE_RUNNING" in text
    assert "Refusing to re-enter" in text


# --------------------------------------------------------------------------
# The Gate F scope contract
# --------------------------------------------------------------------------

SCOPE = REPO_ROOT / "configs/gate_f_replay_scope.json"


def _scope() -> dict:
    import json

    return json.loads(SCOPE.read_text())


def test_both_replay_scripts_read_the_scope_artifact() -> None:
    """Neither may keep its own list.

    The harness sweeping derivative order 4 on its own authority is what stopped
    Gate F closing on run 31278210299.
    """
    for name in ("replay_workloads.py", "compare_replay.py"):
        text = (REPO_ROOT / "scripts" / name).read_text()
        assert "gate_f_replay_scope.json" in text, f"{name} does not read the scope"


def test_the_gate_population_excludes_the_exploratory_orders() -> None:
    scope = _scope()
    assert scope["supported_derivative_orders"] == [1, 2, 3]
    assert scope["exploratory_derivative_orders"] == [4]
    assert not set(scope["supported_derivative_orders"]) & set(
        scope["exploratory_derivative_orders"]
    )


def test_exploratory_rows_are_emitted_but_barred_from_the_gate() -> None:
    """Retained as evidence; labelled so they cannot be read as gate evidence."""
    policy = _scope()["exploratory_policy"]
    assert policy["emitted"] is True
    assert policy["gate_use"] == "not_used_for_gate_decision"
    assert policy["label"] == "outside_frozen_scope"


def test_the_tolerances_are_frozen_and_derived() -> None:
    tolerances = _scope()["tolerances"]
    assert tolerances["cross_platform_scaled_difference"] == 1e-8
    assert tolerances["patch_drift_scaled_difference"] == 0.0, (
        "patch drift must require bitwise identity: same platform, same libm, "
        "same BLAS, and a CPython patch changes no floating-point semantics, so "
        "any nonzero tolerance would accept a real regression"
    )
    for key in ("cross_platform_derivation", "patch_drift_derivation"):
        assert tolerances[key], f"{key} is empty; a bound with no derivation is a guess"


def test_no_runner_uses_a_floating_python_alias() -> None:
    """A floating alias silently changes what a confirmatory gate measured."""
    for runner in _scope()["runners"]:
        assert re.fullmatch(r"\d+\.\d+\.\d+", runner["python"]), (
            f"{runner['os']} pins {runner['python']!r}, which is not an exact patch"
        )


def test_the_impossible_runner_cell_is_recorded() -> None:
    """So nobody re-specifies the 2x2 without learning why it was dropped."""
    constraint = _scope()["runner_constraint"]
    assert "3.12.11" in constraint and "macOS" in constraint


def test_the_release_checklist_states_the_gate_runs_externally() -> None:
    """The claim removed from pytest must live somewhere that is actually read.

    ``test_the_gate_actually_passes_on_this_tree`` was deleted because it ran
    the gate script, which runs this suite, which ran that test -- seven levels
    of recursion before it exhausted system swap.

    Deleting it left a real gap: nothing asserted the gate passes. That claim
    cannot be made from inside the thing the gate runs, so it belongs in the
    release procedure, executed before tagging. This test checks the procedure
    still says so, rather than the gap quietly closing over.
    """
    text = (REPO_ROOT / "docs/design/RELEASE_ENFORCEMENT.md").read_text()
    assert "release_gate_local.sh" in text, (
        "the release procedure does not name the gate script"
    )
    lowered = text.lower()
    assert "never from pytest" in lowered or "not from pytest" in lowered, (
        "the release procedure must state that the gate is run externally, "
        "never from inside the test suite -- otherwise the recursion that "
        "exhausted system swap gets reintroduced by someone restoring the "
        "'assert the gate passes' test in good faith"
    )


def test_the_replay_lane_audits_its_population_before_upload() -> None:
    """F-11, checked at the point of production.

    A malformed population must fail on the runner that made it, not be
    discovered during comparison -- by which point the artifact exists, looks
    complete, and invites being compared anyway.
    """
    workflow = (REPO_ROOT / ".github/workflows/benchmark_platform_replay.yml").read_text()
    assert "audit_replay_population.py" in workflow
    audit_at = workflow.index("audit_replay_population.py")
    upload_at = workflow.index("Upload measurements")
    assert audit_at < upload_at, (
        "the independent audit must run before the artifact is uploaded"
    )


def test_the_gate_checks_its_interpreter_before_running_any_subgate() -> None:
    """An environment fault must not present as three code faults.

    Running the gate where bare ``python`` is 3.11 reported ruff PASS and
    mypy/pytest/install FAIL. Nothing was wrong with the code; the package
    requires >=3.12.

    The wasted run is not the harm. The harm is that a gate failing for
    environment reasons teaches the operator to re-run it under a different
    environment until it goes green -- a selection effect operating on the
    release control itself.
    """
    text = SCRIPT.read_text()
    assert "requires-python" in text, (
        "the gate does not check its interpreter against pyproject"
    )
    assert "NOTHING WAS MEASURED" in text, (
        "the abort message must say no sub-gate ran, or its output reads like "
        "a partial result"
    )
    assert "exit 3" in text, "the interpreter abort needs its own exit code"

    # Ordering is the load-bearing part: the check must precede the first gate.
    check_at = text.index("requires-python")
    first_gate_at = text.index('run_gate "ruff (lint)"')
    assert check_at < first_gate_at, (
        "the interpreter check runs after a sub-gate, so a wrong interpreter "
        "still produces sub-gate output"
    )


def test_the_interpreter_abort_uses_a_distinct_exit_code() -> None:
    """2 is re-entry, 3 is a bad interpreter, 1 is a genuine gate failure.

    Collapsing them would make "the gate failed" ambiguous in exactly the
    situation where the distinction matters most.
    """
    text = SCRIPT.read_text()
    assert "exit 2" in text and "exit 3" in text
    assert text.index("exit 2") < text.index("exit 3"), (
        "re-entry is checked before the interpreter, so the codes should appear "
        "in that order; if this flipped, verify both paths still work"
    )


def test_the_external_smoke_refuses_to_measure_the_working_tree() -> None:
    """The one property that makes it a smoke test rather than a second suite.

    Run against the checkout it would pass on a wheel missing half its modules,
    because the source tree is importable and every dev dependency is present.
    That is the environment a release must not be trusted in.
    """
    script = REPO_ROOT / "scripts/external_smoke.py"
    assert script.exists()
    text = script.read_text()
    assert "REFUSING TO RUN" in text
    assert "pyproject.toml" in text, (
        "the checkout detection must key on something the installed "
        "distribution does not have"
    )


def test_the_external_smoke_is_not_collected_by_pytest() -> None:
    """It requires an installed distribution, so as a test it would fail or --
    worse -- pass against the working tree and mean nothing."""
    script = REPO_ROOT / "scripts/external_smoke.py"
    assert not script.name.startswith("test_")
    assert script.parent.name == "scripts"


def test_the_release_checklist_names_the_external_smoke() -> None:
    text = (REPO_ROOT / "docs/design/RELEASE_ENFORCEMENT.md").read_text()
    assert "external_smoke.py" in text, (
        "the release procedure does not run the external smoke, so the tag "
        "would ship without anyone installing it the way a user would"
    )
