# CONTRACTS AND DEFAULT EVALUATION CONVENTIONS

This document defines the **strict executable layer** of the PDELie system.

These rules ensure:

1. reproducibility  
2. comparability across implementations  
3. numerical verifiability  

These rules override any ambiguous or higher-level descriptions elsewhere.

---

# 1. CANONICAL OBJECT SCHEMAS

All canonical objects MUST:

- include `schema_version`
- implement `.to_dict()` and `.from_dict()`
- be JSON-compatible
- pass validation checks

Validation failures MUST raise typed errors:

- `PDELieValidationError`
- `SchemaValidationError`
- `ShapeValidationError`
- `ScopeValidationError`

---

## 1.1 FieldBatch

~~~python
FieldBatch(
    schema_version: str,
    values: ArrayLike,
    dims: Tuple[str, ...],
    coords: Dict[str, ArrayLike],
    var_names: List[str],
    metadata: Dict[str, Any],
    preprocess_log: List[Dict[str, Any]],
    mask: Optional[ArrayLike] = None
)
~~~

### Required rules

- dims is authoritative
- ordering must be:
  ("batch"?, "time"?, spatial..., "var")
- `var` MUST be last
- spatial dims MUST be ordered (x, y, z)
- coordinates MUST match axis lengths
- missing data MUST be encoded via mask or NaN

### Metadata MUST include

- `boundary_conditions`
- `grid_type`
- `coordinate_system`
- `grid_regularity`
- `parameter_tags`

---

## 1.2 DerivativeBatch

~~~python
DerivativeBatch(
    schema_version: str,
    derivatives: Dict[str, ArrayLike],
    backend: str,
    config: Dict[str, Any],
    boundary_assumptions: str,
    diagnostics: Dict[str, Any]
)
~~~

### Required rules

- backend ∈ {"spectral_fd", "spectral", "finite", "weak"}
- derivatives MUST align with source FieldBatch shape
- wrt dimensions MUST exist in FieldBatch

---

## 1.3 ResidualEvaluator

~~~python
class ResidualEvaluator:
    def evaluate(
        field: FieldBatch,
        derivatives: Optional[DerivativeBatch] = None
    ) -> ResidualBatch
~~~

---

## 1.4 ResidualBatch

~~~python
ResidualBatch(
    schema_version: str,
    residual: ArrayLike,
    definition_type: str,
    normalization: str,
    diagnostics: Dict[str, Any]
)
~~~

### Required rules

- definition_type ∈ {"analytic", "weak", "surrogate", "operator"}
- residual MUST be shape-compatible with evaluation domain

---

## 1.5 GeneratorFamily

~~~python
GeneratorFamily(
    schema_version: str,
    parameterization: str,
    coefficients: ArrayLike,
    normalization: str,
    diagnostics: Dict[str, Any]
)
~~~

---

## 1.6 VerificationReport

~~~python
VerificationReport(
    schema_version: str,
    norm: str,
    epsilon_values: ArrayLike,
    error_curve: ArrayLike,
    classification: str,
    diagnostics: Dict[str, Any]
)
~~~

### Required rules

- classification ∈ {"exact", "approximate", "failed"}
- epsilon_values MUST be strictly increasing
- error_curve MUST match epsilon_values length

---

# 2. RESIDUAL ONTOLOGY

The residual layer consists of:

- ResidualEvaluator → computes residuals
- ResidualBatch → stores results

All symmetry fitting MUST be defined relative to a residual.

No symmetry method may bypass this abstraction.

---

# 3. DEFAULT VERIFICATION SETTINGS

## Norm

Default:

~~~python
relative_l2 = ||error|| / (||reference|| + 1e-12)
~~~

---

## Epsilon sweep

Default:

~~~python
epsilon_values = logspace(-4, -1, 7)
~~~

Minimum length: 5

---

## Held-out evaluation

Minimum:

- 3 unseen initial conditions  
- 2 unseen parameter settings (if applicable)

---

## Classification rules

Let:

- e_small = median error at smallest ε  
- e_max = max error  

Then:

- exact → e_small ≤ 1e-6 and stable curve  
- approximate → e_small ≤ 1e-2 and bounded  
- failed → otherwise  

For V0.1 verification:

- stable curve = monotone nondecreasing error curve with e_max ≤ 1e-4
- bounded = e_max ≤ 1e-1

Raw curves MUST always be reported.

---

# 4. IDENTIFIABILITY CONVENTIONS

## Normalization

All generators MUST satisfy:

~~~python
||X||₂ = 1
~~~

---

## Span comparison

Default:

~~~python
d(X, Y) = ||X - P_Y(X)|| / (||X|| + ε)
~~~

---

## Closure residual

~~~python
R = ||[X_i, X_j] - Σ c_ij^k X_k|| / (||[X_i, X_j]|| + ε)
~~~

---

# 5. GRID POLICY (v0.x)

## Supported

- uniform rectilinear grids

## Representable but NOT guaranteed

- nonuniform rectilinear grids

## Unsupported

- unstructured meshes

Stable derivative backends MUST assume uniform grids.

Nonuniform grids MUST raise:
- validation error OR
- route to experimental backend

---

# 6. BENCHMARK CONTROL RULES

All comparisons MUST control:

- feature library size  
- regularization  
- train/test splits  
- noise level  

---

## Mandatory

Include at least one nuisance baseline:

- random coordinate transform  
OR  
- feature-count matched transform  

---

# 7. SUCCESS CRITERIA

A symmetry claim is valid only if:

- passes held-out tests  
- passes epsilon sweep  
- is stable under noise  
- is not explainable by conditioning alone  

---

# 8. SERIALIZATION RULES

All canonical objects MUST:

- include `schema_version`
- support `.to_dict()` / `.from_dict()`
- preserve values under round-trip

---

# FINAL RULE

If anything is ambiguous:

→ choose the option that maximizes:

1. reproducibility  
2. comparability  
3. numerical verifiability  
