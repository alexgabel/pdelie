# v0.38c — Pilot Report

**Append-only.** Blocked runs retained unedited.

Pre-registered in [`v0_38c_hypothesis_freeze.md`](v0_38c_hypothesis_freeze.md) §4.

Platform: `Darwin/arm64`, CPython 3.12, NumPy 2.5.1.

---

## Run 1 — passed

### Trapezoidal exactness (B-5)

| grid | spacing ratio | constant error | derived tolerance | linear (relative) |
|---|---:|---:|---:|---:|
| uniform, 40 nodes | 1.00 | `0.00e+00` | `2.66e-14` | `0.00e+00` |
| irregular, 40 nodes | 78.77 | `3.55e-15` | `1.87e-13` | `0.00e+00` |

The derived tolerance `n · eps · interval_length` is attainable with ~50×
margin on a grid whose spacing ratio is nearly 80. Linear exactness is **exact**
on both, which is a property of the rule rather than of the spacing.

### Identity namespaces (B-3)

```
strong: 47daf9b7d68fad5b0739c3c8...      (bare SHA-256 hex)
weak  : weakwin:326e8588560063353bd4...  (prefixed)
```

**Disjoint by construction**, not by chance: a `DesignRowLineage` identity is a
bare hex digest and can never begin with `weakwin:`. A collision is not merely
improbable, it is unrepresentable.

### Window overlap (B-4 of the freeze's §4 list)

Four windows of four samples each over ten distinct samples:

```
sample_slots_total 16   distinct_samples 10   shared_slots 6
overlap_fraction 0.375  windows_are_independent False
```

Reported, so window residuals cannot be read as independent evidence without
the reader seeing that 37.5% of the sample slots are shared.

### Refusals (B-1, B-2)

| input | outcome |
|---|---|
| `rule="simpson"` | refused — *"is not one of \['nonuniform_trapezoidal', …\]"* |
| unit weights over a length-3 interval | refused — *"sum to 4.0 over an interval of length 3.0"* |

### B-6 — norms

**PASS.** The constant check is an absolute error against a derived absolute
tolerance in the same units; the linear check is reported both absolutely and
relative to a stated scale. No number is a relative error against a near-zero
denominator.

---

## No amendments

Every criterion passed on the first run.

Stated plainly rather than presented as a virtue: v0.38c's checks are
structural and algebraic — namespace disjointness, closed vocabulary, exactness
on a constant — with a single derived tolerance carried over from a pattern
v0.38b had already established and measured. There was less here for a pilot to
catch than in v0.38b, where a threshold had to be discovered.

Block count is diagnostic, not a score. See `docs/planning/LEADERSHIP_METRICS.md`.
