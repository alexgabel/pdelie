# V0.8 Scope Freeze

## Summary

`v0.8` is the first weak-form numerics release for `pdelie`.

Its purpose is:

> add a narrow stable weak residual path for the existing scalar 1D Heat/Burgers regime, with deterministic clean/noisy/coarse robustness comparisons against the current spectral/analytic path, while preserving canonical data and generator-family contracts.

`v0.8` is intentionally narrow.
It is not a broad numerics, PDE-zoo, or adapter release.

---

## Stable Scope

Stable `v0.8` scope is limited to:

- `pdelie.residuals.evaluate_weak_heat_residual(...)`
- `pdelie.residuals.evaluate_weak_burgers_residual(...)`
- window-indexed weak residual reports rather than field-shaped residual arrays
- canonical scalar 1D uniform periodic `FieldBatch` inputs only
- Heat and Burgers only
- deterministic clean/noisy/coarse robustness comparisons against the current `spectral_fd` / analytic path

Stable `v0.8` release definition:

`canonical FieldBatch -> stable weak residual report APIs for Heat/Burgers -> deterministic clean/noisy/coarse robustness comparisons against the current spectral/analytic path`

---

## Exact Public API Contracts

Planned stable public APIs:

- `evaluate_weak_heat_residual(field, *, diffusivity: float | None = None) -> dict[str, Any]`
- `evaluate_weak_burgers_residual(field, *, diffusivity: float | None = None) -> dict[str, Any]`

These are stable runtime report-style APIs under `pdelie.residuals`.

---

## Weak Residual Output Family

Frozen output-family rules:

- the primary output is a window-indexed report
- the stable output shape is `(batch, time_window, x_window, var)`
- the stable scalar slice keeps `var = 1`
- the report is not a field-shaped residual array
- exact report keys are deferred to M1

---

## Weak Method Family

Frozen method-family rules:

- local compact spacetime windows
- separable polynomial test functions
- integration by parts shifts derivatives off `u` where the frozen PDE identity allows
- exact polynomial degree, window lengths, overlap/stride, quadrature rule, and normalization are deferred to M1

`v0.8` does not commit to a broad user-configurable weak-form framework.

---

## PDE Identities

Frozen PDE-identity starting points:

- Heat starts from `u_t - nu u_xx = 0`
- Burgers starts from conservative form `u_t + 1/2 (u^2)_x - nu u_xx = 0`
- sign-consistent weak identities are frozen in M1

---

## Scope Limits

Stable `v0.8` scope is further limited to:

- canonical `FieldBatch` only
- scalar `("batch", "time", "x", "var")` only
- uniform time only
- uniform periodic rectilinear `x` only
- finite unmasked values only
- Heat/Burgers only

---

## Explicit Non-goals

Out of stable `v0.8` scope:

- no stable weak derivative API
- no stable `ResidualBatch` / `ResidualEvaluator` integration
- no stable KdV API
- no multidimensional expansion
- no multivariable expansion
- no nonuniform-grid support
- no operator-method expansion
- no adapter expansion
- no new canonical object

---

## Milestones

Planned `v0.8` sequence:

- Milestone 0 — roadmap reset
- Milestone 1 — weak semantics freeze
- Milestone 2 — weak residual report implementation
- Milestone 3 — optional contract-integration exploration
- Milestone 4 — robustness comparison layer
- Milestone 5 — optional KdV stress
- Milestone 6 — release gate
