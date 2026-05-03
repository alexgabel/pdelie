# PDELie - Execution Plan (V0.22)

**Status:** COMPLETE

**V0.22 is complete as the downstream discovery contracts release**

This file is the completed execution record for the `v0.22` release series.

## Release Theme

`v0.22` adds downstream sparse-discovery supportability reports:

> FieldBatch / orbit batch / bridge outputs / backend-native discovery result -> JSON-compatible discovery summaries -> optional recovery summary -> downstream workflow report

The public claim is intentionally narrow. The release standardizes runtime contracts around downstream discovery inputs, backend-neutral result mappings, recovery summaries, and workflow composition. It does not add split management, leakage detection, broad backend frameworks, file loaders, Dataset support, new PDEs, KS promotion, weak-form expansion, time translation, neural/callable generator APIs, operator APIs, or root exports.

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

Authoritative scope:

- `docs/planning/V0_22_SCOPE.md`

`API_STABILITY.md` was updated when the public `v0.22` discovery/reporting APIs landed.

## Milestone 0 - Scope Freeze

Freeze `v0.22` as a downstream discovery contracts release.

Closeout:

- added `docs/planning/V0_22_SCOPE.md`
- reset `PLAN.md` as the active `v0.22` execution record
- updated `ROADMAP.md` to record `v0.22` as the current completed release
- kept numerical scope and ingestion scope unchanged

## Milestone 1 - Contract Semantics Freeze

Frozen public helpers:

```python
pdelie.discovery.summarize_discovery_bridge_output(
    trajectories,
    time_values,
    feature_names,
    *,
    source_field_id=None,
    provenance=None,
)

pdelie.discovery.summarize_discovery_result(
    result,
    *,
    target_terms=None,
    support_epsilon=1e-8,
    train_residual=None,
    heldout_residual=None,
    source_result_id=None,
)

pdelie.reporting.summarize_downstream_discovery_workflow(
    *,
    field_readiness=None,
    generator_confidence=None,
    orbit_batch=None,
    discovery_inputs=None,
    discovery_result=None,
    extra_metrics=None,
)
```

Frozen interpretation:

- reports are runtime summaries, not canonical objects
- bridge reports validate arrays and provenance without returning transformed `FieldBatch` objects
- discovery-result reports summarize coefficient matrices without copying them into output
- `target_terms` must be feature-keyed
- recovery summaries are empirical configured diagnostics, not benchmark success claims
- orbit-batch provenance checks are traceability reports only
- split/leakage diagnostics are deferred

## Milestone 2 - Bridge Output Summary

Implemented:

- `pdelie.discovery.summarize_discovery_bridge_output(...)`

The helper validates finite 2D trajectories, shared shape, strictly increasing time, unique feature names, and JSON-compatible provenance.

## Milestone 3 - Discovery Result And Recovery Summary

Implemented:

- `pdelie.discovery.summarize_discovery_result(...)`

The helper accepts backend-neutral and `fit_pysindy_discovery(...)`-style mappings, summarizes coefficients by compact norms/counts, handles backend failure mappings as reports, and optionally computes feature-keyed recovery summaries through `evaluate_discovery_recovery(...)`.

## Milestone 4 - Workflow Summary And Example

Implemented:

- `pdelie.reporting.summarize_downstream_discovery_workflow(...)`
- `pdelie.examples.run_downstream_discovery_contracts_example(...)`
- command module: `python -m pdelie.examples.downstream_discovery_contracts`

The example emits JSON only and combines field readiness, generator confidence, orbit-batch provenance, discovery bridge summaries, discovery-result summaries, and downstream workflow status.

## Milestone 5 - API / Public-surface Audit

Audit result:

- discovery summaries are importable only from `pdelie.discovery`
- downstream workflow summaries are importable only from `pdelie.reporting`
- the JSON example is importable only from `pdelie.examples`
- root `pdelie` remains unchanged
- `API_STABILITY.md` documents the new runtime helpers and example runner
- no split management, leakage detection, broad backend framework, file loader, Dataset adapter, new PDE, KS runtime API, weak-form expansion, time-translation API, operator API, neural/callable generator API, or root export landed

## Milestone 6 - Release Gate And Readiness

Implemented:

- added compact `tests/test_v0_22_release_gate.py`
- updated CI so the current explicit release gate is `v0_22-release-gate`
- kept full editable `python -m pytest`
- kept package smoke and added downstream-discovery-contracts smoke coverage
- bumped package metadata to `0.22.0`
- updated README, changelog, publishing notes, roadmap, and release readiness docs
- documented direct `v0.22.0` Git-tag release path

Required checks before tagging:

- `v0_22-release-gate`
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
- `python -m pdelie.examples.downstream_discovery_contracts`
- `git diff --check`
