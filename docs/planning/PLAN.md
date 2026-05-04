# PDELie - Execution Plan (V0.24)

**Status:** COMPLETE

**V0.24 is complete as the weak-form supportability reset release**

This file is the completed execution record for the `v0.24` release series.

## Release Theme

`v0.24` adds weak-form supportability reporting:

> existing Heat/Burgers weak residual reports + explicit weak contracts + strong residual evidence + robustness/imported-parity diagnostics + internal identity-first Fisher-KPP feasibility -> JSON-compatible weak-form supportability report

The public claim is intentionally narrow. The release reports supportability of the existing frozen Heat/Burgers weak residual report slice and diagnostic-only internal feasibility evidence. It does not add a weak derivative backend, weak design matrices, WSINDy, weak sparse recovery, weak KdV, weak KS, public weak reaction-diffusion APIs, new PDEs, broad adapters, split policy, neural/callable APIs, operator APIs, or root exports.

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

Authoritative scope:

- `docs/planning/V0_24_SCOPE.md`

`API_STABILITY.md` was updated when the public `v0.24` reporting helper landed.

## Milestone 0 - Scope Freeze

Freeze `v0.24` as a weak-form supportability reset.

Closeout:

- added `docs/planning/V0_24_SCOPE.md`
- reset `PLAN.md` as the active `v0.24` execution record
- updated `ROADMAP.md` to record `v0.24` as the current completed release
- explicitly kept WSINDy, weak design matrices, weak sparse recovery, and weak derivative backends out of scope

## Milestone 1 - Semantics Freeze

Frozen public helper:

```python
pdelie.reporting.summarize_weak_form_supportability(
    *,
    weak_report=None,
    weak_report_summary=None,
    weak_contract=None,
    strong_residual=None,
    strong_residual_summary=None,
    robustness=None,
    imported_parity=None,
    feasibility=None,
    thresholds=None,
    extra_metrics=None,
)
```

Frozen interpretation:

- supportability labels are `supported_existing_slice`, `diagnostic_only`, `failed`, and `insufficient_evidence`
- `supported_existing_slice` covers only the frozen public Heat/Burgers weak residual report surface
- weak contracts normalize equation, test-function, operator-order, integration-by-parts, patch, quadrature, row-count, skipped-patch, and finite-value-policy metadata
- quadrature is recorded in every weak supportability report
- malformed/nonfinite evidence raises typed validation errors unless a nested report already encodes failure
- no scalar weak confidence score
- no WSINDy implementation, weak design matrix, weak sparse recovery, weak derivative backend, weak KdV, weak KS, or public weak reaction-diffusion API

## Milestone 2 - Reporting Helper

Implemented:

- `pdelie.reporting.summarize_weak_form_supportability(...)`

The helper reuses `summarize_weak_residual_report(...)` and `summarize_residual_batch(...)`, validates strict JSON compatibility, derives weak contracts from frozen weak report diagnostics when useful, applies local thresholds, and returns deterministic component statuses and supportability labels.

## Milestone 3 - Internal Feasibility Harness

Implemented test-only Fisher-KPP feasibility diagnostics under `tests/_helpers`.

The harness is identity-first:

- constant-field identity check
- pure-time sign check
- pure-space Fourier integration-by-parts check
- manufactured smooth Fisher-KPP-like weak identity check
- generated Fisher-KPP field sanity check
- quadrature and tolerance recording
- no-public-export guards

This evidence remains `diagnostic_only` regardless of numerical quality.

## Milestone 4 - Example and Docs

Implemented:

- `pdelie.examples.run_weak_form_supportability_example(...)`
- command module: `python -m pdelie.examples.weak_form_supportability`

The example emits JSON only, demonstrates Heat/Burgers weak supportability through public APIs, and includes a static internal Fisher-KPP feasibility marker. It does not import `tests/_helpers`.

Docs now state explicitly that PDELie weak residual reports are not WSINDy.

## Milestone 5 - API / Public-surface Audit

Audit result:

- weak supportability summaries are importable only from `pdelie.reporting`
- the JSON example is importable only from `pdelie.examples`
- root `pdelie` remains unchanged
- `API_STABILITY.md` documents the new runtime helper and example runner
- no weak derivative backend, weak KdV, weak KS, public weak reaction-diffusion API, weak residual evaluator subclass, broad adapter, new PDE, time-translation API, operator API, neural/callable generator API, split policy, or root export landed

## Milestone 6 - Release Gate And Readiness

Implemented:

- added compact `tests/test_v0_24_release_gate.py`
- updated CI so the current explicit release gate is `v0_24-release-gate`
- kept full editable `python -m pytest`
- kept package smoke and added weak-form-supportability smoke coverage
- bumped package metadata to `0.24.0`
- updated README, changelog, publishing notes, roadmap, and release readiness docs
- documented direct `v0.24.0` Git-tag release path

Required checks before tagging:

- `v0_24-release-gate`
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
- `python -m pdelie.examples.split_leakage_provenance`
- `python -m pdelie.examples.weak_form_supportability`
- `python scripts/check_notebooks.py`
- `git diff --check`
