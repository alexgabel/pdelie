# PDELie — Architecture

## Module layout

```text
pdelie/
data/
derivatives/
residuals/
symmetry/
parameterization/
fitting/
verification/
invariants/
discovery/
verification/
viz/
```

 ---

## Responsibilities

### data/
- load external datasets
- convert to FieldBatch

### derivatives/
- compute derivatives
- return DerivativeBatch

### residuals/
- define ResidualEvaluator implementations

### symmetry/
- parameterize generators
- fit generators
- verify generators

### invariants/
- construct invariant maps
- transform data

### discovery/
- PDE / model discovery

### verification/
- numerical validation
- generate VerificationReport

---

## Internal layering

Symmetry module MUST be split:

1. parameterization
2. fitting
3. verification

---

## Development order

1. FieldBatch
2. synthetic PDE data
3. derivatives
4. residual evaluator
5. generator fitting
6. verification
7. invariant maps
8. PDE discovery
