# pdelie

Numerical discovery and verification of Lie symmetries for PDE data.

The current repository implements the current stable V0.x core with two synthetic PDE paths:

- synthetic 1D heat equation
- synthetic 1D Burgers equation
- uniform periodic grid
- `FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> VerificationReport`
- one stable derivative backend: `spectral_fd`
- one spatial-translation verification path

## Setup

### Conda environment

From the repo root:

```bash
conda env create -f environment.yml
conda activate pdelie-v0_1
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

Run the packaged MVP example module from the repo root:

```bash
python -m pdelie.examples.heat_vertical_slice
```

That exact command is validated in CI both after editable install and after built-wheel packaging smoke checks.

The packaged example currently demonstrates the Heat path only:

1. generate synthetic heat-equation data
2. compute `spectral_fd` derivatives
3. evaluate the analytic heat residual
4. fit the polynomial spatial-translation baseline
5. verify the generator on held-out heat batches

You can also call the example programmatically:

```python
from pdelie.examples import run_heat_vertical_slice_example

result = run_heat_vertical_slice_example()
print(result["verification_classification"])
```

## Current Scope

Included in the current MVP:

- canonical V0.1 objects and typed validation errors
- synthetic heat and Burgers data
- polynomial translation baseline only
- finite-transform verification only

Explicitly deferred:
- operator symmetry
- weak-form features
- broad adapters and interoperability work
- invariant/discovery contracts beyond the current slice
