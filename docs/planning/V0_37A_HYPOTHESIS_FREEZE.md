# v0.37a — Hypothesis Freeze: Problem-State and Action Contracts

**Status:** frozen. Written before implementation, per
`docs/design/DESIGN_FREEZE_PROCESS.md`.

**Scope:** contracts only. No executor, no commutation-report values, no
benchmark cases. Those are v0.37b and v0.37c.

**Tolerances:** deliberately unset. `ExpectedResidualRelation.tolerance_declaration`
is `None` at v0.37a and is filled at the v0.37c confirmatory freeze, after a
pilot measures what the values should be. Rule R-A13 makes an unset tolerance
mandatory where nothing is declared.

This document also closes the two items
`V0_37_BINDING_DESIGN_CONSTRAINTS.md` marked `resolves_in_v0_37a`.

---

## 1. Frozen dataclasses

| Type | Module | Holds |
| --- | --- | --- |
| `CoordinateFieldAction` | `actions/problem_spec.py` | `family`, `parameters` |
| `CoefficientFieldRef` | `actions/problem_spec.py` | `field_name`, `coordinate_dependency`, `treatment`, `values_artifact`, `analytical_spec` |
| `ProblemInstanceSpec` | `actions/problem_spec.py` | equation, parameters, coefficient fields, axes, domain, boundaries |
| `ExpectedResidualOperator` | `actions/action_bundle.py` | `family`, `parameters` |
| `ExpectedResidualRelation` | `actions/action_bundle.py` | five axes + operator + tolerance |
| `ProblemActionBundle` | `actions/action_bundle.py` | problem, actions, relation, **required** `seed` |

Field lists are frozen. Extending a vocabulary requires a versioned migration,
not an edit.

---

## 2. Closing C-2 — one authority, and a generalised tag

**Decision: generalise, do not invent.**

`nu_treatment_policy: "fixed_background"` already ships. It is emitted by
`heat_1d`, `burgers_1d` and `advection_diffusion_1d` from a shared constant and
asserted by `tests/test_v0_33d_variable_coefficient_generators.py`.
`CoefficientFieldRef.treatment` generalises it from `nu`-specific to per-field,
**keeping `fixed_background` verbatim** and adding `co_transformable_background`.

**Decision: `co_transformable_`, not `co_transforming_`.**

| Form | Asks | Where | Layer |
| --- | --- | --- | --- |
| `co_transformable_background` | *can* this field co-transform? | `CoefficientFieldRef.treatment` | declared capability |
| `co_transformed` | did this transformation say it moved? | `coefficient_relation` | claimed action |
| `co_transforming_background_equivalence` | did it, on this run? | v0.34b `BACKGROUND_TREATMENT_LABELS` | measured outcome |

The v0.34b label is frozen into `support_matrix.v0_34.json` and
`support_matrix.v0_35.json` and is **not** renamed. Renaming it would put a
measured outcome and a declared capability under one word, which is the collapse
C-4 forbids.

**Decision: the bundle is the sole authority for the action.**
`CoefficientFieldRef` carries no action field. `ProblemActionBundle.coefficient_field_actions`
is the only place an action lives, so the two cannot disagree. Every declared
field must appear there — `family="identity"` says *left alone*, because silence
and left-alone are different claims.

---

## 3. Closing C-5 — the schema key, and no `*_available` pairs

**Decision: `summary_schema_version` for both new summary types.**

The original claim that the repository had no convention was measured over the
wrong population — all of `src/`, most of which emits no `summary_type`.
Re-measured over payloads that declare one:

| Key | Payloads with `summary_type` |
| --- | ---: |
| `summary_schema_version` | **34** |
| `schema_version` | 5 |

There is a convention. The five exceptions are v0.36 modules that broke it
without noticing. They are **not** migrated — they are released, and changing an
emitted key is a shape change for a cosmetic gain.

**Decision: nested `optional_evidence`, no paired booleans.** Four
`<name>_available` flags beside four payloads is eight top-level fields, not
four. Absence is expressed by a key being absent. This binds the v0.37b report.

---

## 4. The operator parameter table (R-A12a–e)

Every family declares a closed parameter set, so `parameters` is a contract
rather than an escape hatch.

| Rule | Family | Parameters | Semantics |
| --- | --- | --- | --- |
| R-A12a | `identity` | `{}` | `R'(u) = R(u)` |
| R-A12b | `scalar_multiplier` | `{"multiplier": float}` | `R'(u) = c·R(u)` |
| R-A12c | `affine` | `{"multiplier": float, "offset": float}` | `R'(u) = α·R(u) + β` |
| R-A12d | `linear_combination_of_derivatives` | `{"coefficients": {name: float}}` | keys from the frozen derivative vocabulary |
| R-A12e | `diagnostic_fitted` | `{}` | nothing declared in advance |

Three decisions embedded in that table:

**Empty is a shape, not a gap.** `identity` and `diagnostic_fitted` genuinely
have nothing to declare ahead of time. An empty mapping expresses that; it is
not a placeholder for a spec nobody wrote.

**`affine.offset` is zero-order.** A spatially varying offset would need a
coefficient field or an artifact reference, which is larger than v0.37 needs.
Anyone extending this later is extending, not filling a gap.

**`affine` with `offset == 0.0` is allowed and is not canonicalised.** It
expresses what `scalar_multiplier` expresses, so one relation has two spellings
and two `semantic_hash` values. Rejecting it would break any dose-response sweep
passing through zero — and v0.37c sweeps one. Silently rewriting the family
would make the spec record something other than what was declared. The
non-canonicalisation is stated rather than hidden, and a test pins it.

### The derivative vocabulary

`DERIVATIVE_NAMES = ("u_t", "u_x", "u_xx", "u_xxx")` — the **measured union** of
`_REQUIRED_DERIVATIVES` across all five residual evaluators, not a fresh
vocabulary. Pattern: `u_` + (`t` | `x`×order).

`heat_1d` and `burgers_1d` previously declared theirs inline rather than as a
module constant; both were hoisted in this change so the union is derivable by
one idiom across all five. `heat_1d` keeps `u_x` **out** of its required tuple —
it is needed only on the variable-coefficient path, and that requirement is
raised at the point of use.

A test recomputes the union and fails if it diverges. If a new PDE introduces
`u_xxxx`, the vocabulary is extended deliberately rather than by accident — the
same growth-only pattern as the forbidden-language table.

The `(t, x)` axis naming is hardcoded, which is correct for v0.37's scalar 1-D
scope. Custom axis names arrive with named-axis discipline at v0.40.

---

## 5. R-A13 and the observed-status vocabulary

`diagnostic_fitted` declares nothing, so a fit against it is **exploration**,
not a check — there is no analytical decision for it to contradict. Its only
honest observed status is therefore:

> `diagnostic_fitted` ⟹ `observed_relation_status ∈ {no_relation_declared, blocked}`

This is the cleanest available statement of "the diagnostic fit never overrides
an analytical decision": for this family there is no analytical decision.

**`no_relation_declared`, not `diagnostic_only`.** The string `diagnostic_only`
is already a boolean payload flag in **24 emissions across 16 modules**, meaning
*this payload makes no numerical claim*. Reusing it as an enum value would give
one word two roles. It is also not `inconclusive`: that means the measurement
was attempted and could not decide, whereas this means there was never a
decision to make.

This extends C-4's four-value set by exactly one value, and a test asserts the
extension is exactly one.

---

## 6. The rule table — and why R-A9 is missing

Twelve rules, R-A1 … R-A13, **with R-A9 absent**.

R-A9 coupled `boundary_action` back to a collapsed `relation_type`: if the
boundary was acted on, the collapsed value had to be one of two members. With
five independent axes there is nothing to couple — `boundary_relation` states
what happened to the boundary and `equation_relation` states what happened to
the equation, and neither constrains the other. The rule was a patch for a
coupling that existed only because the axes had been merged.

**The number is not reused.** A table that recycles numbers cannot be cited in a
review six months later.

| Rule | Refuses |
| --- | --- |
| R-A1 | `same_equation` + `fixed` coefficient relation + a non-identity coefficient action |
| R-A2 | `transformed` parameters with no `parameter_action` |
| R-A3 | `co_transformed` with every coefficient action `identity` |
| R-A4 | a `co_transformable_background` field claimed to co-transform with an identity action |
| R-A5 | a `fixed_background` field carrying a non-identity action |
| R-A6 | `unknown` treatment with a confirmable operator relation |
| R-A7 | spatial translation + transformed parameters over an x-dependent `fixed_background` field — **the v0.34b non-equivalence case, 77×–15437×** |
| R-A8 | conservative form with an `affine` residual relation |
| R-A10 | `overlap_crop` domain with a boundary claim other than `interior_only`/`unknown` |
| R-A11 | `co_transformable_background` with no values, no analytical spec and no closed form |
| R-A12 | `equation_invalid` with a confirmable operator relation |
| R-A13 | `diagnostic_fitted` carrying a tolerance |

Every rule has a violating example, and the test asserts each example trips
**exactly** its own rule by matching the message prefix — `validate_action_bundle`
stops at the first firing rule, so a substring match would let an example filed
under one rule actually trip an earlier one and leave its own rule untested.

---

## 7. The seed hard cut

v0.36 accepted an omitted seed with a `FutureWarning`. v0.37 does not: `seed` is
a required positional field, so omission is a `TypeError` from the dataclass
itself rather than a validation error raised later. A non-integer — including
`bool`, which is an `int` subclass — is refused.

This applies to `ProblemActionBundle` only. The v0.36→v0.37 transition for the
weak-form diagnostic is separate and unchanged; per C-1 it must not be
generalised to action families, and `pdelie.actions` still contains no `seed`
outside the bundle.

---

## 8. Non-goals for v0.37a

- No executor. `execute.py` and `commutation_report.py` do not exist, and a test
  asserts it.
- No report values — only the shapes those values will have to satisfy.
- No benchmark cases, no coefficient profiles, no α grids.
- No tolerances.
- No root export. `pdelie.__all__` is unchanged.
- No changes to `src/pdelie/residuals/` beyond hoisting two constants that were
  already there inline.
