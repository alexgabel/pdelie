# Equation-to-Implementation Traceability Template

**Status:** required for any sub-phase whose gate depends on an analytical
property of a residual operator.

## Why this exists

The v0.37c §6 obstruction bound was derived against `a·u_xx` while the shipped
evaluator computes `(a·u_x)_x = a'·u_x + a·u_xx`. Nobody wrote down which
operator the derivation was about, so nobody noticed it was a different one from
the code's. The bound was off by a term of the same order and the pilot blocked.

Filling this table forces the two to be written next to each other, where a
mismatch is visible rather than latent.

## The table

One instance per (equation, evaluator, transformation) triple under test.

| # | Field | Content |
|---|---|---|
| 1 | **PDE as written** | The equation in the form a reader would write it on paper. |
| 2 | **Equation form** | `conservative` / `nonconservative`, and which the evaluator dispatches on. |
| 3 | **Evaluator class** | The exact class, with module path. |
| 4 | **Coefficient dispatch** | Scalar vs array path, and whether they differ numerically. State how this was checked, not that it was. |
| 5 | **Expanded operator** | The operator **as the code computes it**, fully expanded. This is the field the v0.37c defect lived in. |
| 6 | **Domain assumptions** | Periodicity, uniformity, and what breaks if violated. |
| 7 | **Boundary assumptions** | What is assumed at the edges, and whether the evaluator enforces or presumes it. |
| 8 | **Transformation** | The action applied, and — explicitly — **which declared field the runner consumes to apply it**. |
| 9 | **Expected residual relation** | The analytical relation, in the metric named by its `ErrorMetricSpec`. |
| 10 | **Independent reviewer** | Who checked rows 5 and 8 against the source, and when. Not the author. |

## Rows that are load-bearing

**Row 5** is where a derivation and an implementation silently diverge. Write
the operator out; do not name it.

**Row 8** is where a declaration and an execution silently diverge — the C-5
class. Naming the transformation is not enough: name the field the runner reads.
C-5 declared a parameter action and the runner read the state.

**Row 9** must reference an `ErrorMetricSpec` by id, not say "the error". A
bound in one norm compared against a measurement in another is what blocked
pilot 1.

**Row 10** must not be the author. Two derivations by one person share that
person's assumptions — see `ANALYTICAL_ORACLE_DISCIPLINE.md`.

## Worked example

Filled from the v0.37c C-3 case, as it should have been written at the time.

| # | Field | Content |
|---|---|---|
| 1 | PDE as written | `u_t = (a(x)·u_x)_x` |
| 2 | Equation form | Conservative in the flux; the spec declared `nonconservative`, which is **row 2 disagreeing with row 5** and is exactly the defect. |
| 3 | Evaluator class | `pdelie.residuals.heat_1d.HeatResidualEvaluator` |
| 4 | Coefficient dispatch | Array path. Scalar and constant-array were measured identical (`2.321210e-02` both), so dispatch was ruled out as the discrepancy source. |
| 5 | Expanded operator | `u_t − a'(x)·u_x − a(x)·u_xx` — **two** terms. The original §6 bound kept only the second. |
| 6 | Domain assumptions | `periodic_uniform`; a nonperiodic profile carries a seam that `np.roll` moves through the interior. |
| 7 | Boundary assumptions | Periodic wrap, presumed by the spectral derivative rather than enforced. |
| 8 | Transformation | 3-cell periodic translation of the **state**, via `execute_state_action`; the coefficient field is untouched (`identity`). The runner consumes `execution.transformed_field`. |
| 9 | Expected residual relation | `‖R(Tu) − T R(u)‖∞ ≤ a₀·α·(‖Δf‖∞‖u_xx‖∞ + ‖Δf'‖∞‖u_x‖∞)`, metric `linf_absolute`. |
| 10 | Independent reviewer | *(unfilled at v0.37c — this is the gap)* |

Row 2 versus row 5 shows the defect in one glance, which is the point.

## First consumer

The v0.38b convergence-gate hypothesis freeze must contain a filled instance
before its pilot runs.
