# PDELie - Execution Plan (V0.21)

**Status:** COMPLETE

**V0.21 is complete as the external data readiness report release**

This file is the completed execution record for the `v0.21` release series.

## Release Theme

`v0.21` adds one scoped supportability/reporting API:

> user-owned data -> canonical FieldBatch -> readiness report -> optional residual-evaluator preflight -> confidence/downstream workflows

The public claim is intentionally narrow. The release adds a JSON-compatible reporting helper and a JSON-only example. It does not add file loaders, Dataset support, broad adapters, resampling, metadata mutation, train/test policy, downstream contracts, new PDEs, KS promotion, weak-form expansion, time translation, neural/callable generator APIs, operator APIs, or root exports.

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

Authoritative scope:

- `docs/planning/V0_21_SCOPE.md`

`API_STABILITY.md` was updated when the public `v0.21` readiness reporting API landed.

## Milestone 0 - Scope Freeze

Freeze `v0.21` as an external-data readiness reporting release.

Closeout:

- added `docs/planning/V0_21_SCOPE.md`
- reset `PLAN.md` as the active `v0.21` execution record
- updated `ROADMAP.md` to record `v0.21` as the current completed release
- kept ingestion and numerical scope unchanged

## Milestone 1 - Semantics Freeze

Frozen public helper:

```python
pdelie.reporting.summarize_field_batch_readiness(
    field,
    *,
    residual_evaluator=None,
    expected_equation=None,
)
```

Frozen interpretation:

- readiness is empirical compatibility with current stable contracts, not proof of scientific validity
- reports are runtime summaries, not canonical objects
- residual preflight is optional
- metadata suggestions are report-only and conservative
- no file loaders ship in `v0.21`
- no Dataset support ships in `v0.21`

Frozen labels:

- `ready`
- `needs_attention`
- `not_ready`

Frozen component statuses:

- `passed`
- `warning`
- `failed`
- `not_configured`
- `unavailable`

## Milestone 2 - Readiness Helper

Implemented:

- `pdelie.reporting.summarize_field_batch_readiness(...)`

The helper reports canonical dims/shape, finite values, mask state, time and x coordinate compatibility, metadata completeness, optional expected-equation matching, conservative metadata suggestions, and optional residual-evaluator preflight.

## Milestone 3 - External Data Path Coverage

Validation added for:

- generated Heat, Burgers, KdV, Fisher-KPP, and advection-diffusion fields
- `from_numpy(...)` fields
- `from_xarray(...)` DataArray-derived fields when xarray is installed
- metadata-incomplete fields
- masked fields
- nonfinite fields
- multivariable fields
- nonperiodic metadata
- nonuniform coordinates
- endpoint-duplicated periodic grids when a domain-length tag exposes the duplication
- expected-equation mismatch
- residual-evaluator mismatch

## Milestone 4 - Example And Notebook Alignment

Implemented:

- `pdelie.examples.run_external_data_readiness_example(...)`
- command module: `python -m pdelie.examples.external_data_readiness`

The example emits JSON only and demonstrates:

- one ready `from_numpy(...)` Heat field
- one metadata-incomplete field
- one residual-evaluator mismatch

Tutorial material now points users to the public helper where external data is introduced.

## Milestone 5 - API / Public-surface Audit

Audit result:

- `summarize_field_batch_readiness(...)` is importable only from `pdelie.reporting`
- `run_external_data_readiness_example(...)` is importable only from `pdelie.examples`
- root `pdelie` remains unchanged
- `API_STABILITY.md` documents the new reporting helper and example runner
- no file loader, Dataset adapter, PDEBench/The Well adapter, multidimensional/nonuniform stable API, resampling API, metadata mutation API, new PDE, KS runtime API, weak-form expansion, split/leakage policy, time-translation API, operator API, neural/callable generator API, or root export landed

## Milestone 6 - Release Gate And Readiness

Implemented:

- added compact `tests/test_v0_21_release_gate.py`
- updated CI so the current explicit release gate is `v0_21-release-gate`
- kept full editable `python -m pytest`
- kept package smoke and added field-readiness smoke coverage
- bumped package metadata to `0.21.0`
- updated README, changelog, publishing notes, roadmap, and release readiness docs
- documented direct `v0.21.0` Git-tag release path

Required checks before tagging:

- `v0_21-release-gate`
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
- `python -m pdelie.examples.external_data_readiness`
- `git diff --check`
