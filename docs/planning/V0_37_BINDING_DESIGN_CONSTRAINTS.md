# v0.37 — Binding Design Constraints (pre-registered)

**Status:** binding. Written *before* v0.37 implementation, as a hypothesis
freeze in the sense of `docs/design/DESIGN_FREEZE_PROCESS.md`.

These six constraints were raised as P0 corrections against a v0.37 design
proposal. **That proposal is not in this repository** — the types it names
(`ProblemActionBundle`, `CoefficientFieldRef`, `ActionExecutionConfig`,
`ExpectedResidualRelation`, and the residual commutation report) do not exist in
any file here. The constraints are recorded anyway, because they are
self-contained and binding regardless of where the proposal lives: v0.37 must
satisfy them, and a design that violates one is rejected at review rather than
discovered at implementation.

Where a constraint already holds in shipped code, that is stated. Where acting
on it required a change, the change is linked.

---

## C-1 — A mathematical action carries no seed

`u(t,x) ↦ u(t,x−τ)` has no random seed. Embedding one in an action's immutable
mathematical specification makes deterministic actions appear stochastic,
changes semantic hashes for no mathematical reason, couples the weak-library RNG
transition to every future action family, and contaminates caching and equality.
It will get worse for exact symbolic and group actions.

**Three layers, not one:**

| Layer | Holds |
|---|---|
| action specification | the pure mathematical/declarative action |
| execution config | interpolation backend, tolerances, optional stochastic settings |
| run manifest | the actual seed value and RNG provenance |

```python
@dataclass(frozen=True)
class ActionExecutionConfig:
    interpolation_backend: str
    numerical_tolerances: ToleranceDeclaration
    seed: int | None
    deterministic_expected: bool
```

A deterministic action is `seed=None, deterministic_expected=True`.

**The v0.36→v0.37 explicit-seed transition applies only to the weak-diagnostic
API that actually uses an RNG** — `inspect_pysindy_weak_pde_library`, whose
`FutureWarning` is already live. It must not be generalised to action families.

**Status: already satisfied.** `pdelie.actions` contains no `seed` anywhere.
`ProblemActionSpec` is purely declarative. The constraint binds the *proposal*,
not the shipped code.

---

## C-2 — One authority for a coefficient action

A coefficient-field *reference* describes the field. The action bundle is the
**only** authority for the transformation applied to it. Holding a
`coordinate_field_action` on the reference *and* a `coefficient_field_actions`
mapping on the bundle permits direct contradiction — reference says identity,
bundle says shift — with no rule to decide which wins.

```python
@dataclass(frozen=True)
class CoefficientFieldRef:
    field_name: str
    coordinate_dependency: tuple[str, ...]
    treatment_policy: Literal[
        "fixed_background", "co_transformable_background", "unknown"
    ]
    values_artifact: ArtifactRef | None
    analytical_spec: AnalyticalFieldSpec | None
```

Note `co_transformable_background`, not `co_transforming_background`: the
reference declares what the field *may* do. Whether it actually co-transforms is
the action bundle's claim.

**Status: no duplication exists to remove.** `ProblemActionSpec` holds a single
`coefficient_field_action: ActionRef | None`, and there is no second location.
`CoefficientFieldRef` does not exist.

**But `treatment_policy` partially does, and must be generalised rather than
invented.** `nu_treatment_policy: "fixed_background"` is a **v0.33d generator
tag**, emitted by `heat_1d`, `burgers_1d` and `advection_diffusion_1d` from the
shared constant `NU_TREATMENT_POLICY_FIXED_BACKGROUND` and asserted by
`tests/test_v0_33d_variable_coefficient_generators.py`. A new
`CoefficientFieldRef.treatment_policy` must extend that tag from `nu`-specific
to per-field, keeping `fixed_background` as a value, or the repository will
carry two names for one declaration.

**Open — needs a decision before v0.37.** `co_transforming_background_equivalence`
is a *third construct*: an **admissibility classification label** from v0.34b
(`src/pdelie/symmetry/admissibility.py`) describing a measured outcome, frozen
into `docs/specs/support_matrix.v0_34.json` and `support_matrix.v0_35.json`.
Renaming it breaks two frozen release specs to align a label with an unrelated
field. Recommendation: adopt `co_transformable_background` for the **new**
declarative vocabulary and leave the v0.34b label alone — the `-ing` form is
correct for something that has been observed to happen.

See **C-3a** below for how the three fit together.

---

## C-3 — Relation axes stay independent

Boundary preservation is orthogonal to equation equivalence. A transformation
can be an equivalence transformation with the boundary preserved, or an
equivalence transformation with the boundary destroyed; one collapsed
`relation_type` enum cannot say which.

Equivalence transformations are a standard distinction in group classification
of variable-coefficient PDE classes — they map members of a class into one
another — and must not be compressed into same-equation symmetry labels.

Required axes: `equation_relation`, `parameter_relation`, `coefficient_relation`,
`domain_relation`, `boundary_relation`, each with its own closed vocabulary.

**Status: shipped, and the missing axis has been added.** `ProblemActionSpec`
has carried four independent axes since v0.36b with the required
`same_equation` / `equivalence_transformation` / `equation_invalid` distinction.
`coefficient_relation` was genuinely absent and was added in `ea20e14`, together
with a seventh interaction rule refusing `co_transformed` with no
`coefficient_field_action`.

**Deviation:** the axes use `unknown`, not `unverified`. Four sibling axes
already used `unknown`; five axes disagreeing on the word for the same state
would be worse than matching the proposal's wording.

---

## C-3a — The background question has three layers, and they already exist

This is the cross-reference between the new `coefficient_relation` axis and the
constraints above. It is the part most likely to be got wrong twice, because
three shipped vocabularies describe the same physical question at different
layers and were introduced three releases apart.

| Layer | Asks | Where it lives | Vocabulary |
|---|---|---|---|
| **1. Declared capability** | What may this background do? | v0.33d generator tag `nu_treatment_policy` | `fixed_background` (+ `co_transformable_background`, to be added by C-2) |
| **2. Claimed action** | What does *this transformation* say it did? | v0.36b `ProblemActionSpec.coefficient_relation` | `fixed`, `co_transformed`, `not_applicable`, `unknown` |
| **3. Measured outcome** | What actually happened when we computed the residual? | v0.34b `BACKGROUND_TREATMENT_LABELS` | `fixed_background_same_target_symmetry_failed`, `co_transforming_background_equivalence`, `inconclusive_background_separation` |

The three are **not** synonyms and must not be merged. Layer 1 is a property of
the *data*. Layer 2 is a *claim* made by a transformation. Layer 3 is an
*observation* produced by measurement. The v0.34b module already knew this — its
docstring says it "extends the v0.33d `nu_treatment_policy` value
`fixed_background` with the equivalence reading" — but until `coefficient_relation`
was added there was **no layer 2**, so a claim could only be inferred from the
presence of an action.

**Binding rules for v0.37:**

1. A spec claiming `coefficient_relation="co_transformed"` against a field whose
   declared `treatment_policy` is `fixed_background` is a **cross-layer
   contradiction** and must be refused. This is the real content of C-2:
   duplication is not two fields holding the same value, it is two layers
   permitted to disagree with no rule to resolve them.
2. Layer 3 must never be written into a `ProblemActionSpec`. A measured outcome
   on a declarative spec is exactly the expected/observed collapse C-4 forbids.
3. Layers 1 and 2 are `expected_case` inputs in C-4's vocabulary; layer 3 is
   `observed_relation_status`. The split C-4 asks for is already prefigured by
   the v0.33d/v0.34b division — v0.37 should adopt it, not reinvent it.

---

## C-4 — Expected case, observed status and benchmark outcome are three fields

Statuses like `confirmed` / `violated` / `diagnostic_only` /
`wrong_direction_expected` mix what the benchmark *expected*, what the residual
computation *observed*, and whether the report is diagnostic. In particular, a
deliberate obstruction must not receive a special success-like verification
status.

| Field | Vocabulary |
|---|---|
| `expected_case` | `valid_relation`, `deliberate_obstruction`, `diagnostic_unknown` |
| `observed_relation_status` | `confirmed`, `violated`, `inconclusive`, `blocked` |
| `benchmark_outcome` | `expected_result_observed`, `unexpected_result_observed`, `not_evaluated` |

The wrong-direction case is then unambiguous:
`expected_case=deliberate_obstruction`, `observed_relation_status=violated`,
`benchmark_outcome=expected_result_observed`.

This mirrors the split the migration audit already enforces: comparators assign
only evidence-backed labels, and policy assigns interpretation — a comparator
may not promote its own failure into an intentional change.

**Status: nothing to change.** No commutation report exists in this repository.

---

## C-5 — Nest optional evidence; use one schema key

Four paired `*_available` booleans plus four payloads is **eight** top-level
fields, not four. Prefer nesting:

```python
optional_evidence = {
    "parameter_deltas": ...,
    "coefficient_field_deltas": ...,
    "expected_multiplier": ...,
    "fitted_operator_diagnostic": ...,
}
```

One stable top-level field, no paired availability booleans — absence is
expressed by the key being absent.

**Open — the repository has no single convention.** Measured on the current
tree: `schema_version` appears 37 times and `summary_schema_version` 36 times in
`src/`. There is no established standard key to defer to. A repo-wide rename on
the belief that one of them is "the project standard" would break roughly half
the payloads, including `discovery_task_result`.

**The rule, therefore, is per payload:** preserve whatever key a payload already
uses; choose deliberately, and state the choice, only for a genuinely new
payload.

The v0.37 report is a new payload, so it chooses freely. So is anything emitted
by `pdelie.actions`, which currently carries **no schema key at all** —
`ProblemActionSpec.as_dict()` has none. That is a clean slate rather than a
migration, and whichever key it adopts should be stated here when it does.

---

## C-6 — Hash the science, not the run

A report cannot be byte-for-byte deterministic *and* contain `runtime_seconds`.
Split them:

- `scientific_payload` — hashed as `scientific_result_hash`
- `execution_metadata` — runtime, timestamps, host, PID, hardware

**Nothing nondeterministic may enter the hashed payload.** Test that the
scientific payload is deterministic and that the execution-metadata *schema* is
stable — never whole-dictionary byte equality.

This is the v0.36a portability taxonomy applied to reports: `exact_discrete` for
the scientific payload, `platform_specific_diagnostic` for execution metadata,
which is reported and never asserted.

**Status: nothing to change.** No such report exists here.

---

## Summary

| # | Constraint | Applies to shipped code? |
|---|---|---|
| C-1 | no seed in an action spec | already satisfied — no seed in `pdelie.actions` |
| C-2 | one coefficient-action authority | no duplication exists; rename decision open |
| C-3 | independent relation axes | shipped; `coefficient_relation` added in `ea20e14` |
| C-4 | expected vs observed vs outcome | no commutation report exists |
| C-5 | nested optional evidence; one schema key | no report exists; repo key convention is genuinely split |
| C-6 | hash science, not runtime | no report exists |

**Four of six bind a design that is not in this repository.** They are recorded
here so that when it arrives, it arrives already constrained.
