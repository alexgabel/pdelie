# `CoefficientField` — Deliberate Deferral and Revisit Triggers

**Status:** deferred, deliberately. Reviewed at v0.35 day-0; no trigger fires.

**Purpose of this document.** `CoefficientField` is a formalization that has been considered and **not** adopted. Without a record, the next maintainer has to re-derive why — and the natural instinct on encountering a dict of loosely-related string keys is to "clean it up" into a dataclass. This document exists so that instinct meets an argument instead of a vacuum, and so the conditions under which it *should* be adopted are written down in advance rather than argued after the fact.

---

## 1. What exists today

`CoefficientField` **does not exist** anywhere in `src/`, `docs/`, or `configs/`. It is a name from the v0.34a design discussion, never shipped.

What exists instead is an informal convention: variable-coefficient provenance travels in `FieldBatch.metadata["parameter_tags"]`, a flat `dict[str, object]`. As of v0.34.0 it carries eight tags:

| Tag | Introduced | Consumed by |
|---|---|---|
| `nu_profile_kind` | v0.33d | v0.34a dispatch |
| `nu_form` | v0.33d | v0.34a operator selection |
| `c_form` | v0.33d | v0.34a operator selection (advection) |
| `nu_treatment_policy` | v0.33d | v0.34b (extension point) |
| `nu_min`, `nu_max`, `nu_l2_norm` | v0.33d | v0.34a uniform read path |
| `nu_profile_hash` | v0.33d | provenance / fixture identity |

Produced by the v0.33d generators (`data/_coefficient_profiles.py`, 97% coverage); consumed by all three residual evaluators through the single helper `residuals/_variable_coefficient.resolve_variable_coefficient` (97% coverage).

---

## 2. Why it is deferred

The evidence is that the informal shape is **load-bearing without incident**: eight tags × three evaluators × two equation forms, shipped across two releases, with no shape-related defect and 97% coverage on both the producing and consuming module.

The v0.34a work did surface two real bugs — a silent NumPy broadcast over the wrong axis, and a guard that refused the exact combination the v0.33d crash test depends on. **Neither was a schema problem.** A dataclass would have prevented neither: the first was an axis-alignment error inside a computation, the second a validation-logic error. Formalizing `parameter_tags` would have changed nothing about either.

So the case for adoption currently rests on aesthetics, and the case against is concrete:

- **A dataclass is a contract.** Once `CoefficientField` is public, its field set is frozen under the same invariant discipline as `discovery_task_result`'s 22 keys — including for coefficient kinds not yet designed. The flat dict absorbs a new tag in one line; a frozen dataclass absorbs it in a schema amendment.
- **Premature structure encodes today's guesses.** The 2-D contract widening (v0.37+) will change what a coefficient field *is* — multi-axis, possibly anisotropic. A dataclass designed against 1-D scalar `ν(x)` would likely be the wrong shape, and would then need breaking revision rather than extension.
- **The repo's own precedent points this way.** v0.30.1's `SymmetryCandidate` reserved discriminators shipped reserved-but-unconstructable and were hardened in v0.32a without breaking anyone, *because nothing public depended on them yet*. Structure is cheap to add and expensive to retract.

> **The operative rule:** don't formalize what's already load-bearing until measurement shows the informal shape has broken something. Nothing has broken. **Formalizing is currently the risk, not deferring.**

---

## 3. Revisit triggers

Adopt `CoefficientField` when **any one** of these fires. They are deliberately observable — each is a fact about the repo, not a judgement call.

### T-1 · A new evaluator needs more than three coefficient fields

The flat dict works because each PDE carries at most two coefficients (`ν`, `c`) with a small fixed tag set per coefficient. At four or more, the flat namespace requires per-coefficient prefixing (`nu_*`, `c_*`, `d_*`, `k_*`) and the prefix convention becomes an unenforced schema — the point at which a dataclass is doing real work rather than restating a dict.

### T-2 · Coefficient provenance must survive a symmetry action

Today coefficients are consumed under `nu_treatment_policy = "fixed_background"`: the background does not transform. v0.34b introduced the other reading — `co_transforming_background_equivalence`, where `ν` transforms with the field. **If a coefficient must carry its provenance *through* a transformation** — so that a transformed field's tags describe the transformed background rather than the original — that is a lifecycle the flat dict has no way to express, and the transformation rule needs to live with the data.

### T-3 · Coverage on the informal path drops below 90% for two consecutive releases

Currently 97% on both `data/_coefficient_profiles.py` and `residuals/_variable_coefficient.py`. A sustained drop means the informal shape is accumulating untested branches under real use — the empirical signature of a convention drifting past what its consumers can validate. **Two consecutive releases**, not one, so a single busy release does not trigger a refactor.

### T-4 · The 2-D contract widening lands (v0.37+)

Multi-axis coefficient fields almost certainly need first-class treatment: an axis-aware coefficient cannot be described by scalar `nu_min`/`nu_max` summaries, and broadcasting rules stop being expressible as "reshape to `(1, 1, -1, 1)`". This is the trigger most likely to fire, and the one where designing *now* would be most wasteful — the right shape is not knowable until the 2-D contract is.

---

## 4. Status at v0.35

**None of T-1 through T-4 fires.**

- T-1 — v0.35a and v0.35c take raw `np.ndarray` design matrices, not `FieldBatch`; they never read `parameter_tags`. No new evaluator.
- T-2 — v0.35b consumes `FormulaGeneratorFamily`, not coefficient provenance.
- T-3 — both modules at 97%.
- T-4 — 2-D widening is not in v0.35 scope.

**Action for v0.35: none.** Re-check at the v0.35.0 release close, and record the outcome here rather than re-deriving it.
