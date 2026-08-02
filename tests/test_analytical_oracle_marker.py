"""Enforce the oracle-source declaration on load-bearing analytical bounds.

`docs/design/ANALYTICAL_ORACLE_DISCIPLINE.md` requires that every test marked
``@pytest.mark.load_bearing_analytical`` declare an ``oracle_source`` naming the
second, independent derivation. This module makes that requirement executable.

Two things this deliberately does NOT do.

It does not scan text. Six times across v0.36-v0.37 a text scan flagged prose
that *refused* a claim, because ``"foo" in source`` cannot tell a declaration
from a discussion. Every check here parses the decorator with ``ast``.

It does not verify the oracle is *correct* -- no test can. It verifies one was
named, by which method, and where it lives. The v0.37c section-6 bound would
have passed this check and still been wrong; what this prevents is the weaker
and more common failure of never producing a second derivation at all.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

MARKER = "load_bearing_analytical"

#: The three secondary derivations the discipline document admits. A bound whose
#: oracle is "we checked it" is undeclared, so the vocabulary is closed.
APPROVED_ORACLE_METHODS: frozenset[str] = frozenset(
    {
        "symbolic_expansion",
        "manufactured_solution",
        "independent_implementation",
    }
)

_TESTS_DIR = Path(__file__).resolve().parent


def _marked_functions(tree: ast.AST) -> list[tuple[str, ast.expr]]:
    """Return ``(function_name, decorator_node)`` for each marked function."""
    found: list[tuple[str, ast.expr]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            target = decorator.func if isinstance(decorator, ast.Call) else decorator
            if isinstance(target, ast.Attribute) and target.attr == MARKER:
                found.append((node.name, decorator))
    return found


def _module_string_constants(tree: ast.AST) -> dict[str, str]:
    """Module-level ``NAME = "literal"`` bindings, for resolving a shared constant.

    Several tests in one module usually cite the same oracle. Requiring the
    string inline at each marker means three copies of a path, which is a drift
    risk of exactly the kind this guard exists to prevent -- so a module-level
    constant is resolved instead. It stays fully static: only a direct string
    literal assigned at module scope is accepted, never a computed value.
    """
    constants: dict[str, str] = {}
    for node in getattr(tree, "body", []):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if (
            isinstance(target, ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            constants[target.id] = node.value.value
    return constants


def _oracle_source(decorator: ast.expr, constants: dict[str, str] | None = None) -> str | None:
    """Extract the ``oracle_source=`` from the decorator, if present.

    A bare ``@pytest.mark.load_bearing_analytical`` is not a call and so carries
    no keywords: it claims the bound is load-bearing while declaring nothing
    about how it was checked, which is the exact state this guard exists to
    refuse.

    A ``Name`` is resolved against module-level string constants, and against
    nothing else -- an expression that has to be executed to know its value is
    not a static declaration.
    """
    if not isinstance(decorator, ast.Call):
        return None
    for keyword in decorator.keywords:
        if keyword.arg != "oracle_source":
            continue
        value = keyword.value
        if isinstance(value, ast.Constant):
            return value.value if isinstance(value.value, str) else None
        if isinstance(value, ast.Name) and constants is not None:
            return constants.get(value.id)
        return None
    return None


def _collect() -> list[tuple[Path, str, ast.expr, dict[str, str]]]:
    collected: list[tuple[Path, str, ast.expr, dict[str, str]]] = []
    for path in sorted(_TESTS_DIR.rglob("test_*.py")):
        if path.name == Path(__file__).name:
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        constants = _module_string_constants(tree)
        for name, decorator in _marked_functions(tree):
            collected.append((path, name, decorator, constants))
    return collected


def test_every_marked_test_declares_an_oracle_source() -> None:
    """The marker without the field is the failure mode worth catching."""
    for path, name, decorator, constants in _collect():
        source = _oracle_source(decorator, constants)
        assert source is not None, (
            f"{path.name}::{name} is marked {MARKER} but declares no literal "
            f"oracle_source. Per ANALYTICAL_ORACLE_DISCIPLINE.md the second, "
            f"independent derivation must be named at the marker."
        )


def test_declared_oracle_methods_are_in_the_closed_vocabulary() -> None:
    """``method: where it lives`` -- both halves are required."""
    for path, name, decorator, constants in _collect():
        source = _oracle_source(decorator, constants)
        assert source is not None, f"{path.name}::{name}"
        method, _, location = source.partition(":")
        method = method.strip()
        assert method in APPROVED_ORACLE_METHODS, (
            f"{path.name}::{name} declares oracle method {method!r}, which is "
            f"not one of {sorted(APPROVED_ORACLE_METHODS)}"
        )
        assert location.strip(), (
            f"{path.name}::{name} names method {method!r} but no location. "
            f"An unlocatable derivation cannot be reviewed; use "
            f"'{method}: path/to/derivation'."
        )


def test_the_registry_is_not_empty() -> None:
    """v0.38 §6: at least one genuine load-bearing consumer must exist.

    Until v0.38 the population was empty and every check over it passed
    vacuously -- the sentinels below established that the guard *could* fire,
    which is guard mechanics, not integration with a real scientific consumer.

    The first consumer is the operator-form identity
    (``d/dx(nu*u_x) - nu*u_xx == nu' * u_x``), which two pass/fail verdicts cite
    and which the equation-form resolver's refusal message depends on.
    """
    population = _collect()
    assert population, (
        "no test carries the load_bearing_analytical marker. If the last "
        "consumer was removed, that is a deliberate act: either another bound "
        "took its place and should be marked, or the decorator now governs "
        "nothing and ANALYTICAL_ORACLE_DISCIPLINE.md should say so."
    )


def test_every_oracle_source_location_exists() -> None:
    """A derivation nobody can open has not been produced."""

    repo_root = _TESTS_DIR.parent
    for path, name, decorator, constants in _collect():
        source = _oracle_source(decorator, constants)
        assert source is not None, f"{path.name}::{name}"
        location = source.partition(":")[2].strip().split("#", 1)[0].strip()
        assert location, f"{path.name}::{name} names no location"
        assert (repo_root / location).exists(), (
            f"{path.name}::{name} cites {location!r}, which does not exist. An "
            f"unopenable derivation cannot be reviewed, so it is not a second "
            f"derivation."
        )


def test_the_marker_is_registered() -> None:
    """An unregistered marker silently does nothing under ``--strict-markers``."""
    pyproject = (_TESTS_DIR.parent / "pyproject.toml").read_text()
    assert f'"{MARKER}:' in pyproject, f"{MARKER} is not registered in pyproject.toml [tool.pytest.ini_options]"


# --------------------------------------------------------------------------
# Sentinels.
#
# The v0.38b Fornberg bound is the first real consumer. Until it lands the
# population above is EMPTY, and the two tests over it pass vacuously -- they
# would pass just as well if the extraction logic were inverted. These sentinels
# assert the guard can actually fire, so the day a marked test appears the
# checks are known to work rather than assumed to.
# --------------------------------------------------------------------------

_BARE_MARKER = """
import pytest

@pytest.mark.load_bearing_analytical
def test_something() -> None:
    pass
"""

_NO_LOCATION = """
import pytest

@pytest.mark.load_bearing_analytical(oracle_source="symbolic_expansion")
def test_something() -> None:
    pass
"""

_UNAPPROVED_METHOD = """
import pytest

@pytest.mark.load_bearing_analytical(oracle_source="we_checked_it: somewhere")
def test_something() -> None:
    pass
"""

_VALID = """
import pytest

@pytest.mark.load_bearing_analytical(
    oracle_source="manufactured_solution: docs/design/foo.md#section-6"
)
def test_something() -> None:
    pass
"""


@pytest.mark.parametrize(
    ("source", "expected_oracle"),
    [
        (_BARE_MARKER, None),
        (_NO_LOCATION, "symbolic_expansion"),
        (_UNAPPROVED_METHOD, "we_checked_it: somewhere"),
        (_VALID, "manufactured_solution: docs/design/foo.md#section-6"),
    ],
)
def test_extraction_sentinel(source: str, expected_oracle: str | None) -> None:
    """The AST extraction distinguishes all four shapes."""
    marked = _marked_functions(ast.parse(source))
    assert len(marked) == 1, "the marker itself was not detected"
    assert _oracle_source(marked[0][1]) == expected_oracle


_VIA_CONSTANT = """
import pytest

_ORACLE = "manufactured_solution: docs/design/foo.md"

@pytest.mark.load_bearing_analytical(oracle_source=_ORACLE)
def test_something() -> None:
    pass
"""

_VIA_COMPUTED = """
import pytest

_PREFIX = "manufactured_solution"

@pytest.mark.load_bearing_analytical(oracle_source=_PREFIX + ": docs/design/foo.md")
def test_something() -> None:
    pass
"""


def test_a_module_level_constant_resolves() -> None:
    """The branch added so three tests can share one path without three copies."""
    tree = ast.parse(_VIA_CONSTANT)
    constants = _module_string_constants(tree)
    marked = _marked_functions(tree)
    assert len(marked) == 1
    assert (
        _oracle_source(marked[0][1], constants)
        == "manufactured_solution: docs/design/foo.md"
    )


def test_a_computed_oracle_source_is_refused() -> None:
    """Resolution stays static. An expression is not a declaration.

    Without this the Name branch would be an opening for anything that
    eventually evaluates to a string, and the guard could no longer read the
    declaration without running the module.
    """
    tree = ast.parse(_VIA_COMPUTED)
    constants = _module_string_constants(tree)
    marked = _marked_functions(tree)
    assert len(marked) == 1
    assert _oracle_source(marked[0][1], constants) is None, (
        "a concatenated expression resolved; only a direct module-level string "
        "literal may"
    )


def test_an_unresolvable_name_does_not_silently_pass() -> None:
    """A name bound nowhere must read as undeclared, not as some default."""
    tree = ast.parse(_VIA_CONSTANT.replace('_ORACLE = ', '_UNUSED = '))
    marked = _marked_functions(tree)
    assert _oracle_source(marked[0][1], _module_string_constants(tree)) is None


def test_guard_rejects_each_malformed_shape() -> None:
    """Every rejection path is exercised, not just the happy one."""
    bare = _oracle_source(_marked_functions(ast.parse(_BARE_MARKER))[0][1])
    assert bare is None, "a bare marker must not read as declaring an oracle"

    no_location = _oracle_source(_marked_functions(ast.parse(_NO_LOCATION))[0][1])
    assert no_location is not None
    assert not no_location.partition(":")[2].strip(), "a method with no location must be detectable as missing one"

    unapproved = _oracle_source(_marked_functions(ast.parse(_UNAPPROVED_METHOD))[0][1])
    assert unapproved is not None
    assert unapproved.partition(":")[0].strip() not in APPROVED_ORACLE_METHODS

    valid = _oracle_source(_marked_functions(ast.parse(_VALID))[0][1])
    assert valid is not None
    method, _, location = valid.partition(":")
    assert method.strip() in APPROVED_ORACLE_METHODS
    assert location.strip()


def test_marker_population_is_reported_not_assumed() -> None:
    """Record the current population so vacuity is visible, not silent.

    This does not assert a count. It asserts the collector runs and returns a
    well-formed result: the number is expected to go from zero to non-zero at
    v0.38b, and a test pinning it would have to be edited to allow that.
    """
    population = _collect()
    assert isinstance(population, list)
    for path, name, _, _ in population:
        assert path.exists() and name.startswith("test_")
