# BoundaryConditionSpec — Design Document

**Status:** DESIGN-FROZEN in v0.30a; **RUNTIME IMPLEMENTED in v0.30b** (internal helpers and FieldBatch 0.2 migration). Adapters accept structured nonperiodic specs in v0.30b; nonperiodic derivative and residual backends are deferred to v0.30c.

This document defines the structured representation that will replace the current string-only `metadata["boundary_conditions"]["x"]` in canonical `FieldBatch` objects. It is normative for v0.30 proper. The runtime in v0.30a is unchanged.

## Motivation

The current canonical `FieldBatch` carries boundary information as a free-form string under `metadata["boundary_conditions"]["x"]`. The only accepted value across the runtime is `"periodic"`, and this is enforced at every consumer site:

- ingestion: `src/pdelie/data/numpy_adapter.py:120-121` rejects everything ≠ `"periodic"`
- ingestion: `src/pdelie/data/xarray_adapter.py:114-115` rejects the same
- derivatives: `src/pdelie/derivatives/spectral_fd.py:32-33` rejects the same
- residuals: three sites in `src/pdelie/residuals/` enforce periodic-x at runtime — `advection_diffusion_1d.py:51-53`, `reaction_diffusion_1d.py:44-46`, `kdv_1d.py:32`
- weak residuals: `src/pdelie/residuals/weak_1d.py:106-107` enforces the same
- symmetry: two sites in `src/pdelie/symmetry/parameterization/polynomial_translation.py:34-35` and `:82-83`
- verification: `src/pdelie/verification/finite_transform.py:22-23`

Lifting any one of these requires knowing more about the boundary than a string can carry.

### Operational problem

A Dirichlet boundary without the boundary value cannot be used by a one-sided finite-difference stencil to produce a correct derivative at the boundary. A 2nd-order one-sided stencil that must extrapolate the missing boundary point produces O(h) error rather than O(h²). A string label `"dirichlet"` hides three pieces of information:

- the boundary value (e.g. `u(a) = 0`)
- which side the value applies to (left, right, or both)
- whether the value is time-dependent

A library that accepts string-only boundary metadata cannot tell whether `"dirichlet"` means "homogeneous Dirichlet" (boundary value zero), "inhomogeneous Dirichlet with the value embedded in `field.values`", or "Dirichlet, value not specified, user error to fit residuals here". Existing FD libraries (DeepXDE, deal.II, FEniCS) all use typed boundary objects for the same reason.

### Why not a wider string set

Widening to `{"periodic", "dirichlet", "neumann", "open"}` has the same problem at a different scale. `"dirichlet"` without a value is still unusable; `"open"` is ambiguous across PDE communities (outflow, absorbing, Sommerfeld, "finite domain unstated"); and time-dependent boundaries have no expression in a string.

## Proposed structured spec

`metadata["boundary_conditions"]["x"]` becomes a structured dict:

```
{
    "type": Literal["periodic", "dirichlet", "neumann", "open_unknown"],
    "left": BoundaryFace | None,
    "right": BoundaryFace | None,
    "specified": bool,
    "time_dependent": bool | None,
    "notes": str | None,
}
```

`BoundaryFace` is:

```
{
    "value": float | None,
    "time_dependent": bool,
    "source": Literal["user_supplied", "default", "inferred_unspecified"],
}
```

### Field semantics

- `type`: the boundary class. The set is closed; new types require a scope freeze.
- `left`, `right`: per-face data. `None` for the side where the boundary class makes no per-face value meaningful (e.g. `"periodic"` has no faces; both are `None`). Required for `"dirichlet"` and `"neumann"`; either may be `None` for one-sided constraints.
- `specified`: `True` iff every face that the boundary class requires has `value is not None` AND `source != "inferred_unspecified"`. Periodic is always `specified=True`. `open_unknown` is always `specified=False`.
- `time_dependent`: top-level convenience flag. `True` iff any face has `time_dependent=True`. `None` for boundary classes where the question doesn't apply (`periodic`, `open_unknown`).
- `notes`: free-form string for human-readable context; never load-bearing.

### Rename: `"open"` → `"open_unknown"`

In v0.30 the unspecified-finite-domain case is named `"open_unknown"`. The string `"open"` is intentionally not accepted because it carries different meanings in different PDE communities (outflow, absorbing, Sommerfeld, free-boundary). `"open_unknown"` makes the meaning explicit: "finite domain, boundary character unstated/unknown to PDELie; treat as needing user attention."

## Legacy compatibility

v0.30 bumps `FieldBatch.SCHEMA_VERSION` from `"0.1"` to `"0.2"` because the structural change is not a pure widening of accepted values.

`FieldBatch.from_dict` accepts both `"0.1"` and `"0.2"` payloads under a backwards-compatible loader:

- A `"0.2"` payload presents `boundary_conditions["x"]` already in structured form. The loader validates the structure against the spec above.
- A `"0.1"` payload presents `boundary_conditions["x"]` as a string. The loader normalizes:
  - `"periodic"` → `{"type": "periodic", "left": None, "right": None, "specified": True, "time_dependent": None, "notes": None}`
  - `"dirichlet"` → `{"type": "dirichlet", "left": {"value": None, "time_dependent": False, "source": "inferred_unspecified"}, "right": {"value": None, "time_dependent": False, "source": "inferred_unspecified"}, "specified": False, "time_dependent": False, "notes": "normalized from legacy 0.1 string"}`
  - `"neumann"` → analogous to `"dirichlet"`
  - `"open"` or `"open_unknown"` → `{"type": "open_unknown", "left": None, "right": None, "specified": False, "time_dependent": None, "notes": "normalized from legacy 0.1 string"}`
  - any other string → `ScopeValidationError`

In all `"0.1"` normalization cases the loader appends one entry to `preprocess_log`:

```
{
    "operation": "schema_0_1_to_0_2_boundary_normalization",
    "parameters": {
        "legacy_x_boundary": "<original string>",
        "normalized_specified": <bool>,
    },
}
```

This preserves provenance; downstream readiness reports can detect the synthetic normalization and warn appropriately.

`"0.1"` payloads whose boundary classes other than `"periodic"` are normalized **always** materialize with `"specified": False`. The library never invents boundary values.

## Readiness signaling

`summarize_field_batch_readiness` (in `src/pdelie/reporting/summaries.py`) gains a new field `"boundary_condition_warnings"`: a list of strings drawn from a frozen vocabulary:

- `"dirichlet_value_unspecified"` — type is `"dirichlet"` but `specified` is False
- `"neumann_value_unspecified"` — analogous for Neumann
- `"open_unknown_boundary"` — type is `"open_unknown"`
- `"boundary_normalized_from_legacy_schema"` — provenance recorded in `preprocess_log`
- `"boundary_time_dependent"` — any face has `time_dependent=True`; v0.30 derivative backends do not support time-dependent BCs

Any non-empty `boundary_condition_warnings` list downgrades the report's `readiness_label` from `"ready"` to at most `"needs_attention"`. The existing `_READINESS_LABELS = frozenset({"ready", "needs_attention", "not_ready"})` vocabulary is sufficient; no new label.

`"not_ready"` is reserved for hard failures (missing required metadata keys, non-finite values, non-uniform grid). Under-specified boundary conditions are recoverable by the user, so they degrade to `"needs_attention"`, not `"not_ready"`.

## Out of scope for v0.30

The following are deliberately deferred to later releases:

- time-dependent boundary value tables (Dirichlet/Neumann values that vary with `t`)
- mixed / Robin boundaries (`αu + β u_x = γ`)
- free-boundary problems (Stefan-type, moving interfaces)
- vector or tensor boundary conditions (multi-channel data, deferred to v0.34 multi-D/multi-channel scope)
- 2D and 3D boundary conditions (deferred to v0.34)
- nonuniform grids (`from_numpy` currently requires uniform; this does not change in v0.30)
- time-axis boundary conditions (initial / terminal-time conditions)

The scope of v0.30 is intentionally narrow: structured BC metadata, scalar 1D, uniform grids, time-independent boundary values only.

## Validation requirements (for v0.30 proper, not v0.30a)

When `BoundaryConditionSpec` lands:

- `FieldBatch.validate()` must enforce that `metadata["boundary_conditions"]["x"]` matches the structured shape exactly (for `schema_version == "0.2"`)
- `FieldBatch.from_dict` round-trip: `from_dict(d.to_dict()) == d` for both `"0.1"` and `"0.2"` payloads
- Strict JSON: `json.dumps(field.to_dict(), allow_nan=False)` succeeds for any valid `FieldBatch`
- All consumers (residuals, derivatives, weak, symmetry, verification) read `metadata["boundary_conditions"]["x"]["type"]` and not the raw string
- Adapters (`from_numpy`, `from_xarray`, `from_xarray_dataset`) accept both legacy string inputs (normalized internally) and pre-structured dict inputs

## Implementation pointer (for v0.30 proper)

The most surgical implementation places a new module `src/pdelie/contracts/boundary.py` (or extends `src/pdelie/contracts.py`) with:

- `BoundaryConditionSpec` dataclass and `BoundaryFace` dataclass
- `normalize_legacy_x_boundary(value: str) -> BoundaryConditionSpec` for the loader path
- `validate_x_boundary(spec: dict | BoundaryConditionSpec) -> BoundaryConditionSpec` for ingestion
- `_ALLOWED_X_BOUNDARY_TYPES = frozenset({"periodic", "dirichlet", "neumann", "open_unknown"})` matching the existing `frozenset` discipline (e.g. `_READINESS_LABELS`, `_CONFIDENCE_LABELS` in `summaries.py`)

The existing JSON-strict helpers (`_validate_strict_json_compatible` and `_json_safe` in the reporting layer) handle the serialization of the structured form without modification.
