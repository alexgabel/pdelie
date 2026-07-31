# Cross-Platform Portability Classes

**Status:** normative from v0.36 onward. Every assertion that compares two numeric artifacts must declare its class.

## Why this exists

Three CI failures across three releases had one cause: **a claim measured on one platform and recorded as universal.**

| Release | Claim | What happened |
|---|---|---|
| v0.33e | golden fixture compared with `==` | passed on macOS, failed on Linux CI |
| v0.35a | rebuilt design matrix compared with `array_equal` | passed on macOS, failed on both CI Python versions |
| v0.35c | QR permutation equal to SciPy's on 8 matrices | passed on macOS, failed on Linux for 2 of them |

None was a numerical defect. Each was a **classification error** — an assertion demanding bit-equality of something that is only equal up to tolerance, or demanding a unique answer from a computation that has none. The v0.35a case is the sharpest: the invariant it violated was written into that same release's own engineering spec.

A single rule would not have caught all three, because the three artifacts differ in kind. Hence four classes.

---

## The four classes

### 1. `exact_discrete` — bit-equality is correct and required

Artifacts with no floating-point path between input and output. Integer or boolean data whose values are *selected*, not *computed*.

**Examples:** trajectory IDs; train/heldout split membership; boolean masks; a `.npz` reloaded from disk and compared to what was written; a JSON payload round-tripped through `json.dumps`/`loads`; the output of `semantic_hash`.

**Assertion:** `np.array_equal`, `==`, `assert a is b`.

**This is the only class where bit-exact comparison is permitted.** If an artifact reaches this class through a computation involving floats — even one — it is misclassified.

> Boundary worth stating: a `.npz` **round-trip** is `exact_discrete` (pure file I/O). A `.npz` compared against a **fresh rebuild** is not — the rebuild ran the computation again. v0.35a conflated these; the fix split them into two tests.

### 2. `tolerance_numeric` — equal up to a declared tolerance

Floating-point results whose value is well-defined but whose last bits depend on BLAS, instruction ordering, or compiler flags.

**Examples:** derivatives; residuals; design matrices; Gram matrices; condition numbers; fitted coefficients; aggregate metrics.

**Assertion:** `np.allclose(..., rtol=..., atol=...)` or `pytest.approx`, with **both tolerances explicit**.

Rules:

- **Repo floor is `rtol=1e-6`.** The worst cross-platform deviation observed anywhere in this repo is `1.5e-9` — roughly 650× of headroom. Do not tighten below the floor without measuring on both platforms.
- **Assert the drift is far inside the tolerance.** A test that passes only because the tolerance is loose is not testing anything. Prefer a secondary assertion that observed drift is ≥10× below the gate, so a real regression cannot hide in the slack.
- **`atol` is not optional.** Near-zero quantities need it; `rtol` alone compares nothing there.

### 3. `qualitative_invariant` — the value varies, a property does not

Computations whose *output* is not unique — because of a tie, a sign convention, a subspace basis, or a permutation — but which have a well-defined invariant.

**Examples:** SVD `U`/`V` (compare **principal angles between subspaces**, never raw vectors); QR pivot permutations on tied-norm designs (compare the **selected-row objective value**, never the permutation); eigenvector sign; ordering among equal-score elements; support membership.

**Assertion:** compare the invariant, and say in the test *why the raw value is not comparable*.

This class exists because of v0.35c. `scipy.linalg.qr(pivoting=True)` returned `[1 0 2 3]` under one LAPACK and `[0 1 2 3]` under another on an orthonormal matrix — every column norm being exactly 1.0, both are correct pivoted QRs. Asserting permutation equality there asserted that two platforms' LAPACK agree, which is not a property of this package.

**Detecting the boundary.** A pivot sequence is determined only where competing column norms separate by more than rounding. Measured on the v0.35c canonical set, four of eight matrices were determined (minimum relative gap 3.0e-02 to 9.8e-01) and four were not (0 to 1.1e-16). Where a determinacy criterion exists, **assert it as a test precondition** so a future near-tie fails with a clear cause rather than an inscrutable mismatch.

### 4. `platform_specific_diagnostic` — reported, never asserted

Values that legitimately differ by platform and carry diagnostic value, but must not gate anything.

**Examples:** BLAS vendor and threading configuration; wall-clock timings; memory high-water marks; `numpy.show_config()` output; exact iteration counts of an iterative solver.

**Assertion:** none. Record them in provenance; never compare them across platforms.

---

## Choosing a class

```text
    Does any floating-point arithmetic occur between input and output?
                    |                                     |
                   no                                    yes
                    |                                     |
            exact_discrete          Is the output unique given the input?
                                          |                    |
                                         yes                   no
                                          |                    |
                                 tolerance_numeric    Is there a well-defined
                                                       invariant to compare?
                                                          |            |
                                                         yes           no
                                                          |            |
                                            qualitative_invariant   platform_
                                                                    specific_
                                                                    diagnostic
```

The two questions that matter are the ones the three failures got wrong: *did any float arithmetic happen* (v0.33e, v0.35a) and *is the output unique* (v0.35c).

---

## Obligations

1. **Declare the class.** Any test asserting equality between numeric artifacts states its class in a comment or docstring.
2. **Both platforms for any equality claim.** A claim of exact or near-exact agreement between two implementations, or between a fixture and a rebuild, must run on Linux **and** macOS before it is frozen — via the `portability` marker and lane (`.github/workflows/portability.yml`) — or be narrowed to `tolerance_numeric` / `qualitative_invariant`.
3. **Narrow rather than loosen.** On a cross-platform failure the correct response is usually to reclassify, not to widen the tolerance until it passes. Widening hides regressions; reclassifying states what is actually true.
4. **The portability lane is budgeted.** At most 30 tests carry `@pytest.mark.portability`, enforced by `tests/test_portability_lane_budget.py`. The lane exists to protect claims that genuinely cross platforms; a lane that runs everything protects nothing and takes twice as long to tell you so.
