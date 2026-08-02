# Analytical Oracle Discipline

**Status:** binding for any load-bearing analytical bound.

A bound written once, by one person, and confirmed by the measurement it was
written to explain is not evidence. It is a hypothesis and its own grader.

## The rule

Every **load-bearing** analytical bound requires **two independent derivations**:

1. a primary hand derivation, and
2. one of:
   - **symbolic expansion** — `sympy`, expanding the operator and comparing term
     by term;
   - **manufactured-solution identity** — a closed-form `u` for which the exact
     residual is known, so the bound can be checked against a value nobody
     measured;
   - **independent implementation** — the quantity computed a second way that
     shares no code with the first.

"Load-bearing" means: a tolerance, threshold, floor or ceiling depends on it, or
a pass/fail verdict cites it.

## Why two, and why independent

The v0.37c §6 obstruction bound was derived once and looked right. It came in at
`0.52`–`1.00` of the observed error — **not a bound at all** — because it kept
`a·u_xx` and dropped `a'·u_x` from `(a·u_x)_x`. A symbolic expansion of the
operator would have shown two terms immediately. The hand derivation and the
measurement disagreed, and it took a pilot block to notice, because nothing else
was looking.

Independence is the load-bearing word. A second derivation that reuses the first
one's expansion reproduces its omissions.

## Oracle source is a declared field

Any test marked `@pytest.mark.load_bearing_analytical` must declare its
`oracle_source` — which of the three secondary methods was used, and where the
derivation lives. A bound whose oracle is "we checked it" is undeclared.

The form is `oracle_source="<method>: <location>"`, with `<method>` one of
`symbolic_expansion`, `manufactured_solution`, `independent_implementation`.
`tests/test_analytical_oracle_marker.py` enforces all of it: a bare marker with
no call, a method outside the vocabulary, and a method with no location are each
refused. It parses the decorator with `ast` rather than scanning text, because a
scan cannot distinguish a declaration from a discussion of one.

**What it cannot check.** That the oracle is *right*. The v0.37c §6 bound would
have passed this and still been wrong. It prevents the more common failure —
never producing a second derivation at all.

## What this does not cover

**Execution-vs-declaration mismatch.** An oracle checks that a *formula* is
right. It cannot tell you the code ran a different transformation than the one
declared — the C-5 class, where a benchmark declared a parameter rescale and
executed a state rescale. That needs an audit asking *is the declared action the
one that was consumed?*, which is
`tests/test_benchmark_action_semantics_guard.py`, not an oracle.

The two disciplines are complementary and neither substitutes for the other.

## First consumer

The v0.38b Fornberg convergence-order bound. Its hypothesis freeze must name its
oracle source before the pilot runs.
