# v0.36a-β — Full Migration Audit: Confirmatory Freeze

**Status:** confirmatory (measured, then frozen)
**Scope:** 5 PDEs × 20 stages = **100 stage comparisons**
**Predecessor:** [`V0_36A_ALPHA_MIGRATION_FREEZE.md`](V0_36A_ALPHA_MIGRATION_FREEZE.md)
**Gate runbook:** [`V0_36A_ALPHA_TO_BETA_RUNBOOK.md`](V0_36A_ALPHA_TO_BETA_RUNBOOK.md)

α audited one PDE through sixteen stages and closed clean. β widens the axis to
five PDEs and adds back the four PySINDy-routed stages α deliberately routed
around. Everything below was produced by running the audit; nothing was
frozen before it was measured twice.

---

## 1. Result

| Label | Count |
| --- | ---: |
| `exactly_preserved` | **38** |
| `numerically_equivalent_within_tolerance` | **53** |
| `intentional_contract_change` | **4** |
| `blocked_missing_legacy_dependency` | **5** |
| `unexplained_regression` | **0** |
| **Total** | **100** |

All five experiments report `all_stages_explained = True`.

Reproducibility: both sides re-exported end to end and compared byte-for-byte
against the first run. Legacy and modern arrays are **bit-identical across runs**,
and the worst kdv residual delta reproduced at `2.260692e-12` exactly.

---

## 2. Scope — what β can audit, and what it cannot

The scope is enumerated by `pdelie.audit.full_migration_scope`, frozen into
[`configs/full_migration/full_migration_scope.json`](../../configs/full_migration/full_migration_scope.json),
and asserted to still match the code by
`test_frozen_scope_manifest_matches_the_code`.

**100 combinations. 10 auditable. 90 blocked.**

| Blocked axis | Why | Introduced |
| --- | --- | --- |
| every non-periodic boundary | v0.22.0 has no `pdelie._boundary`; no generator accepts `boundary_condition_x` | v0.30d / v0.33 |
| `weak_default` | `pdelie.tasks` does not exist in v0.22.0 | v0.31b2 |
| `weak_normalized` | column normalization has no v0.22.0 counterpart | v0.34c |
| `row_selection_diagnostics` | no v0.22.0 counterpart | v0.35c |
| non-periodic KdV | explicitly deferred since v0.30 | ROADMAP |

Nonperiodic data *can* be manufactured on both sides by cropping a periodic
field. It is still blocked, because the legacy side has no boundary-aware
*processing* to compare against — a nonperiodic stage would compare a modern
boundary-aware pipeline to a legacy one that does not know boundaries exist.
That is not a like-for-like comparison, and 90 honestly-blocked combinations are
worth more than 90 faked ones.

---

## 3. The PySINDy finding — β's reason to exist

α routed stages 9–16 around PySINDy so its numerical baseline would not be
confounded by the PySINDy 1.7.5 → 2.1.x version delta. β audits that path
against α's clean baseline.

**Structure is identical on both sides.** Same coefficient shape `(64, 2145)`,
same library size `2145`, same nonzero cardinality.

**Magnitudes diverge on two of five PDEs:**

| PDE | Legacy ‖c‖∞ | Modern ‖c‖∞ | Verdict |
| --- | ---: | ---: | --- |
| `heat_1d` | — | — | identical (both all-zero after thresholding) |
| `burgers_1d` | — | — | identical |
| `reaction_diffusion_1d` | — | — | identical |
| `advection_diffusion_1d` | `3.6695e+10` | `8.9725e+00` | **diverges ~10 orders** |
| `kdv_1d` | `1.2885e+09` | `1.9405e+02` | **diverges ~7 orders** |

Support differs on exactly those two PDEs — 0.067% of entries on
`advection_diffusion_1d`, 0.177% on `kdv_1d` — and is identical on the other
three.

Coefficients of order `1e10` indicate an ill-conditioned STLSQ solve on the
**legacy** side. By the runbook's attribution rule, and given α's clean close,
this is attributable to the **PySINDy version delta**, not to migration
numerical drift. Both stages are labelled `intentional_contract_change` with a
linked release note; neither is a regression.

### Direct evidence for the conditioning diagnosis (Linux replay)

The Linux run turned the ill-conditioning claim from an inference into a
measurement. Comparing each side **against itself** across macOS and Linux —
same data, same library, same seed, only BLAS differs:

| PDE | Side | macOS ‖c‖∞ | Linux ‖c‖∞ | Relative difference |
| --- | --- | ---: | ---: | ---: |
| `advection_diffusion_1d` | legacy | `3.6695e+10` | `3.6869e+10` | **`4.74e-03`** |
| `advection_diffusion_1d` | modern | `8.9725e+00` | `8.9725e+00` | `4.21e-11` |
| `kdv_1d` | legacy | `1.2885e+09` | `1.6451e+09` | **`2.17e-01`** |
| `kdv_1d` | modern | `1.9405e+02` | `1.9405e+02` | `9.86e-12` |

The three all-zero PDEs are bit-identical on both sides on both platforms.

**A solve whose answer moves 22% when the BLAS changes is ill-conditioned.** The
legacy coefficients are not merely large, they are not reproducible; the modern
coefficients agree across platforms to ~`1e-11`. This is independent of the
α-baseline attribution argument and confirms it: the legacy magnitudes are
artifacts of the solve, not properties of the data.

It also sharpens the downstream warning. A legacy coefficient magnitude for
these two PDEs is not a number that would survive being recomputed on different
hardware.

---

## 4. Amendment 1 — α's residuals tolerance did not transfer

**This is the finding β exit gate 6 exists to catch, and it fired.**

α froze `atol = 1e-12` for every `tolerance_numeric` stage. That value was
measured on `heat_1d` alone. Applied to five PDEs it **fails on `kdv_1d`**, which
initially reported as `kdv_1d/residuals → unexplained_regression`.

It is not a regression. The mechanism, measured:

| PDE | ‖c‖∞ | Δc (max abs) | Δresidual (max abs) |
| --- | ---: | ---: | ---: |
| `heat_1d` | `1.000e-01` | `1.775e-16` | `1.829648e-13` |
| `burgers_1d` | `1.000e+00` | `1.147e-13` | `1.317835e-13` |
| `advection_diffusion_1d` | `7.500e-01` | `1.332e-15` | `4.396483e-14` |
| `reaction_diffusion_1d` | `4.718e-01` | `3.331e-15` | `5.614953e-14` |
| `kdv_1d` | **`4.404e+01`** | **`6.281e-12`** | **`2.260692e-12`** |

kdv's fitted coefficient vector is 440× larger than heat's, so the same
*relative* precision yields an absolute coefficient error **35,000× larger**.
That propagates linearly into the residual through `|X| @ Δc` — the bound
`|X|∞ · |Δc|∞ · n_cols = 7.839e-12` covers the observed `2.261e-12`. Meanwhile
kdv's residual *elements* are ~`4e-09`, so the `rtol` term contributes
essentially nothing and the entire allowance falls to `atol`.

> **Error scale is set by the largest intermediate; tolerance scale by the
> smallest output.** An absolute tolerance measured on one PDE cannot transfer
> across a five-PDE axis.

Note the asymmetry that hid this: `coefficients` **passed** on the same run,
because `rtol · ‖c‖ = 4.4e-05` is an enormous allowance when ‖c‖ = 44. The stage
carrying the large error passed; the stage carrying the small output failed.

**Resolution.** A per-stage override on `residuals` only — `atol 1e-12 → 5e-11`,
a **22.1× margin** over the worst of five measured values, spread 51× between
best (`4.396e-14`) and worst (`2.261e-12`). The other nineteen stages keep
`1e-12`. This is a targeted change justified by measurement across the full
axis, not a global loosening to make a red run green.

`test_alpha_tolerance_would_have_failed_on_kdv` asserts both halves: that α's
value fails on kdv, and that it did hold on the PDE α actually measured.

---

## 5. Amendment 2 — α's margin was a heat-only margin

α reported worst DerivativeBatch-routed drift of `5.997790e-10` against
`rtol = 1e-6`, roughly **1,700× of headroom**. Across all five PDEs the worst is
`7.951155e-08` — leaving **12.6×**.

The tolerance still holds. But widening the PDE axis cost two orders of
magnitude of headroom, and α's 1,700× must not be quoted as the arc's margin.
Recorded in `comparison_policy.json` as
`measured_worst_derivative_batch_drift_all_pdes` beside
`alpha_measured_worst_heat_only` so the two are never confused.

---

## 6. Amendment 3 — the α stage-1 reclassification, asserted across all five

`generated_field_statistics` was classified `qualitative_invariant` with a `sign`
invariant. That was a latent cross-platform failure and a check that could not
have caught anything: `std` and `l2` are non-negative by construction, and the
mean is `-4.17959937e-17` — numerical zero, whose sign is rounding noise.

Reclassified to `tolerance_numeric` in α (commit `c85c122`). β asserts it on all
five configs via `test_stage_one_is_tolerance_numeric_not_qualitative`, so it
cannot silently return on a PDE nobody re-checked.

> **Provenance note.** `c85c122` did not reach PR #134 — that PR merged a single
> commit, `14c547f`. The fix was cherry-picked onto the β branch as `397663e`
> and lands with β. Anyone reading α's merge commit alone will not find it there.

---

## 7. β exit gates

| # | Gate | Status |
| --- | --- | --- |
| 1 | Every stage artifact traceable through `StageRecord`'s `parent_stage_ids` | **PASS** — asserted per PDE by `test_no_stage_is_its_own_ancestor_and_every_parent_exists`; every parent resolves, no cycles |
| 2 | No unexplained regression remains | **PASS** — 0 of 100, all five experiments `all_stages_explained` |
| 3 | Every intentional change linked to a release note | **PASS** — asserted by `test_every_intentional_contract_change_links_a_release_note`; enforced structurally by `StagePolicy.__post_init__` |
| 4 | All portable claims pass Linux + macOS | **PASS** — audit replayed on `ubuntu-22.04`, identical labels, see §8 |
| 5 | Migration report reproducible from built wheels | **PASS** — both sides bit-identical across two full re-exports |
| 6 | α conclusions remain valid under generalized tooling | **PASS, and it fired** — α replayed through `run_full_migration.py` reproduces `6 / 9 / 1` exactly; the gate also surfaced Amendment 1 |

---

## 8. Gate 4 — the Linux replay

The original measurements were produced on **macOS 26.5.2 / arm64**, legacy
CPython 3.11.14 + NumPy 1.26.4, modern CPython 3.12 + NumPy 2.x. Under the v0.35
portability taxonomy, 38 `exact_discrete` stages make cross-platform bit-equality
claims and 53 `tolerance_numeric` stages make bounded-agreement claims — none of
which a single-platform run can support. The audit was therefore replayed on
`ubuntu-22.04`.

### Linux replay — attempt 2 (run 30653779754): PASS

**Labels reproduce exactly.** 38 / 53 / 4 / 5, 0 unexplained, all five
experiments `all_stages_explained`. Exit gate 6 reproduced α's frozen `6 / 9 / 1`
on Linux as well.

**Tolerance margins hold, and are reported rather than assumed:**

| PDE | macOS Δresidual | Linux Δresidual | Linux/macOS | Margin vs `atol=5e-11` |
| --- | ---: | ---: | ---: | ---: |
| `heat_1d` | `1.829648e-13` | `2.045031e-13` | 1.12× | 244.5× |
| `burgers_1d` | `1.317835e-13` | `1.529887e-13` | 1.16× | 326.8× |
| `advection_diffusion_1d` | `4.396483e-14` | `4.041212e-14` | 0.92× | 1237.3× |
| `reaction_diffusion_1d` | `5.614953e-14` | `6.081247e-14` | 1.08× | 822.2× |
| `kdv_1d` | `2.260692e-12` | `2.555844e-12` | 1.13× | **19.6×** |

The worst case is `kdv_1d` on Linux at `2.555844e-12`, 13% above the macOS worst.
**The binding margin for the release is therefore 19.6×, not the 22.1× measured
on macOS** — and per the calibration policy in `CONTRIBUTING.md`, that is the
number to quote.

The tolerance is now calibrated on ten measurements (five PDEs × two platforms)
rather than one, and `configs/full_migration/comparison_policy.json` records the
platform axis alongside the PDE axis.

### Linux replay — attempt 1 (run 30651544238): infrastructure failure, no data

The first `workflow_dispatch` run on `ubuntu-22.04` died before producing a
single comparison, at `heat_1d`, the first PDE:

```
ImportError: PySINDy discovery adapter requires pdelie[downstream] or pdelie[test].
```

**Not a portability finding — an orchestrator defect, and the audit had never
run on Linux before.** `uv venv --seed` seeds current setuptools (83.0.0 as
measured), which removed `pkg_resources`. PySINDy 1.7.5 does
`from pkg_resources import DistributionNotFound` at import time, so
`import pysindy` raises `ModuleNotFoundError` and every PySINDy stage dies.
`pip install <wheel>[downstream]` exits 0 regardless, and `-q` prints nothing,
so the failure was silent until an exporter tried to use it.

Measured: setuptools 80.9.0 and 81.0.0 still provide `pkg_resources` (with a
deprecation warning), 83.0.0 does not — consistent with the `setuptools<82` cap
in `docs/design/RUNTIME_COMPATIBILITY_POLICY.md`.

**Why the macOS numbers are unaffected.** Two legacy venvs existed locally. Every
β measurement in this document was produced under `setuptools 68.2.2`, where
`pysindy 1.7.5` imports correctly and reports its version. The orchestrator-built
venv is the one that lacked it. The legacy PySINDy coefficients in §3 are
genuine 1.7.5 output, verified by re-running the import in the venv that produced
them.

**Fix.** `LEGACY_RUNTIME_PINS = ("setuptools==68.2.2",)` applied to the legacy
*runtime* venv in both orchestrators — previously only the *build* venv was
pinned — plus `verify_legacy_downstream()`, which probes `import pysindy` right
after the install and fails there with an actionable message rather than several
minutes and two wheel builds later. Both are asserted by unit tests so the next
regression costs a test run rather than a CI hour.

---

## 9. Non-goals

- No root `pdelie` export; `pdelie.audit` stays a sub-package import.
- No `discovery_task_result` schema change.
- No `pdelie_weak_pde_library_diagnostic` drift beyond the frozen 27/28 conditional.
- No cross-platform bit-exact assertion outside `exact_discrete`.
- No fix to the legacy PySINDy conditioning — v0.22.0 is a frozen tag and the
  divergence is the finding, not a defect to repair.
