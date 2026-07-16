# Valid But Not Useful — the PDELie wedge in one example

**Status:** advisory, not a stable contract. This note documents PDELie's core wedge philosophy — *a valid symmetry candidate can pass every empirical check PDELie ships and still fail to improve downstream utility* — using a hand-authored static JSON fixture (`docs/strategy/data/valid_but_not_useful_example.json`) *and*, since `v0.32c`, a runnable submodule-only example.

The v0.32c runnable example is `pdelie.examples.candidate_to_discovery_workflow` (composed summary: `summarize_candidate_to_discovery_workflow`, `summary_type = "candidate_to_discovery_workflow"`). It ships two deterministic scenarios:

- `scenario="successful"` — end-to-end executable chain (`FieldBatch → run_symmetry_method → validate → verify → materialize orbit (train-only) → run_pysindy_pde_task ×2 → measured downstream comparison`). The evidence-conclusion label is chosen from the measured `absolute_delta` against a fixed threshold; the runner never claims universal downstream improvement.
- `scenario="valid_but_not_useful_static"` — every real stage (field-readiness through split/leakage) runs on the same real fixtures, but the two `discovery_task_result` slots and the `downstream_comparison` block are marked as a provenance-backed static illustration (`extra_metrics.static_illustration = True`) so runtime numbers are never mistaken for a live measurement.

Both scenarios preserve the 15 explicit stages, and the composed summary carries `evidence_conclusion.downstream_gain_claimed = False` as a hard invariant.

## Why this note exists

PDELie's public surface reports two categorically different kinds of facts:

1. **Empirical validity** — did the candidate transform preserve residuals, pass finite-transform verification, agree with a reference span, and clear the invariant/leakage checks? Everything under `pdelie.symmetry.validate_symmetry_candidate`, `pdelie.verification.verify_translation_generator`, `pdelie.invariants.*`, and `pdelie.reporting.summarize_split_leakage_provenance` lives here.
2. **Downstream utility** — did applying the transform to the data actually improve a subsequent PDE-discovery task? Everything under `pdelie.discovery.*` and (from v0.31) `pdelie.tasks.discovery.*` lives here.

The wedge is that these two are **not the same fact**. A candidate can be `validated` in category (1) and simultaneously *degrade* metrics in category (2). PDELie is designed to report both without collapsing them into a single supportability label, precisely because a category-(1) pass can mislead when treated as a category-(2) claim. Everything about the wedge — the vocabulary boundaries, the refusal to add a fifth `discovery_task_supportability_label`, the resistance to a root `pdelie.discover_symmetries` API — traces back to this distinction.

## A concrete example

The fixture at `docs/strategy/data/valid_but_not_useful_example.json` records a hypothetical run using shapes and vocabularies from the actual v0.30.0 public reporting surfaces (`symmetry_candidate_validation_report`, `discovery_bridge_output`, `discovery_result`, `downstream_discovery_workflow`). It is **hand-authored** — not the output of a runtime example — so the reader can inspect it without depending on runtime that hasn't shipped yet, and it is strict-JSON compatible (`json.loads(json.dumps(payload, allow_nan=False)) == payload`).

The scenario:

- A user has a scalar 1D periodic Heat-equation-like `FieldBatch`.
- They supply a synthetic candidate: `xi = 1 + 0.03 * u, tau = 0, phi = 0` — a translation that couples slightly to the field amplitude.
- They validate it against PDELie's `validate_symmetry_candidate` and record every check.
- They then run PySINDy sparse discovery on the **transformed** data via the existing `pdelie.discovery.build_translation_canonical_discovery_inputs → fit_pysindy_discovery` bridge, and independently on the **original** data as a reference.

What PDELie reports (fixture excerpt):

**Category (1) — empirical validity: every check passes.**

```json
"validation": {
  "conclusion": "validated",
  "check_reports": {
    "residual_stability":            {"status": "passed", "residual_max_before": 8.2e-05, "residual_max_after": 9.6e-05},
    "finite_transform_verification": {"status": "passed", "classification": "exact", "error_curve_max": 6.7e-13},
    "reference_span_comparison":     {"status": "passed", "max_principal_angle_rad": 1.4e-06}
  }
}
```

The candidate is `validated` under the v0.16 vocabulary. Finite-transform verification reports `classification == "exact"` (v0.4 vocabulary). Residual, span, and principal-angle checks all pass their configured thresholds.

**Category (2) — downstream utility: the transform makes recovery worse.**

```json
"discovery_result_after_transform": {
  "recovery": {"aggregate": {"support_precision": 0.40, "support_recall": 0.60, "support_f1": 0.48, "exact_support": false, "coefficient_relative_l2_error": 0.83, "exact_count": 0, "partial_count": 1, "failed_count": 0}}
},
"reference_run_without_transform": {"support_precision": 0.90, "support_recall": 0.90, "support_f1": 0.90, "exact_support": true, "coefficient_relative_l2_error": 0.09},
"downstream_gain": {"support_f1_delta": -0.42, "coefficient_relative_l2_delta": 0.74, "sign": "negative"}
```

The transformed-run F1 is 0.42 lower and the coefficient-recovery relative L2 error is 0.74 higher than the reference. On category (2), this candidate is actively harmful.

## What PDELie reports, and what it deliberately does not report

**Reports:**

- both validation results (category 1) and downstream metrics (category 2) side by side;
- a `downstream_gain.sign` field that is `negative` when the transformed run underperforms the reference;
- the vocabulary of each label family exactly as documented in `docs/specs/LABEL_REGISTRY.md`.

**Does not report:**

- a single scalar "useful yes/no" label. There is no `useful_label` field on any v0.30 summary, and there will not be one in v0.31 either.
- a policy that rejects the candidate because downstream metrics got worse. PDELie's job is evidence, not gatekeeping.
- a `supportability_label` that overloads category (1) and (2). The `supportability_label` family (v0.24) is scoped to the weak-form Heat/Burgers report slice; extending it to cover "candidate is useful for downstream" would break the vocabulary boundary documented in `docs/specs/LABEL_REGISTRY.md`.

Downstream tooling can consume this fixture (or its runtime successor) and derive a policy — "reject candidates whose `downstream_gain.sign` is negative" — but that policy is a **downstream decision**, not a PDELie contract. PDELie surfaces the evidence; the caller decides what to do with it.

## Why a static fixture, not a runnable example, right now

A runnable version of this example needs three things that v0.30.0 does not yet publicly expose:

1. **A supplied-candidate → transform → sparse-discovery task path.** The v0.6 `pdelie.discovery.build_translation_canonical_discovery_inputs` heuristically aligns to a peak; a general amplitude-coupled candidate needs the v0.31 task bridge and its `TaskResult` schema (`docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md`).
2. **A reference-run comparison as a first-class field.** The `downstream_gain` block in the fixture is not part of any v0.30 summary; a runnable example would either wire this in via v0.31 or leave the delta computation to the caller.
3. **A policy-consistency guarantee that the negative-gain case doesn't silently downgrade an upstream label.** Today this is guaranteed by the vocabulary rules in `docs/specs/LABEL_REGISTRY.md`; a runnable example must additionally pass a regression test asserting no upstream summary is coupled to `downstream_gain.sign`.

Shipping this as prose + committed JSON now stops the wedge from being a slogan while v0.31 is still design-only. Once v0.31 ships runtime, this note gains a paired `pdelie.examples.symmetry_without_downstream_gain` module that produces a numerically real version of the same fixture from real inputs, and this note updates to reference it. Until then, the fixture is the record.

## Related documents

- `docs/strategy/SCIENTIFIC_POSITIONING.md` — the wedge chain, the refuse-list, and the adjacent-not-competitor taxonomy.
- `docs/specs/LABEL_REGISTRY.md` — the label vocabularies this fixture uses.
- `docs/specs/API_STABILITY.md` — the stable public surface (canonical → validation → discovery bridge → downstream summaries) that produces the shapes.
- `docs/planning/V0_31_DISCOVERY_TASK_BRIDGE_SCOPE.md` — the v0.31a scope-freeze that specifies where the runnable version will live.
