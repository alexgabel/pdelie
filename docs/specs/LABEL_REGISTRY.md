# PDELie Label Registry

**Status:** advisory. This registry documents every label vocabulary that PDELie emits or accepts through its stable public reporting surfaces. Adding a new label family requires a scope-freeze note in the release that introduces it. Renaming or removing an existing label is a **breaking change** and is not permitted through a semver-patch release.

The registry exists because label vocabularies proliferate quickly (readiness, confidence, supportability, risk, verification, evidence, policy…) and become uncitable if not centrally documented. Downstream tooling that maps PDELie summaries into experiment trackers, dashboards, or publication tables should consume this registry rather than re-deriving allowed values from source.

## Registry table

Each row is one label family. Columns:

- **Field name** — the JSON field the vocabulary populates.
- **Owner** — the release that froze the vocabulary.
- **Summary type(s)** — the `summary_type` string(s) of payloads that carry the field.
- **Allowed values** — closed set. Downstream consumers must treat any value outside the set as a schema violation.
- **Semantics category** — one of `empirical` (measured from data), `diagnostic` (measured from internal state), `pass_fail` (synthesis of underlying evidence), `supportability` (whether the release supports the configured setup), `decision` (a scope-freeze-time decision recorded in configured evidence).
- **Source reference** — file+line in `src/pdelie/` where the vocabulary is defined.

| Field name | Owner | Summary type(s) | Allowed values | Category | Source reference |
|---|---|---|---|---|---|
| `readiness_label` | v0.21 | `field_batch_readiness`, `xarray_dataset_readiness` | `ready`, `needs_attention`, `not_ready` | supportability | `src/pdelie/reporting/summaries.py:40` |
| `confidence_label` | v0.20 | `generator_confidence` | `strong`, `qualified`, `failed`, `insufficient_evidence` | pass_fail | `src/pdelie/reporting/summaries.py:38` |
| `supportability_label` | v0.24 | `weak_form_supportability` | `supported_existing_slice`, `diagnostic_only`, `failed`, `insufficient_evidence` | supportability | `src/pdelie/reporting/summaries.py:107-110` |
| `risk_label` | v0.23 | `split_leakage_provenance` | `no_detected_overlap`, `traceable_overlap`, `missing_provenance`, `inconclusive` | supportability | `src/pdelie/reporting/summaries.py:99-102` |
| `classification` | v0.4 | `verification_report` | `exact`, `approximate`, `failed` | empirical | `src/pdelie/verification/finite_transform.py:58-61,105` |
| `conclusion` | v0.16 (generator), v0.17 (formula) | `symmetry_candidate_validation_report` | `validated`, `partially_validated`, `failed` | empirical | `src/pdelie/reporting/summaries.py:500-505` |
| `evidence_label` | v0.11+ | `generator_fit_diagnostics`, embedded in `generator_family` fit diagnostics | `direct_svd_in_tolerance`, `reference_fallback`, `mixed`, `unavailable` | diagnostic | `src/pdelie/reporting/summaries.py:31-33` |
| `residual_domain_policy` | v0.30c | `residual_batch` | `full_grid`, `interior_only`, `drop_boundary_width_k`, `not_configured` | diagnostic | `src/pdelie/reporting/summaries.py:1320-1327` |
| component `status` (per-component within confidence, weak-supportability, downstream-workflow synthesis) | v0.10 | embedded in synthesis payloads | `passed`, `warning`, `failed`, `not_configured`, `unavailable` | diagnostic | `src/pdelie/reporting/summaries.py:39` |
| KdV scope decision labels | v0.25 | `kdv_scope_decision_example` | `current_frozen_supported`, `deferred_no_go` | decision | `docs/planning/V0_25_SCOPE.md` + `src/pdelie/examples/kdv_scope_decision.py` |

## Categories in more depth

**empirical** labels are measurements against the data with a documented threshold. `verification.classification == "exact"` requires the finite-transform error curve to remain below `1e-12`; anything above but below the failure threshold is `approximate`; above the failure threshold is `failed`. `symmetry_candidate.conclusion == "validated"` requires every configured check to pass; `partially_validated` means one or more checks were `unavailable` but none `failed`; any `failed` check downgrades the whole candidate to `failed`.

**diagnostic** labels record internal state at report time. `evidence_label` reports which fit path produced the coefficients (`direct_svd_in_tolerance` = SVD produced a solution within the training epsilon; `reference_fallback` = we fell back to the reference generator; `mixed` = span metric agreed but not identity; `unavailable` = fit was skipped). `residual_domain_policy` records the trim rule the residual metrics used. Component `status` is the per-check summary before synthesis.

**pass_fail** labels are the final rollup of pass/fail synthesis. Today `confidence_label` is the only one: `strong` requires every configured component `passed` and evidence present; `qualified` allows warnings on non-critical components with the essential ones still passed; `failed` if any critical component fails; `insufficient_evidence` if too many components are `not_configured`/`unavailable`.

**supportability** labels are the release's statement about whether the configured setup is supported. `readiness_label`, `supportability_label`, and `risk_label` are all in this category — none of them is a claim about numerical correctness beyond what the underlying checks measure; they encode whether PDELie's release scope covers the case.

**decision** labels record scope-freeze-time decisions. The KdV `current_frozen_supported` / `deferred_no_go` pair is the only current instance; future scope-freeze artifacts will use the same shape (e.g. a hypothetical v0.32 The Well feasibility label lattice with `scalar_slice_supported` / `blocked_multichannel_required`, if that scope-freeze lands).

## Vocabulary rules

1. **Do not overload existing families.** Adding `qualified_with_reservations` to `confidence_label` for a new evaluator is a breaking change and requires a new release cycle. Instead, introduce a new family (e.g. a `discovery_task_supportability_label` field on a new `discovery_task_result` summary) and document it here.
2. **Do not reuse the same string across incompatible families.** `failed` appears in five families here, and that's fine because they are distinguishable by the field name; a hypothetical `failed_but_promotable` in one family and a different meaning in another would break downstream consumers.
3. **Every new label vocabulary is a scope-freeze artifact.** New families land through a `docs/planning/V0_NN_SCOPE.md` or `docs/design/*.md` document that names the field, allowed values, category, and semantics. The release-gate manifest (`configs/release_gate_manifest.json`) enforces the phrasing on the scope doc.
4. **Downstream tooling must not derive labels from source.** MLflow / DVC / Weights & Biases integrations should consume this registry (or `docs/specs/support_matrix.v0_30.json` and its successors) rather than reading `src/pdelie/reporting/summaries.py` allowed-value frozensets. This is what protects the registry against silent drift.
5. **v0.31's `discovery_task_result` will reuse existing families, not add a fifth `discovery_task_supportability_label`.** Per the v0.31a scope freeze at `docs/planning/V0_31_DISCOVERY_TASK_BRIDGE_SCOPE.md`, the task-bridge release consumes `readiness_label`, `confidence_label`, and `supportability_label` on embedded sub-summaries and records `warnings: list[str]` at the top level. If a new task-level vocabulary genuinely becomes necessary in v0.31b or later, it will be added here first, then to the schema.

## Planned additive extensions (not shipped)

The following are planned as **additive** fields on existing summaries and are not part of any stable contract yet. They appear here so the label registry can grow in one place rather than fragmenting across release notes.

- **`method_scores: dict[str, float] | None`** on `generator_confidence` (planned for v0.32a or later). Numeric per-component scores (span-distance, residual-l2, error-curve-max) alongside the existing categorical `confidence_label`. Enables downstream calibration studies without breaking the v0.20 frozen `confidence_label` contract.
- **`uncertainty_report: dict | None`** on `generator_confidence` (planned for v0.32a or later). Where a method emits mean/variance/HDR intervals, this is where they land. `None` for point-estimate methods (the current default for `polynomial_translation_svd`).
- **`calibration_report: dict | None`** on `generator_confidence` (planned for v0.32a or later). Reliability-diagram / ECE data where available. `None` for uncalibrated methods.

These three fields are scope-freeze-planned per `docs/planning/PLAN.md`'s v0.32a planning note. Downstream consumers may pre-register keys but must accept `None` until the fields ship as documented public API.

## See also

- `docs/specs/API_STABILITY.md` — the source of truth for which summary functions and their labels are stable public API.
- `docs/specs/SUPPORT_MATRIX.md` — the compact per-PDE support map.
- `docs/specs/support_matrix.v0_30.json` — the current machine-readable release matrix.
- `docs/strategy/SCIENTIFIC_POSITIONING.md` — brief vocabulary-boundaries summary.
