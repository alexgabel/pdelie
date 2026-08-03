# v0.38c — Hypothesis Freeze (irregular weak bridge)

**Status:** frozen. Written before any v0.38c runtime code.

**Reconnaissance disclosure:** no measurement informed this freeze. One
structural survey was done — the shipped weak form (`residuals/weak_1d.py`)
computes scalar `dt, dx` and fixed kernels, so it is uniform-grid only; and
v0.38a's row masks are over **samples**. Both facts shape §3 and neither is a
measurement.

---

## 1. The distinction this sub-phase turns on

**A weak row is a test-function window. A strong row is a sample.**

v0.38a identifies rows by `DesignRowLineage` over samples. A weak-form row is an
integral over a support region covering many samples. They are different objects,
and a mask built for one does not describe the other.

Conflating them would be the same defect class as the rest of this arc: two
things with one name, disagreeing later with nothing able to notice.

---

## 2. Binding constraints inherited

From C-3, restated:

- **Quadrature narrows to `{nonuniform_trapezoidal, user_supplied_validated_weights}`.**
  Anything else is **refused, not approximated**.
- **`diagnostic_only` becomes `diagnostic_only_v0_38`** — release-scoped. A flag
  asserting a property forever cannot be revisited when the property changes.
  "This payload made no numerical claim in v0.38" is the honest statement.

---

## 3. What v0.38c freezes

### 3.1 Weak-row identity (WK-1 … WK-4)

| Rule | Statement |
|---|---|
| **WK-1** | A weak row is identified by its **window**: the support interval and the sample identities it covers. Not by a sample, and not by an index. |
| **WK-2** | A weak-row identity is **not** interchangeable with a `DesignRowLineage` identity. A test asserts the two namespaces cannot collide. |
| **WK-3** | A window records which sample rows it consumed. A window whose samples were excluded by a v0.38a mask is itself excluded, and says which samples caused it. |
| **WK-4** | Windows may overlap. Overlap is declared, not inferred, and a report states the overlap fraction — two windows sharing samples are not independent evidence. |

### 3.2 Quadrature (WK-5 … WK-9)

| Rule | Statement |
|---|---|
| **WK-5** | Exactly two rules: `nonuniform_trapezoidal` and `user_supplied_validated_weights`. A third name is **refused**, never silently mapped onto a neighbour. |
| **WK-6** | `nonuniform_trapezoidal` weights are derived from the sample coordinates, never supplied. |
| **WK-7** | `user_supplied_validated_weights` are **validated, not trusted**. Validation is exactness on the constant — a rule that cannot integrate `1` over its own interval is not a quadrature rule. |
| **WK-8** | The validation tolerance is **derived**, not guessed: summing `n` weights accumulates `O(n·eps)` relative error, so the bound is `n · eps · interval_length`. Same derivation pattern as v0.38b's FN-12 amendment. |
| **WK-9** | Weights that fail validation are **refused**. There is no "approximately valid" acceptance and no renormalisation — renormalising would make the failure invisible while changing the caller's declared rule. |

### 3.3 Release-scoped diagnostic flag (WK-10, WK-11)

| Rule | Statement |
|---|---|
| **WK-10** | Payloads carry `diagnostic_only_v0_38`, not `diagnostic_only`. |
| **WK-11** | A test asserts the unscoped key is **absent** from v0.38c payloads, so the two cannot coexist and a consumer cannot read whichever it finds first. |

### 3.4 What is not claimed (WK-12)

| Rule | Statement |
|---|---|
| **WK-12** | v0.38c computes weak residuals on irregular samples. It makes **no accuracy claim** about them: quadrature error on scattered nodes is not bounded here, and the payload says so rather than omitting the question. |

---

## 4. Pre-registered pilot

**Artifact:** `docs/design/v0_38c_pilot_report.md`. Append-only.

**What the pilot measures:**

1. Trapezoidal exactness on the constant and on linear functions, uniform and
   non-uniform — confirming WK-8's derived tolerance is attainable.
2. Whether a weak-row identity can collide with a strong-row identity.
3. Overlap fraction across a realistic window layout.

**Block criteria:**

- **B-1** A quadrature name outside the two admitted being accepted.
- **B-2** User-supplied weights failing the constant test yet accepted.
- **B-3** A weak-row identity equal to any strong-row identity.
- **B-4** `diagnostic_only` appearing unscoped in any v0.38c payload.
- **B-5** Trapezoidal weights failing the derived tolerance on a grid the
  diagnostic did not flag.
- **B-6** Any measurement quoted in a norm other than the one its bound was
  derived in.

---

## 5. What v0.38c does **not** claim

- **No accuracy bound on irregular quadrature.** WK-12.
- **No derivative-error reporting.** v0.38d.
- **No replacement of the uniform weak form.** `weak_1d.py` is untouched; this is
  a parallel path for irregular samples, and a test asserts the uniform one is
  unchanged.
- **No discovery claim**, no unstructured meshes, no arbitrary geometry.
- **No cross-platform claim** until a replay runs.

---

## 6. Signature

Frozen before implementation, with no guessed threshold.
