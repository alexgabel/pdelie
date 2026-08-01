# V0.36 Release Readiness

## 1. Release Target

- package version: `0.36.0`
- git tag: `v0.36.0`
- release decision: `v0_36_0_migration_audit_artifact_lineage_and_design_comparison`
- support matrix: [`docs/specs/support_matrix.v0_36.json`](../specs/support_matrix.v0_36.json)

**Git-tag-only.** Do not publish to TestPyPI or PyPI for `v0.36`. An earlier plan
targeted TestPyPI at this release; that was superseded and publication stays
deferred to `v1.0`. v0.36f built and hardened the publish path without exercising
it — see §4.

## 2. Consolidation Policy

One tag for eight sub-milestones, per the solo-dev consolidation policy.

| Sub-milestone | Scope | PRs |
|---|---|---|
| day-zero | freeze process, portability classes, artifact identity, roadmap corrections | #126 |
| v0.36a-α | migration audit: hypothesis freeze, machinery, 16 stages, 1 PDE | #127, #134 |
| v0.36b | artifact identity, observation/differentiation specs, action rules, budget, lineage | #129 |
| v0.36d | sparse-recovery assumption and empirical support-stability reports | #130 |
| v0.36e | three-state seed for the weak-form diagnostic | #132 |
| v0.36c | attainable-design comparison with declared information access | #133 |
| v0.36a-β | full migration audit: 20 stages, 5 PDEs, PySINDy path | #135, #136 |
| v0.36f | publish-path hardening; P0 corrections; v0.37 constraints | #137, #138 |

Submodule-only surface throughout. `pdelie.__all__` is unchanged, no existing
payload changed shape, and no new PDE was added.

## 3. Success Criteria

| # | Criterion | Outcome |
|---|---|---|
| 1 | Legacy-vs-modern comparison across paper-critical stages | **Met, and widened.** α: 16 stages, 1 PDE. β: 100 comparisons, 5 PDEs, 0 unexplained regressions. |
| 2 | Seven-label migration vocabulary with comparator/policy split | **Met.** Comparators assign only evidence-backed labels; the other three require human justification, and `intentional_contract_change` additionally requires a linked release note. |
| 3 | No-pickle interchange | **Met.** `.npy` + strict JSON, `allow_nan=False`, asserted by test. |
| 4 | Content-addressed artifact identity | **Met.** `pdelie.artifact.semantic_hash` is the single canonical hash; stores are per-run, never global. |
| 5 | Migration result reproducible from built wheels | **Met.** Both sides re-exported end to end, bit-identical. |
| 6 | Portable claims verified on Linux + macOS | **Met, after a restatement.** See amendment A-3. |
| 7 | Design comparison with declared information access | **Met.** Six mandatory flags; a missing flag raises rather than defaulting. The bare word "oracle" is deliberately not a method class. |
| 8 | Explicit-seed transition for the weak-form diagnostic | **Met.** Three states — explicit int, explicit `None`, omitted — with `FutureWarning` on omission and the 27/28-key conditional unchanged. |
| 9 | TestPyPI release candidate | **Not met — deliberately withdrawn.** Superseded by the deferral to `v1.0`. The path was built and hardened instead; see §4. |

### Amendments recorded during the arc

**A-1 — stage 1 was misclassified, and the check could not have caught anything.**
`generated_field_statistics` was frozen as `qualitative_invariant` with a `sign`
invariant. `std` and `l2` are non-negative by construction and the mean is
`-4.17959937e-17` — numerical zero, whose sign is rounding noise. It was a latent
cross-platform failure that had not yet fired. Reclassified to
`tolerance_numeric`; β asserts it on all five configs so it cannot silently
return on a PDE nobody re-checked.

**A-2 — α's residuals tolerance did not transfer to five PDEs.** `atol = 1e-12`
was calibrated on `heat_1d` alone and fails on `kdv_1d`. Not a regression: see
finding 2 in §6 for the mechanism. Resolved with a per-stage override on
`residuals` only — `1e-12 → 5e-11` — leaving the other nineteen stages
untouched. Targeted and measured, not a global loosening to make a red run green.

**A-3 — α's reported margin was a heat-only margin.** α reported worst drift
`5.997790e-10` against `rtol = 1e-6`, roughly 1,700× of headroom. Across five
PDEs the worst is `7.951155e-08`, leaving 12.6×. Then the Linux replay moved the
binding residual margin from macOS's 22.1× to **19.6×**. Both the tolerance and
the release quote the binding number.

**A-4 — the first Linux run of the audit failed on infrastructure, not
portability.** `uv venv --seed` seeds setuptools 83.0.0, which removed
`pkg_resources`; PySINDy 1.7.5 imports it at module load. Only the *build* venv
was pinned, never the *runtime* venv, and `pip install <wheel>[extra]` exits 0
either way. Fixed with `LEGACY_RUNTIME_PINS` plus a probe that fails at the venv
rather than inside an exporter two wheel builds later.

## 4. Additions Beyond Frozen Scope

**Publish-path hardening (v0.36f).** `publish.yml` was the only workflow in the
repository still using floating action tags — and the only one granted
`id-token: write`. All five actions are now SHA-pinned, and the build job writes
`SHA256SUMS` which each publish job verifies before upload. The plan asked for a
second `publish-testpypi.yml`; hardening the existing workflow was chosen
instead, consistent with the single-workflow shape
[`PUBLISHING.md`](PUBLISHING.md) already required. All six install
configurations were verified from a locally built wheel outside the checkout.
The 19 contract tests are mutation-tested.

**`coefficient_relation` (v0.36b, late).** A fifth relation axis on
`ProblemActionSpec`. See finding 3 in §6.

**`docs/planning/V0_37_BINDING_DESIGN_CONSTRAINTS.md`.** Six design constraints
pre-registered before v0.37 implementation, with a status vocabulary and a named
resolution vehicle. Four of the six bind a design that does not exist in this
repository yet; they are recorded so it arrives already constrained.

## 5. Known Limitations Carried Forward

- **The audit is `workflow_dispatch`-only.** It builds two wheels across a major
  Python boundary and runs ten pipelines. Its result is evidence to read, not a
  gate every PR passes. The contract tests that *do* gate every PR are separate.
- **Five stages are `blocked_missing_legacy_dependency`,** one per PDE. v0.22.0
  has no counterpart for weak-form column normalization. Blocked is neither
  passed nor regressed, and the taxonomy keeps them distinct.
- **90 of 100 scope combinations are blocked.** Every non-periodic boundary, the
  weak-form paths, and row-selection diagnostics have no v0.22.0 counterpart.
  Each blocked combination names its reason and the release that introduced the
  gap.
- **The residuals tolerance is `5e-11` with a 19.6× binding margin.** Measured on
  ten points (5 PDEs × 2 platforms). It is not a general-purpose tolerance.
- **C-2 and C-5 ship open,** marked `resolves_in_v0_37a`. Neither names a defect
  in shipped code; both are answered by the v0.37a hypothesis freeze.
- **The legacy PySINDy conditioning is not fixed.** `v0.22.0` is a frozen tag and
  the divergence is the finding, not a defect to repair.

## 6. Process Note — three findings that outlived the release

These are the substantive contribution v0.36 makes beyond feature delivery.
Everything above is context for them.

### Finding 1 — legacy STLSQ conditioning

Under PySINDy 1.7.5 the legacy solve produced coefficient magnitudes of order
`1e9`–`1e10` fitting a 2145-column library on `advection_diffusion_1d` and
`kdv_1d`. The modern stack produces `8.97e+00` and `1.94e+02` on the same data
and the same library.

Structure is preserved: same coefficient shape, same library size, same nonzero
cardinality, and support identical on three of five PDEs.

The Linux replay turned the diagnosis from inference into measurement. Comparing
each side *against itself* across macOS and Linux — identical data, library and
seed, only BLAS differing — the legacy solve moves by `4.74e-03` and `2.17e-01`;
the modern solve by `4.21e-11` and `9.86e-12`.

> **A solve whose answer moves 22% when the BLAS changes is ill-conditioned.**

**Scope for anyone citing this work.** Coefficient *magnitudes* for those two
PDEs under the 1.7.5 line rest on a numerically fragile solve and would not
survive being recomputed on different hardware. *Regressor-selection* results are
not implicated — the structure is preserved on the modern stack. The difference
is fit conditioning, not a modeling change.

### Finding 2 — the tolerance-calibration pattern, five instances

| Release | Calibrated on | Recorded as | Caught by |
|---|---|---|---|
| v0.33e | macOS-generated fixture | cross-platform golden | Linux CI |
| v0.35a | macOS fixture vs Linux rebuild | `array_equal` | both CI versions |
| v0.35c | macOS-only SciPy permutation | exact permutation equality | pre-merge review |
| v0.36a-α | `heat_1d` residuals | universal `atol=1e-12` | β exit gate 6 |
| v0.36a-β | macOS `kdv_1d` | a 22.1× margin | the Linux replay |

Platform and input datum are the same axis: both are "the one thing it was
measured on."

The mechanism, from A-2: kdv's fitted coefficient vector has magnitude
`4.404e+01` against heat's `1.000e-01`, so the same *relative* precision yields
an absolute coefficient error 35,000× larger, propagating through `|X| @ Δc` into
a residual whose own elements are ~`4e-09`.

> **Error scale is set by the largest intermediate; tolerance scale by the
> smallest output.**

Note the asymmetry that hid it: `coefficients` **passed** on the same run,
because `rtol · ‖c‖` is an enormous allowance when ‖c‖ = 44. The stage carrying
the large error passed; the stage carrying the small output failed.

Encoded as policy in `CONTRIBUTING.md` (repository root): a numerical
tolerance must be calibrated on **at least two inputs** with the spread reported,
**or** named for its calibration input (`HEAT_1D_RTOL`, `MACOS_ATOL`). A
single-input tolerance under a generic name is a review-blocking violation —
that is how all five reached CI. Margins inherit the rule.

### Finding 3 — coefficient handling has three layers

Three shipped vocabularies describe the same physical question, introduced three
releases apart, and were unrelated to one another:

| Layer | Asks | Where | Since |
|---|---|---|---|
| Declared capability | what may this background do? | `nu_treatment_policy` | v0.33d |
| Claimed action | what does this transformation say it did? | `coefficient_relation` | **v0.36b** |
| Measured outcome | what happened when we computed the residual? | `BACKGROUND_TREATMENT_LABELS` | v0.34b |

**v0.36 completed the middle layer.** Before it, `coefficient_field_action` could
be attached while the claim it implements — background `fixed` or
`co_transformed` — had nowhere to live, so a claim could only be *inferred from
the presence of an action*. The v0.34b module already knew the stack existed; its
docstring says it "extends the v0.33d `nu_treatment_policy` value
`fixed_background` with the equivalence reading."

This also gave the v0.34b measurement a home. That translating a
variable-coefficient problem is an *equivalence transformation* unless the
background travels with it — measured at 77× to 15437× separation in residual L2
— was not expressible in the type built to express it.

The layers must not be merged: layer 1 is a property of the *data*, layer 2 is a
*claim*, layer 3 is an *observation*. A claim of `co_transformed` against a field
declared `fixed_background` is a cross-layer contradiction and must be refused.

v0.37's expected/observed split adopts this pattern rather than reinventing it:
layers 1 and 2 are the expected case, layer 3 is the observed status.

## 7. Verification

| Gate | Result |
|---|---|
| test suite | 2356 passed, 3 skipped |
| mypy | 147 errors in 29 files — baseline unchanged |
| ruff | clean |
| docs | `sphinx-build -W` clean |
| migration audit, macOS | 100 stages, 0 unexplained |
| migration audit, Linux | 100 stages, 0 unexplained, labels identical |
| α replay under β tooling | `6 / 9 / 1` reproduced exactly |
