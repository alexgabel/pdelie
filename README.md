# pdelie

Numerical discovery and verification of Lie symmetries for PDE data.

The current repository implements the stable V0.3 core on the frozen synthetic Heat/Burgers slice:

- synthetic 1D heat equation
- synthetic 1D Burgers equation
- uniform periodic grid
- `FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> InvariantMapSpec -> VerificationReport`
- one stable derivative backend: `spectral_fd`
- one stable invariant canonical object: `InvariantMapSpec`
- one runtime-only invariant path: `pdelie.invariants.InvariantApplier`
- one runtime-only backend-specific downstream bridge: `pdelie.discovery.to_pysindy_trajectories`

## Setup

### Conda environment

From the repo root:

```bash
conda env create -f environment.yml
conda activate pdelie
```

### Editable install

The environment file installs the package in editable mode with test dependencies.

To install manually from the repo root:

```bash
python -m pip install -e .[test]
```

## Run Tests

From the repo root:

```bash
python -m pytest
```

## Minimal End-To-End Example

Run the packaged example module from the repo root:

```bash
python -m pdelie.examples.heat_vertical_slice
```

That exact command is validated in CI both after editable install and after built-wheel packaging smoke checks.

The packaged example currently demonstrates the stable Heat verification path only:

1. generate synthetic heat-equation data
2. compute `spectral_fd` derivatives
3. evaluate the analytic heat residual
4. fit the polynomial spatial-translation baseline
5. verify the generator on held-out heat batches

V0.3 adds a stable invariant canonical object and narrow runtime-level invariant/downstream utilities, but it does not yet add a broad public discovery workflow.

You can also call the example programmatically:

```python
from pdelie.examples import run_heat_vertical_slice_example

result = run_heat_vertical_slice_example()
print(result["verification_classification"])
```

## Current Scope

Included in the current stable core:

- stable canonical objects and typed validation errors, including `InvariantMapSpec`
- synthetic heat and Burgers data
- polynomial translation baseline only
- finite-transform verification only
- single-generator invariant map support
- matched Heat/Burgers benchmark and release-gate checks in the test layer

Runtime-level public APIs in the frozen V0.3 slice:

- `pdelie.invariants.InvariantApplier` for single-generator periodic `x` uniform translation only
- `pdelie.discovery.to_pysindy_trajectories` for the narrow backend-specific PySINDy bridge

Explicitly deferred:
- multi-generator invariant machinery
- broad downstream discovery contracts
- operator symmetry
- weak-form features
- broad adapters and interoperability work
