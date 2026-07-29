# V0.35 Release Readiness

## Release Target

- package version: `0.35.0`
- git tag: `v0.35.0` (to be cut after review approval; **do not tag until then**)
- package-index publication: deferred until `v1.0` or later

`v0.35.0` is a Git-tag-only release. Do not publish to TestPyPI or PyPI for `v0.35`. PyPI remains targeted at `v0.36`.

## Consolidation Policy

`v0.35.0` consolidates three internal sub-milestones under a single tag per the solo-dev consolidation policy, plus one day-0 polish PR.

| Sub-milestone | Focus | PR | Merged as |
|---|---|---|---|
| **day-0 polish** | blocking-toolchain pins + release-guard tightening | #121 | `9c6ae09` |
| **v0.35a** | design-matrix diagnostics (`pdelie.diagnostics`) | #122 | `e3b462e` |
| **v0.35c** | deterministic row selection (`pdelie.design`) | #123 | `04c933c` |
| **v0.35b** | private point-symmetry catalogue | #124 | `2ca6a02` |

Release decision label: `v0_35_0_design_diagnostics_row_selection_and_point_symmetry_catalogue`.

## Success criteria

### 1. Design-matrix diagnostics functional — **met**

`pdelie.diagnostics` reports mutual coherence, leverage scores, the Zhao–Yu irrepresentability constant, and a support-restricted eigenvalue. Every reference is hand-computed or closed-form — `coherence(I₄) = 0`, `leverage(I₄) = 1` everywhere, `RE(I₄, S={0,1}) = 1/4`, `Σhᵢ = rank` — so a NumPy release cannot silently move the reference.

Two measurements changed the contract before it froze:

**All metrics are computed on the column-normalized matrix.** Coherence and leverage are scale-invariant; the irrepresentability constant and restricted eigenvalue are not. On the canonical weak matrix (column norms spanning 1158×) an arbitrary but legitimate rescaling moved the irrepresentability constant from 1.129160013 to **0.2955377896** — across the 1.0 threshold, flipping the reported verdict on identical data. The scaling is fixed and reported in every payload.

**Leverage is computed from the thin SVD, never the hat matrix.** Measured against the analytic value on square full-rank matrices, `diag(A(AᵀA)⁻¹Aᵀ)` errs by **5.634e-01** on Hilbert(8) and **6.258e-01** on Hilbert(10) — against a quantity bounded in `[0, 1]`. The SVD route holds at machine epsilon.

### 2. Row selection functional and core-installable — **met**

`pdelie.design` ships three deterministic methods. `import pdelie.design` loads no scipy or pysindy module, asserted at runtime and by source inspection — the constraint that forced the hand-rolled pivoted QR, since `np.linalg.qr` has no `pivoting` parameter and scipy is not a core dependency.

The hand-rolled Householder QR matches `scipy.linalg.qr(pivoting=True)` exactly on the four canonical matrices whose pivot sequence is determined, and matches on selection quality on all eight. The LINPACK norm-downdate safeguard is load-bearing: across twelve adversarial matrices it changed the permutation in **eight**, and in each the guarded result matched the oracle while the unguarded one did not.

### 3. Point-symmetry catalogue functional — **met (criterion restated)**

The frozen criterion read: *"`pdelie.symmetry.point_symmetry_registry` catalogues known point symmetries per PDE and the classification is exercised end-to-end."*

Two words in that sentence did not survive measurement.

**`point_symmetry_registry` is `_point_symmetry_registry`.** Gate B-2 found no arXiv, DOI, Zenodo, or preprint reference anywhere in the repository. Publishing an API that asserts *"these are the point symmetries of this PDE"* without a citable source would make PDELie the reference for a claim it cannot support. Un-privatising is a one-line change once a write-up exists; retracting a public API is not.

**The classification could not be derived from the design diagnostics alone.** Keying it on `ρ_IR < 1` put all three supported PDEs in the same bucket, and across all ten two-element supports of the canonical heat design only **1 of 10** reached the useful branch. The cause is structural: the irrepresentability constant is a property of the design matrix and support and never consults the symmetry. A classification whose verdict does not depend on the thing being classified is a constant.

Restated criterion: **`pdelie.symmetry._point_symmetry_registry` catalogues 13 known Lie point symmetries across the three supported PDEs, and `classify_point_symmetry` emits the frozen three-value vocabulary from two independently-sourced axes — validity supplied by the caller from the existing verification machinery, usefulness from `pdelie.diagnostics`.** Both non-trivial branches are reachable and tested, the useful one at the measured `ρ_IR = 0.9634`.

> **Scientific note, not a defect.** At the canonical weak-form configuration every supported PDE reports `ρ_IR` above 1.0 — heat 2.743, Burgers 2.194, advection-diffusion 1.178 — so a symmetry that validates there classifies as `valid_but_not_useful`. The wedge this library was built to describe is wide on its own canonical data.

### 4. `SymmetryMethod` contract has multiple entries — **NOT met**

Recorded as a miss rather than restated into a pass.

The criterion assumed catalogue entries would register through `pdelie.symmetry.registry`. They do not, and should not. That registry's `SymmetryMethod` contract requires `fit(field, ...)` — an algorithm that *discovers* a generator from data. A catalogued point symmetry is analytically known and discovers nothing. Registering the catalogue would have meant writing a `fit()` that ignores its input and returns a constant, and would have made `list_symmetry_methods()` report fourteen methods of which thirteen never read the data they are handed.

`SymmetryMethod` therefore still has exactly one built-in, `polynomial_translation_svd`, and its `fit()` semantics are intact.

**Downstream consequence, already applied.** `docs/planning/ROADMAP.md` previously gated the v0.36 Ko-sparse port on *"the v0.35 point-symmetry registry hav[ing] proven the multi-method contract with more than one built-in."* That precondition cannot be satisfied by a catalogue-data registry and has been dropped. The Ko-sparse port is itself what proves the multi-method contract: **v0.36 is unblocked, and is the proof rather than the beneficiary of one.**

### 5. Zero invariant breakage — **met**

Frozen four `method_scores` names; `_CONFIDENCE_LABELS`; `discovery_task_result` 22-key top-level schema; `pdelie_weak_pde_library_diagnostic` 27-key default schema; `VerificationReport.classification`; `SymmetryCandidate` discriminators; `ResidualBatch` top-level shape.

**No new root exports.** `pdelie.__all__` is unchanged; `pdelie.diagnostics`, `pdelie.design`, and the private registry are submodule-only, asserted by test in each.

Three new `summary_type` values are introduced, all on *new* payloads produced by *new* functions: `pdelie_design_matrix_diagnostic`, `pdelie_row_selection_diagnostic`, `pdelie_point_symmetry_catalogue` (plus `pdelie_point_symmetry_classification`). No existing payload changed shape.

### 6. Explicit non-claims held — **met**

No WSINDy claim, no noise-robustness claim, no dataset-recovery claim in any new module or report. Asserted by test in all three sub-milestones: module docstrings and emitted payloads are checked for `wsindy`, `noise_robust`, `noise-robust`, and `noise robustness`.

Every new report carries `diagnostic_only = True` and round-trips through `json.dumps(..., allow_nan=False)`.

## Additions beyond the frozen scope

**Day-0 toolchain pins (#121).** Not in the v0.35 plan. `lint` is a blocking CI job, but `[test]` specified `ruff>=0.6` — an unpinned floor, with CI installing the newest release at run time. Measured on the v0.34.0 tree with source unchanged: ruff 0.9.10 reported 102 errors, 0.14.5–0.15.20 reported 5, and 0.16.0 reported none. `main` was green only because CI happened to resolve 0.16.0. `mypy` carried the same exposure and had already drifted — the `>=1.11` floor was resolving to **2.3.0**, unnoticed because `typecheck` is advisory. Both are now pinned to compatible-release ranges.

**Release-guard tightening (#121).** The README/release alignment guard accepted any of four version strings across two release lines, which is how `v0.33.0` shipped with a README advertising `v0.32.0`. It is now derived from `pyproject` and asserts both the prose mention and the pip-install pins.

## Known limitations carried forward

- `leverage_row_selection` is **not** a conditioning method. Measured on the canonical weak matrix it beat only **8%** of 40 random draws (condition number 2.52e+05 against a random median of 4.52e+04) where the other two beat 100%. It reports influence, and says so in its own warnings.
- `d_optimal_exchange_row_selection` is a local search. It is repeat-stable and contains no RNG, but across three matrices and five random starting sets it reached **four to five distinct optima**. The starting set defaults to the deterministic QR selection and is reported.
- Maximizing the determinant is not minimizing the condition number; the two objectives can disagree, measured on a 200×5 matrix.
- The pivoted-QR permutation agrees with SciPy only where pivoting has signal. On tied-norm designs — the Kahan matrix is the extreme — every tie-break is a valid pivoted QR and SciPy's own choice is not portable across LAPACK builds. Selection *quality* agrees everywhere.
- `classify_point_symmetry` requires caller-supplied validity. It cannot determine on its own whether a symmetry holds on given data.
- The catalogue holds at the canonical parameter values recorded in `CANONICAL_PARAMETERS`; at other parameterizations the generators differ.
- The default (unseeded) weak diagnostic remains nondeterministic, unchanged from v0.34.

## Process note

All three sub-milestones were prototyped and measured **before** their contracts were frozen. Eight of the twelve gates changed what shipped, and three defects would otherwise have shipped silently: the hat-matrix leverage route, the scale-dependent classification verdict, and the irrepresentability constant returning `0.4956551696` from a singular support where `lstsq` had quietly substituted a minimum-norm solution.

Two errors were caught by CI rather than by inspection, and both were the same class — a claim measured on one platform and recorded as universal:

- **v0.35a** asserted `array_equal` between the committed fixture and a fresh rebuild. The fixture is generated on macOS and replayed on manylinux under a different BLAS. This repeats the v0.33e mistake, against an invariant written into this release's own spec.
- **v0.35c** asserted permutation equality with SciPy on all eight canonical matrices, which passed on macOS and failed on Linux for two of them. The pivot sequence is only determined where column norms separate by more than rounding; on the other four, asserting agreement was asserting that two platforms' LAPACK agree.

Both now assert the property that is actually invariant — numerical agreement within the repo-wide `rtol=1e-6` floor, and selection quality — with the exact claim narrowed to where it holds and the boundary tested at both ends.
