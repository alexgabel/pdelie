# v0.38c — Confirmatory Freeze

**Status: SIGNED.**

Signed after [`v0_38c_pilot_report.md`](v0_38c_pilot_report.md) run 1 met every
criterion. Governed by
[`v0_38c_hypothesis_freeze.md`](v0_38c_hypothesis_freeze.md).

## 1. The distinction this sub-phase establishes

**A weak row is a window; a strong row is a sample.** They are different objects
with different identities, and the identity sets are **disjoint by
construction** — a `DesignRowLineage` identity is a bare hex digest and a weak
identity carries the `weakwin:` prefix, so a collision is unrepresentable rather
than improbable.

This matters because the rest of the v0.38 arc's defects began as two things
sharing one name.

## 2. What is frozen

**Two quadrature rules, and no third.** `nonuniform_trapezoidal` is derived from
the coordinates; `user_supplied_validated_weights` is **validated, not trusted**.
An unrecognised rule is refused rather than mapped onto the nearest admitted one
— approximating a rule nobody asked for produces a payload describing a
computation nobody performed.

**Validation is exactness on the constant.** A rule that cannot integrate `1`
over its own interval is not a quadrature rule. The tolerance is
`n · eps · interval_length` — **derived** from the arithmetic of summing `n`
weights, the same pattern as v0.38b's FN-12 amendment, and measured attainable
with ~50× margin at spacing ratio 79.

**Failing weights are refused, never renormalised.** Renormalising would hide
the failure while silently turning the caller's declared rule into a different
one. A test asserts the caller's array is not mutated.

**Linear exactness is measured and reported, not required.** Trapezoidal
achieves it; a caller's rule legitimately might not, and refusing on that basis
would reject valid rules of other orders.

**Overlap is declared.** Two windows sharing samples are not independent
evidence, and a report listing window residuals without the overlap fraction
invites them to be read as if they were.

**`diagnostic_only_v0_38`, not `diagnostic_only`.** Release-scoped, and a test
asserts the unscoped key is absent so a consumer cannot read whichever it finds
first.

## 3. What this freeze does **not** establish

- **No accuracy bound on irregular quadrature.** The payload carries
  `irregular_quadrature_error_bounded: false` — stated rather than omitted,
  because a payload that leaves the question out reads as if it had been
  answered.
- **No replacement of the uniform weak form.** `weak_1d.py` is untouched and a
  test asserts its public surface is unchanged. This is a parallel path.
- **No derivative-error reporting.** v0.38d.
- **No discovery claim**, no unstructured meshes, no arbitrary geometry.
- **No cross-platform claim.** The namespace and vocabulary checks are
  `exact_discrete`; the quadrature errors are `tolerance_numeric` and a replay
  is owed.

## 4. Signature

Signed. Changes to §2 are amendments with dated entries.
