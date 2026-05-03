# V0.22 Release Readiness

- package version: `0.22.0`
- git tag: `v0.22.0`
- release type: final Git-tag release

`v0.22.0` is a Git-tag-only release.
Do not publish to TestPyPI or PyPI for `v0.22.0`.

## Release Summary

`v0.22` closes the downstream discovery contracts slice:

```text
FieldBatch / orbit batch / bridge outputs / backend-native discovery result
-> JSON-compatible discovery summaries
-> optional recovery summary
-> downstream workflow report
```

## Public API Notes

New submodule-only runtime APIs:

- `pdelie.discovery.summarize_discovery_bridge_output(...)`
- `pdelie.discovery.summarize_discovery_result(...)`
- `pdelie.reporting.summarize_downstream_discovery_workflow(...)`
- `pdelie.examples.run_downstream_discovery_contracts_example(...)`

No root `pdelie` exports are added.

## Non-goals Preserved

- no split management or heldout-leakage detection
- no general discovery-backend framework
- no manuscript benchmark policy
- no file loaders or `xarray.Dataset` support
- no PDEBench/The Well adapters
- no multidimensional or nonuniform-grid stable support
- no new PDEs
- no KS runtime promotion
- no weak-form expansion
- no time-translation APIs
- no neural/callable generator APIs
- no operator-facing APIs

## CI Expectations

The current explicit release gate is:

- `v0_22-release-gate`

The workflow also keeps:

- full editable `python -m pytest`
- package build and clean-wheel smoke
- example smoke, including `python -m pdelie.examples.downstream_discovery_contracts`

## Local Validation Checklist

Before tagging `v0.22.0`, run:

```bash
python -m pytest
python -m build --sdist --wheel
python -m pdelie.examples.heat_vertical_slice
python -m pdelie.examples.kdv_vertical_slice
python -m pdelie.examples.reaction_diffusion_vertical_slice
python -m pdelie.examples.advection_diffusion_vertical_slice
python -m pdelie.examples.orbit_coverage_diagnostics
python -m pdelie.examples.invariant_workflow_summary
python -m pdelie.examples.translation_orbit_batch
python -m pdelie.examples.symmetry_candidate_validation
python -m pdelie.examples.formula_generator_validation
python -m pdelie.examples.generator_confidence_report
python -m pdelie.examples.external_data_readiness
python -m pdelie.examples.downstream_discovery_contracts
git diff --check
```

Expected build artifacts:

- `dist/pdelie-0.22.0.tar.gz`
- `dist/pdelie-0.22.0-py3-none-any.whl`

## Direct Tag Checklist

```bash
git tag v0.22.0
git push origin v0.22.0
```

Do not publish to TestPyPI or PyPI for `v0.22.0`.
