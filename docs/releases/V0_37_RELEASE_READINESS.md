# V0.37 Release Readiness

## 1. Release Target

- package version: `0.37.0`
- git tag: `v0.37.0`
- release decision: `v0_37_0_parameter_equivariant_actions_and_admissibility_benchmark`
- support matrix: [`docs/specs/support_matrix.v0_37.json`](../specs/support_matrix.v0_37.json)

**Git-tag-only.** Do not publish to TestPyPI or PyPI for `v0.37`. Publication
remains deferred to `v1.0`; the path was hardened in v0.36f and has still never
been run.

## 2. Consolidation Policy

One tag, five sub-milestones.

| Sub-milestone | Scope | PRs |
|---|---|---|
| day-zero | forbidden-language extension, coverage ratchet 80→85, C-5 correction | #140 |
| v0.37a | problem-state and action contracts; no executable code | #141 |
| v0.37b | executable actions, six runtime paths, commutation report | #142 |
| v0.37c | six-case benchmark → hypothesis freeze, three pilots, signed confirmatory freeze | #143, #144, #145, #146 |
| v0.37d | downstream crash test, seven branches | #147 |

Submodule-only. `pdelie.__all__` unchanged, no existing payload changed shape,
no new PDE.

**Two new `summary_type` values**, both on new payloads from new functions:
`pdelie_problem_action_residual_relation` (v0.37b) and
`pdelie_downstream_task_with_action_bundle` (v0.37d).

## 3. Success Criteria

| # | Criterion | Outcome |
|---|---|---|
| 1 | Full problem/action contract triple, contracts before executables | **Met.** v0.37a shipped types and a 12-rule table with no executor; a test asserts the contract modules import no array library and define no `execute*`. |
| 2 | Seed transition hard-cut to `TypeError` | **Met, at a different layer.** See A-1. |
| 3 | Six runtime paths, each reachable and distinguishable | **Met.** P-1…P-6, with P-4 distinguished from P-3 by the *sign* of the coefficient shift. |
| 4 | Diagnostic fit never overrides an analytical decision | **Met, structurally.** `FittedOperatorDiagnostic` has no status, no boolean, no threshold; two adversarial cases fit at `r²=1.0` and stay `violated`. |
| 5 | Six-case admissibility benchmark, all distinguishable | **Met for five.** See A-3. |
| 6 | Two-stage freeze: no tolerance frozen before a pilot measures it | **Met, and it fired twice.** See §6. |
| 7 | Seven downstream branches, blocking before discovery | **Met, and measured.** Zero task invocations across the four blocked branches, with a sentinel proven able to fire. |
| 8 | `discovery_task_result` 22-key schema unchanged | **Met.** Regression-asserted; the augmented payload is a different type at 22+2. |

### Amendments

**A-1 — the seed moved layer rather than being weakened.** The plan put a
required `seed: int` on `ProblemActionBundle`. Implemented, then rejected by
`test_v0_37_binding_constraints.py` before it left the branch: every v0.37
action family is deterministic, so a seed there makes deterministic actions read
as stochastic and gives two mathematically identical bundles different
`semantic_hash` values. Moved to `ActionExecutionConfig`, still required with no
default, so omission is still a `TypeError`.

**A-2 — R-A9 does not exist, and its number is not reused.** It coupled
`boundary_action` back to a collapsed `relation_type`. With five independent
axes there is nothing to couple. A table that recycles numbers cannot be cited
in a review six months later.

**A-3 — C-4 retired.** `monotone_smooth` is `tanh`, which is nonperiodic by
construction, while every case declares `domain_type: periodic_uniform`. The
wrap discontinuity of `1.9998` — against a typical adjacent step of `0.3198` —
dominated the measurement. Retirement rather than restatement: a monotone
function is not periodic, so no periodic profile still measures what C-4 named.

**A-4 — the §6 obstruction bound was wrong and is fixed.** It kept only
`a·u_xx` and came in at `0.52`–`1.00` of the observed error: not a bound. The
operator is `(a·u_x)_x = a'·u_x + a·u_xx`. With both terms it holds at
`1.86`–`1.96×` on C-3 and `1.81`–`9.02×` on C-6.

## 4. Additions Beyond Frozen Scope

**A domain gate on the periodic roll.** `execute_state_action` refuses
`spatial_translation` on any `domain_type` but `periodic_uniform`. It changes no
v0.37 result — all cases are periodic — and closes the gap before nonperiodic
actions make it load-bearing.

**`absolute_error_linf` beside `absolute_error_l2`.** Added additively after
pilot 1 blocked: `absolute_error` alone is ambiguous in a report that gets cited.

**A periodicity guard on the profile registry.** The requirement was implicit
until C-4 violated it; a test now fails a nonperiodic profile at commit.

## 5. Known Limitations Carried Forward

- **Nothing about monotone coefficients.** C-4 is retired; that axis returns
  with nonperiodic actions.
- **Nothing about nonperiodic domains.** All five cases are periodic and the
  executor now refuses anything else.
- **`linear_combination_of_derivatives` is declared but not synthesised.** It
  reports `inconclusive` with a stated reason. No v0.37c case selects it, so the
  gap is inert here — a test fails if a future case does select it.
- **`fourier` and `linear` backends are declared and unimplemented.** They raise
  rather than falling back.
- **Every v0.37c number was measured on macOS/arm64.** The margins are eleven
  orders, so a cross-platform difference cannot plausibly change a
  classification — but that is an argument, not a measurement, and it is
  recorded as one in the confirmatory freeze.
- **The publish path is still unexercised.** Hardened at v0.36f, never run.
- **The weak-diagnostic seed cut did not happen, and its notice was corrected.**
  `inspect_pysindy_weak_pde_library` still accepts an omitted seed. Its
  `FutureWarning` said *"v0.37 will require an explicit integer seed"* — a
  promise this release does not keep, because v0.37a's freeze scoped the
  weak-diagnostic transition out explicitly and making an unscoped breaking
  change during a release close is worse than deferring one. The notice now
  names **v0.38**, and a test asserts the version it names is always still in
  the future, so this cannot silently recur.

## 6. Process Note — the two-stage freeze fired twice

This is the substantive contribution beyond feature delivery.

v0.37c ran **three** pilots. Two blocked, and each block caught a specification
defect that would otherwise have propagated into v0.37d and compounded there.

**Pilot 1 — an interface mismatch between two documents.** The freeze derived
bounds in `‖·‖∞`; the report emitted `‖·‖₂`. Ratio `11.96` on C-5. No tolerance
derived from those bounds could trace to what was measured.

**Pilot 2 — a self-contradictory specification.** Two defects: the §6 bound
dropped a term of the same order, and `monotone_smooth` was nonperiodic on a
domain every case declared periodic.

Neither was a code bug, and neither was reachable by **unit tests generated from the same defective specification** — which is the trap, not a general claim about testing. Both were reachable by other means: a manufactured-solution check, a symbolic expansion of the operator, a metamorphic property, or an execution-vs-declaration audit. The v0.37.1 C-5 finding proves the last of those — an audit asking *is the declared action the one the runner consumed?* would have caught it immediately. See `docs/design/ANALYTICAL_ORACLE_DISCIPLINE.md`.

Had the derivations been skipped and thresholds fitted to the pilot numbers,
they would have "worked" on every case, and the freeze would have shipped citing
bounds in a norm nobody had checked, over a case measuring a seam.

The pilot report retains all three runs unedited, with a test asserting it: a
report showing only the passing run is a selection-effect document.

## 7. Point-Symmetry Registry Decision

**The point-symmetry registry remains private per lack of citable write-up, and
per v0.37c's narrowed evidentiary base.**

The v0.37 plan made promotion contingent on whether v0.37c's benchmark taxonomy
is defensible as a public statement. It is not, for a reason the arc itself
produced: the benchmark validated a **five**-case taxonomy after retiring one
case for a specification defect, and its confirmatory freeze explicitly records
that it establishes nothing about monotone coefficients, nonperiodic domains, or
any platform other than macOS.

A public registry would be read as a claim about symmetry classification in
general. What v0.37c actually supports is narrower and is stated where it can be
read in full. The v0.35b reason for privacy — no citable write-up — is also
unchanged.

## 8. Verification

| Gate | Result |
|---|---|
| test suite | 2636 passed, 3 skipped |
| mypy | 147 errors in 29 files — baseline unchanged since v0.36 |
| ruff | clean |
| docs | `sphinx-build -W` clean |
| coverage | above the 85 floor ratcheted at day-zero |
| v0.37c pilot | 3 runs, 2 blocked, 1 passed; all retained |
| v0.37c confirmatory | 125 measurements on a disjoint grid, separation at every point |
