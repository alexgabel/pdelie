# Contributing to PDELie

PDELie is a reusable research library. Keep changes paper-agnostic, contract-driven, and numerically verifiable.

## Source of Truth

Read these before changing runtime behavior or public interfaces:

- [`docs/specs/SPEC.md`](docs/specs/SPEC.md)
- [`docs/specs/CONTRACTS_AND_DEFAULTS.md`](docs/specs/CONTRACTS_AND_DEFAULTS.md)
- [`docs/specs/ARCHITECTURE.md`](docs/specs/ARCHITECTURE.md)
- [`docs/specs/API_STABILITY.md`](docs/specs/API_STABILITY.md)

Use [`docs/planning/ROADMAP.md`](docs/planning/ROADMAP.md) for release direction and [`docs/planning/PLAN.md`](docs/planning/PLAN.md) for current execution state.

## Stable Boundaries

The stable `v0.x` scope is intentionally conservative:

- uniform rectilinear grids, with strongest support for scalar 1D periodic data
- synthetic PDE data and strict structured ingestion
- Lie point symmetries
- canonical polynomial `GeneratorFamily` objects
- runtime-only formula-backed generator records
- frozen invariant, reporting, orbit, downstream-discovery, and split-provenance reports

Do not implement these unless a frozen scope explicitly asks for them:

- neural generators
- Python-callable or executable-string generator APIs
- advanced weak-form methods beyond frozen weak-report slices and supportability reports
- operator symmetry
- multidimensional or nonuniform-grid expansion
- paper-specific experiment logic
- broad dataset adapters or file-based dataset loaders
- broad discovery-backend frameworks
- public KS runtime APIs
- train/test policy, split creation, leakage prevention, or heldout-leakage management

## Development Workflow

For nontrivial changes:

1. inspect the relevant specs and tests
2. plan the smallest release-appropriate change
3. implement one milestone or concern at a time
4. add focused tests before broad release-gate tests
5. update docs when interfaces or claims change
6. report ambiguity instead of silently expanding scope

Do not conflate report-only diagnostics with policy. PDELie may summarize readiness, confidence, provenance, and downstream contracts, but it does not decide benchmark success, train/test validity, or manuscript claims.

### Freezing a number: hypothesis → pilot → confirmatory

Any change that adds a constant a test asserts against — a threshold, a tolerance, a seed, a pinned fixture value, a label vocabulary, an axis or unit convention — follows the three-phase process in `docs/design/DESIGN_FREEZE_PROCESS.md`:

1. **Hypothesis freeze**, written *before* implementation. Names the quantity, enumerates the inputs, states the decision rule, and leaves every threshold unset. Includes an invalidation clause: what would make the hypothesis *wrong* rather than merely unmet.
2. **Pilot.** Prototype code, run outside the package. Every quantity produced by two independent routes or checked against a closed form. Report the spread, not a single draw. Probe the degenerate inputs.
3. **Confirmatory freeze**, written *after* the pilot. Thresholds now set, each justified from the measured spread. Every branch of any new vocabulary shown reachable on real input.

Keep the hypothesis after amending it. Across v0.33–v0.35, sixteen of twenty-one frozen contracts changed on contact with measurement, and the diff between hypothesis and confirmatory freeze is what every release-readiness note since has been written from.

### Comparing numbers across platforms

Three CI failures in three releases had the same cause: a claim measured on one platform and recorded as universal. Every assertion comparing numeric artifacts must declare a class from `docs/design/CROSS_PLATFORM_PORTABILITY_CLASSES.md`:

| Class | Bit-equality | Examples |
|---|---|---|
| `exact_discrete` | **required** | IDs, split membership, boolean masks, `.npz` round-trip, `semantic_hash` output |
| `tolerance_numeric` | forbidden | derivatives, residuals, design and Gram matrices, coefficients, metrics |
| `qualitative_invariant` | forbidden | SVD subspaces (compare principal angles), QR permutations on tied norms (compare the objective) |
| `platform_specific_diagnostic` | never asserted | BLAS config, timings, iteration counts |

**The rule that would have caught all three failures:** if any floating-point arithmetic happens between input and output, bit-equality is the wrong assertion. A `.npz` round-trip is `exact_discrete` because it is pure file I/O; comparing that file against a fresh *rebuild* is not, because the rebuild ran the computation again.

Any claim of equality between two implementations — or between a fixture and a rebuild — either runs in the portability lane on Linux **and** macOS (`@pytest.mark.portability`, budgeted at 30 tests) or is narrowed to a tolerance or invariant claim. On a cross-platform failure, reclassify rather than widen the tolerance: widening hides regressions, reclassifying states what is actually true.

### Language PDELie does not use

These terms must not appear in v0.36 production paths (`tests/test_forbidden_language.py`):

| Term | Why |
|---|---|
| `wsindy` | PDELie does not implement WSINDy and makes no WSINDy benchmark claim |
| `noise_robust`, `noise-robust`, `noise robustness` | no noise-robustness claim is made or supported |

The scan covers declared v0.36 source paths only. Modules shipped before v0.36 deliberately *name* these terms in order to refuse them — "It is not WSINDy and makes no noise-robustness claim" — and prose documentation must be able to say what it disclaims. Flagging a disclaimer as a violation would push the codebase toward silence, which is the opposite of the intent.


### Deleting merged branches — verify by patch identity, not by diff

Sub-milestone branches are **squash-merged**, so a merged branch is never an ancestor of `main` and its tip commit SHA never appears in `main`'s history. Two common checks give the wrong answer here:

- `git branch --merged` omits squash-merged branches entirely — they look unmerged.
- `git diff main..<branch>` is actively misleading. It reports `main`'s *subsequent* work as deletions on the branch side. A fully-merged `feat/v0.34a` showed **24 files changed, 1322 deletions** against `main` — none of it unmerged work, all of it later milestones read backwards.

Use patch identity instead. `git cherry` marks a commit `-` when an equivalent patch already exists upstream, which is exactly the squash-merge case:

```bash
git fetch origin main
git cherry -v origin/main <branch>     # every line starts with '-'  ->  safe to delete
                                       # any line starts with '+'    ->  unique work, stop
```

Delete only when **every** line is `-`. Branches named `backup/*` or carrying unique commits are audited individually rather than swept — those names usually indicate a deliberate stash.

## Useful Commands

Install the test environment:

```bash
python -m pip install -e .[test]
```

Run focused tests:

```bash
python -m pytest tests/test_public_api.py tests/test_api_stability_audit.py tests/test_examples.py
```

Run the full suite:

```bash
python -m pytest
```

Validate notebooks structurally:

```bash
python scripts/check_notebooks.py
```

Build package artifacts:

```bash
python -m build --sdist --wheel
```

Check whitespace:

```bash
git diff --check
```

## Release Expectations

Every release should have:

- a frozen scope doc
- API stability updates for public surfaces
- a compact release gate
- examples or smoke coverage for new runtime surfaces
- release-readiness notes
- no accidental root exports

Current `v0.x` releases are Git-tag-only. Package-index publishing remains deferred until `v1.0` or later.
