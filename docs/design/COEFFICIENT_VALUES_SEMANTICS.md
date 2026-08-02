# Coefficient Values — Semantics

**Status:** binding from v0.38e.

What a coefficient array *is*, and the two different questions people ask about
whether two of them are "the same".

## The two questions

They get asked in the same words and have different answers.

**"Are these the same stored array?"** — same dtype, same shape, same bits.
Asked when deduplicating artifacts, checking a cache is valid, or reproducing a
run byte-for-byte. Answered by `storage_representation_identity`.

**"Do these represent the same physical field?"** — agreeing to within a
declared tolerance, whatever their dtype or memory layout. Asked when checking
that a co-transformation produced the background it was supposed to. Answered by
`scientific_identity`.

A `float32` view and a `float64` view of the same coefficient are **scientifically
identical and not storage-identical**. Both answers are correct; they answer
different questions.

## Why conflating them is a defect

Use storage identity for a scientific question and a dtype cast reads as a
different physical field — the run gets flagged for a difference that does not
exist. Use scientific identity for a storage question and two arrays that differ
in the last few bits read as interchangeable, so a cache returns the
lower-precision one and nothing records that it did.

Neither failure is loud. Both produce a number.

## The rules

### Separate functions, no shared implementation

`storage_representation_identity` and `scientific_identity` are separate public
functions. Neither is implemented in terms of the other, and neither takes a
flag that turns it into the other. A single function with a `tolerance=None`
switch is the conflation with extra steps: every call site then has to be read
to find out which question was asked.

### Storage identity is exact and takes no tolerance

There is no approximate version of "same bits". A tolerance parameter on it
would only ever be used to make it answer the other question.

### Scientific identity requires a declared metric

`scientific_identity` takes an `ErrorMetricSpec`. There is no default.

A default tolerance is a claim nobody made, attributed to whoever reads the
result. v0.37c pilot 1 blocked because a bound derived in `‖·‖∞` was compared
against a measurement emitted in `‖·‖₂` — a ratio of `11.96` between two numbers
that both looked like "the error". Requiring the spec makes that mismatch a
`ScopeValidationError` instead of a silent factor of twelve.

### Scientific identity is not transitive

`a ≈ b` and `b ≈ c` within tolerance does not give `a ≈ c`. Approximate equality
is reflexive and symmetric but **not** transitive, so it is not an equivalence
relation and cannot induce equivalence classes.

The practical consequence: it must never back a hash, a set, or a dict key. A
container keyed on approximate equality has membership that depends on insertion
order, which is a bug that reproduces only sometimes.

Storage identity *is* an equivalence relation and may back a hash.

### Storage identity implies scientific identity, never the converse

Identical bits agree under every metric. The reverse fails by construction —
that is the entire reason both exist. Both directions are asserted as
properties, including a case where scientific identity holds and storage
identity does not, so the implication is known to be strict rather than
vacuous.

## What neither function does

Neither decides whether a *transformation* was correct. They compare two arrays.
Whether the second should have equalled the first is a question about the
declared action, answered by the co-action consistency report — a different
module, deliberately.
