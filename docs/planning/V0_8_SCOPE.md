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
- the exact top-level report keys are:
  - `equation`
  - `equation_form`
  - `method_family`
  - `window_residuals`
  - `time_window_centers`
  - `x_window_centers`
  - `normalization`
  - `diagnostics`
- `equation = "heat_1d"` or `"burgers_1d"`
- `equation_form = "nonconservative"` for Heat
- `equation_form = "conservative"` for Burgers
- `window_residuals` has shape `(batch, n_time_windows, n_x_windows, 1)`
- `time_window_centers` and `x_window_centers` store the physical coordinates of the window-center indices
- `diagnostics` includes exactly:
  - `strong_form`
  - `weak_form`
  - `diffusivity`
  - `time_window_size`
  - `x_window_size`
  - `time_window_stride`
  - `x_window_stride`
  - `quadrature`
  - `test_function`
  - `periodic_x_wrapping`
  - `window_counts`
  - `max_abs_residual`
  - `l2_residual`

---

## Weak Method Family

Frozen method-family rules:

- local compact spacetime windows
- separable polynomial test functions
- integration by parts shifts derivatives off `u` where the frozen PDE identity allows
- the frozen base bump is:
  - `beta(s) = (1 - s^2)^2` for `|s| <= 1`
  - `beta(s) = 0` for `|s| > 1`
- the frozen bump derivatives are:
  - `beta'(s) = -4s(1 - s^2)` for `|s| <= 1`, else `0`
  - `beta''(s) = -4 + 12s^2` for `|s| <= 1`, else `0`
- the frozen separable test function is:
  - `phi(t, x) = beta(s_t) * beta(s_x)`
- the frozen local coordinates are:
  - `s_t = (t - t_c) / h_t`
  - `s_x = (x_local - x_c_local) / h_x`
- the frozen window sizes are:
  - time window size = `5` grid points
  - x window size = `9` grid points
- the frozen half-widths are:
  - time half-width = `2` time steps, so `h_t = 2 * dt`
  - x half-width = `4` x steps, so `h_x = 4 * dx`
- local support maps exactly to `[-1, 1]` in both coordinates
- the frozen test-function derivatives are:
  - `d_t(phi) = (1 / h_t) * beta'(s_t) * beta(s_x)`
  - `d_x(phi) = (1 / h_x) * beta(s_t) * beta'(s_x)`
  - `d_xx(phi) = (1 / h_x^2) * beta(s_t) * beta''(s_x)`
- the frozen window geometry is:
  - time stride = `1`
  - x stride = `1`
  - time windows use full support only and are centered on interior time indices
  - x windows are centered on every x index
  - no time padding, interpolation, or extrapolation is allowed
- periodic x windows are defined by integer index offsets, not raw coordinate subtraction:
  - x offsets are `[-4, -3, ..., 4] * dx`
  - sample indices are taken modulo `num_points`
  - `x_window_centers` stores the physical coordinate of the center index
  - local x support and derivatives are evaluated from these wrapped index offsets
- the frozen quadrature is the composite tensor-product trapezoidal rule on the native window grid
- the frozen normalization is `normalization = "none"`
- `window_residuals` store signed weak residual values, not absolute values
- the frozen method identifier is `method_family = "local_separable_quartic_bump_trapezoid_v1"`

`v0.8` does not commit to a broad user-configurable weak-form framework.

---

## PDE Identities

Frozen PDE-identity starting points:

- Heat starts from `u_t - nu u_xx = 0`
- Burgers starts from conservative form `u_t + 1/2 (u^2)_x - nu u_xx = 0`
- the frozen Heat weak integrand is `-u * d_t(phi) - nu * u * d_xx(phi)`
- the frozen Burgers weak integrand is `-u * d_t(phi) - 1/2 * u^2 * d_x(phi) - nu * u * d_xx(phi)`
- the frozen report strings are:
  - Heat:
    - `strong_form = "u_t - nu u_xx = 0"`
    - `weak_form = "-u phi_t - nu u phi_xx"`
  - Burgers:
    - `strong_form = "u_t + 1/2 (u^2)_x - nu u_xx = 0"`
    - `weak_form = "-u phi_t - 1/2 u^2 phi_x - nu u phi_xx"`
- boundary terms vanish because:
  - the compact bump vanishes at local time-window endpoints
  - the compact bump vanishes at local x-window endpoints
  - x sampling is periodic and wrapped by index
- M2 must preserve these signs exactly and must not flip residual orientation

---

## Scope Limits

Stable `v0.8` scope is further limited to:

- canonical `FieldBatch` only
- dims exactly `("batch", "time", "x", "var")`
- uniform time only
- uniform periodic rectilinear `x` only
- finite unmasked values only
- scalar `var` only
- at least `5` time points
- at least `9` x points
- `diffusivity=None` means use `field.metadata["parameter_tags"]["nu"]`
- Heat/Burgers only

---

## Explicit Non-goals

Out of stable `v0.8` scope:

- no stable weak derivative API
- no stable `ResidualBatch` / `ResidualEvaluator` integration
- no per-term public contribution arrays
- no stable KdV API
- no multidimensional expansion
- no multivariable expansion
- no nonuniform-grid support
- no operator-method expansion
- no adapter expansion
- no imported-field parity requirement in M1
- no new canonical object

---

## Benchmark Fixtures

Frozen `v0.8` M1 benchmark fixtures use only the existing native generators and robustness utilities.

Shared base sizes:

- `batch_size = 2`
- `num_times = 33`
- `num_points = 64`

Frozen fixtures:

- Heat clean:
  - `generate_heat_1d_field_batch(seed=8001, batch_size=2, num_times=33, num_points=64)`
- Heat noisy:
  - clean Heat fixture + `add_gaussian_noise(std_fraction=1e-3, seed=8002)`
- Heat coarse:
  - clean Heat fixture + `subsample_time(stride=2)` then `subsample_x(stride=2)`
- Burgers clean:
  - `generate_burgers_1d_field_batch(seed=8101, batch_size=2, num_times=33, num_points=64)`
- Burgers noisy:
  - clean Burgers fixture + `add_gaussian_noise(std_fraction=1e-3, seed=8102)`
- Burgers coarse:
  - clean Burgers fixture + `subsample_time(stride=2)` then `subsample_x(stride=2)`

Imported `FieldBatch` parity is explicitly deferred from M1 to M4.

Frozen `v0.8` M4 downstream robustness fixtures are separate from the M1 report-surface fixtures.
They benchmark downstream translation fitting and held-out verification, not raw residual magnitudes.

Shared M4 downstream settings:

- `train_batch_size = 4`
- `heldout_batch_size = 3`
- `num_times = 33`
- `num_points = 64`
- `noise_std_fraction = 1e-3`
- coarse degradation is exactly:
  - `subsample_time(stride=2)`
  - then `subsample_x(stride=2)`
- the wrong-generator control is fixed to the affine non-translation coefficient row:
  - `[0.0, 0.0, 1.0, 0.0]`

Frozen M4 Heat fixtures:

- clean training:
  - `generate_heat_1d_field_batch(seed=8401, batch_size=4, num_times=33, num_points=64)`
- clean heldout:
  - `generate_heat_1d_field_batch(seed=8402, batch_size=3, num_times=33, num_points=64)`
- noisy training:
  - clean Heat training + `add_gaussian_noise(std_fraction=1e-3, seed=8403)`
- noisy heldout:
  - clean Heat heldout + `add_gaussian_noise(std_fraction=1e-3, seed=8404)`
- coarse training:
  - clean Heat training + `subsample_time(stride=2)` then `subsample_x(stride=2)`
- coarse heldout:
  - clean Heat heldout + `subsample_time(stride=2)` then `subsample_x(stride=2)`

Frozen M4 Burgers fixtures:

- clean training:
  - `generate_burgers_1d_field_batch(seed=8501, batch_size=4, num_times=33, num_points=64)`
- clean heldout:
  - `generate_burgers_1d_field_batch(seed=8502, batch_size=3, num_times=33, num_points=64)`
- noisy training:
  - clean Burgers training + `add_gaussian_noise(std_fraction=1e-3, seed=8503)`
- noisy heldout:
  - clean Burgers heldout + `add_gaussian_noise(std_fraction=1e-3, seed=8504)`
- coarse training:
  - clean Burgers training + `subsample_time(stride=2)` then `subsample_x(stride=2)`
- coarse heldout:
  - clean Burgers heldout + `subsample_time(stride=2)` then `subsample_x(stride=2)`

Frozen M4 degraded-data success rule:

- M4 compares downstream translation recovery and held-out verification, not direct weak-report-vs-strong-residual magnitudes.
- Clean-data baseline requirements:
  - both the strong path and the weak path must be deterministic on repeated runs for Heat and Burgers
  - both paths must return either:
    - translation coefficients within `DEFAULT_TRANSLATION_SPAN_TOLERANCE` of the canonical translation reference, or
    - an explicit canonical translation reference fallback
  - both paths must achieve a first-epsilon wrong-vs-fitted median separation ratio of at least `5.0x` on clean Heat and clean Burgers
- Degraded-data robustness requirements:
  - for each PDE separately, at least one degraded condition in `{noisy, coarse}` must produce a weak-path robustness signal
  - a weak-path robustness signal exists only if the weak path is deterministic on repeated runs and one of the following is true:
    - contract-stability signal:
      - the weak path returns in-tolerance translation coefficients or an explicit canonical translation reference fallback, and
      - the strong path does not
    - separation signal:
      - the weak-path first-epsilon wrong-vs-fitted median separation ratio is at least `1.5x` the strong-path ratio, and
      - the weak-path ratio is at least `3.0x`
- M4 does not require the weak path to beat the strong path on every degraded fixture.
- Imported `FieldBatch` parity for M4 should reuse these same frozen fixtures after canonical ingestion, not introduce a second benchmark matrix.

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
