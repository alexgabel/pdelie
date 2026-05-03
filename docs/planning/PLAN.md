# PDELie - Execution Plan (V0.20)

**Status:** COMPLETE

**V0.20 is complete as the unified generator confidence report release**

This file is the completed execution record for the `v0.20` release series.

## Release Theme

`v0.20` adds one scoped supportability/reporting API:

> residual / fit / verification / candidate-validation / orbit diagnostics -> JSON-compatible generator confidence report -> categorical evidence label and component statuses

The public claim is intentionally narrow. The release adds a JSON-compatible reporting helper and a JSON-only example. It does not add a scalar confidence score, train/test policy, downstream success policy, new PDEs, KS promotion, weak-form expansion, broad adapters, time translation, neural/callable generator APIs, operator APIs, or root exports.

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

Authoritative scope:

- `docs/planning/V0_20_SCOPE.md`

`API_STABILITY.md` was updated when the public `v0.20` confidence reporting API landed.

## Milestone 0 - Scope Freeze

Freeze `v0.20` as a reporting/supportability release.

Closeout:

- added `docs/planning/V0_20_SCOPE.md`
- reset `PLAN.md` as the active `v0.20` execution record
- updated `ROADMAP.md` to record `v0.20` as the current completed release
- kept numerical scope unchanged

## Milestone 1 - Semantics Freeze

Frozen public helper:

```python
pdelie.reporting.summarize_generator_confidence(...)
```

Frozen interpretation:

- confidence is categorical empirical evidence, not proof
- no scalar score ships in `v0.20`
- reports are runtime summaries, not canonical objects
- thresholds are caller-configured when they are not already encoded by existing reports

Frozen labels:

- `strong`
- `qualified`
- `failed`
- `insufficient_evidence`

Frozen component statuses:

- `passed`
- `warning`
- `failed`
- `not_configured`
- `unavailable`

## Milestone 2 - Reporting Helper

Implemented:

- `pdelie.reporting.summarize_generator_confidence(...)`

The helper reuses existing reporting helpers for residual, generator, fit, verification, candidate-validation, coverage, consistency, and orbit evidence. Existing reporting schemas remain unchanged.

## Milestone 3 - Examples And Notebook Alignment

Implemented:

- `pdelie.examples.run_generator_confidence_report_example(...)`
- command module: `python -m pdelie.examples.generator_confidence_report`

The example emits JSON only and demonstrates:

- one `strong` direct-SVD Heat case with configured residual and verification thresholds
- one `qualified` formula-candidate case with partial empirical validation

Tutorial material now points users to the public helper for confidence summaries while retaining notebook display helpers as non-normative display glue.

## Milestone 4 - Cross-PDE Confidence Coverage

Validation added for:

- direct-SVD passing evidence
- reference-fallback qualified evidence
- partial candidate validation
- failed candidate validation
- residual threshold failure
- insufficient evidence
- coverage, consistency, and orbit report composition

Existing Heat, Burgers, KdV, Fisher-KPP, and advection-diffusion vertical-slice paths remain unchanged.

## Milestone 5 - API / Public-surface Audit

Audit result:

- `summarize_generator_confidence(...)` is importable only from `pdelie.reporting`
- `run_generator_confidence_report_example(...)` is importable only from `pdelie.examples`
- root `pdelie` remains unchanged
- `API_STABILITY.md` documents the new reporting helper and example runner
- no new PDE, KS runtime API, weak-form expansion, broad adapter, scalar score, train/test policy, time-translation API, operator API, neural/callable generator API, or root export landed

## Milestone 6 - Release Gate And Readiness

Implemented:

- added compact `tests/test_v0_20_release_gate.py`
- updated CI so the current explicit release gate is `v0_20-release-gate`
- kept full editable `python -m pytest`
- kept package smoke and added confidence-report smoke coverage
- bumped package metadata to `0.20.0`
- updated README, changelog, publishing notes, roadmap, and release readiness docs
- documented direct `v0.20.0` Git-tag release path

Required checks before tagging:

- `v0_20-release-gate`
- `editable-tests`
- `package-smoke`

Local validation checklist:

- `python -m pytest`
- `python -m build --sdist --wheel`
- `python -m pdelie.examples.heat_vertical_slice`
- `python -m pdelie.examples.kdv_vertical_slice`
- `python -m pdelie.examples.reaction_diffusion_vertical_slice`
- `python -m pdelie.examples.advection_diffusion_vertical_slice`
- `python -m pdelie.examples.orbit_coverage_diagnostics`
- `python -m pdelie.examples.invariant_workflow_summary`
- `python -m pdelie.examples.translation_orbit_batch`
- `python -m pdelie.examples.symmetry_candidate_validation`
- `python -m pdelie.examples.formula_generator_validation`
- `python -m pdelie.examples.generator_confidence_report`
- `git diff --check`
