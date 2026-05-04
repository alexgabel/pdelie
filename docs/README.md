# PDELie Documentation Index

This directory contains the tracked source of truth for PDELie contracts, planning, release history, and strategy notes.

## Normative Docs

Use these when changing runtime behavior or public interfaces:

- [`specs/SPEC.md`](specs/SPEC.md) - project scope, canonical pipeline, and stable/experimental boundaries
- [`specs/CONTRACTS_AND_DEFAULTS.md`](specs/CONTRACTS_AND_DEFAULTS.md) - executable object contracts and validation conventions
- [`specs/API_STABILITY.md`](specs/API_STABILITY.md) - stable public surface by release slice
- [`specs/ARCHITECTURE.md`](specs/ARCHITECTURE.md) - module responsibilities and layering

## Planning Docs

- [`planning/ROADMAP.md`](planning/ROADMAP.md) - authoritative release roadmap
- [`planning/PLAN.md`](planning/PLAN.md) - current or most recent execution plan
- `planning/V0_*_SCOPE.md` - frozen release scopes

Planning docs are release-management records. They do not override the specs.

## Release Docs

- [`releases/PUBLISHING.md`](releases/PUBLISHING.md) - publishing and tag policy
- `releases/V0_*_RELEASE_READINESS.md` - release closeout records and local validation checklists

Current `v0.x` releases, including `v0.27.0`, are Git-tag-only. PyPI/TestPyPI publishing remains deferred until `v1.0` or later.

## Strategy Notes

- [`strategy/INTEROPERABILITY_AND_BENCHMARKING.md`](strategy/INTEROPERABILITY_AND_BENCHMARKING.md) - non-authoritative research and interoperability notes

Strategy docs may describe future directions, but they do not commit a feature to a release.

## Tutorials

Tutorial notebooks live outside this directory:

- [`../notebooks/README.md`](../notebooks/README.md)

They are the recommended user entry point. Notebook outputs are runtime summaries, not API contracts or canonical artifact schemas.

## Contributor Guidance

- [`../CONTRIBUTING.md`](../CONTRIBUTING.md)

Local agent/context files are intentionally untracked. Durable contributor guidance belongs in tracked docs, not local tool-context files.
