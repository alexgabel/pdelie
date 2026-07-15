# Generator-Confidence Additive Fields (v0.32b — frozen)

**Status:** FROZEN by v0.32b. Machine-readable form: `configs/planning/v0_32_method_scores_scope.json`.

**Decision label:** `v0_32b_generator_confidence_additive_method_scores_uncertainty_calibration`.

## Purpose

v0.32b extends `pdelie.reporting.summarize_generator_confidence` with three additive optional fields:

- `method_scores`
- `uncertainty_report`
- `calibration_report`

The existing `confidence_label` categorical vocabulary and every `component_statuses` entry are **preserved verbatim**. Default calls to `summarize_generator_confidence(...)` without the new arguments produce semantically equivalent payloads (byte-identical apart from the frozen strict-JSON hardening described in the "Strictness migration" section below).

## Non-goals

- No scalar aggregate confidence probability. `method_scores` are method-native, not Bayesian posteriors.
- No renaming of `_CONFIDENCE_LABELS`. The frozen vocabulary `{"strong", "qualified", "failed", "insufficient_evidence"}` is invariant.
- No new symmetry method. No new `SymmetryCandidate` discriminator. No new PDE. No noise or WSINDy claim.
- No root `pdelie` export. No package version bump. No tag.

## Field shapes (frozen)

### `method_scores: dict[str, dict] | None`

Non-empty mapping from a stable score-name to a strict-JSON metadata block. `None` means "the method did not populate any scores this call" (equivalent-semantics for legacy callers).

Each score-name entry is a dict with **exactly** these keys:

```text
{
    "value":       float | None,              # finite scalar; NaN/Inf raise
    "direction":   "lower_is_better"          # frozen Literal set (see below)
                 | "higher_is_better"
                 | "diagnostic_only",
    "description": str,                       # non-empty; documents the score semantics
    "units":       str | None,                # optional; free-form units string or None
}
```

**Frozen direction vocabulary**:

```text
lower_is_better    # smaller value is preferred (e.g. residual)
higher_is_better   # larger value is preferred (e.g. classification F1)
diagnostic_only    # value is informational; direction is method-dependent
```

Unknown direction values raise `SchemaValidationError`.

**Booleans**: booleans MUST NOT appear as numeric scores. Boolean-shaped diagnostics belong on the method's `fit_diagnostics` or `provenance` blocks, preserving type identity.

### `uncertainty_report: dict | None`

`None` for point-estimate methods (default). When a method emits opt-in uncertainty:

```text
{
    "method":          "bootstrap"       # frozen Literal (extendable in later releases)
                     | "point_estimate",
    "resampling_unit": "batch"           # frozen Literal — FieldBatch batch/trajectory
                     | "trajectory"          only. Never spatial/temporal row bootstrap.
                     | "not_applicable",
    "sample_count":    int,              # >= 0; number of independent units observed
    "seed":            int | None,       # deterministic seed
    "interval_level":  float,            # in [0.0, 1.0]; e.g. 0.95
    "intervals":       dict[str, dict],  # score_name -> {"low": float | None, "high": float | None}
    "point_estimates": dict[str, float | None],  # score_name -> point estimate
    "failed_resamples": int,             # >= 0; retained explicitly
    "warnings":        list[str],
    "diagnostic_only": bool,             # ALWAYS True in v0.32b
}
```

Each interval entry: `{"low": float | None, "high": float | None}` — both bounds are finite floats or `None` (NaN/Inf raise). `None` means "the interval was not computed for this score" (e.g. too few independent units).

### `calibration_report: dict | None`

`None` for uncalibrated methods (default, including the built-in `polynomial_translation_svd`). When a caller supplies an explicit calibration target and method:

```text
{
    "method":          str,              # non-empty; method identifier
    "target":          str,              # non-empty; target identifier
    "sample_count":    int,              # >= 0
    "metrics":         dict[str, float | None],
    "warnings":        list[str],
    "diagnostic_only": bool,             # ALWAYS True in v0.32b
}
```

The v0.32b built-in method (`polynomial_translation_svd`) does NOT synthesize a calibration report. Every value in `metrics` is a finite float or `None` (NaN/Inf raise).

## Strictness migration

`summarize_generator_confidence` migrates from a permissive `_summary_payload` handler to the strict boundary:

```python
_validate_strict_json_compatible(payload, name="generator confidence summary")
```

**Behavior hardening**: previously, nested NaN/Inf values could survive into the emitted dict; v0.32b rejects them at the composition boundary via `SchemaValidationError`. No silent conversion to `None` — the caller is responsible for sanitizing inputs.

The three new fields, when `None`, appear as literal `None` in the payload (round-trips to `null` under `json.dumps(..., allow_nan=False)`).

## Built-in method: `polynomial_translation_svd`

`polynomial_translation_svd` populates `method_scores` with **exactly** these four frozen names:

| Name | Direction | Semantics |
|---|---|---|
| `span_distance` | `lower_is_better` | Post-selection SVD span-distance of the chosen translation-coefficient direction. |
| `residual_l2` | `lower_is_better` | L2 norm of the baseline residual field emitted by the residual evaluator. |
| `error_curve_max` | `diagnostic_only` | Maximum L2 norm of the finite-difference deltas across the polynomial basis. |
| `svd_condition_number` | `diagnostic_only` | Ratio of largest to smallest singular value from the SVD design matrix. |

By default:

- `method_scores` is populated (with `None` values only when a score is not computable, e.g. degenerate SVD).
- `uncertainty_report` is `None` — the caller opts in via `run_symmetry_method(...)` config.
- `calibration_report` is `None` — no built-in calibration target.

## Opt-in bootstrap uncertainty for `polynomial_translation_svd`

When the caller passes `config={"uncertainty": {"method": "bootstrap", "num_resamples": N, "seed": S, "interval_level": L, "min_units": M}}`:

- **Resampling unit**: `batch` — one trajectory (batch element) per unit. Row-level bootstrap is refused with `ScopeValidationError`; there is no silent fallback.
- **Independent-unit minimum**: `M` (default 8). If `field.values.shape[0] < M`, the report is emitted with `sample_count = actual`, empty `intervals`, an entry in `warnings`, and `intervals` values `{"low": None, "high": None}` — never a spurious interval.
- **Fit-per-resample**: each resample re-runs the full `fit_translation_generator` on the resampled `FieldBatch`. The bootstrap does NOT resample precomputed scalar scores.
- **Deterministic**: `np.random.default_rng(seed)` selects batch indices. Same seed + same field → byte-identical `intervals`.
- **Interval method**: percentile (`"percentile"`) — the interval endpoints are `numpy.quantile(samples, [(1-L)/2, (1+L)/2])`.
- **Failed resamples**: any resample whose fit raises is caught, counted in `failed_resamples`, and its scores are excluded from the interval computation.

Resource envelope for the default config (`num_resamples=64`, `min_units=8`, T=17, X=32): observed wall-clock ~2–5 s on a modest machine; peak memory dominated by the residual evaluator's per-resample working set.

## Public API surface

Additive on `summarize_generator_confidence`:

```python
def summarize_generator_confidence(
    *,
    # ... existing kwargs unchanged ...
    method_scores: Mapping[str, Any] | None = None,
    uncertainty_report: Mapping[str, Any] | None = None,
    calibration_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
```

`SymmetryMethodResult.method_scores` remains a simple `dict[str, float | None]` for backward compatibility with the v0.30.1 registry contract. The enriched-metadata form lives on the confidence report only. A new helper `pdelie.reporting.enrich_method_scores(...)` composes the two.

## References

- `configs/planning/v0_32_method_scores_scope.json` — machine-readable frozen shape.
- `docs/specs/LABEL_REGISTRY.md` — additive-fields note (v0.32b implementation).
- `docs/specs/API_STABILITY.md` — v0.32b stable-surface note.
- `src/pdelie/reporting/summaries.py::summarize_generator_confidence` — implementation.
- `src/pdelie/symmetry/methods/polynomial_translation_svd.py` — built-in method that emits the frozen four scores.
- `tests/test_v0_32b_method_scores_uncertainty.py` — 20+ contract tests.
