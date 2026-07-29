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
