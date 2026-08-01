"""v0.36e: three-state seed semantics for the weak-form diagnostic.

The diagnostic has been silently unreproducible since v0.31b2, because
``pysindy.WeakPDELibrary`` draws its domain centers from the global NumPy RNG and
exposes no seed parameter. v0.34c added an opt-in ``seed`` but deliberately left
the default alone to avoid changing a shipped surface.

That was right then and is wrong now: v0.36f publishes to an index, and new users
meet the default first. This is the transition warning, not the flip -- v0.37
makes an explicit seed required.
"""

from __future__ import annotations

import json
import warnings

import pytest

from pdelie.data import generate_heat_1d_field_batch
from pdelie.errors import ScopeValidationError
from pdelie.tasks.weak_pde_library import inspect_pysindy_weak_pde_library


@pytest.fixture(scope="module")
def field():
    return generate_heat_1d_field_batch(
        batch_size=1, num_times=64, num_points=64, seed=3120
    )


def call(field, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        return inspect_pysindy_weak_pde_library(field, task_name="v0_36e", **kwargs)


def future_warnings(field, **kwargs) -> list[warnings.WarningMessage]:
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        inspect_pysindy_weak_pde_library(field, task_name="v0_36e", **kwargs)
    return [item for item in captured if issubclass(item.category, FutureWarning)]


# --- the three states -------------------------------------------------------


def test_omitting_the_seed_emits_exactly_one_future_warning(field) -> None:
    """Exactly one: not zero, and not one per internal call site."""
    emitted = future_warnings(field)
    assert len(emitted) == 1


def test_the_warning_is_a_future_warning_not_a_deprecation_warning(field) -> None:
    """DeprecationWarning is hidden by default outside __main__.

    Using it would make this transition invisible to precisely the callers who
    need to see it -- library code importing pdelie, which is most of them.
    """
    emitted = future_warnings(field)
    assert emitted[0].category is FutureWarning
    assert not issubclass(emitted[0].category, DeprecationWarning)


def test_the_warning_names_both_exact_fixes(field) -> None:
    message = str(future_warnings(field)[0].message)
    assert "seed=<int>" in message
    assert "seed=None" in message
    # The named release must be one that has NOT shipped. It said v0.37 until
    # v0.37 closed without making the cut -- v0.37a's freeze scoped the
    # weak-diagnostic transition out explicitly -- at which point the warning
    # was promising something the release did not deliver. A deprecation notice
    # naming a version already released is worse than no notice.
    import tomllib
    from pathlib import Path

    version = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    )["project"]["version"]
    named = [tok for tok in message.split() if tok.startswith("v0.")]
    assert named, f"the warning names no target release: {message}"
    for token in named:
        assert token.strip(".,") > f"v{version}", (
            f"the warning promises {token} but the package is already v{version}; "
            f"either make the cut or name a later release"
        )


def test_explicit_none_is_silent_and_records_the_opt_in(field) -> None:
    """None now means 'I want nondeterminism', which is a different claim from
    saying nothing at all."""
    assert future_warnings(field, seed=None) == []
    provenance = call(field, seed=None)["provenance"]["seed_provenance"]
    assert provenance["seed"] is None
    assert provenance["seed_was_omitted"] is False
    assert provenance["nondeterministic_requested"] is True


def test_an_integer_seed_is_silent_and_recorded(field) -> None:
    assert future_warnings(field, seed=42) == []
    provenance = call(field, seed=42)["provenance"]["seed_provenance"]
    assert provenance["seed"] == 42
    assert provenance["seed_was_omitted"] is False
    assert provenance["nondeterministic_requested"] is False


def test_omitted_is_distinguishable_from_explicit_none_in_the_payload(field) -> None:
    """The whole point of the sentinel: these were indistinguishable before."""
    omitted = call(field)["provenance"]["seed_provenance"]
    explicit = call(field, seed=None)["provenance"]["seed_provenance"]
    assert omitted["seed"] == explicit["seed"] is None
    assert omitted["seed_was_omitted"] != explicit["seed_was_omitted"]
    assert omitted["nondeterministic_requested"] != explicit["nondeterministic_requested"]


# --- determinism ------------------------------------------------------------


def test_the_same_integer_seed_reproduces_the_conditioning_numbers(field) -> None:
    first = call(field, seed=20340, column_normalize=True)["column_normalization"]
    second = call(field, seed=20340, column_normalize=True)["column_normalization"]
    assert first == second


def test_different_seeds_may_give_different_conditioning(field) -> None:
    """If every seed agreed, the seed would not be doing anything."""
    ratios = {
        call(field, seed=seed, column_normalize=True)["column_normalization"][
            "condition_number_before_normalization"
        ]
        for seed in (20340, 20341, 20342)
    }
    assert len(ratios) > 1


# --- rejected inputs --------------------------------------------------------


def test_bool_is_rejected_even_though_it_is_an_int_subclass(field) -> None:
    """seed=True would otherwise silently seed with 1."""
    with pytest.raises(ScopeValidationError, match="must be an int, None, or omitted"):
        call(field, seed=True)


def test_string_and_float_seeds_are_rejected(field) -> None:
    for bad in ("42", 42.0, [42]):
        with pytest.raises(ScopeValidationError, match="must be an int, None, or omitted"):
            call(field, seed=bad)


# --- the frozen 27/28 conditional -------------------------------------------


@pytest.mark.parametrize("seed_kwargs", [{}, {"seed": None}, {"seed": 42}])
@pytest.mark.parametrize("normalize", [False, True])
def test_seed_semantics_preserve_the_27_28_conditional_schema(
    field, seed_kwargs: dict, normalize: bool
) -> None:
    """seed_provenance is nested, so no top-level key is added in any state."""
    report = call(field, column_normalize=normalize, **seed_kwargs)
    assert len(set(report)) == (28 if normalize else 27)


def test_seed_provenance_lives_inside_the_existing_provenance_block(field) -> None:
    report = call(field, seed=42)
    assert "seed_provenance" not in report
    assert "seed_provenance" in report["provenance"]


def test_the_provenance_block_carries_all_seven_keys(field) -> None:
    provenance = call(field, seed=42)["provenance"]["seed_provenance"]
    assert set(provenance) == {
        "seed",
        "seed_was_omitted",
        "rng_backend",
        "rng_scope",
        "nondeterministic_requested",
        "thread_safe",
        "legacy_global_rng_workaround",
    }
    assert provenance["rng_backend"] == "numpy_legacy_global_state"
    assert provenance["rng_scope"] == "process_wide_context_manager"
    assert provenance["thread_safe"] is False
    assert provenance["legacy_global_rng_workaround"] is True


@pytest.mark.parametrize("seed_kwargs", [{}, {"seed": None}, {"seed": 42}])
def test_the_report_is_strict_json_in_every_seed_state(field, seed_kwargs: dict) -> None:
    encoded = json.dumps(call(field, **seed_kwargs), allow_nan=False)
    assert "NaN" not in encoded and "Infinity" not in encoded


# --- the warning must be visible from library code --------------------------


def test_the_warning_reaches_a_caller_in_another_module(field, tmp_path) -> None:
    """Regression guard for the DeprecationWarning-would-be-hidden failure mode.

    Emitted from an imported module under Python's default filters, a
    DeprecationWarning is suppressed and a FutureWarning is not. This runs the
    call from a separate module with default filters restored, which is the
    situation a downstream library is actually in.
    """
    module = tmp_path / "downstream_caller.py"
    module.write_text(
        "from pdelie.data import generate_heat_1d_field_batch\n"
        "from pdelie.tasks.weak_pde_library import inspect_pysindy_weak_pde_library\n"
        "\n"
        "def run():\n"
        "    field = generate_heat_1d_field_batch(\n"
        "        batch_size=1, num_times=64, num_points=64, seed=3120\n"
        "    )\n"
        "    return inspect_pysindy_weak_pde_library(field, task_name='downstream')\n",
        encoding="utf-8",
    )
    import subprocess
    import sys

    runner = tmp_path / "run_downstream.py"
    runner.write_text(
        "import sys, warnings\n"
        f"sys.path.insert(0, {str(tmp_path)!r})\n"
        "warnings.resetwarnings()\n"
        "import downstream_caller\n"
        "with warnings.catch_warnings(record=True) as captured:\n"
        "    warnings.simplefilter('always')\n"
        "    downstream_caller.run()\n"
        "print(sum(1 for item in captured "
        "if issubclass(item.category, FutureWarning)))\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(runner)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-1] == "1"
