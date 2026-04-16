# PDELie — Specification (v0.x)

## Purpose

`pdelie` is a modular system for:

> Numerical discovery and exploitation of Lie symmetries in PDE data.

It is a **library**, not a project repo.

---

# 1. Scope

## Stable (v0.x)

- uniform rectilinear grids
- Lie point symmetries
- polynomial generator parameterizations
- synthetic + small benchmark PDEs

## Experimental

- neural generators
- weak-form extensions
- operator-level symmetry discovery
- multi-generator invariant charts

---

# 2. Pipeline

```text
FieldBatch
→ DerivativeBatch
→ ResidualBatch (via ResidualEvaluator)
→ GeneratorFamily
→ InvariantMap
→ InvariantLibrary
→ DiscoveryResult
→ VerificationReport
```

 All modules MUST use canonical objects.

---

# 3. Canonical Objects

## FieldBatch

Represents PDE data.

Constraints:
- dims authoritative
- ordering: ("batch", "time", spatial..., "var")
- uniform rectilinear grids only (V0.1 stable slice)
- coords must define domain + centering
- metadata must include BCs, grid type, parameters

---

## DerivativeBatch

Contains derivatives + provenance:
- backend (`spectral_fd` stable in V0.1; `spectral` / `finite` / `weak` reserved)
- smoothing parameters
- boundary assumptions

---

## ResidualEvaluator

Interface:

```text
evaluate(FieldBatch, DerivativeBatch?) → ResidualBatch
```

Defines symmetry target.

---

## ResidualBatch

- residual values
- residual type (analytic / weak / surrogate / operator)
- normalization

---

## GeneratorFamily

- parameterization type
- coefficients
- normalization
- diagnostics

---

## InvariantMap

- generator(s)
- mapping definition
- validity (local/global)

---

## DiscoveryResult

- discovered model
- coefficients
- feature library
- validation metrics

---

## VerificationReport

- norm
- epsilon sweep
- held-out evaluation
- classification: exact / approximate / failed

---

# 4. Residual Ontology

Symmetry is always defined relative to a residual.

No symmetry fitting is allowed without a residual.

---

# 5. Identifiability

Generators MUST satisfy:

- normalization (||X|| = 1)
- comparison via span (not coefficients)
- closure diagnostics if multi-generator

---

# 6. Verification Protocol

Every symmetry must be validated using:

- relative L2 norm
- epsilon sweep (logspace 1e-4 → 1e-1)
- held-out initial conditions
- held-out parameter sets

Outputs must include:
- error vs ε curve
- residual error
- classification

---

# 7. Grid Policy

Supported:
- uniform rectilinear grids

Representable but unstable:
- nonuniform rectilinear

Unsupported:
- unstructured meshes

---

# 8. Preprocessing

Preprocessing MUST be logged.

Allowed:
- dtype conversion
- coordinate harmonization
- mild denoising

Restricted:
- normalization
- amplitude scaling
- aggressive smoothing

---

# 9. Serialization

All canonical objects MUST:

- include `schema_version`
- support `.to_dict()` / `.from_dict()`
- be JSON-compatible

---

# 10. Final Rule

If ambiguous:

→ choose the simplest, verifiable implementation
