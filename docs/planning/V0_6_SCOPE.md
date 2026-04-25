# V0.6 Scope

## Summary

`v0.6` is the first **symmetry-guided PDE discovery utilities** release for PDELie.

It does **not** introduce a new numerical regime.  
It does **not** promote KdV to a stable PDE path.  
It does **not** make weak-form methods, operator methods, external dataset ingestion, or broad adapters part of the stable library.

Instead, it asks:

> Can PDELie expose a small, generic public-library layer that supports controlled symmetry-guided PDE discovery workflows in the existing canonical Heat/Burgers regime?

Frozen release definition:

`PDE data -> generator family -> translation-canonical inputs -> sparse PDE discovery -> recovery metrics`

`v0.6` is therefore a discovery-utility release, not a broader data-ingestion release and not a broader numerics release.

---

## Stable Scope

Stable scope for `v0.6`:

- uniform rectilinear grids only
- synthetic PDE data only
- scalar, periodic Heat/Burgers regime only
- polynomial Lie point generator families only
- current `to_pysindy_trajectories(...)` bridge remains the stable discovery entry shape
- discovery recovery metrics
- one thin PySINDy discovery adapter
- one translation-canonical discovery-input builder
- simple robustness utilities
- one compact `v0.6` release gate
- no new stable canonical object

Deferred from stable `v0.6`:

- stable KdV path
- external dataset-ingestion axis
- weak-form methods
- operator methods
- broad adapters
- paper-specific experiment orchestration

---

## Core User Story

`v0.6` should support the generic public-library portion of this workflow:

1. start from canonical Heat/Burgers `FieldBatch` data
2. start from a known, imported/coerced, or discovered translation generator family
3. build translation-canonical discovery inputs
4. run one thin sparse discovery adapter
5. evaluate recovery against a known target equation with generic metrics

Unsupported in stable `v0.6`:

- arbitrary symbolic-term alias resolution
- full differential-invariant generation
- multiple discovery backends
- broad dataset-loading workflows
- manuscript-facing tables, figures, or claim logic

---

## Milestone 1 — Discovery recovery metrics
**Status:** Active

Public runtime API:

- `pdelie.discovery.evaluate_discovery_recovery(target_terms, discovered_terms, *, support_epsilon=1e-8, train_residual=None, heldout_residual=None) -> dict[str, object]`

Frozen input policy:

- `target_terms` and `discovered_terms` are mappings of canonical term string to scalar coefficient
- exact string equality defines support identity
- aliases, symbolic simplification, and term normalization are out of scope
- callers are responsible for consistent naming
- term keys must be non-empty strings
- coefficients must be finite
- non-finite coefficients or invalid term keys raise `SchemaValidationError`
- `support_epsilon` must be finite and non-negative
- support is defined by `abs(coef) > support_epsilon`

Frozen edge-case policy:

- empty target support + empty discovered support = `exact`
- empty target support + non-empty discovered support = `failed`
- non-empty target support + empty discovered support = `failed`
- classification is support-based only:
  - `exact`
  - `partial`
  - `failed`

Frozen outputs:

- support precision / recall / F1
- support exact-match flag
- coefficient L2, relative-L2, and Linf error on union support
- sparsity
- train residual norm if provided
- held-out residual norm if provided
- normalized held-out residual if provided
- equation-string summary

---

## Milestone 2 — Thin PySINDy discovery adapter
**Status:** Pending

Public runtime API:

- `pdelie.discovery.fit_pysindy_discovery(trajectories, time_values, feature_names, *, config=None) -> dict[str, object]`

Frozen scope:

- PySINDy only
- continuous-time only
- target derivative exactly `"u_t"`
- accepts only the current trajectory shape from `to_pysindy_trajectories(...)`
- `feature_names` are the input trajectory columns
- default config is the current deterministic downstream benchmark profile
- this is not a general discovery-backend framework

Frozen extraction policy:

- returns `library_feature_names`
- returns a dense `coefficients` vector aligned 1:1 with `library_feature_names`
- returns sparse `equation_terms`
- default coefficient threshold is `1e-8`
- raw multi-target backend matrices are out of scope

Frozen failure policy:

- missing dependency remains `ImportError`
- invalid inputs remain typed validation errors
- backend fitting failures return `status="failed"` with stable failure information

Frozen returned fields:

- `status`
- `backend`
- `target_derivative`
- `feature_names`
- `library_feature_names`
- `coefficients`
- `equation_terms`
- `equation_string`
- `fit_config`
- `fit_diagnostics`
- `failure_reason` when failed

---

## Milestone 3 — Translation-canonical discovery inputs
**Status:** Pending

Public runtime API:

- `pdelie.discovery.build_translation_canonical_discovery_inputs(field, *, generator_family=None, invariant_spec=None) -> dict[str, object]`

Frozen scope:

- translation/canonical path only
- current invariant-application path only
- scalar variable only
- periodic `x` only
- supports known/oracle translation families
- supports imported/coerced translation families
- supports discovered translation families
- rejects unsupported non-translation families
- no full differential-invariant generation

Frozen alignment behavior:

- alignment is per sample
- alignment uses the initial-time slice only
- alignment uses `values[batch, 0, :, 0]`
- peak index selection uses first-index tie-breaking
- shift is `x[peak_index] - x[0]`
- output shifts are deterministic and reported in batch order

Frozen returned fields:

- `transformed_field`
- `trajectories`
- `time_values`
- `feature_names`
- `generator_metadata`
- `construction_method`
- `alignment_policy`
- `alignment_shifts`
- `provenance`

---

## Milestone 4 — Robustness utilities
**Status:** Pending

Public runtime APIs under `pdelie.data`:

- `add_gaussian_noise(field, *, std_fraction, seed) -> FieldBatch`
- `subsample_time(field, *, stride) -> FieldBatch`
- `subsample_x(field, *, stride) -> FieldBatch`
- `split_batch_train_heldout(field, *, train_size, seed) -> tuple[FieldBatch, FieldBatch]`

Public runtime API under `pdelie.discovery`:

- `summarize_recovery_grid(records) -> list[dict[str, object]]`

Frozen utility policy:

- `FieldBatch` in / `FieldBatch` out
- deterministic noise, subsampling, and splitting
- coords are copied
- masks are preserved
- `NaN` values remain `NaN`
- noise is applied only to finite unmasked values
- subsampling is stride-only
- train/heldout split is deterministic and preserves original order within each split
- no dataframe object
- no plot layer
- no table-rendering system

Frozen preprocess-log policy:

- each utility appends exactly one new plain-dict entry
- each entry includes at least:
  - `operation`
  - `parameters`
- no broader preprocess-log schema is introduced in `v0.6`

---

## Milestone 5 — V0.6 release gate
**Status:** Pending

The `v0.6` release gate remains compact and representative only.

Frozen representative slices:

- one discovery-metrics slice
- one deterministic Heat smoke fit
- one deterministic Burgers smoke fit
- one raw/vanilla input slice
- one oracle/known translation family input slice
- one imported/coerced translation family input slice
- one robustness slice

Frozen release-gate policy:

- no discovery superiority claim
- no exact PySINDy model-string assertions
- no KdV stable-surface addition
- no broad performance claim beyond finite, reproducible, structurally valid outputs

---

## Release Gate

`v0.6` is releasable only if:

- discovery recovery metrics are deterministic and typed
- the thin PySINDy adapter runs reproducibly in the current scalar periodic regime
- translation-canonical inputs are deterministic for representative known/imported translation families
- robustness utilities preserve `FieldBatch` validity, coordinate-copying behavior, mask handling, and preprocess-log behavior
- Heat/Burgers stable paths still pass unchanged
- no new canonical object is introduced
- no stable KdV surface is added
- no weak-form, operator, broad-adapter, or manuscript-facing feature is required

---

## KdV Policy

KdV is explicitly deferred from stable `v0.6` scope.

`v0.5` established only a tests-first feasibility result. That does **not** promote KdV into the stable library.

Stable `v0.6` therefore does **not** include:

- stable third-derivative backend support
- stable synthetic KdV data generation
- stable KdV residual evaluation
- stable KdV discovery coverage
- any stable KdV public API surface

KdV may be reconsidered in a later release only under an explicit scope reset.

---

## Paper / Private Repo Boundary

The public `pdelie` repo may contain only generic discovery utilities in `v0.6`.

Allowed in public `v0.6` scope:

- generic recovery metrics
- one thin PySINDy adapter
- one translation-canonical discovery-input builder
- generic robustness utilities
- compact release-gate coverage

Not part of public `v0.6` scope:

- paper-specific experiment matrices
- manuscript thresholds
- manuscript figures or tables
- representative-aware losses
- private orchestration comparing many methods
- venue-specific presentation logic

---

## Explicit Non-goals

- new canonical discovery objects
- root exports from `pdelie.__init__`
- general discovery-backend framework
- general invariant-theory engine
- stable KdV promotion
- external dataset-ingestion axis
- weak-form methods
- operator methods
- broad adapters
- dataframe / plotting / manuscript layer
- paper-specific experiment matrix, thresholds, figures, or manuscript logic
