# v0.36a-α — Hypothesis Freeze

**Phase:** hypothesis. Written before implementation, per `docs/design/DESIGN_FREEZE_PROCESS.md`.

**Status:** thresholds deliberately unset. No `rtol`, no `atol`, no drift bound appears in this document. They are filled by the pilot and recorded in the confirmatory freeze below, which is empty until then.

---

## Question

Does the modern PDELie pipeline (`v0.35.0`, Python 3.12, NumPy 2.x, PySINDy 2.1.x) reproduce the paper-critical results of the legacy pipeline (`v0.22.0`, Python 3.11, NumPy 1.26.x, PySINDy 1.7.5), stage by stage — and where it does not, is every difference attributable to a documented contract change rather than an unexplained regression?

## Feasibility, established before this freeze

Four preconditions were probed because a hypothesis that assumes an unbuildable legacy is worthless. All four hold, and two contradict the planning assumptions.

| Precondition | Result |
|---|---|
| `v0.22.0` tag exists | yes — `51a34ac`, tagged 2026-05-03 |
| `v0.22.0` builds | **yes, but not with the planned toolchain** — see below |
| legacy runtime installs and runs | yes — pdelie 0.22.0 / numpy 1.26.4 / pysindy 1.7.5 / scikit-learn 1.2.2 on CPython 3.11.14 |
| stages are comparable at all | yes — a field and a derivative were exported from both and compared |

**Correction to the planned legacy toolchain.** The risk mitigation specified `setuptools==65.5.0`, `pip==23.0`, `wheel==0.38.4`. That fails: `v0.22.0`'s own `[build-system]` declares `requires = ["setuptools>=68"]`, so 65.5.0 is *below* its floor and the build aborts with `Missing dependencies: setuptools>=68`. The wheel builds with `setuptools==68.2.2` and `wheel==0.38.4`. **The Docker fallback is not required.**

**Correction to the legacy install command.** `pysindy` and `scikit-learn` are in `v0.22.0`'s `[downstream]` extra, not its core dependencies, and both carry the marker `python_version < '3.12'`. A bare wheel install silently produces a pdelie with no discovery path. The legacy venv must be Python 3.11 and must install `pdelie[downstream]`.

## Quantity measured

For each of the sixteen paper-critical stages, one comparison between the legacy artifact and the modern artifact, producing exactly one `MigrationLabel` from the frozen seven-value vocabulary.

Comparisons are performed by `pdelie.audit.comparators`:

| Comparison class | Function | Decides between |
|---|---|---|
| `exact_discrete` | `compare_exact` | `exactly_preserved` / `unexplained_regression` |
| `tolerance_numeric` | `compare_numeric` | `numerically_equivalent_within_tolerance` / `unexplained_regression` |
| `qualitative_invariant` | `compare_qualitative` | `qualitatively_preserved` / `unexplained_regression` |

`intentional_contract_change`, `platform_specific_difference`, and `blocked_missing_legacy_dependency` are assigned by the comparison **policy**, not derived from array values — they require a human-supplied justification and, for `intentional_contract_change`, a linked release note. A comparator may not promote its own failure into an intentional change.

## Inputs

Enumerated, not described.

**Legacy side** — CPython 3.11.14, `pdelie==0.22.0` built from tag `v0.22.0` with `setuptools==68.2.2` / `wheel==0.38.4`, installed with the `[downstream]` extra, resolving `numpy==1.26.4`, `pysindy==1.7.5`, `scikit-learn==1.2.2`.

**Modern side** — CPython 3.12.13, `pdelie==0.35.0` built from the merge commit of PR #126, resolving `numpy==2.5.1`, `pysindy==2.1.0`, `scikit-learn==1.9.0`.

**Experiments** — two generic configurations, carrying no paper table numbers:

- `configs/alpha_migration/burgers_experiment.json`
- `configs/alpha_migration/hard_heat_experiment.json`

Both fix `seed`, `batch_size`, `num_times`, `num_points`, and the derivative and discovery configuration explicitly. No value is defaulted by either package version.

**Stages** — the sixteen listed in `configs/alpha_migration/*.json` under `stages`, each carrying its `comparison_class` as data rather than as code.

## Decision rule

For each stage *s* with class *c* and comparator output *d*:

- if *c* = `exact_discrete` and the arrays are byte-equal → `exactly_preserved`; otherwise `unexplained_regression` unless the policy supplies a justification;
- if *c* = `tolerance_numeric` and *d* ≤ **⟨PLACEHOLDER: per-stage tolerance⟩** → `numerically_equivalent_within_tolerance`; otherwise `unexplained_regression` unless the policy supplies a justification;
- if *c* = `qualitative_invariant` and the named invariant holds → `qualitatively_preserved`; otherwise `unexplained_regression`.

A stage whose legacy artifact could not be produced at all is `blocked_missing_legacy_dependency` and is excluded from the pass/fail count while being reported.

## Thresholds

**DELIBERATELY UNSET.** Filled by the pilot.

| Stage group | Threshold | Set by |
|---|---|---|
| stages 7–13 (`tolerance_numeric`) | ⟨PLACEHOLDER⟩ | pilot |
| stage 12 (Gram matrix) | ⟨PLACEHOLDER⟩ | pilot — flagged in the plan as the most cross-BLAS-sensitive |
| stages 15–16 (metrics) | ⟨PLACEHOLDER⟩ | pilot |
| `qualitative_invariant` condition-number bound | ⟨PLACEHOLDER⟩ | pilot |

The planning note proposed `rtol=1e-9, atol=1e-12` for the Gram matrix *after* the pilot, and a fallback to `qualitatively_preserved` with `rtol=1e-3` on sign, rank, and condition number. Those are recorded here as **candidate** values with no authority until measurement supports them.

## Invalidation

This hypothesis is **wrong**, not merely unmet, if any of the following holds:

1. **The legacy and modern pipelines do not compute the same quantity.** If a stage's legacy output has no modern counterpart with the same mathematical meaning — not merely a different name — then "did it reproduce" is not a well-posed question for that stage, and the stage must be reclassified as `intentional_contract_change` before any numeric comparison is attempted.
2. **A stage's output is not unique given its input.** If either side's stage depends on an unseeded RNG, a tie-break, or a subspace basis, then no tolerance can make the comparison meaningful and the stage must move to `qualitative_invariant`. `inspect_pysindy_weak_pde_library` is a known instance: it draws domain centers from the global NumPy RNG, which is why v0.34c added a seed and why v0.36e is deferring the default flip.
3. **The legacy artifacts cannot be produced without modifying the legacy tree.** The audit compares what v0.22.0 *was*, not what it can be patched into being.

Outcome (2) is the one the v0.34c experience predicts and the one a threshold miss would otherwise be mistaken for.

## Early observations

Recorded as feasibility evidence, **not** as pilot results. They do not set any threshold.

- The generated field is **bit-identical** across the version gap: `max|Δ| = 0.000e+00` on a `(1, 16, 32, 1)` heat field at `seed=3120`, Python 3.11/NumPy 1.26 versus Python 3.12/NumPy 2.5. If this holds across the enumerated experiments, stage 1 may be reclassifiable from `qualitative_invariant` to `exact_discrete` — a decision for the confirmatory freeze.
- `u_xx` differs by `1.245e-14` relative on the same field, consistent with FFT reduction ordering.
- `DerivativeBatch` is **contract-identical** between v0.22.0 and v0.35.0 — the same six fields — but the entry point moved from `compute_spectral_fd_derivatives` to `compute_derivatives`, and `config` gained `backend_selected_by_boundary_condition` and `backend_selection_reason` from the v0.30d dispatch work. **This is the first identified `intentional_contract_change` and requires a linked release note before stage 7 can be labelled.**

## Non-goals

- No full pipeline coverage — that is β.
- No public paper-specific API.
- No claim about β stages.
- No global artifact store; in-memory plus per-run disk only.
- No modification of the legacy tree, ever. The legacy worktree is checked out detached at the tag and is read-only by convention; exit gate Aα-5 asserts it.

## Gate applicability

`Aα-6` (`grep -r "from pdelie\._" private_paper_repo/` returns empty) references a repository that is **not present in and not reachable from this repository**. It cannot be executed here and is recorded as **not evaluable in this environment** rather than silently passed. Every other α gate is evaluable.

---

# Confirmatory Freeze

**Run:** 2026-07-31, after the pilot, before the tolerances entered any policy.

## Hypothesis status: **survived, with two amendments**

No invalidation clause fired. Both were checked rather than assumed.

## Label distribution across the sixteen paper-critical stages

| label | count |
|---|---|
| `exactly_preserved` | **6** |
| `numerically_equivalent_within_tolerance` | **8** |
| `qualitatively_preserved` | **1** |
| `blocked_missing_legacy_dependency` | **1** |
| `intentional_contract_change` | 0 |
| `platform_specific_difference` | 0 |
| **`unexplained_regression`** | **0** |

`all_stages_explained: true`.

## Measured per-stage relative drift

Legacy `py3.11.14 / numpy 1.26.4 / pysindy 1.7.5` versus modern
`py3.12.13 / numpy 2.5.1 / pysindy 2.1.0`.

| stage | class | result |
|---|---|---|
| `trajectory_ids` | exact_discrete | **exactly_preserved** |
| `split_membership` | exact_discrete | **exactly_preserved** |
| `observation_mask` | exact_discrete | **exactly_preserved** |
| `derivative_validity_mask` | exact_discrete | **exactly_preserved** |
| `regression_row_mask` | exact_discrete | **exactly_preserved** |
| `selected_support` | exact_discrete | **exactly_preserved** |
| `target_y` | tolerance_numeric | `0.000000e+00` |
| `gram_matrix` | tolerance_numeric | `2.067376e-16` |
| `generated_field_statistics` | qualitative_invariant | `5.606564e-16` |
| `coefficients` | tolerance_numeric | `2.282758e-15` |
| `derivatives` | tolerance_numeric | `6.034927e-14` |
| `design_matrix_x` | tolerance_numeric | `6.034927e-14` |
| `residuals` | tolerance_numeric | `6.705474e-14` |
| `per_seed_metrics` | tolerance_numeric | **`5.997790e-10`** |
| `aggregate_metrics` | tolerance_numeric | **`5.997790e-10`** |
| `normalization_vector` | tolerance_numeric | **blocked** — no v0.22 counterpart |

**Overall worst: `5.997790e-10`.**

### Two results worth naming

**The Gram matrix risk did not materialize.** The plan flagged stage 12 as the most cross-BLAS-sensitive and proposed a fallback to `qualitative_invariant` if drift exceeded what a tolerance could cover. Measured, it is the **second-best stage in the whole audit** at `2.067376e-16`. The proposed `rtol=1e-9, atol=1e-12` would have been satisfied with seven orders to spare, and the fallback is not needed.

**The metrics stages are four orders worse than everything else, for a boring reason.** `per_seed_metrics` reports a *relative* residual norm — a ratio of two nearly-equal quantities — so ordinary cancellation amplifies the input drift. `5.998e-10` from inputs at `6.7e-14` is roughly the amplification a ratio of that conditioning predicts. It is error propagation, not a regression, and it is the stage that sets the tolerance.

## Threshold, now set

| threshold | value | justification |
|---|---|---|
| all `tolerance_numeric` stages | **`rtol=1e-6`, `atol=1e-12`** | worst measured drift `5.998e-10` — roughly **1,700x** of margin |

**Deliberately not tightened below the repo floor.** Every stage except two would tolerate `rtol=1e-12`, and it is tempting. But these fourteen stages have been measured on **macOS only**. Tightening a cross-platform claim that has not been measured cross-platform is precisely the mistake v0.33e, v0.35a, and v0.35c each made — three times, in three consecutive releases. The floor holds until the stages run in the portability lane.

## Amendments

**1. The derivative entry-point rename is not an `intentional_contract_change` after all.**

The hypothesis freeze predicted it would be the first such label, because `compute_spectral_fd_derivatives` became `compute_derivatives` and `DerivativeBatch.config` gained two keys from v0.30d dispatch.

Measurement says otherwise: the *outputs* agree at `6.03e-14`, so the stage is `numerically_equivalent_within_tolerance`. The rename is an **API** change, not an output change. It is documented in the experiment config, and labelling the stage as a contract change would have overstated it — the contract that matters for this audit is the numbers, and they held.

**2. Stage 1 is not reclassified to `exact_discrete`, despite the bit-identical field.**

The pilot observed `max|Δ| = 0.000e+00` on the generated field and noted stage 1 might move from `qualitative_invariant`. It stays where it is. What stage 1 exports is *statistics of* the field — mean, std, L2 — not the field itself, and those are computed sums that drift at `5.6e-16`. The field being bit-identical does not make its aggregates bit-identical, and promoting the stage would assert something the exported artifact does not support.

## Reachability

Four of seven labels were reached by a real stage. The three that were not:

| label | why not reached |
|---|---|
| `intentional_contract_change` | see amendment 1 — no stage needed it |
| `platform_specific_difference` | no stage is classed `platform_specific_diagnostic` in alpha scope |
| `unexplained_regression` | **nothing was unexplained** — the desired outcome |

That `unexplained_regression` is unreached is the result, not a coverage gap: its machinery is exercised by the v0.36a-alpha contract tests on synthetic pairs.

## Scope actually audited

Fifteen of sixteen stages compare real artifacts from both versions. The
sixteenth, `normalization_vector`, is blocked because column normalization
arrived in v0.34c and v0.22.0 has no counterpart — comparing it would require
inventing a legacy baseline.

Stages 9-16 build the design matrix from the `DerivativeBatch` rather than
routing through PySINDy. That is deliberate: PySINDy 1.7.5 versus 2.1.x is a
separately-documented contract change, and running the comparison through it
would confound "did the numerics survive the migration" with "did PySINDy
change". Auditing the PySINDy path itself is beta scope.
