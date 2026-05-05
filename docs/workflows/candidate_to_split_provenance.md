# Candidate to Split Provenance Workflow

This is a V0.29 recipe page over existing public APIs; it adds no runtime surface.

This recipe is the complete candidate-validation path for users who already have a generator candidate and plan to materialize orbit-derived data.

```text
supplied candidate
-> configured validation
-> generator confidence
-> orbit batch provenance
-> split leakage provenance report
```

## Minimal Recipe

1. Represent the candidate as a supported public object or payload.
2. Run `validate_symmetry_candidate(...)` against the intended field and residual evaluator.
3. Keep validation, closure, finite-transform, and residual evidence distinct.
4. Summarize combined evidence with `summarize_generator_confidence(...)`.
5. If materializing translations, keep source and shift indices enabled.
6. Pass user-supplied partition labels to `summarize_split_leakage_provenance(...)`.
7. Treat traceable overlap as a reportable risk, not an automatic benchmark policy.

## Tutorial Page

The rendered notebook `13_candidate_to_split_provenance_workflow.ipynb` shows this path with a known translation generator, one intentionally weak candidate, orbit provenance, and a split-risk report.

## Boundaries

This workflow does not create splits, prevent leakage, train a detector, prove a symmetry, or add arbitrary finite-transform/group-action machinery.
