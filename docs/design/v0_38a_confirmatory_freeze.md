# v0.38a — Confirmatory Freeze

**Status: SIGNED.**

Signed after [`v0_38a_pilot_report.md`](v0_38a_pilot_report.md) run 1 met every
applicable criterion. Governed by
[`v0_38a_hypothesis_freeze.md`](v0_38a_hypothesis_freeze.md), frozen before any
v0.38a code was written.

## 1. What is frozen

**Row identity is `DesignRowLineage.identity()`.** v0.38a introduces no second
identity scheme. A parallel identity would be a second answer to one question,
and the two would eventually disagree.

**A mask stores identities, never positions.** Positions are derived on demand
against a specific row set. A mask applied to a row set it does not describe —
truncated, extended, or foreign — is **refused**, not silently intersected. A
reordered set still resolves correctly, which is the property a boolean array
cannot provide.

**Five exclusion reasons**, growth-only, one per excluded row. An included row
carries none: `None` and `"included"` are not both allowed to mean admissible.
Reason counts report zeros, so "excluded by nothing" and "never checked" are
distinguishable.

**`full_field_derivatives_available` is derived**, computed from which
derivatives were actually produced. No constructor accepts it, and a test
asserts that absence rather than relying on it not having been written.

**Composition intersects the admitted set**, commutatively and associatively. A
doubly-excluded row keeps the left reason and records the discarded one, because
"excluded for one reason" and "excluded for two" are different diagnostic
situations. Masks over different row sets, or the same rows in different orders,
are refused.

## 2. What this freeze establishes

- A design-matrix filter, sort or concatenation can no longer silently re-point
  a mask. It either still applies or says it does not.
- An excluded row is always traceable to exactly one stated reason.
- Availability of derivatives cannot be asserted by a caller.

## 3. What this freeze does **not** establish

- **No irregular differentiation.** Deciding a stencil does not fit is here;
  computing a derivative on a non-uniform grid is v0.38b.
- **No detection logic.** Every reason is constructible; none is yet produced by
  shipped code. The producers are owed by v0.38b, and the pilot report names
  which.
- **No accuracy claim.** v0.38a computes no derivative and reports no error.
- **No weak-form support**, no unstructured meshes, no arbitrary geometry, and
  no discovery claim.
- **No cross-platform claim.** Every check is `exact_discrete` — string identity
  and set membership, no floating-point threshold — so a replay is *expected* to
  agree exactly. That is an argument, not a measurement, and is recorded as one.

## 4. Signature

Signed. Changes to §1 after this point are amendments with dated entries.
