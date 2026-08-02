# Operator-Form Identity — Second Derivation

**Status:** the oracle for the load-bearing bound behind the v0.38 equation-form
resolver. Required by [`ANALYTICAL_ORACLE_DISCIPLINE.md`](ANALYTICAL_ORACLE_DISCIPLINE.md).

**Oracle method:** `manufactured_solution`.
**Executable check:** `tests/test_v0_38_operator_form_oracle.py`.

## The claim being checked

The conservative and non-conservative diffusive operators differ by exactly one
term:

```
d/dx( ν(x) · u_x )  −  ν(x) · u_xx  =  ν'(x) · u_x
```

Two things in v0.38 rest on this:

1. **The resolver blocks on a form disagreement.** Its refusal message says the
   forms coincide when ν is constant and differ otherwise. That is only true if
   the difference is exactly `ν'·u_x`.
2. **Two tests assert a numerical consequence** — `ratio > 0.5` on a sinusoidal
   profile, `ratio == 0.0` exactly on a constant one. Both are pass/fail
   verdicts citing the identity, which is what makes it load-bearing.

## Primary derivation (product rule)

```
d/dx( ν · u_x ) = ν' · u_x + ν · u_xx
```

Subtracting `ν · u_xx` leaves `ν' · u_x`. One line, and it looked right the
first time — which is the situation the oracle discipline exists for. The
v0.37c §6 bound was also one line, also looked right, and had dropped this exact
term.

## Secondary derivation (manufactured solution)

Independent because it shares **no code and no numerical method** with the
benchmark: no spectral differentiation, no finite differences, no `np.gradient`.
Every derivative is written in closed form.

Take

```
ν(x) = a₀ (1 + α sin(k x))        ν'(x) = a₀ α k cos(k x)
u(x) = sin(m x)                   u_x   = m cos(m x)
                                  u_xx  = −m² sin(m x)
```

Then the conservative flux and its exact derivative are

```
ν · u_x        = a₀ (1 + α sin(kx)) · m cos(mx)

d/dx(ν · u_x)  = a₀ α k cos(kx) · m cos(mx)
               − a₀ (1 + α sin(kx)) · m² sin(mx)
```

and the non-conservative operator is

```
ν · u_xx       = − a₀ (1 + α sin(kx)) · m² sin(mx)
```

Their difference is

```
a₀ α k cos(kx) · m cos(mx)  =  ν'(x) · u_x
```

which is the claim. Both sides are evaluated from these closed forms and
compared pointwise; no derivative is approximated anywhere.

## Why this method rather than symbolic expansion

`ANALYTICAL_ORACLE_DISCIPLINE.md` admits three secondary methods.
`symbolic_expansion` would mean adding `sympy` as a runtime dependency for a
single identity, which is a larger change than the thing being checked.
`manufactured_solution` gives the same independence here because the identity is
algebraic — every term has a closed form, so nothing is approximated and there
is no discretization to share.

## What this oracle does **not** cover

- **It does not check the numerical value `1.0353`.** That ratio is a property
  of one profile at one α on one grid, measured and recorded in the v0.38e
  confirmatory freeze. The oracle establishes the *form* of the difference, which
  is what the resolver's behaviour depends on.
- **It does not check that the evaluators implement either operator correctly.**
  That is a separate claim with its own tests.
- **It cannot detect an execution-vs-declaration mismatch.** An oracle checks a
  formula. Whether the code ran the operator it declared is the C-5 class, and
  the resolver plus `test_benchmark_action_semantics_guard.py` are what address
  it.

## Provenance of the error this would have caught

The v0.37c §6 obstruction bound kept `a·u_xx` and dropped `a'·u_x` from
`(a·u_x)_x`. It came in at `0.52`–`1.00` of the observed error — not a bound at
all — and took a pilot block to notice. A manufactured-solution check of the
operator identity would have shown two terms immediately.
