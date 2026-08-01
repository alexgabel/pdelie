# v0.37c — Hypothesis Freeze: Six-Case Admissibility Benchmark

**Status:** frozen. Written before the pilot runs.

**No tolerance value appears in this document.** Every threshold lives in
`docs/design/v0_37c_confirmatory_freeze.md`, which may only be written after the
pilot passes PS-1, PS-2 and PS-3. A tolerance frozen here would make the pilot
theatre.

---

## 0. Glossary — three layers, three vocabularies

The benchmark touches all three layers of the coefficient question, and they use
different words on purpose. Conflating them is the single most likely
misreading of this document.

| Layer | Asks | Vocabulary | Since |
| --- | --- | --- | --- |
| Declared capability | *Can* this background co-transform? | `fixed_background`, `co_transformable_background` | v0.33d tag, generalised v0.37a |
| Claimed action | Does *this transformation* say it moved? | `fixed`, `co_transformed` | v0.36b `coefficient_relation` |
| Measured outcome | Did it, *on this run*? | `co_transforming_background_equivalence`, `fixed_background_same_target_symmetry_failed` | v0.34b |

A case declares with the first two and is judged by the third. The `-able` form
is a capability; the `-ing` form is an observation.

---

## 1. Pre-registration reconnaissance — disclosed

Before this freeze was written, an exploratory run measured the six cases in
order to (a) determine each case's `expected_operator_family` and (b) establish
the *analytical form* of the obstruction. Both were needed to write this
document at all, and both are reported here rather than presented as pilot
findings.

**What it established.** Co-transformation is *exact* under `exact_grid_shift`,
and every obstruction is *exactly first order in α* — `error/α` was constant to
seven significant figures across the whole grid.

**What it did not do.** No tolerance is derived from it. The constants it
observed are not recorded in this document, and the **confirmatory α grid is
disjoint from the grid the reconnaissance used**, so the confirmatory
measurement lands on points nobody has looked at.

This is disclosed because a pilot presented as blind when it was not is worse
than a pilot honestly described as informed.

---

## 2. Benchmark cases — frozen

| Case | Equation | Profile | Action | `expected_operator_family` | Expected classification |
| --- | --- | --- | --- | --- | --- |
| C-1 | `heat_1d` | `constant` | translation, state only | `identity` | `valid_same_target` |
| C-2 | `heat_1d` | `sinusoidal` | translation, state **+** background | `identity` | `valid_equivalence` |
| C-3 | `heat_1d` | `sinusoidal` | translation, state only, `fixed_background` | `identity` | `invalid_fixed_background_obstruction` |
| C-5 | `burgers_1d` | `constant` | `scalar_rescale` on the **parameter**, no state action | `identity` | `invalid_parameter_only_without_state` |
| C-6 | `advection_diffusion_1d` | `localized_bump` | translation, state only, `fixed_background` | `identity` | `invalid_state_only_with_localized_coefficient` |

The benchmark is **not** "pass them all". It is "distinguish each by the
classification it is expected to receive". C-3, C-5 and C-6 are deliberate
obstructions, and a run in which they *passed* would be a failure.

### C-4 retired at pilot 2 (2026-08-01)

The `monotone_smooth` profile is **nonperiodic by construction** — `tanh` runs
from `−0.9999` to `+0.9999` — while every case declares
`domain_type = periodic_uniform`. The wrap discontinuity of `1.9998`, against a
typical adjacent-sample step of `0.3198`, dominated the measurement rather than
the intended monotone coefficient variation.

**Retirement, not restatement.** The case as frozen was self-contradictory and
its meaning cannot be preserved under the domain constraint: a monotone function
is not periodic, so no periodic profile still measures what C-4 named.
Monotone-coefficient obstruction returns when a nonperiodic action family is
available.

### The operator-family set is `{identity}`

> **Amendment 4 (v0.37.1).** C-5 previously declared `scalar_multiplier`, which
> matched the *state* rescale the runner was performing rather than the
> *parameter* rescale its bundle declared. With the semantics repaired, the
> claim under test is that rescaling `nu` leaves the residual unchanged --
> `identity` -- and measurement violates it. **No case now exercises
> `scalar_multiplier`**, which is a coverage loss recorded rather than hidden:
> the family is contract-tested in `test_v0_37a_problem_action_contracts.py`
> but no longer exercised end to end by a benchmark case.

Neither `linear_combination_of_derivatives` nor `diagnostic_fitted` is used by
any case.

> **Note, not a blocker.** v0.37b declares
> `linear_combination_of_derivatives` but does not synthesise it, reporting
> `inconclusive` with a stated reason. Because no v0.37c case selects that
> family, **the gap is inert for this benchmark** and does not need closing
> before the pilot. It remains open for a later phase.

C-5 is the only `scalar_multiplier` case. Burgers is nonlinear —
`R(cu) = c·u_t + c²·u·u_x − c·ν·u_xx` — so the `u u_x` term scales as `c²` and
the naive claim that rescaling `u` scales the residual is false. That falsity is
the point of the case.

---

## 3. Coefficient profiles — frozen

All profiles take the form

```
a(x) = a₀ · (1 + α · f(x)),    |f|∞ ≤ 1,    0 ≤ α < 1,    a₀ > 0
```

**Every profile must be periodic** under the frozen
`domain_type = periodic_uniform`. The requirement had been implicit throughout
and was written down only after `monotone_smooth` violated it; it is stated here
so a future profile addition does not repeat the C-4 error. A nonperiodic
profile carries a wrap discontinuity, and `np.roll` moves that seam through the
interior where it dominates whatever the case meant to measure.
`test_no_nonperiodic_profile_is_registered` enforces it.

**This form guarantees positivity.** With `|f|∞ ≤ 1` and `α < 1`, the factor
`(1 + αf)` is strictly positive, so `a(x) > 0` everywhere and the problem stays
parabolic for every point on both grids. An additive form `a₀ + α·f(x)` would
admit negative diffusivity for `α > a₀`, which is not a harder test — it is a
different and ill-posed equation.

| Profile ID | `f(x)` | Fixed parameters |
| --- | --- | --- |
| `constant` | `0` | `a₀ = 0.1` |
| `sinusoidal` | `sin(k·x)` | `a₀ = 0.1`, `k = 2` |
| `localized_bump` | `exp(−((x − x₀)/w)²)` | `a₀ = 0.1`, `x₀ = mid-domain`, `w = 0.05·L` |
| `higher_frequency` | `sin(k·x)` | `a₀ = 0.1`, `k = 6` |

`α` is the dose-response knob and is the only thing that varies within a case.
Positivity is asserted per profile per α by the runner, not assumed.

---

## 4. α grids — frozen and disjoint

| Grid | Values |
| --- | --- |
| Pilot | `0.0, 0.05, 0.1, 0.2, 0.4, 0.8` |
| Confirmatory | `0.025, 0.075, 0.15, 0.3, 0.6` |

Disjointness is asserted by test:
`set(PILOT_ALPHA_GRID).isdisjoint(set(CONFIRMATORY_ALPHA_GRID))`.

`α = 0` appears only in the pilot grid and is a **control**: at zero dose every
profile degenerates to `constant`, so C-3, C-4 and C-6 must become
indistinguishable from C-1. A pilot in which they separated at `α = 0` would
indicate the separation is an artefact of something other than the coefficient
variation, and PS-1 is stated to require exactly that.

---

## 5. Pilot success criteria — frozen

All three must pass before the confirmatory freeze may be signed.

### PS-1 — Decision margin, not pairwise ratio

For every `α > 0` on the pilot grid, there must exist a single decision
threshold `T` such that:

1. every **valid** case (C-1, C-2) measures **below** `T`;
2. every **invalid** case (C-3…C-6) measures **above** `T`;
3. the margin — the ratio of the smallest invalid measurement to the largest
   valid measurement — is reported, per α.

And, as the control: **at `α = 0`, no such separating threshold exists** between
C-1 and the profile-dependent obstruction cases, because at zero dose they are
the same problem.

This replaces an earlier pairwise-5× formulation. A pairwise criterion asks
whether two cases differ; what the benchmark actually needs is whether a
*decision* can be made, which is a property of the whole set against a single
boundary.

### PS-2 — Traceable tolerances

Every tolerance in the confirmatory freeze must trace to **either** a
hand-computed reference **or** an analytically-derived bound, and must cite it.
An experimentally-tuned value chosen to make the intended labels pass is a
PS-2 failure, however well it works.

The derivations are given in §6 and are to be completed *before* the pilot runs,
so that a PS-2 failure at pilot time is a measurement finding rather than
unfinished arithmetic.

### PS-3 — Grid non-reuse

No confirmatory α coincides with any pilot α. Asserted by test.

---

## 6. Traceability derivations — to be completed before the pilot

Each case's tolerance must trace to one of these.

**C-1 — exact, floor-limited.** Constant coefficient plus an exact grid shift is
a permutation of samples: `R(Tu) = T R(u)` identically, and the only error is
the spectral-derivative floor. The reference is that floor, measured on the same
grid, not a fitted number.

**C-2 — exact, floor-limited.** When the background shifts by the same whole
number of cells as the state, both sides are the same permutation of the same
samples. The equivalence is exact for the same reason C-1 is, and the tolerance
is the same floor. **This is a derivation, not an approximation** — it does not
degrade with α.

**C-3, C-6 — first order in α, bounded below.** These are obstructions, so
their tolerance is a **floor**: the error must *exceed* a stated value.

> **Amendment 1 (post-pilot).** The derivation below previously kept only the
> `a·u_xx` term and was **not** a valid bound: measured against the pilot it came
> in at `0.52`–`1.00` of the observed error. The diffusion operator is
> `(a(x)·u_x)_x = a'(x)·u_x + a(x)·u_xx`, and the `a'` term is the same order in
> α. Dropping it was a derivation error, not a measurement one. With both terms
> the bound holds with margin on the periodic profiles.
>
> **Amendment 3 (pilot 2).** C-4's derivation is deleted rather than corrected.
> There is nothing to derive for a retired case, and the bound never failed
> because the algebra was wrong -- it failed because the case was measuring a
> seam.

Writing `a(x) = a₀(1 + αf(x))`, the state shift moves `u` but not `a`, leaving
both terms:

```
R(Tu) − T R(u)  =  −[a(x) − a(x−τ)]·u_xx(x−τ)  −  [a'(x) − a'(x−τ)]·u_x(x−τ)
```

so

```
‖R(Tu) − T R(u)‖∞  ≤  a₀·α·( ‖f(x) − f(x−τ)‖∞·‖u_xx‖∞  +  ‖f'(x) − f'(x−τ)‖∞·‖u_x‖∞ )
```

Still **exactly first order in α**, which the pilot confirmed to seven
significant figures. Each case's floor cites this bound with its own profile
differences.

**C-5 — bounded below by the diffusive term.** The action rescales the
*parameter*, not the state: `nu -> c*nu` with `u` untouched. For Burgers
`R = u_t + u·u_x − nu·u_xx`, so

```
R_{c·nu}(u) − R_{nu}(u)  =  −(c − 1)·nu·u_xx
```

and therefore

```
‖R_{c·nu}(u) − R_{nu}(u)‖∞  =  |c − 1| · nu · ‖u_xx‖∞
```

exactly. Verified at ratio `1.000000` on every seed. It vanishes only at
`c = 1`, which the case does not use.

> **Amendment 5 (v0.37.1).** The previous derivation was
> `|c² − c|·‖u·u_x‖∞`, correct arithmetic for a *state* rescale — which is what
> the runner was doing and not what the bundle declared. See
> `docs/releases/V0_37_C5_ERRATUM.md`.

---

## 7. Pre-registered artifacts and block status

| Artifact | Path | Written when |
| --- | --- | --- |
| Hypothesis freeze | `docs/design/v0_37c_hypothesis_freeze.md` | now |
| Pilot report | `docs/design/v0_37c_pilot_report.md` | after the pilot runs |
| Confirmatory freeze | `docs/design/v0_37c_confirmatory_freeze.md` | **only if** PS-1, PS-2 and PS-3 all pass |

**Block status: `blocked_pilot_criteria_not_met`.**

If any criterion fails, v0.37c terminates in that status, the block reason
**names the specific PS criterion violated**, and `v0.37d does not open`. This
status is pre-registered here so that blocking is a first-class declared outcome
rather than an implicit failure discovered by the absence of a document.

There is no third outcome. "Pilot passed with a note" is not available: the
two-stage freeze is only worth having if its signal is clean.

---

## 8. Seeds

Every benchmark run is seed-full from the first line. `ProblemActionBundle`
carries no seed by C-1; `ActionExecutionConfig` requires one, with no default,
so a fixture that forgets is a `TypeError` rather than a silently
irreproducible run.

Every seed used in the pilot is retained in the pilot report. None are dropped,
including any that produce inconvenient results — a dropped seed is a selection
effect, and the report must be auditable for its absence as much as its content.

---

## 9. Non-goals

- No tolerance values in this document.
- No new PDE, no new profile beyond the five frozen here.
- No change to the v0.37b report schema.
- No root export.
