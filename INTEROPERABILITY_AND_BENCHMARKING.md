This document is non-normative.
All contracts are defined in SPEC.md.

# INTEROPERABILITY & BENCHMARKING CONTEXT

## PURPOSE

This document defines:

- external datasets to support
- competing / complementary methods
- data formats and canonical representation
- preprocessing invariants
- benchmarking and verification protocols

Goal:

> Make `pdelie` a **hub** that connects PDE data → symmetry generators → invariants → downstream methods.

NOT a silo.

---

# CORE DESIGN PRINCIPLE

## Canonical internal representation

ALL external data must be converted to a unified format:

```python
FieldBatch(
    values,              # array-like
    dims,                # ("batch", "time", spatial..., "var")
    coords,              # coordinate arrays (authoritative)
    var_names,           # ["u", "v", ...]
    metadata,            # structured metadata (see below)
    preprocess_log       # transformations applied
)
```

### FieldBatch contract (STRICT)

- dims MUST be explicit and authoritative 
- spatial axes MUST be ordered and named (x, y, z)
- time is optional (stationary PDEs allowed)
- grids MUST be structured rectilinear in v0.x
- coordinates MUST specify:
  - node-centered vs cell-centred
  - domain bounds
- metadata MUST include:
  - PDE family (if known)
  - boundary conditions (periodic, Dirichlet Neumann)
  - grid regularity (uniform/nonuniform)
  - parameter tags (per-trajectory coefficients)
- multivariate fields:
  - encoded via var axis (channel-last)
- missing data:
  - MUST be represented via masks or NaNs

---

## Canonical pipeline objects

ALL stages must produce structured outputs:
- FieldBatch
- DerivativeBatch
- ResidualEvaluator
- GeneratorFamily
- InvariantMap
- InvariantLibrary
- DiscoveryResult
- VerificationReport

These are stable contracts, not implementation details.

---

## Residual abstraction (CORE)

All symmetry fitting MUST be defined relative to a residual:

```python
class ResidualEvaluator:
    def evaluate(field: FieldBatch) -> ResidualBatch
```

Supported residual types:
- analytic PDE residual
- weak-form residual
- learned surrogate residual
- operator pushforward residual

---

## SUPPORTED DATA FORMATS

### Tier 1 (MUST support)

- HDF5
- NumPy (.npz)
- in-memory NumPy arrays
- xarray Dataset / DataArray

---

### Tier 2 (SHOULD support)

- netCDF
- Zarr
- Mathematica HDF5 exports

---

### Tier 3 (DO NOT prioritize)

- custom solver-specific formats
- proprietary binary formats

---

## DATASET ADAPTERS

All adapters MUST convert external data into the canonical FieldBatch format.

### Required adapters

```python
from_hdf5_pdebench(...)
from_hdf5_thewell(...)
from_numpy(...)
from_xarray(...)
from_wolfram_hdf5(...)
from_sympy_expression(...)
```

### Export adapters

```python
to_xarray(...)
to_netcdf(...)
to_zarr(...)
to_pysindy_library(...)
to_neuraloperator_dataset(...)
to_json_report(...)
```

## KEY DATA SOURCES

### 1. PDEBench

- structured HDF5 PDE rollouts
- canonical benchmark
---

### 2. The Well

- large-scale multi-physics dataset
- stress testing only in v0.x

---

### 3. Wolfram / Mathematica

- GT symmetry validation
- exact PDE control

---

### 4. SymPy

- symbolic validation only

---

### 5. RealPDEBench (future)

- real + simulated PDE data
- paired experiments

**Use later for:**
- robustness validation

---

## SCOPE (x0.x)

Stable:
- structured-grid PDE data
- Lie point symmetries only
- polynomial generator parameterisations
- small PDE set (heat, Burgers, wave)

Experimental:
- neural generators
- weak-form advanced variants
- operator symmetry

---

## IDENTIFIABILITY CONVENTIONS

Generators are not unique.


Therefore:
- generators MUST be normalised (e.g. unit norm)
- comparison MUST be via span, not coefficients
- closure MUST be evaluated via Lie bracket residual
- approximate symmetries MUST be labeled explicitly

---


## PREPROCESSING (CRITICAL INVARIANT)

Preprocessing is a transformation and MUST be tracked.

### Allowed before symmetry discovery

- dtype conversion
- coordinate harmonization
- mild denoising

### Restricted

- normalisation
- amplitude scaling
- aggresive smoothing

---

## REQUIRED: preprocessing log

```json
{
  "transform_type”: "...",
  “parameters”: {...},
  "invertible": true/false
}
```

## Preprocessing Modes

### Mode 1: `physical`

- minimal transforms

---

### Mode 2: `analysis`

- smoothing/interpolation

---

### Mode 3: `ml_standardized`

- normalization/batching

---

## DERIVATIVE PROVENANCE

Each DerivativeBatch MUST include:

- backend (spectral / finite diff / weak)
- smoothing parameters
- boundary assumptions
- stencil / spectral config

---

## VERIFICATION PROTOCOL (STRICT)

Every symmetry claim MUST report:

- norm used (L2 / relative / normalized)
- ε-range for finite transforms
- held-out initial conditions
- held-out parameter sets
- error vs ε curve
- residual error vs baseline

Verification must distinguish:

- exact symmetry
- approximate symmetry
- failure

---

## FAILURE MODES

- dataset symmetry ≠ PDE symmetry
- derivative noise
- overexpressive generators
- conditioning vs symmetry confusion

---

## LIBRARY POSITIONING

pdelie is:

A bridge from PDE data → symmetry → invariants → downstream methods.

---

## ROADMAP

### v0.1

- FieldBatch contract
- polynomial symmetry detection
- spectral derivatives
- PDEBench integration

### v0.2

- invariant coordinate pipeline
- weak-form derivatives

### v0.3

- NeuralOperator integration
- operator symmetry (experimental)

## FINAL INSTRUCTION FOR AGENT

When extending the code:

1. Respect canonical contracts
2. Track all transformations
3. Validate all results numerically
4. Use simplest correct implementation
5. Distinguish stable vs experimental code
