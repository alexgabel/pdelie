# PDELie

[![CI](https://github.com/alexgabel/pdelie/actions/workflows/ci.yml/badge.svg)](https://github.com/alexgabel/pdelie/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/pdelie/badge/?version=latest)](https://pdelie.readthedocs.io/en/latest/?badge=latest)
![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue)
![Version](https://img.shields.io/badge/version-0.29.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

PDELie is a research library for empirical Lie-symmetry diagnostics on controlled PDE time-series data. It turns canonical scalar 1D periodic fields into residuals, generator candidates, configured validation, finite-transform verification, confidence summaries, supportability reports, invariant/orbit diagnostics, and downstream discovery reports.

Hosted documentation: <https://pdelie.readthedocs.io/en/latest/>

![PDELie pipeline](docs/assets/pdelie_pipeline.svg)

The current stable release is `v0.30.0` / **V0.30**: nonperiodic-readiness and low-order finite-difference derivative diagnostics. It adds structured boundary-condition metadata (`FieldBatch.SCHEMA_VERSION` bump `0.1` → `0.2`), a `finite_difference` derivative backend for `u_t`, `u_x`, `u_xx` on scalar 1D nonperiodic uniform grids, a `compute_derivatives(backend="auto")` dispatcher, interior-only residual diagnostics for the Heat / Burgers / advection-diffusion / reaction-diffusion strong evaluators, non-blocking ruff / mypy / coverage hygiene, and a narrow declarative release-gate consolidation. KdV, weak evaluators, and translation finite-transform verification remain periodic-only. The V0.29 workflow recipes and support matrix are retained; the V0.28 narrow scalar `xarray.Dataset` path remains part of the stable data surface. No root API expansion; `numpy<2` and Python 3.11-only CI matrix unchanged.

## Choose Your Workflow

Helpers below are imported from their documented submodules, not from root `pdelie`.

- **I have PDE data.** Start with Dataset or `FieldBatch` readiness, then run residual preflight before trusting downstream evidence: `pdelie.reporting.summarize_xarray_dataset_readiness(...)`, `pdelie.data.from_xarray_dataset(...)`, and `pdelie.reporting.summarize_field_batch_readiness(...)`.
- **I have a candidate generator or transform.** Use configured validation and finite-transform verification rather than an unqualified symmetry claim: `pdelie.symmetry.validate_symmetry_candidate(...)`, `pdelie.verification.verify_translation_generator(...)`, and `pdelie.reporting.summarize_generator_confidence(...)`.
- **I want downstream/export provenance.** Summarize bridge arrays, discovery outputs, orbit provenance, and user-supplied partitions before handing data to sparse discovery or ML workflows: `pdelie.discovery.summarize_discovery_bridge_output(...)`, `pdelie.reporting.summarize_downstream_discovery_workflow(...)`, and `pdelie.reporting.summarize_split_leakage_provenance(...)`.

For the full stable surface and PDE support matrix, see [`docs/specs/API_STABILITY.md`](docs/specs/API_STABILITY.md) and [`docs/specs/SUPPORT_MATRIX.md`](docs/specs/SUPPORT_MATRIX.md).

## Install

Core editable install:

```bash
python -m pip install -e .
```

CI/test/tutorial install:

```bash
python -m pip install -e .[test]
```

Focused optional extras:

```bash
python -m pip install -e .[viz]         # Matplotlib plotting helpers
python -m pip install -e .[xarray]      # xarray DataArray/Dataset ingestion
python -m pip install -e .[downstream]  # narrow PySINDy bridge path
```

The downstream path is intentionally narrow and currently validated on the PySINDy 1.x / scikit-learn 1.2.x line under Python `<3.12`.

## 60-Second Example

```python
from pdelie.data import generate_heat_1d_field_batch, split_batch_train_heldout
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry import fit_translation_generator
from pdelie.verification import verify_translation_generator
from pdelie.reporting import (
    summarize_generator_confidence,
    summarize_generator_fit_diagnostics,
    summarize_residual_batch,
    summarize_verification_report,
)

field = generate_heat_1d_field_batch(batch_size=5, num_times=33, num_points=64, seed=0)
train, heldout = split_batch_train_heldout(field, train_size=2, seed=1)

evaluator = HeatResidualEvaluator()
derivatives = compute_spectral_fd_derivatives(train)
residual = evaluator.evaluate(train, derivatives)
generator = fit_translation_generator(train, evaluator, epsilon=1e-4)
verification = verify_translation_generator(heldout, generator, evaluator)

confidence = summarize_generator_confidence(
    residual=summarize_residual_batch(residual),
    generator=generator,
    fit_diagnostics=summarize_generator_fit_diagnostics(generator),
    verification=summarize_verification_report(verification),
    thresholds={"residual_rms": 1e-5, "verification_first_error": 5e-4},
)

print(confidence["confidence_label"])
print(confidence["component_statuses"])
```

## Tutorial Path

New users should start with `notebooks/`. The recommended first pass is:

1. `notebooks/00_pde_timeseries_to_generators.ipynb` - PDE time series to generator evidence.
2. `notebooks/09_xarray_dataset_ingestion.ipynb` - V0.28 Dataset readiness and scalar-variable ingestion.
3. `notebooks/02_robustness_sweeps.ipynb` - residual, fit, span, and verification diagnostics under perturbation.
4. `notebooks/06_orbit_coverage_diagnostics.ipynb` - invariant coverage, consistency, read-only orbit reports, and materialized orbit batches.
5. `notebooks/12_dataset_to_downstream_workflow.ipynb` and `notebooks/13_candidate_to_split_provenance_workflow.ipynb` - V0.29 end-to-end workflow recipes.
6. `notebooks/10_scope_decisions_and_weak_supportability.ipynb` and `notebooks/11_multi_generator_diagnostics.ipynb` - supportability, no-go, and multi-generator diagnostic boundaries.

The notebooks are tutorials, not API contracts. They do not define train/test policy, leakage safety, threshold policy, or manuscript success criteria.

## Stable Scope

PDELie is intentionally conservative. The stable `v0.x` surface currently covers:

- canonical objects: `FieldBatch`, `DerivativeBatch`, `ResidualBatch`, `GeneratorFamily`, `InvariantMapSpec`, `VerificationReport`
- uniform rectilinear grids, with the strongest support for scalar 1D periodic fields
- synthetic Heat, Burgers, normalized short-horizon KdV, Fisher-KPP reaction-diffusion tagged as `reaction_diffusion_fisher_kpp`, and constant-coefficient advection-diffusion tagged as `advection_diffusion_constant_coefficient`
- `spectral_fd` derivatives through `u_xxxx`
- polynomial translation-generator fitting and finite-transform verification
- JSON-compatible reporting helpers for residuals, weak reports, weak supportability, fits, verification, confidence, readiness, invariant workflows, downstream discovery contracts, and split-provenance diagnostics
- algebraic span/closure diagnostics for supplied polynomial `GeneratorFamily` objects, including diagnostic handling of rank-deficient well-formed families
- uniform `x`-translation coverage, consistency, read-only orbit reports, and materialized orbit batches
- empirical validation of `GeneratorFamily`, `InvariantMapSpec`, and safe formula-backed `FormulaGeneratorFamily` candidates
- narrow structured ingestion through `from_numpy(...)`, optional `from_xarray(...)`, and optional scalar `from_xarray_dataset(...)`
- narrow optional downstream support through PySINDy bridge utilities and backend-neutral discovery reports

The authoritative public surface is documented in [`docs/specs/API_STABILITY.md`](docs/specs/API_STABILITY.md).
The compact support matrix and selected helper inventory live in [`docs/specs/SUPPORT_MATRIX.md`](docs/specs/SUPPORT_MATRIX.md).

## What PDELie Is Not

PDELie is not:

- a mathematical proof engine
- a neural symmetry-detector training framework
- a broad PDEBench/The Well adapter layer
- a file-loader or broad data-adapter framework
- a general nonuniform or multidimensional PDE framework
- a split manager, leakage-prevention tool, or benchmark policy layer
- an operator-learning framework
- a paper-specific experiment pipeline

KdV remains intentionally frozen to the normalized scalar 1D periodic short-horizon strong path: no custom KdV initial-condition API, configurable KdV coefficients, general KdV regime support, or weak KdV API is promoted. KS remains internal feasibility/no-go evidence, including an internal KS diagnostic sweep; no stable KS runtime API is promoted. Weak-form methods beyond the frozen Heat/Burgers weak-report slice and `v0.24` supportability reporting layer remain deferred.

## Examples

Packaged examples print JSON-compatible runtime summaries:

```bash
python -m pdelie.examples.heat_vertical_slice
python -m pdelie.examples.kdv_vertical_slice
python -m pdelie.examples.kdv_scope_decision
python -m pdelie.examples.multi_generator_diagnostics
python -m pdelie.examples.data_ecosystem_feasibility
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
python -m pdelie.examples.split_leakage_provenance
python -m pdelie.examples.weak_form_supportability
```

These are smoke/reporting examples, not canonical artifact schemas.

## Validation

The current release is validated by:

- the explicit `v0_30-release-gate` CI job
- full editable `python -m pytest`
- built-wheel package smoke
- packaged example smoke
- notebook structural validation through `python scripts/check_notebooks.py`
- `git diff --check`

Package-index publishing is deferred until `v1.0` or later. Current `v0.x` releases are Git-tag-only.

Build the documentation site locally with:

```bash
python -m pip install -r docs/requirements.txt
sphinx-build -b html -W --keep-going docs docs/_build/html
```

The docs site renders committed notebook outputs and does not execute notebooks during the build.

## Documentation

- Hosted docs: <https://pdelie.readthedocs.io/en/latest/>
- Docs index: [`docs/README.md`](docs/README.md)
- Read the Docs config: [`.readthedocs.yaml`](.readthedocs.yaml)
- Contracts and specs: [`docs/specs/`](docs/specs/)
- Public API stability: [`docs/specs/API_STABILITY.md`](docs/specs/API_STABILITY.md)
- Roadmap and planning: [`docs/planning/`](docs/planning/)
- Release readiness: [`docs/releases/`](docs/releases/)
- Tutorials: [`notebooks/README.md`](notebooks/README.md)
- Contributor guide: [`CONTRIBUTING.md`](CONTRIBUTING.md)
