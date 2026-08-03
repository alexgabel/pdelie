# Fornberg Accuracy — Second Derivation

**Status:** the oracle for `formal_accuracy = stencil_size − derivative_order`.
Required by [`ANALYTICAL_ORACLE_DISCIPLINE.md`](ANALYTICAL_ORACLE_DISCIPLINE.md)
and by C-2 of the v0.38 binding constraints.

**Oracle method:** `manufactured_solution`.
**Declared before the pilot ran**, in `v0_38b_hypothesis_freeze.md` §4.
**Executable check:** `tests/test_v0_38b_fornberg_oracle.py`.

## The claim

For a stencil of `n` nodes approximating a `d`-th derivative,

```
formal_accuracy = n − d
```

It is load-bearing: `FornbergWeights.formal_accuracy` returns it, the v0.38b
convergence gate compares an observed order against it, and a pass/fail cites it.

## Primary derivation

Fornberg weights over `n` nodes reproduce exactly the `d`-th derivative of any
polynomial of degree `≤ n−1`. Expanding a smooth `u` about the evaluation point,
the weights annihilate the first `d` Taylor terms, reproduce the next `n−d`
exactly, and leave a leading error term of order `h^(n−d)`.

One line, and it looked right. So did the v0.37c §6 bound.

## Secondary derivation — manufactured solution

**Independent because it shares no code and no numerical method** with the
recursion that produces the weights. It refines nothing, approximates nothing,
and compares against an answer known in closed form.

Take nodes `x₀ … x_{n−1}` that are **deliberately non-uniform** — chosen so no
symmetry could make a wrong formula accidentally right — and the monomial

```
p(x) = x^k        p^(d)(x) = k!/(k−d)! · x^(k−d)      for k ≥ d
```

For every `k ≤ n−1`, applying the weights to `p` sampled at the nodes must
reproduce `p^(d)` at the evaluation point to roundoff:

```
Σ wᵢ · xᵢ^k  =  k!/(k−d)! · x*^(k−d)
```

This is an **exact algebraic identity**, not a limit. If it holds for every
`k ≤ n−1` and fails for `k = n`, the weights annihilate exactly the right space —
which is what `formal_accuracy = n − d` asserts.

The failure at `k = n` is checked too. Exactness up to `n−1` alone would also be
satisfied by a formula exact to *all* orders, which does not exist; asserting
where exactness **stops** is what pins the accuracy rather than bounding it below.

## Why not the other two methods

`symbolic_expansion` would mean adding `sympy` as a dependency for one identity —
a larger change than the thing being checked.

`independent_implementation` would mean a second copy of Fornberg's recursion,
which is not independent in the way that matters: a transcription error in the
original is likely to be repeated, and an algorithmic misunderstanding certainly
would be.

Polynomial exactness is checkable against a right answer known **in advance**.
That is the property that caught the bogus 13.8% figure during the v0.38e pilot,
where a quantity obtained by subtracting two numbers went unquestioned until a
case with a known answer of exactly zero reported `1.9e+03`.

## What this oracle does **not** cover

- **It does not establish the observed convergence order.** That is a property
  of a refinement sweep on a specific function and grid family, measured in the
  v0.38b pilot and bounded there. The oracle establishes the *formal* order.
- **It does not bound roundoff.** Polynomial exactness is an algebraic statement;
  the achieved floor on a strongly non-uniform grid is a measurement, and the
  pilot reports it separately.
- **It cannot detect an execution-vs-declaration mismatch.** An oracle checks a
  formula. Whether the code ran the stencil it declared is a different question,
  answered by the mask and its producers.
