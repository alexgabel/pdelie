"""v0.38: the weak diagnostic's seed is required. The promise is kept.

Supersedes the three-state semantics asserted in
``test_v0_36e_deterministic_seed.py``, which is retained in reduced form as the
record of what the transition replaced.

The history, because it is the point
====================================

The diagnostic was silently unreproducible from v0.31b2: ``WeakPDELibrary``
draws its domain centers from the global NumPy RNG and exposes no seed. v0.34c
added an opt-in seed and deliberately left the default alone. v0.36e added a
``FutureWarning`` promising the flip at v0.37. v0.37 did not flip it -- the
transition was scoped out of v0.37a's freeze -- and the notice was re-dated to
v0.38, with ``test_forward_promises.py`` added so the slip could not happen
silently a third time.

v0.38 keeps it. Omission is a ``TypeError`` from the signature; ``None`` is
refused; there is **no undocumented compatibility default**, because retaining
one would preserve exactly the nondeterminism this removes.
"""

from __future__ import annotations

import inspect
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
        return inspect_pysindy_weak_pde_library(field, task_name="v0_38", **kwargs)


# --------------------------------------------------------------------------
# 1. Omission raises TypeError
# --------------------------------------------------------------------------


def test_omitting_the_seed_raises_type_error(field) -> None:
    """From the signature itself, so no code path can soften it."""
    with pytest.raises(TypeError, match="seed"):
        inspect_pysindy_weak_pde_library(field, task_name="v0_38")


def test_the_signature_carries_no_default(field) -> None:
    """A default would be the compatibility escape hatch, by another name."""
    parameter = inspect.signature(inspect_pysindy_weak_pde_library).parameters["seed"]
    assert parameter.default is inspect.Parameter.empty
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, (
        "seed must be keyword-only; positionally it could be confused with "
        "another argument at a call site that does not name it"
    )
    assert parameter.annotation in ("int", int)


def test_no_sentinel_survives_in_the_module() -> None:
    """``_UNSET`` was the mechanism for the omitted state; it is gone.

    Left in place it would be an obvious way to reintroduce an implicit
    default, and nothing else in the module needs it.
    """
    import pdelie.tasks.weak_pde_library as module

    assert not hasattr(module, "_UNSET")


# --------------------------------------------------------------------------
# 2. None is rejected
# --------------------------------------------------------------------------


def test_explicit_none_is_rejected(field) -> None:
    """It used to mean "opt into nondeterminism". That option is withdrawn."""
    with pytest.raises(ScopeValidationError, match="None is refused"):
        call(field, seed=None)


# --------------------------------------------------------------------------
# 3. bool is rejected despite being an int subclass
# --------------------------------------------------------------------------


@pytest.mark.parametrize("value", [True, False])
def test_bool_is_rejected_even_though_it_is_an_int_subclass(field, value: bool) -> None:
    """``seed=True`` would otherwise silently seed with 1."""
    with pytest.raises(ScopeValidationError, match="int subclass"):
        call(field, seed=value)


@pytest.mark.parametrize("value", ["13", 13.0, [13], object()])
def test_non_integer_seeds_are_rejected(field, value: object) -> None:
    with pytest.raises(ScopeValidationError, match="seed must be an int"):
        call(field, seed=value)


# --------------------------------------------------------------------------
# 4. Same input and seed reproduce the same scientific payload
# --------------------------------------------------------------------------


def test_the_same_input_and_seed_reproduce_the_same_payload(field) -> None:
    """The reason the promise was worth keeping."""
    first = call(field, seed=4242)
    second = call(field, seed=4242)
    assert first == second


def test_the_same_seed_reproduces_the_conditioning_numbers(field) -> None:
    first = call(field, seed=4242, column_normalize=True)
    second = call(field, seed=4242, column_normalize=True)
    assert first["column_normalization"] == second["column_normalization"]


def test_different_seeds_may_differ(field) -> None:
    """Otherwise the seed would be inert and reproducibility would be luck."""
    a = call(field, seed=1)
    b = call(field, seed=999_983)
    assert a["provenance"]["seed_provenance"]["seed"] == 1
    assert b["provenance"]["seed_provenance"]["seed"] == 999_983


# --------------------------------------------------------------------------
# 5. Every internal caller supplies a seed explicitly
# --------------------------------------------------------------------------


def test_every_internal_caller_passes_a_seed() -> None:
    """AST, not text: a call is a call node, not a substring."""
    import ast
    from pathlib import Path

    src_root = Path(__file__).resolve().parents[1] / "src" / "pdelie"
    offenders: list[str] = []
    for path in sorted(src_root.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name != "inspect_pysindy_weak_pde_library":
                continue
            keywords = {kw.arg for kw in node.keywords}
            # `**kwargs` forwards arrive as arg=None and may carry the seed.
            if "seed" not in keywords and None not in keywords:
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, (
        f"unseeded internal call sites: {offenders}. The seed is required, so "
        f"these would raise at runtime rather than fall back to anything."
    )


# --------------------------------------------------------------------------
# 6. An AST test forbids calls without seed=
# --------------------------------------------------------------------------


def test_the_ast_guard_detects_a_planted_unseeded_call() -> None:
    """A guard that cannot fire is the defect it is meant to prevent."""
    import ast

    planted = ast.parse(
        "inspect_pysindy_weak_pde_library(field, task_name='x')\n"
        "inspect_pysindy_weak_pde_library(field, task_name='y', seed=1)\n"
    )
    unseeded = [
        node
        for node in ast.walk(planted)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", None) == "inspect_pysindy_weak_pde_library"
        and "seed" not in {kw.arg for kw in node.keywords}
    ]
    assert len(unseeded) == 1, "the guard cannot tell a seeded call from an unseeded one"


# --------------------------------------------------------------------------
# 7. The forward promise is discharged
# --------------------------------------------------------------------------


def test_the_future_warning_is_gone(field) -> None:
    """The notice announced this change. Keeping it would re-promise a past event."""
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        call(field, seed=13)
    assert not [w for w in captured if issubclass(w.category, FutureWarning)]


def test_the_source_no_longer_promises_a_seed_transition() -> None:
    from pathlib import Path

    import pdelie.tasks.weak_pde_library as module

    text = Path(module.__file__).read_text()
    assert "will require an explicit integer seed" not in text, (
        "the promise text survives; it now describes a change already made"
    )


# --------------------------------------------------------------------------
# Payload shape is preserved
# --------------------------------------------------------------------------


@pytest.mark.parametrize("column_normalize", [False, True])
def test_the_frozen_27_28_conditional_schema_is_unchanged(
    field, column_normalize: bool
) -> None:
    report = call(field, seed=13, column_normalize=column_normalize)
    assert len(report) == (28 if column_normalize else 27)


def test_the_seed_provenance_block_keeps_all_seven_keys(field) -> None:
    """Two are now constant. They are kept, not dropped.

    The block sits inside a frozen conditional schema; removing keys would
    change the payload shape for every existing consumer to communicate
    something the ``seed`` value already says.
    """
    provenance = call(field, seed=13)["provenance"]["seed_provenance"]
    assert set(provenance) == {
        "seed",
        "seed_was_omitted",
        "rng_backend",
        "rng_scope",
        "nondeterministic_requested",
        "thread_safe",
        "legacy_global_rng_workaround",
    }
    assert provenance["seed"] == 13
    assert provenance["seed_was_omitted"] is False
    assert provenance["nondeterministic_requested"] is False


def test_the_report_is_strict_json(field) -> None:
    json.dumps(call(field, seed=13), allow_nan=False)
