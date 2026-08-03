# v0.38b — Hypothesis Freeze (Fornberg non-uniform finite differences)

**Status:** frozen. Written before any v0.38b runtime code.

**Reconnaissance disclosure:** no measurement informed this freeze. **No
threshold value appears anywhere in it** — per C-2 of the binding constraints,
the stencil-size cap and the G-5 ratio are piloted, not guessed, and are frozen
only at the confirmatory freeze after a pilot measures them.

---

## 1. What v0.38b is for

v0.38a decided *which rows are admissible*. It computes no derivative. v0.38b
computes derivatives on a **non-uniform 1-D grid**, and produces four of the five
exclusion reasons v0.38a declared but nobody yet emits.

The method is Fornberg's recursion for finite-difference weights on arbitrary
node distributions.

---

## 2. Binding constraints inherited

Restated so this freeze is self-contained:

- **`formal_accuracy` is derived, never caller-declared.**
- **Duplicate or unsorted coordinates are rejected, not repaired.** A silent sort
  changes which row is which; a silent dedup changes the count. Rejecting is
  recoverable, repairing is not.
- **G-5 is `max_spacing / min_spacing > threshold`** — a ratio, so it is
  scale-free. An absolute spacing test classifies the same grid differently in
  metres and in kilometres.
- **The cap and the threshold are piloted.** Neither appears below.

---

## 3. What v0.38b freezes

### 3.1 Weights (FN-1 … FN-5)

| Rule | Statement |
|---|---|
| **FN-1** | Weights come from Fornberg's recursion, computed for the requested derivative order at a requested evaluation point over a declared stencil. |
| **FN-2** | **`formal_accuracy` is derived** as `stencil_size − derivative_order`, from the stencil actually used — never from a caller argument. A test asserts no such parameter exists. |
| **FN-3** | A stencil smaller than `derivative_order + 1` is **refused**: fewer nodes than the derivative order cannot determine it, and returning weights anyway would produce a number with no approximation property at all. |
| **FN-4** | Weights sum to zero for every derivative order ≥ 1, and reproduce the exact derivative of any polynomial of degree < `stencil_size`. Both are asserted as properties. |
| **FN-5** | The evaluation point need not be a node. Off-node evaluation is legal and reported as such. |

### 3.2 Coordinates (FN-6 … FN-9)

| Rule | Statement |
|---|---|
| **FN-6** | Duplicate coordinates are **refused**, naming the duplicated values. |
| **FN-7** | Unsorted coordinates are **refused**, not sorted. |
| **FN-8** | Non-finite coordinates are refused. |
| **FN-9** | Fewer than two coordinates is refused: a single point has no spacing, so no ratio and no stencil. |

### 3.3 Grid regularity diagnostic (FN-10 … FN-12)

| Rule | Statement |
|---|---|
| **FN-10** | `spacing_ratio` is `max_spacing / min_spacing`, reported always, on every grid including uniform ones (where it is `1.0`). |
| **FN-11** | The **G-5 threshold is not frozen here.** The pilot measures conditioning against the ratio and the confirmatory freeze fixes it. Until then the diagnostic reports the ratio and no verdict. |
| **FN-12** | A uniform grid must report `spacing_ratio == 1.0` **exactly**, not approximately — `np.diff` of a `linspace` is not bitwise constant, so this is a claim about the *ratio* being computed in a way that survives that. If it cannot be made exact, FN-12 is amended with the measured deviation rather than loosened silently. |

### 3.4 Row-mask producers (FN-13 … FN-15)

v0.38b owes four of v0.38a's five exclusion reasons.

| Rule | Statement |
|---|---|
| **FN-13** | `stencil_does_not_fit` is produced when the requested stencil extends past the available coordinates at a row. |
| **FN-14** | `duplicate_coordinate` and `coordinate_missing` are produced from coordinate validation. |
| **FN-15** | `derivative_unavailable` is produced when a derivative was requested and no weights could be formed. |

### 3.5 Convergence (FN-16, FN-17)

| Rule | Statement |
|---|---|
| **FN-16** | The observed convergence order under grid refinement must be **at least** the derived `formal_accuracy`, less a slack the pilot measures. The slack is **not frozen here**. |
| **FN-17** | The bound is load-bearing and carries a declared oracle — see §4. |

---

## 4. Oracle source, declared before the pilot

**Required by `ANALYTICAL_ORACLE_DISCIPLINE.md` and C-2, and named here rather
than after a measurement.**

**Primary derivation.** Fornberg weights over `n` nodes are exact for polynomials
of degree `≤ n−1`. Approximating a `d`-th derivative therefore annihilates the
first `d` Taylor terms and reproduces the next `n−d` exactly, leaving a leading
error term of order `h^(n−d)`. Hence `formal_accuracy = n − d`.

**Secondary derivation — `manufactured_solution`.** Apply the computed weights to
a polynomial of degree exactly `n−1` whose `d`-th derivative is known in closed
form, on a **deliberately non-uniform** node set. The weights must reproduce it
to roundoff. This is an exact algebraic property, not a limit, so it needs no
grid refinement and shares no code with the recursion that produced the weights.

Write-up: `docs/design/FORNBERG_ACCURACY_ORACLE.md`, with the executable check
marked `@pytest.mark.load_bearing_analytical`.

**Why this method.** `symbolic_expansion` would mean adding `sympy` for one
identity. An `independent_implementation` of Fornberg is a second copy of the
same algorithm and would reproduce its errors. Polynomial exactness is checkable
against a right answer known in advance — the property that caught the bogus
13.8% figure during the v0.38e pilot.

---

## 5. Pre-registered pilot

**Artifact:** `docs/design/v0_38b_pilot_report.md`. Append-only.

**What the pilot measures** (and what the confirmatory freeze will fix):

1. Weight-matrix conditioning as a function of `spacing_ratio` → the **G-5
   threshold**.
2. Conditioning and accuracy as a function of `stencil_size` → the **cap**.
3. Observed convergence order against derived `formal_accuracy` → the **slack**
   in FN-16.

**Block criteria:**

- **B-1** Polynomial exactness failing at any tested `(n, d)` — the oracle
  refuting the primary derivation.
- **B-2** Observed convergence order below derived `formal_accuracy` by more than
  the measured slack, on a grid the diagnostic did not flag.
- **B-3** Any of the four owed exclusion reasons not produced by shipped logic.
- **B-4** A uniform grid reporting `spacing_ratio != 1.0` (FN-12).
- **B-5** Duplicate or unsorted coordinates accepted anywhere.
- **B-6** Any measurement quoted in a norm other than the one its bound was
  derived in.
- **B-7** A threshold appearing in shipped code before the confirmatory freeze
  fixes it.

---

## 6. What v0.38b does **not** claim

- **No weak-form support on irregular samples.** That is v0.38c.
- **No derivative-error reporting.** v0.38b computes derivatives and reports
  conditioning; quantified error reference is v0.38d.
- **1-D only**, on a declared axis. No unstructured meshes, no arbitrary
  geometry.
- **No discovery claim.**
- **No cross-platform claim** until a replay runs. Conditioning numbers are
  `tolerance_numeric` and will need one.

---

## 7. Signature

Frozen before implementation, with the oracle named and no threshold present.
