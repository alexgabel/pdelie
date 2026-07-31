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

**Open — needs a decision before v0.37.** The repository already ships
`co_transforming_background_equivalence`, but it is a *different construct*: an
**admissibility classification label** from v0.34b
(`src/pdelie/symmetry/admissibility.py`), describing a measured outcome, not a
declared treatment policy. It is frozen into `docs/specs/support_matrix.v0_34.json`
and `support_matrix.v0_35.json`. Renaming it would break two frozen release
specs to align a label with an unrelated field's naming. The recommendation is
to adopt `co_transformable_background` for the **new** `treatment_policy`
vocabulary and leave the v0.34b classification label alone, since the `-ing`
form is correct for a thing that has been observed to happen.

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
`src/`. There is no established standard key to defer to. v0.37 must either pick
one and state it, or accept both with the choice documented per payload family.
Picking one repo-wide is a breaking change to roughly half the payloads and is
not a v0.37 side quest.

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
