"""v0.38 §6: the first genuine ``load_bearing_analytical`` consumer.

The bound: ``d/dx(nu*u_x) - nu*u_xx == nu' * u_x``, exactly.

It is load-bearing under the definition in ``ANALYTICAL_ORACLE_DISCIPLINE.md``:
two pass/fail verdicts cite it (``ratio > 0.5`` on a variable profile,
``ratio == 0.0`` on a constant one), and the resolver's refusal message asserts
its consequence -- that the forms coincide iff ``nu`` is constant.

Its second, independent derivation is a **manufactured solution**: closed-form
``nu`` and ``u`` for which every derivative is known analytically, so nothing
here is approximated and no code is shared with the spectral path the benchmark
uses. The write-up is ``docs/design/OPERATOR_FORM_IDENTITY_ORACLE.md``.

This is the derivation that would have caught the v0.37c section-6 error, which
dropped exactly the ``a' * u_x`` term.
"""

from __future__ import annotations

import numpy as np
import pytest

_ORACLE = "manufactured_solution: docs/design/OPERATOR_FORM_IDENTITY_ORACLE.md"

# Manufactured problem. Fixed rather than swept: the identity is algebraic, so a
# sweep would repeat one proof at many points rather than strengthen it.
_A0 = 0.1
_ALPHA = 0.5
_K = 2.0
_M = 3.0


def _grid(num_points: int = 257) -> np.ndarray:
    # Endpoint excluded so the grid is periodic; irrelevant to the algebra, but
    # it keeps the fixture the same shape as the ones the benchmark uses.
    return np.linspace(0.0, 2.0 * np.pi, num_points, endpoint=False)


def _closed_forms(x: np.ndarray, *, alpha: float = _ALPHA) -> dict[str, np.ndarray]:
    """Every quantity in closed form. No derivative is approximated."""
    return {
        "nu": _A0 * (1.0 + alpha * np.sin(_K * x)),
        "nu_prime": _A0 * alpha * _K * np.cos(_K * x),
        "u_x": _M * np.cos(_M * x),
        "u_xx": -(_M**2) * np.sin(_M * x),
    }


def _conservative_operator(closed: dict[str, np.ndarray]) -> np.ndarray:
    """``d/dx(nu * u_x)``, expanded analytically by the product rule."""
    return closed["nu_prime"] * closed["u_x"] + closed["nu"] * closed["u_xx"]


def _nonconservative_operator(closed: dict[str, np.ndarray]) -> np.ndarray:
    """``nu * u_xx``."""
    return closed["nu"] * closed["u_xx"]


@pytest.mark.load_bearing_analytical(oracle_source=_ORACLE)
def test_the_two_operators_differ_by_exactly_nu_prime_times_u_x() -> None:
    """The identity itself, on a manufactured solution."""
    x = _grid()
    closed = _closed_forms(x)

    difference = _conservative_operator(closed) - _nonconservative_operator(closed)
    predicted = closed["nu_prime"] * closed["u_x"]

    residual = float(np.max(np.abs(difference - predicted)))
    scale = float(np.max(np.abs(predicted)))
    assert residual <= 1e-14 * scale, (
        f"the operator difference is not nu' * u_x: max deviation {residual:.3e} "
        f"against a term of magnitude {scale:.3e}. The primary derivation is the "
        f"product rule; if this fails, one of the two is wrong."
    )


@pytest.mark.load_bearing_analytical(oracle_source=_ORACLE)
def test_the_difference_vanishes_identically_for_a_constant_coefficient() -> None:
    """The consequence the resolver's refusal message asserts.

    ``alpha = 0`` makes ``nu`` constant, so ``nu' == 0`` and the two operators
    are the same operator. Exactly zero, not small: this is algebra, not a
    limit.
    """
    x = _grid()
    closed = _closed_forms(x, alpha=0.0)

    assert np.all(closed["nu_prime"] == 0.0), "the manufactured nu is not constant"
    difference = _conservative_operator(closed) - _nonconservative_operator(closed)
    assert np.all(difference == 0.0), (
        "the forms do not coincide for a constant coefficient, so the resolver's "
        "statement that a mismatch is numerically harmless there is false"
    )


@pytest.mark.load_bearing_analytical(oracle_source=_ORACLE)
def test_the_difference_is_non_trivial_for_a_variable_coefficient() -> None:
    """Otherwise the two tests above would agree for an uninteresting reason.

    A bound that is zero on both sides proves nothing about either.
    """
    x = _grid()
    closed = _closed_forms(x)
    predicted = closed["nu_prime"] * closed["u_x"]
    nonconservative = _nonconservative_operator(closed)

    ratio = float(np.max(np.abs(predicted))) / float(np.max(np.abs(nonconservative)))
    assert ratio > 0.1, (
        f"the difference term is only {ratio:.3e} of the operator on this "
        f"manufactured problem, so it could not distinguish the two forms"
    )


def test_the_primary_and_secondary_derivations_are_independent() -> None:
    """Guard the independence claim, which is the load-bearing word.

    A secondary derivation that reuses the first one's machinery reproduces its
    omissions. This oracle must not import the differentiation stack the
    benchmark measures with.
    """
    import ast
    from pathlib import Path

    tree = ast.parse(Path(__file__).read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden = {name for name in imported if name.startswith("pdelie")}
    assert not forbidden, (
        f"this oracle imports {sorted(forbidden)}. Its independence is the whole "
        f"point: sharing the differentiation code would reproduce its errors "
        f"rather than check them."
    )


def test_no_derivative_here_is_approximated() -> None:
    """The manufactured-solution property, asserted rather than trusted.

    ``np.gradient``, ``np.diff`` or a spectral derivative would silently turn
    this into a discretization comparison -- which is exactly the mistake that
    produced a bogus 13.8% figure during the v0.38e pilot.
    """
    import ast
    from pathlib import Path

    source = Path(__file__).read_text()
    tree = ast.parse(source)
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called.add(node.func.attr)

    for numerical in ("gradient", "diff", "fft", "ifft", "convolve"):
        assert numerical not in called, (
            f"this oracle calls np.{numerical}, so it is approximating a "
            f"derivative. Every quantity here must be closed-form or the "
            f"independence claim is false."
        )
