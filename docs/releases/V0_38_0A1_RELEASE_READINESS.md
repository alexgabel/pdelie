# V0.38.0a1 Release Readiness

## 1. Release Target

- package version: `0.38.0a1`
- git tag: `v0.38.0a1`
- release decision: `v0_38_0a1_action_semantics_preview`

**Git-tag-only.** Do not publish to TestPyPI or PyPI for `v0.38`. Publication
remains deferred to `v1.0`.

## 2. This is an alpha, and deliberately not a release candidate

**`v0.38.0a1`, not `v0.38.0-rc1`.**

An RC is feature-complete, with only release-blocking fixes expected after it.
v0.38a–d — irregular row masks, Fornberg non-uniform finite differences, the
irregular weak bridge, and derivative-error reporting — have not started. A
candidate cut before them would not represent the release it claims to
candidate, and every subsequent feature merge would contradict the label.

The sequence from here:

| Tag | Cut when |
|---|---|
| `v0.38.0a1` | **now** — day-zero + action-semantics hardening complete |
| `v0.38.0b1` | after v0.38a–d land and the public API is frozen, if broader integration testing remains |
| `v0.38.0-rc1` | after **all** Gates A–F pass and no planned feature remains |
| `v0.38.0` | defect corrections only after rc1 |

### What downstream consumers may do with this tag

**May:** pin it by exact commit for contract reconnaissance; develop golden-gate
tooling against it; exercise the action-semantics surface.

**May not:** produce final confirmatory evidence against it. The irregular-grid
layer that a variable-coefficient study needs is not in this alpha, and the
public API is not frozen until `b1`.

## 3. What shipped

### Breaking

**`inspect_pysindy_weak_pde_library` requires an explicit integer `seed`.**
Keyword-only, no default. Omission is a `TypeError`; `seed=None` — previously
"opt into nondeterminism" — raises. Announced at v0.36e naming v0.37, deferred
once, kept here. Migration: [`V0_38_SEED_MIGRATION.md`](V0_38_SEED_MIGRATION.md).

Payload shape unchanged: the frozen 27/28-key conditional schema and all seven
`seed_provenance` keys survive, with two now constant `False`.

### Two declaration-versus-execution defects, both found and both fixed

**A parameter action rescaled every numeric parameter.** `ActionRef` carried no
target, so a `scalar_rescale` meant for the viscosity also tripled the advection
speed on any problem with more than one parameter. Measured on `main`:
`{'nu_baseline': 0.1 → 0.3, 'advection_speed': 2.0 → 6.0}`.

No v0.37c case could observe it: each declares exactly one numeric parameter,
and on a one-element population "rescale all" and "rescale the declared one" are
the same function. Targets are now a declared field; ambiguity is **refused**,
not resolved by convention.

**The benchmark declared the wrong equation form.** `equation_form` was the
literal `"nonconservative"` on every case while the evaluators dispatched from
provenance and evaluated the **conservative** operator on every
variable-coefficient case. The forms differ by exactly `ν'·u_x`, which measures
`1.035×` the residual magnitude on the sinusoidal profile.

There is now one `EquationForm` enum, one resolver, and one
`ResolvedResidualOperator` consumed by both the spec and the report. A
declaration disagreeing with provenance **blocks** — even when the coefficient is
constant and the mismatch is numerically harmless, because that is precisely the
condition under which it survived a release.

**All 125 released v0.37c measurements are bitwise identical.** The corrections
moved declarations and hashes, not numbers.

### Added

- Two coefficient-array identities as separate helpers — storage-representation
  and scientific — with a non-transitive triple proving the second cannot back a
  hash.
- `ArtifactResolver`, injected explicitly; the global registry is asserted
  absent, not merely unwritten.
- `pdelie_action_coaction_consistency`, a 16-key payload.
- Benchmark cases **C-7** and **C-8**, the first with two numeric parameters.
- Three-layer periodicity validation — structural, values-and-slope, analytical.
- An additive artifact-correction register with append-only semantics.
- The first genuine `load_bearing_analytical` consumer, with a
  manufactured-solution oracle.

## 4. Process corrections landed alongside

Each of these was a guard that could pass for a reason unrelated to its claim.

| Guard | What was wrong |
|---|---|
| C-5 payload count | `str(count) in text` over a document containing "v0.37" sixteen times. Passed on the title; the table sat at 34 against a measured 37 for three payloads. |
| Forward promises | Asserted `src/` always contains an outstanding promise. Zero is the **good** state, and this release produced it. |
| v0.37b residual-layer scope | Diffed `v0.36.0..HEAD`, so a claim about a finished release was a permanent freeze on the layer. |
| Oracle registry | Population empty; every check vacuous. Now non-empty, with all four assertions live. |
| Benchmark case counts | Parsed from prose. Now generated from the registry, with CI diffing the rendered table. |

**Formatting policy** is now explicit: not formatter-governed through v0.38, one
mechanical PR afterwards, then `ruff format --check` permanently.

## 5. Known limitations carried forward

- **No irregular-grid support.** v0.38a–d. Not in this alpha.
- **Nonperiodic domains** — deferred to v0.41. The executor refuses them.
- **Monotone coefficients** — deferred to v0.41; follows the above.
- **`linear_combination_of_derivatives`** is declared and unsynthesised; no
  shipped case selects it, and a test fails if one does.
- **`fourier` and `linear` interpolation backends** are declared and
  unimplemented; they raise rather than falling back.
- **Every v0.38 number is macOS/arm64.** The v0.38e classifications are
  `exact_discrete`, so a replay is *expected* to agree exactly — an argument, not
  a measurement, and recorded as one.
- **The publish path is still unexercised.** Hardened at v0.36f, never run.

## 6. Verification

| Gate | Result |
|---|---|
| test suite | 2864 passed, 4 skipped |
| mypy | 147 errors in 29 files — baseline unchanged since v0.36 |
| ruff | clean |
| docs | `sphinx-build -W` clean |
| coverage | above the 85 floor |
| v0.37c regression | **125/125 bitwise identical** |
| v0.38e pilot | 2 runs, 1 blocked, 1 passed; both retained |
| v0.38e confirmatory | signed on a grid disjoint from the pilot |

## 7. Scope discipline

- `pdelie.__all__` unchanged — no new root exports.
- `discovery_task_result` keeps its 22-key schema, frozen since v0.30.1.
- One new `summary_type`, on a new payload from a new function, with a test
  asserting it has exactly one producer.
