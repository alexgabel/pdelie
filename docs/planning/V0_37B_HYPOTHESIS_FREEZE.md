# v0.37b — Hypothesis Freeze: Executable Coefficient-Aware Actions

**Status:** frozen. Written before implementation.

**Scope:** execution and reporting. No benchmark cases, no coefficient profiles,
no α grids — those are v0.37c.

**Tolerances:** still unset. v0.37b reads whatever
`ActionExecutionConfig.numerical_tolerances` supplies and reports which values it
applied. It freezes no threshold of its own. The v0.37c confirmatory freeze sets
them, after a pilot measures what they should be.

---

## 1. Six runtime paths — frozen

| Path | State | Coefficient | Parameter | Meaning |
| --- | --- | --- | --- | --- |
| P-1 | translation | identity | — | state only (the v0.36 path) |
| P-2 | identity | shift | — | coefficient only |
| P-3 | translation | shift | — | canonical co-transformation |
| P-4 | translation | shift **opposed** | — | deliberate obstruction |
| P-5 | identity | identity | rescale | scalar parameter only |
| P-6 | translation | shift | rescale | complete declared action |

**P-4 differs from P-3 only in the sign** of the coefficient shift relative to
the state shift. Because the distinction is a sign rather than a magnitude, it is
decided in `classify_runtime_path` rather than left for a reader to infer from
two offsets in a payload.

A bundle matching none of the six is **refused**, not reported as the nearest
one.

---

## 2. Exactness — and where it stops

The only implemented backend is `exact_grid_shift`: a periodic translation by a
whole number of grid cells, applied with `numpy.roll`. It permutes samples and
introduces **no interpolation error at all**, which is what lets a residual
difference be attributed to the transformation rather than to the resampling
used to apply it.

**A shift that is not an integer multiple of `dx` is refused, never rounded.**
Rounding would silently measure a different action than the one declared, and
the commutation error that followed would describe the rounding.

`fourier` and `linear` are declared in `INTERPOLATION_BACKENDS` and are **not
implemented**; requesting one raises rather than falling back.

Two properties are asserted rather than assumed: a full-period shift is the
identity, and any shift preserves the multiset of samples.

### The baseline the arc rests on

`R(Tu) = T R(u)` for constant-coefficient heat, **measured at `< 1e-12`**. If
this did not hold at machine precision, every obstruction result downstream
would be uninterpretable — a "violation" could be the method rather than the
physics. It is a test, not a remark.

---

## 3. Report schema — frozen

`pdelie_problem_action_residual_relation`, with `summary_schema_version` per the
corrected C-5 measurement.

Four top-level keys:

| Key | Contents |
| --- | --- |
| `summary_type` | the type name |
| `summary_schema_version` | `"0.1"` |
| `scientific_payload` | everything derived from the data |
| `scientific_result_hash` | `semantic_hash` of the payload |
| `execution_metadata` | runtime, backend, seed, provenance |

### Three status fields, not one

| Field | Vocabulary |
| --- | --- |
| `expected_case` | `valid_relation`, `deliberate_obstruction`, `diagnostic_unknown` |
| `observed_relation_status` | `confirmed`, `violated`, `inconclusive`, `blocked`, `no_relation_declared` |
| `benchmark_outcome` | `expected_result_observed`, `unexpected_result_observed`, `not_evaluated` |

P-4 then reads without contradiction:

> `expected_case=deliberate_obstruction` · `observed_relation_status=violated` ·
> `benchmark_outcome=expected_result_observed`

The transformation failed, and that is the result the benchmark wanted. Two
facts, stated separately, instead of one word (`wrong_direction_expected`)
trying to be both an expectation and a verdict.

### `optional_evidence` is nested

One stable field. Absence is a key being absent — there are no
`<name>_available` booleans, which would have made four optional facts into
eight top-level fields.

Keys that may appear: `fitted_operator_diagnostic`, `parameter_deltas`,
`coefficient_field_shift_cells`, `expected_multiplier`.

---

## 4. Determinism — scoped to what can honestly claim it

A report containing a wall-clock duration cannot be byte-for-byte reproducible.
The payload is therefore split, and **only the scientific half is hashed**.

- `scientific_payload` reproduces exactly across runs; `scientific_result_hash`
  is asserted stable across different `runtime_seconds` values.
- `execution_metadata` is checked for **schema stability only**.

A test asserts the two whole reports are *not* equal, with a docstring saying
why that is correct: a whole-dictionary determinism assertion could only pass by
excluding the timing the report claims to carry.

---

## 5. The diagnostic fit is inert, structurally

`FittedOperatorDiagnostic` has **no status field, no boolean verdict and no
threshold**. A test asserts the dataclass exposes no field named `status`,
`holds`, `verdict`, `passed` or `is_symmetry`, and another asserts the emitted
payload contains none of those words.

The analytical decision is computed **first and alone**, from the declared
operator and the numbers. The fit is gathered afterwards and attached as
evidence. It cannot alter the verdict because it is never consulted in reaching
one.

Two adversarial regression tests: residuals related by `R' = 2R` and `R' = 7R`
fit `R' ~ cR` at `r² = 1.0`, and both stay `violated` against a declared
identity relation.

A degenerate fit returns `None` with a named reason, never a fabricated
coefficient — a fit that could not run and a fit that returned zero are
different facts.

**The asymmetry that makes this safe.** For `scalar_multiplier`, `affine` and
`linear_combination_of_derivatives`, a relation *was* declared, so a fit is a
check that can agree or disagree. For `diagnostic_fitted`, nothing was declared,
so a fit is exploration — which is exactly why R-A13 restricts that family to
`no_relation_declared`.

---

## 6. Known limitation

`linear_combination_of_derivatives` is **declared but not synthesised** at
v0.37b. The relation is between derivative terms rather than between the two
residuals directly, and synthesising it needs a `DerivativeBatch` the report
function is not given. It reports `inconclusive` with the raw difference and a
stated reason, rather than guessing.

---

## 7. Non-goals

- No benchmark cases, coefficient profiles or α grids.
- No tolerances frozen.
- No changes to `src/pdelie/residuals/` — asserted by a test that diffs against
  the `v0.36.0` tag and permits only the two v0.37a constant hoists.
- No root export.
