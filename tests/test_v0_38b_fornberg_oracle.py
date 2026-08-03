"""v0.38b: the manufactured-solution oracle for ``formal_accuracy = n - d``.

Declared in ``v0_38b_hypothesis_freeze.md`` §4 **before the pilot ran**, as C-2
requires. Write-up: ``docs/design/FORNBERG_ACCURACY_ORACLE.md``.

Independent because it shares no numerical method with the recursion under test:
every quantity here is a closed-form monomial derivative. Nothing is refined and
nothing is approximated.
"""

from __future__ import annotations

from math import factorial

import numpy as np
import pytest

from pdelie.differentiation.fornberg import fornberg_weights

_ORACLE = "manufactured_solution: docs/design/FORNBERG_ACCURACY_ORACLE.md"

#: Deliberately irregular, and deliberately not symmetric about any evaluation
#: point: a symmetric stencil can make a wrong formula accidentally right for
#: odd or even derivative orders.
_IRREGULAR_NODES = np.array([0.0, 0.31, 1.07, 1.13, 2.71, 4.02, 4.15, 6.4])

#: Off-node, so FN-5's "the evaluation point need not be a node" is exercised by
#: the oracle rather than only by a separate test.
_EVALUATION_POINT = 1.6


def _monomial_derivative(degree: int, order: int, point: float) -> float:
    """``d^order/dx^order  x^degree``, in closed form."""
    if order > degree:
        return 0.0
    return factorial(degree) / factorial(degree - order) * point ** (degree - order)


@pytest.mark.load_bearing_analytical(oracle_source=_ORACLE)
@pytest.mark.parametrize("stencil_size", [3, 4, 5, 6, 7, 8])
@pytest.mark.parametrize("derivative_order", [1, 2, 3])
def test_weights_are_exact_on_every_polynomial_below_the_stencil_size(
    stencil_size: int, derivative_order: int
) -> None:
    """Exactness for degree <= n-1. The half of the claim that bounds error."""
    if stencil_size < derivative_order + 1:
        pytest.skip("refused by FN-3; covered by its own test")

    nodes = _IRREGULAR_NODES[:stencil_size]
    weights = fornberg_weights(nodes, _EVALUATION_POINT, derivative_order)
    assert weights.formal_accuracy == stencil_size - derivative_order

    for degree in range(stencil_size):
        approximated = float(np.dot(weights.weights, nodes**degree))
        exact = _monomial_derivative(degree, derivative_order, _EVALUATION_POINT)
        scale = max(abs(exact), float(np.max(np.abs(nodes**degree))), 1.0)
        assert abs(approximated - exact) <= 1e-9 * scale, (
            f"stencil={stencil_size} d={derivative_order} degree={degree}: "
            f"{approximated!r} != {exact!r}. Weights over n nodes must reproduce "
            f"the exact derivative of every polynomial of degree < n; if they do "
            f"not, formal_accuracy = n - d is wrong."
        )


@pytest.mark.load_bearing_analytical(oracle_source=_ORACLE)
@pytest.mark.parametrize("stencil_size", [4, 5, 6, 7])
def test_exactness_stops_at_the_stencil_size(stencil_size: int) -> None:
    """The half that pins the order rather than bounding it below.

    Exactness up to ``n-1`` alone would also be satisfied by a formula exact to
    all orders. Asserting where exactness **stops** is what makes
    ``formal_accuracy = n - d`` an equality rather than an inequality.
    """
    nodes = _IRREGULAR_NODES[:stencil_size]
    weights = fornberg_weights(nodes, _EVALUATION_POINT, 1)

    degree = stencil_size  # one beyond what the stencil can reproduce
    approximated = float(np.dot(weights.weights, nodes**degree))
    exact = _monomial_derivative(degree, 1, _EVALUATION_POINT)
    assert abs(approximated - exact) > 1e-6 * max(abs(exact), 1.0), (
        f"a {stencil_size}-node stencil reproduced degree {degree} exactly. It "
        f"must not: if exactness does not stop here, the accuracy order is not "
        f"n - d and the primary derivation is wrong."
    )


@pytest.mark.load_bearing_analytical(oracle_source=_ORACLE)
def test_the_oracle_nodes_really_are_irregular() -> None:
    """Guard the premise. On a uniform grid a wrong formula can be right by symmetry."""
    spacings = np.diff(_IRREGULAR_NODES)
    ratio = float(spacings.max() / spacings.min())
    assert ratio > 10.0, (
        f"the oracle nodes have spacing ratio {ratio:.2f}; they are too close to "
        f"uniform to rule out a formula that is only accidentally right"
    )


def test_the_oracle_shares_no_numerical_method_with_the_implementation() -> None:
    """Independence is the load-bearing word.

    A secondary derivation reusing the first one's machinery reproduces its
    omissions. This oracle imports only the function under test -- never the
    differentiation stack, and never a numerical derivative.
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

    pdelie_imports = {name for name in imported if name.startswith("pdelie")}
    assert pdelie_imports == {"pdelie.differentiation.fornberg"}, (
        f"the oracle imports {sorted(pdelie_imports)}; it must import only the "
        f"function under test"
    )

    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    for numerical in ("gradient", "diff", "fft", "polyfit", "polyder"):
        assert numerical not in called or numerical == "diff", (
            f"the oracle calls np.{numerical}, so it is approximating or fitting "
            f"a derivative rather than writing one in closed form"
        )
