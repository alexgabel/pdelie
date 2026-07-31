# Design Freeze Process — Hypothesis → Pilot → Confirmatory Freeze

**Status:** normative for every numerical work package from v0.36 onward.

## Why this exists

Across v0.33, v0.34, and v0.35, **sixteen of twenty-one frozen contracts required amendment on first contact with measurement.** Six would otherwise have shipped as silent defects:

| Release | What the freeze said | What measurement found |
|---|---|---|
| v0.33d | gate on `span_distance` | inverts to `0.0` — reports a *perfect* fit on a failing candidate |
| v0.33c | mask rows are spatial | rows are **time**; spatial masks zero the design matrix |
| v0.34a | residual is `ν(x)·u_xx` | generators default to divergence form; ~300× mismatch |
| v0.34c | 87× / 111.8 / 3.77 | the target function is **nondeterministic**; those were one draw |
| v0.35a | leverage via the hat matrix | errs by **0.563** on a quantity bounded in `[0, 1]` |
| v0.35b | classify from `ρ_IR` | `ρ_IR` never consults the symmetry; the verdict is a constant |

The pattern is not that the authors were careless. It is that **a number written into a contract before anyone ran the code is a guess wearing the costume of a decision.** This document makes the sequence mandatory so the guess is never mistaken for the decision.

---

## The three phases

### Phase 1 — Hypothesis freeze

Written **before any implementation code**. Freezes *what will be measured and how the answer will be judged* — never the answer itself.

```markdown
## Hypothesis freeze — <work package id>

**Question.** <the single question measurement will answer>

**Quantity measured.** <exact definition; name the function that will compute it>

**Inputs.** <matrices / fixtures / seeds, enumerated — not "canonical cases">

**Decision rule.** If <quantity> <relation> <placeholder>, then <consequence>;
otherwise <alternative consequence>.

**Thresholds.** DELIBERATELY UNSET. Filled by the pilot.

**Invalidation.** This hypothesis is wrong — not merely unmet — if <condition>.
```

The **invalidation** clause is the part people skip and the part that pays. v0.34c's hypothesis was invalidated rather than unmet: the function was unmeasurable, not badly thresholded. A hypothesis with no invalidation clause cannot report that outcome, so it reports a threshold miss instead and someone tunes the threshold.

Rules:

1. **No numeric threshold may appear in a hypothesis freeze.** Write `<placeholder>`.
2. **Inputs are enumerated, not described.** "Five canonical matrices" is not an input list; `I₄`, `Q` from QR of `default_rng(20350).standard_normal((8,4))`, `Hilbert(5)`, … is.
3. **The quantity names its implementation.** If two routes could compute it, say which, or say that comparing them *is* the measurement.

### Phase 2 — Pilot

Prototype code, run outside the package (`scratchpad/`, a helper module, a notebook that is not committed as an API). Produces numbers. **Never merged as the implementation.**

Requirements:

1. **Every quantity produced by at least two independent routes**, or against a closed form. Agreement is evidence; a single route is an assertion. This is what caught the hat-matrix leverage error — the SVD route and the analytic value agreed, and the hat route did not.
2. **Variance reported, not just a central value.** A single draw is not a measurement. v0.34c's planning figures were one sample from a distribution spanning 5.03–14.44.
3. **Degenerate inputs probed explicitly** — empty, all, rank-deficient, zero-column, near-singular. Record what each returns. Three of the six silent defects above were degenerate-path defects.
4. **Both platforms, for any claim of equality.** See `CROSS_PLATFORM_PORTABILITY_CLASSES.md`.

Pilot output is a table of measured numbers with their spread, plus a written statement of which hypothesis clauses survived.

### Phase 3 — Confirmatory freeze

Written **after** the pilot, **before** the implementation PR.

```markdown
## Confirmatory freeze — <work package id>

**Hypothesis status.** survived | amended | invalidated

**Measured values.** <table: quantity, value, spread, inputs, date>

**Thresholds, now set.** <value>, chosen because <reason grounded in the spread>

**Amendments.** <what the hypothesis said, what measurement showed, what changed>

**Reachability.** Every branch of the frozen vocabulary is reachable on real
input, evidenced by <input that reaches it>.
```

The **reachability** clause exists because of v0.35b, where the proposed classification's non-trivial branch was reachable on 1 of 10 real supports. A vocabulary whose branches cannot be reached is a constant with extra steps.

Thresholds must be justified *from the measured spread*, not chosen round. "≥ 1.0, asserted universally, because the measured minimum across six fixtures was 1.79" is a justification. "≥ 20×" is a wish.

---

## What this process is not

- **Not a gate on exploratory work.** Prototype freely. The process governs what may enter a *contract*.
- **Not applicable to mechanical changes.** A rename, a docstring fix, a dependency pin — no hypothesis needed.
- **Not a substitute for review.** It makes the numbers legible; it does not make them right.

## When it applies

Mandatory for any work package that freezes:

- a numeric threshold anyone will assert against,
- a vocabulary of labels or classifications,
- a tolerance, a seed, or a pinned fixture value,
- an axis, layout, or unit convention.

If a PR adds a constant that a test compares against, this process applies to that constant.

## Recording

Both freezes live in the sub-milestone's planning document, in order, with the pilot table between them. Do not delete the hypothesis after amending it — **the diff between hypothesis and confirmatory freeze is the most useful artifact the process produces**, and every release-readiness note in this repo since v0.33 has drawn on it.
