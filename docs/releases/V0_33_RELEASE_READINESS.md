# V0.33 Release Readiness

## Release Target

- package version: `0.33.0`
- git tag: `v0.33.0` (to be cut after review approval; **do not tag until then**)
- package-index publication: deferred until `v1.0` or later

`v0.33.0` is a Git-tag-only release. Do not publish to TestPyPI or PyPI for `v0.33`. PyPI remains targeted at `v0.36`.

## Consolidation Policy

`v0.33.0` consolidates five internal sub-milestones plus one scope-freeze amendment under a single tag per the solo-dev consolidation policy. All six landed on `main` as separate squash-merged PRs; none was tagged individually.

| Sub-milestone | Focus | PR | Merged as |
|---|---|---|---|
| **v0.33e** | golden-numbers regression gate | #110 | `9732c36` |
| **v0.33d** | variable-coefficient data generators | #111 | `64a62fe` |
| *(scope amendment)* | claim-scope narrowing + three-mask model | #112 | `83830a5` |
| **v0.33a** | nonperiodic generator dispatch | #113 | `bbd9cc5` |
| **v0.33b** | overlap-crop finite-transform verification | #114 | `edbd983` |
| **v0.33c** | mask-preserving discovery bridge | #115 | `17664e0` |

Release decision label: `v0_33_0_nonperiodic_interior_symmetry_and_mask_validity`.

## Scope narrowing (title change)

v0.33 was planned as **"Nonperiodic generator support"** and ships as **"Nonperiodic Interior-Symmetry and Mask-Validity Support."**

The original title overclaimed. v0.33a/b establish that a candidate is a symmetry of the **differential equation on interior/overlap rows**. They do **not** establish that it preserves the **boundary-value problem**. A uniform translation on a bounded domain is a domain-changing action — it maps `[0, L]` to `[ε, L + ε]` — and the overlap crop discards exactly the rows that would settle the boundary question.

The `symmetry_claim` diagnostic carries the distinction in machine-readable form over a frozen six-value vocabulary. Both `boundary_value_problem_preserved` and `boundary_value_problem_not_preserved` are **reserved but never emitted**, asserted directly by test — so neither claim can be made accidentally.

## Success criteria

### 1. Nonperiodic generator chain executes end to end — **met**

A caller with a nonperiodic Dirichlet Heat `FieldBatch` runs `fit_translation_generator` → `polynomial_translation_svd` → `verify_translation_generator` and receives strict-JSON payloads at every stage, with correct `boundary_condition_x` / `dispatch_path` / `overlap_fraction` diagnostics.

`run_pysindy_pde_task` remains periodic-only by design: `PySINDyDiscoveryUnsupportedBoundaryError` still fires on nonperiodic fields. The frozen kickoff criterion listed it as part of the chain; v0.33c's non-goals explicitly retain the boundary gate, so the chain terminates at verification for nonperiodic input.

### 2. Mask leakage closed — **met**

For a masked training `FieldBatch` on the default `mask_application="after_differentiation"` path, `regression_row_mask_row_count < observation_mask_row_count`, with the reduction equal to `2 × derivative_stencil_half_width` for a contiguous interior block. The `discovery_task_result` 22-key top-level schema is unchanged.

### 3. Admissibility crash test empirically proven — **met (criterion rewritten)**

Constant candidate on variable-coefficient data (frozen profile `ν(x) = ν₀(1 + 0.5·sin(2πx/L))`) → `residual_l2 ≥ 10×` the constant-coefficient baseline, **18/18 configurations** across grid ∈ {32, 64, 128} × seed ∈ {0, 1, 7} × batch ∈ {1, 2}.

The frozen kickoff criterion named `span_distance`. Measurement during the v0.33d prototype found that `span_distance` inverts to exactly `0.0` in **10 of 18** configurations through the `reference_fallback_used` path — reporting a *perfect* translation generator precisely where the candidate should fail hardest. The metric is additionally bounded above by `√2`, capping any multiplicative gate.

The shipped gate on `residual_l2` (already one of the frozen four score names, so no new surface was required) has **177× headroom** over the 10× threshold; the worst observed ratio was 1772×. `tests/test_v0_33d_variable_coefficient_generators.py::test_span_distance_is_not_a_usable_crash_gate` pins the inverted behaviour so a future selection-policy change prompts revisiting. Measurement record: PR #111.

### 4. No silent numerical drift — **met**

The golden-numbers fixture reproduces on py3.12 and py3.13 within `rtol=1e-6`, `atol=1e-12`, across five periodic and three nonperiodic entries. Any drift requires a named cause.

One regeneration occurred during the arc, with its cause recorded in the fixture's `last_regeneration_reason`: v0.33a added the three nonperiodic entries. Regenerating with `--all` at that point left **every pinned periodic number bit-identical**, confirming v0.33a perturbed no existing numerics.

The bit-exact comparison originally used by the regeneration-integrity test was replaced with tolerance comparison after it failed on the Linux CI runners: the fixture is generated on macOS and replayed on manylinux, and BLAS reduction order differs. Worst observed cross-platform deviation is **1.5e-9** against `rtol=1e-6` — roughly 650× of headroom. No pinned metric is compared with `==` anywhere in the gate.

### 5. Backward compatibility preserved on the user-facing API surface — **met (criterion rewritten)**

All v0.32.0 tests pass **with the exception of seven whose assertions v0.33 deliberately lifts**. Each was rewritten in the PR that superseded it:

| # | Test | Asserted (v0.32) | Superseded by | PR |
|---|---|---|---|---|
| 1 | `test_polynomial_translation_basis_still_rejects_nonperiodic` | `build_translation_basis` refuses nonperiodic input | The basis `{1, t, x, u}` is boundary-condition-agnostic; the gate was incidental to every consumer having been periodic. Renamed `..._accepts_nonperiodic_since_v0_33a`. | #113 |
| 2 | `test_translation_fitter_rejects_nonperiodic_boundary_conditions` | `fit_translation_generator` refuses nonperiodic Heat | v0.33a dispatches to the FD backend with an interior-only shave. Renamed `..._dispatches_nonperiodic_since_v0_33a`. | #113 |
| 3 | `test_translation_fitter_rejects_nonperiodic_burgers_inputs` | Same, for Burgers | Same dispatch. Renamed `..._dispatches_nonperiodic_burgers_inputs_since_v0_33a`. | #113 |
| 4 | `test_adapter_rejects_nonperiodic_field` | `polynomial_translation_svd.fit` refuses nonperiodic input | v0.33a accepts and forwards the dispatch diagnostics; acceptance is not a BVP claim. Renamed `test_adapter_dispatches_nonperiodic_field_since_v0_33a`. | #113 |
| 5 | `test_finite_transform_verification_still_rejects_nonperiodic` | `verify_translation_generator` refuses nonperiodic input | v0.33b dispatches to the overlap-crop path. Renamed `..._dispatches_nonperiodic_since_v0_33b`. | #114 |
| 6 | `test_translation_verification_rejects_nonperiodic_boundary_conditions` | Same, via the public entry point | Same dispatch. Renamed `..._dispatches_nonperiodic_since_v0_33b`. | #114 |
| 7 | `test_underlying_discovery_result_is_embedded_verbatim` | The embedded sibling equals a fresh `summarize_discovery_result` byte-for-byte | v0.33c attaches mask diagnostics under one namespaced key. **Modified in place, not renamed**: the guard now strips `fit_diagnostics["pdelie_mask_diagnostics"]` and still requires byte-for-byte equality on everything else. | #115 |

Entries 1–6 are the same lifted assertion — *the generator layer refuses nonperiodic input* — which is precisely what v0.33 exists to lift. Entry 7 is different in kind: it narrows a published guarantee, and is discussed under **Known narrowings** below.

**User-facing API contracts held.** Frozen four `method_scores` names; `_CONFIDENCE_LABELS` vocabulary; `discovery_task_result` 22-key top-level schema; `pdelie_weak_pde_library_diagnostic` 27-key top-level schema; `VerificationReport.classification` vocabulary `{exact, approximate, failed}`; `SymmetryCandidate` reserved discriminators; root `pdelie` namespace surface — all preserved. No new `summary_type`.

Test-suite total grew from **1418** (v0.32.0) to **1614 collected / 1612 passed / 2 skipped**. Every new assertion is either a v0.33 contract or a strengthening of an existing v0.32 contract.

### 6. Release close mechanically complete — **met on merge**

Version bumped, support matrix authored, release-gate manifest consolidated, CI job renamed `v0_32_0-release-gate` → `v0_33_0-release-gate`. Tag and GitHub Release cut from the release-close merge commit. The `release/v0.31.x` maintenance branch remains frozen at `d5e614e`.

## Known narrowings

Three things this release makes *narrower* than they were, each deliberate:

1. **`underlying_discovery_result` is no longer verbatim without qualification.** Since v0.33c the task attaches mask diagnostics under exactly one namespaced key, `fit_diagnostics["pdelie_mask_diagnostics"]`. Every other field — including every backend-native `fit_diagnostics` entry — remains byte-for-byte what the backend summarizer produced, and the regression guard strips only that key. This was forced: `discovery_task_result` has 22 top-level keys and no top-level `fit_diagnostics`, so the frozen contract's stated location did not exist.

2. **Discovery-bridge mask support is temporal only.** A mask that is not a whole-time-row selection raises `ScopeValidationError`. The bridge maps each x point to a PySINDy feature, so a spatial mask is feature removal rather than row selection — and measured, a single fully-masked x column drives the observation row count to zero.

3. **`v0.33b`'s overlap crop does not activate at default epsilons.** The default `epsilon_values` sweep produces shifts of 0.002–2.04 `dx` while the interior trim removes 4 rows per side; the crop first binds above `|shift| > boundary_trim_width · dx ≈ 0.196`. It is correct and necessary for callers passing large explicit epsilons, but the default nonperiodic verification path is governed by the interior trim.

## Known limitations carried forward

- Nonperiodic fits are resolution-dependent and only Heat is well resolved below `num_points = 256`; Burgers is still at `span_distance ≈ 0.12` at 256. v0.33a emits the honest value plus a low-row warning rather than a hard resolution gate.
- A wrong-basis generator classifies `failed` via the pre-existing `span_distance > span_tolerance` check, not via the overlap-crop error curve; on the error curve alone it scores in the approximate band.
- Residual-side ν(x) support is deferred to v0.34a. Feeding a variable-coefficient `FieldBatch` to a constant-coefficient residual evaluator remains a documented misuse — and is the mechanism of the admissibility crash test.

## Not unlocked

Nonperiodic KdV; nonperiodic PySINDy discovery; nonperiodic weak-form residuals; spatial masks in the discovery bridge; boundary-value-problem preservation claims of any kind; new PDEs; new symmetry methods; multi-D contract widening.

## Process note

Five of six frozen sub-milestone contracts required amendment on contact with measurement, and three of those would otherwise have shipped as silent defects: a gate asserting the opposite of the truth (`span_distance`), a metric reporting near its own ceiling as if valid (the 1-row shave), and a mask contract built on the wrong axis (spatial vs temporal).

Each was caught by prototyping and measuring **before** writing the implementation, not by review of the frozen document. Every amendment is recorded in `docs/design/V0_33_NONPERIODIC_GENERATORS_AND_MASK_PRESERVING_BRIDGE.md` alongside the measurement that forced it, so the reasoning is auditable rather than merely asserted.
