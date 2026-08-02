# v0.38a — Hypothesis Freeze (irregular row masks)

**Status:** frozen. Written before any v0.38a runtime code.

**Reconnaissance disclosure:** no measurement informed this freeze. One
structural survey was done — `DesignRowLineage` (v0.36b) already provides a
semantic row identity, and v0.33c already defines mask-application stages — so
v0.38a extends existing vocabulary rather than introducing a parallel one. No
number below came from a run.

---

## 1. What v0.38a is for

A design matrix row is admissible only if every quantity it needs actually
exists. On an irregular sampling that is not automatic: a stencil may not fit, a
coordinate may be absent, a derivative may be unavailable at the sample.

Today the bridge answers this with a **boolean array positioned against the
matrix**. That is enough while nothing reorders rows, and every real design-matrix
operation reorders rows.

v0.38a makes exclusion **identified, reasoned, and composable**.

---

## 2. Binding constraints inherited

From `V0_38_BINDING_DESIGN_CONSTRAINTS.md` C-1, restated so this freeze is
self-contained:

- **`full_field_derivatives_available` is derived, never asserted.** A
  caller-supplied boolean is a claim about someone else's state.
- **Semantic row IDs are primary; integer indices are secondary and derived.**
  An integer index means nothing after a filter, a sort, or a concatenation, and
  all three are legal operations on a design matrix.

---

## 3. What v0.38a freezes

### 3.1 Row identity (RM-1 … RM-4)

| Rule | Statement |
|---|---|
| **RM-1** | A row's identity is its `DesignRowLineage.identity()` — the v0.36b semantic hash. v0.38a introduces **no second identity scheme**; a parallel one would be a second answer to one question. |
| **RM-2** | A mask stores row **identities**, not positions. Positions are derived on demand, against a specific matrix, and are never stored. |
| **RM-3** | Applying a mask to a row set whose identities it does not cover is **refused**, naming the unmatched identities. Silently intersecting is how a filtered matrix keeps a mask that no longer describes it. |
| **RM-4** | Row order carries meaning (v0.36b), so a mask must not reorder. It selects; it never sorts. |

### 3.2 Exclusion reasons (RM-5 … RM-8)

An excluded row says **why**, from a closed vocabulary.

| Reason | Meaning |
|---|---|
| `stencil_does_not_fit` | The derivative stencil extends past available samples. |
| `coordinate_missing` | A required coordinate is absent at this row. |
| `derivative_unavailable` | A required derivative was not computed here. |
| `observation_masked` | The upstream field mask excludes this sample. |
| `duplicate_coordinate` | Another row occupies the same coordinate. |

| Rule | Statement |
|---|---|
| **RM-5** | Every excluded row carries exactly one reason. Zero is untraceable; several is an unresolved question about which one applies. |
| **RM-6** | The vocabulary is **growth-only**. Retiring a reason is a claim that the situation cannot arise. |
| **RM-7** | An included row carries **no** reason. `None` and `"included"` are not both allowed to mean the same thing. |
| **RM-8** | Reason counts are reported. A mask that excludes rows without saying how many of each is not a diagnostic. |

### 3.3 Derived provenance (RM-9 … RM-11)

| Rule | Statement |
|---|---|
| **RM-9** | `full_field_derivatives_available` is **computed** from which derivatives were actually produced. There is no parameter by which a caller may assert it. |
| **RM-10** | A test asserts the constructor exposes no such parameter — absence is checked, not merely unwritten. |
| **RM-11** | If the derived value and any caller-supplied hint disagree, construction **refuses** rather than choosing. Same rule as the v0.38 equation-form resolver. |

### 3.4 Composition (RM-12 … RM-14)

| Rule | Statement |
|---|---|
| **RM-12** | Two masks compose by **intersection of included rows**. Composition is commutative and associative, asserted as properties. |
| **RM-13** | On composition, a row excluded by both keeps the reason from the **first** mask, and the operation records that a second reason existed. Discarding it silently would lose why a row was doubly excluded. |
| **RM-14** | Composing masks over different row-identity sets is **refused**. |

---

## 4. Pre-registered pilot

**Artifact:** `docs/design/v0_38a_pilot_report.md`. Append-only; blocked runs
retained.

**Block criteria — any one blocks the confirmatory freeze:**

- **B-1** Any exclusion reason in the frozen vocabulary that no constructed case
  produces, and that is not explicitly declared unreachable with a proof.
- **B-2** A mask surviving application to a reordered row set without refusing.
- **B-3** `full_field_derivatives_available` obtainable from a constructor
  argument by any route.
- **B-4** Composition found non-commutative on any constructed pair.
- **B-5** An excluded row carrying zero or more than one reason.
- **B-6** Any measurement quoted in a norm other than the one its bound was
  derived in.

`blocked_pilot_criteria_not_met` is a first-class outcome.

---

## 5. What v0.38a does **not** claim

- **No irregular *differentiation*.** Deciding a stencil does not fit is v0.38a;
  computing a derivative on a non-uniform grid is v0.38b.
- **No weak-form support on irregular samples.** That is v0.38c.
- **No accuracy claim.** v0.38a excludes rows; it computes no derivative and
  reports no error. Error reference is v0.38d.
- **No unstructured meshes, no arbitrary geometry.** 1-D scattered coordinates on
  a declared axis. Both terms are in the forbidden vocabulary.
- **No discovery claim.** A row mask says which rows are admissible, not whether
  a model recovered from them is right.
- **No cross-platform claim** until a replay runs.

---

## 6. Signature

Frozen before implementation. Changes to §3 or §4 after this point are
amendments with dated entries, not edits.
