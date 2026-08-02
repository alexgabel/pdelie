# Periodicity — Three Validation Layers

**Status:** binding from v0.38.

"Periodic" means three different things, and a declaration satisfying one is
routinely mistaken for satisfying all three.

| Layer | Question | Where |
|---|---|---|
| **Structural** | Is a periodic coordinate axis declared? | `ProfileGeometrySpec` |
| **Values** | Do the samples — *and their slope* — join across the wrap, to a declared tolerance? | `validate_periodicity` |
| **Analytical** | Does the source specification define a periodic function at all? | `classify_analytical_periodicity` |

## Why one layer is not enough

C-4 **passed** the structural check. Its bundle declared `periodic_uniform`, its
axis was periodic, and every gate agreed — while the profile was `tanh`, which is
nonperiodic by construction. At the seam it jumped `1.9998` against a typical
interior step of `0.3198`, a ratio of `6.25`. Structure said periodic, the values
said otherwise, and the analytical form had never been asked.

**A declaration must not pass merely because the metadata says periodic.**

## Why the derivative layer is separate

A profile can meet itself in value and still corner. `|sin x|` joins exactly at
the wrap — the values layer sees nothing wrong — and has a kink there. Measured:
value ratio `1.49`, derivative ratio `27.5`.

`periodic_smooth` is a claim about the *slope* across the seam, so a values-only
check would pass a profile that is continuous and not smooth.

## The ratios are scale-free

Both layers compare against the typical interior quantity, not an absolute
threshold. An absolute number would classify the same profile differently in
metres and kilometres, and would need a value nobody has measured.

The tolerance itself is **caller-declared with no default** — same rule as
`scientific_identity`. A defaulted tolerance is a claim nobody made.

## `not_evaluated` is not a pass

A layer that could not run reports `not_evaluated`. A check that did not happen
is not a check that succeeded, and `is_periodic_at_every_layer` refuses both.

Likewise `undetermined` is not `confirmed`: an unrecognised analytical form is an
absence of evidence. Assuming periodicity for want of a rule about a form is how
C-4 got through.

## Measured separation

| profile | value ratio | derivative ratio | verdict |
|---|---:|---:|---|
| sinusoidal | 1.57 | 0.28 | periodic at every layer |
| `tanh` (C-4 form) | large | large | fails values **and** derivative |
| `\|sin x\|` | 1.49 | 27.5 | joins in value, **kinks** |
