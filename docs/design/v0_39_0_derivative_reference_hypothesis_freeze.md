# v0.39-0 Derivative-Error Reference — Hypothesis Freeze

**Status: frozen. Written before any implementation.**

Closes the v0.38d deliverable that did not ship. Lands in `v0.39.0`, **not** as a
change to the `v0.38.0` tag.

---

## 1. What did not ship, stated plainly

v0.38d was specified as a five-backend derivative-error reference report with a
frozen schema and a grep-enforced no-global-best rule. **That did not ship.**

What shipped is the *signal-versus-floor* component — `measure_derivative_error`,
`DerivativeErrorReport`, `compare_against_bound`, `RuntimeStats`,
`summarize_runtime`. The v0.38d pilot blocked twice on floor semantics, the
sub-phase closed on that alone, and the cross-backend comparison was never
built.

The v0.38 record is not amended to pretend otherwise. This document opens the
missing layer as new work.

### What already exists, and is therefore not re-derived

| primitive | what it already does |
|---|---|
| `DerivativeErrorReport` | `reporting_regime`, `absolute_error`, `relative_error`, `reference_magnitude`, `floor_threshold` |
| `measure_derivative_error` | withholds the relative statistic at the floor |
| `RuntimeStats` | `warmup_runs`, `measured_runs`, `median_seconds`, `iqr_seconds` |
| `compare_against_bound` | metric-identity-checked bound comparison |

**This layer is a comparison harness over existing capability, not new
numerics.** No derivative backend is written, modified, or tuned by this work.
If a backend turns out to be wrong, that is a separate defect with its own
freeze — it is not repaired here, because a harness that fixes what it measures
cannot measure it.

---

## 2. The claim being frozen

> For a declared manufactured problem and a declared grid, the report states —
> per backend — whether that backend is **applicable**, and if so what error it
> produced in a named metric, in a named regime, with a named runtime
> distribution.

It is a **capability/error map**, not a leaderboard.

### What the report explicitly does not claim

- that any backend is best, recommended, optimal, or a winner — in general or on
  any fixture;
- that inapplicability is a form of poor performance;
- that a lower error implies a better method, since the fixtures are chosen and
  the choice is not neutral;
- anything about backends outside the five classes below;
- anything about a *learned* generator. See §7.

---

## 3. Backend matrix

Five classes, all already implemented:

| backend id | source |
|---|---|
| `spectral_periodic_uniform` | `pdelie.derivatives.spectral_fd` |
| `fd_uniform` | `pdelie.derivatives.spectral_fd` |
| `fd_nonuniform` | `pdelie.differentiation.fornberg` |
| `weak_uniform` | `pdelie.residuals.weak_1d` |
| `weak_irregular` | `pdelie.residuals.irregular_weak` |

### Inapplicability is a result, never an error value

**A backend that does not apply is recorded as not applying.** It is never
assigned an infinite, large, or sentinel error. Doing so would place a
capability statement and a measurement in the same column, and any comparison
across that column would be meaningless.

Frozen vocabulary:

```
not_applicable_geometry
not_applicable_boundary_condition
not_applicable_missing_full_field
not_applicable_unsupported_derivative_order
```

An inapplicable backend has `applicability != "applicable"`, and **all** of its
error and runtime fields are `null`. Not zero, not infinity — `null`.

An applicable backend that *raises* is a distinct outcome and a defect signal,
recorded as `backend_error` with the exception type. It is not silently folded
into inapplicability.

---

## 4. Fixtures

Frozen at this freeze. Each names the property it exists to exercise, so a
fixture cannot later be reinterpreted to support a claim it was not chosen for.

| fixture id | exercises |
|---|---|
| `periodic_fourier_mode` | the case spectral is exact on; anchors the others |
| `polynomial_exactness` | FD exactness up to formal order; independent of grid |
| `smooth_gaussian` | smooth, non-periodic, well-resolved |
| `boundary_sensitive_nonperiodic` | where periodic methods must decline, not degrade |
| `nonuniform_manufactured` | the grid class Fornberg exists for |
| `weak_integral_manufactured` | where the weak form is the natural discretisation |

Fixtures span **applicability**, not difficulty. `boundary_sensitive_nonperiodic`
exists so that `not_applicable_boundary_condition` is a populated outcome rather
than a vocabulary entry nothing reaches.

---

## 5. Per-backend fields

```
backend_id
applicability                  applicable | not_applicable_* | backend_error
l2_error                       null unless applicable
linf_error                     null unless applicable
interior_error
boundary_error
reporting_regime               signal | floor
metric_spec_id                 identity-checked, never re-derived
valid_row_count
skipped_row_count
diagnostics_ref                stencil or weak-support diagnostics, or null
runtime_median_seconds
runtime_iqr_seconds
warmup_runs
measured_runs
warnings
```

Interior and boundary errors are reported **separately**, never pooled. A method
that is excellent in the interior and poor at the boundary has a pooled number
that describes neither.

Runtime uses `summarize_runtime` with warmups. **A single wall-clock reading is
not a runtime measurement** and is refused at construction.

The payload carries `summary_type` and `summary_schema_version` per current
convention. The stale 18-key draft is **not** resurrected; the field list above
is what this freeze binds.

---

## 6. No-global-best policy

Forbidden anywhere in the payload, at any nesting depth:

```
best_backend
recommended_backend
winner
optimal_backend
```

Enforced by walking the emitted payload, not by scanning source text — a
substring check on source cannot tell a key from a comment explaining why that
key is absent, which is a defect class this repository has caught repeatedly.

Permitted, because each is a narrower and checkable statement:

```
lowest error on this fixture under this policy
not applicable to this fixture
higher runtime under this configuration
```

The distinction is scope. *"Lowest error on `periodic_fourier_mode` at `d=2`"*
is a measurement. *"Best backend"* is a recommendation the data does not
support, because the fixture set was chosen and applicability is not error.

---

## 7. Closure gate for Ko runtime — and what is deferred

Ko training runtime may begin only when the reference can:

1. evaluate a learned finite flow against at least one appropriate reference path;
2. separate derivative error from generator error;
3. report when a verification discrepancy falls below the derivative floor;
4. round-trip strict JSON with `allow_nan=False`;
5. emit no global-backend recommendation.

**Requirements 1–3 are frozen here as a contract and validated at v0.39b.**

They are claims about a learned finite flow, and `CoordinateVectorFieldArtifact`
does not exist yet. Designing them against a guessed artifact shape would be the
v0.38d mistake in a new place: a specification written against something that
cannot be executed. The error-separation contract is therefore frozen abstractly
now — it takes a *reference path* and a *candidate path* and attributes
discrepancy to derivative floor versus generator, without depending on how the
candidate is stored — and is validated against the real artifact at v0.39b.

Requirements 4–5 are validated by this work.

**The gate is not satisfied until the v0.39b validation runs.** Recording it as
frozen here does not discharge it.

### Why this matters

Without error separation, a failed learned-generator verification is attributed
to the candidate when the derivative backend may be the limiting error source.
That would produce a confident negative result about someone else's method on
the strength of our own discretisation error.

---

## 8. Pilot-validity criteria

The pilot is a **validity check on the harness**, not a measurement of the
backends. It passes only if all four hold:

| | criterion |
|---|---|
| **PV-1** | every backend reaches a decidable `applicability` on every fixture — no `unknown`, no silent skip |
| **PV-2** | every inapplicability vocabulary entry is **reached by at least one fixture**; an unreachable outcome is removed from the vocabulary or the fixture set is wrong |
| **PV-3** | at least one fixture lands in the `floor` regime and at least one in `signal`; a harness that only ever sees one regime has not exercised the distinction it was built around |
| **PV-4** | no error, runtime, or applicability field is populated for an inapplicable backend |

Failing any of these yields `blocked_pilot_derivative_reference_criteria_not_met`
and **no confirmatory freeze is written**.

PV-2 is the guard against this freeze's most likely failure: a vocabulary richer
than the fixtures can reach, which reads as thorough and is untested. This
repository has shipped that shape before.

---

## 9. What would falsify this design

Recorded now so it cannot be reinterpreted later:

- If two backends cannot be compared on **any** fixture because applicability
  never overlaps, the report is a per-backend record with no comparative
  content, and should say so rather than presenting a table that implies
  comparison.
- If `interior_error` and `boundary_error` cannot be separated for the weak
  backends, that limitation is recorded — not worked around by pooling.
- If runtime IQR exceeds the median on the canonical lane, runtime is too noisy
  to report at all on that lane and the fields are `null` with a stated reason,
  rather than reported with a caveat nobody reads.

---

## 10. Out of scope

- Any change to a derivative backend's numerics.
- Any claim about 2-D, unstructured grids, or meshfree methods.
- Any recommendation, ranking, or default-selection logic.
- Any modification of the `v0.38.0` tag, its appendices, or its readiness
  documents.

---

## 11. Signature

Frozen before implementation. Fixtures, backend matrix, applicability
vocabulary, field list, no-global-best policy, closure-gate contract, and
pilot-validity criteria are bound by this document. Changing any of them
requires an amendment recorded here, not an edit.
