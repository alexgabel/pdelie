# v0.38d — Hypothesis Freeze (derivative-error reference)

**Status:** frozen. Written before any v0.38d runtime code.

**Reconnaissance disclosure:** no measurement informed this freeze. Two prior
findings from *this arc* shape §3 and are cited as history, not as new
measurement:

1. v0.37c pilot 1 blocked because a bound derived in `‖·‖∞` was compared against
   a measurement emitted in `‖·‖₂` — a factor of `11.96` between two numbers
   both called "the error".
2. The v0.38b pilot's first sweep reported a **uniform** grid as the worst case,
   because it computed a relative error at a zero crossing and divided by a
   `1e-12` floor.

Both are error-reporting defects. v0.38d is the layer that reports errors, so
both are designed against structurally rather than warned about.

---

## 1. What v0.38d is for

v0.38b computes derivatives on irregular grids and reports *conditioning*.
v0.38d reports **error against a reference** — and says, every time, what the
reference was and whether one exists at all.

---

## 2. Binding constraints inherited

From C-4:

- **`per_backend_runtime_stats` carries warmup, repeats, median and IQR.** A
  single timing is a sample of one; a mean without a spread hides bimodality
  from warmup.
- **Every error metric declares its norm via `ErrorMetricSpec`**, with
  `require_matching_metric` refusing a bound and a measurement that carry
  different `metric_spec_id`s.

---

## 3. What v0.38d freezes

### 3.1 The reference must exist and be named (DE-1 … DE-4)

| Rule | Statement |
|---|---|
| **DE-1** | Three reference kinds, closed: `analytical` (a manufactured solution with a closed-form derivative), `refined_grid` (the same computation at higher resolution), `none`. |
| **DE-2** | `none` is a **first-class outcome**, not an omission. Real data has no reference; a payload that quietly reports no error is indistinguishable from one reporting zero error. |
| **DE-3** | With `reference_kind = none`, every error field is `None` — never `0.0`, never omitted. |
| **DE-4** | The reference kind is **derived** from what was supplied, not declared by the caller. Same rule as `formal_accuracy` and `full_field_derivatives_available`. |

### 3.2 Signal versus floor (DE-5 … DE-8)

The v0.38b pilot defect, designed against.

| Rule | Statement |
|---|---|
| **DE-5** | Every error report carries **both** an absolute error and a `reporting_regime` of `signal` or `floor`. |
| **DE-6** | A relative error is emitted **only** in the `signal` regime. In the `floor` regime it is `None` — a relative difference against a near-zero reference is not a number, and reporting one is how a uniform grid comes to look like the worst case. |
| **DE-7** | The regime boundary is **derived**, not guessed: the floor is where the reference magnitude falls below the representable precision of the computation, `n · eps · scale`. Same derivation pattern as v0.38b FN-12 and v0.38c WK-8. |
| **DE-8** | The regime is reported, so a reader never has to infer which number they are looking at. |

### 3.3 Metric declaration (DE-9, DE-10)

| Rule | Statement |
|---|---|
| **DE-9** | Every error carries an `ErrorMetricSpec`. There is no default. |
| **DE-10** | Comparing an error against a bound goes through `require_matching_metric`, so a `‖·‖∞` bound cannot be compared with a `‖·‖₂` measurement. This is the v0.37c pilot-1 defect made impossible. |

### 3.4 Timing (DE-11 … DE-14)

| Rule | Statement |
|---|---|
| **DE-11** | `per_backend_runtime_stats` carries `warmup_runs`, `measured_runs`, `median_seconds`, `iqr_seconds`. |
| **DE-12** | A mean is **not** reported. A mean without a spread hides bimodality, and reporting both invites the mean to be quoted alone. |
| **DE-13** | Fewer than two measured runs is **refused**: an IQR over one sample is not a spread. |
| **DE-14** | Timing is `platform_specific_diagnostic` in the portability taxonomy, and the payload says so. It is never compared across platforms. |

---

## 4. Pre-registered pilot

**Artifact:** `docs/design/v0_38d_pilot_report.md`. Append-only.

**What the pilot measures:**

1. That the `floor` regime is entered at a zero crossing of a manufactured
   solution — the v0.38b defect, reproduced deliberately and caught.
2. Timing spread on a real backend: whether warmup is visible in the IQR.

**Block criteria:**

- **B-1** A relative error emitted in the `floor` regime.
- **B-2** `reference_kind = none` producing any non-`None` error field.
- **B-3** A metric-mismatched comparison succeeding.
- **B-4** A mean appearing in the timing payload.
- **B-5** Timing accepted with fewer than two measured runs.
- **B-6** Any measurement quoted in a norm other than the one its bound was
  derived in — the criterion this whole sub-phase exists to make unfailable.

---

## 5. What v0.38d does **not** claim

- **No accuracy guarantee.** It reports measured error against a stated
  reference; it does not bound error for unseen inputs.
- **No cross-platform timing claim.** DE-14.
- **No discovery claim**, no unstructured meshes, no arbitrary geometry.
- **No reference where none exists.** DE-2 is the whole point.

---

## 6. Signature

Frozen before implementation, with no guessed threshold.
