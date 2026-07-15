# SymmetryMethod Registry (v0.30.1)

**Status:** IMPLEMENTED (v0.30.1). Submodule-only. No root `pdelie` export.

**Decision label:** `submodule_only_symmetry_method_registry_mvp_plus_symmetry_candidate_contract`.

## Purpose

v0.30.1 introduces the internal/public extensibility foundation required before any external symmetry-method port (Ko-style, LieGAN, LaLiGAN, LieGG, or similar) can be integrated. The registry provides a stable name-to-adapter mapping and a uniform `SymmetryMethodResult` shape; the `SymmetryCandidate` contract provides a representation-neutral wrapper for the various generator/invariant objects those methods produce.

**This release does NOT add any external symmetry method.** The only built-in adapter is `polynomial_translation_svd`, which wraps the existing `pdelie.symmetry.fitting.translation_baseline.fit_translation_generator` without changing its numerics.

## Architectural rule

External methods GENERATE candidates. PDELie VERIFICATION determines evidence. Candidate generation, candidate validation, and downstream utility remain distinct stages.

- **Generation** (v0.30.1): a registered `SymmetryMethod` emits `SymmetryCandidate` instances via its `fit(...)` operation.
- **Validation** (pre-v0.30.1): `pdelie.symmetry.validate_symmetry_candidate` semantics preserved verbatim.
- **Verification** (pre-v0.30.1): `pdelie.verification.verify_translation_generator` remains the load-bearing configured evidence surface.

The registry does NOT invoke validation or verification. It does NOT rank candidates. It does NOT expose a `best` accessor. It does NOT call arbitrary method-native scores "confidence" — the field name is `method_scores`, and the values are finite floats or `None`.

## Public submodule surface (`pdelie.symmetry` only)

- `SymmetryCandidate` — dataclass wrapping a representation-specific payload.
- `SymmetryMethod` — `typing.Protocol` (duck-typed).
- `SymmetryMethodMetadata` — frozen dataclass of static metadata.
- `SymmetryMethodResult` — dataclass returned by `fit(...)`.
- `SymmetryMethodSpec` — lazy registration entry.
- `REPRESENTATION_TYPES` — frozenset of the seven reserved discriminators.
- `register_symmetry_method(name, metadata, import_path)`.
- `get_symmetry_method(name) -> SymmetryMethod` — lazy import.
- `list_symmetry_methods() -> list[dict]` — metadata-only listing; does NOT import any adapter module.
- `run_symmetry_method(name, field, *, residual_evaluator=None, config=None) -> SymmetryMethodResult`.
- `build_symmetry_candidate(...)`, `summarize_symmetry_candidate(...)`, `summarize_symmetry_method_result(...)`.

**Root `pdelie` exports for any of these names are forbidden.** The v0.30.1 release-gate manifest guards this invariant.

## Reserved representation types

Seven discriminator values reserved on `SymmetryCandidate.representation_type`:

| Discriminator | v0.30.1 status | Payload type |
|---|---|---|
| `generator_family` | implemented | `pdelie.contracts.GeneratorFamily` |
| `formula_generator_family` | implemented | `pdelie.symmetry.formula.FormulaGeneratorFamily` |
| `invariant_map_spec` | implemented | `pdelie.contracts.InvariantMapSpec` |
| `matrix_lie_algebra` | reserved | none (no validated schema in v0.30.1) |
| `coordinate_vector_field` | reserved | none |
| `finite_transform_spec` | reserved | none |
| `latent_generator_reference` | reserved | none |

The four reserved-but-unimplemented values are constructible only with `payload=None` and emit a `UserWarning` when used outside the internal spec-freeze tests. Attempting to attach a payload raises `ScopeValidationError`.

## `SymmetryMethod` Protocol

The registry uses `typing.Protocol` (not ABC) so external adapters can be plain callables or dataclasses without inheriting a pdelie base class.

Adapters must expose:

- `METADATA: ClassVar[SymmetryMethodMetadata]` — validated at registration time.
- `fit(field: FieldBatch, *, residual_evaluator=None, config=None) -> SymmetryMethodResult`.

Input constraints:

- `field` MUST be a `FieldBatch`. File-path input, ndarray coercion, and xarray coercion are out of scope.
- `residual_evaluator` MAY be required by the specific method (`polynomial_translation_svd` requires it; other methods MAY not).
- `config` is a JSON-safe `Mapping[str, Any]` normalized by the adapter.

Output constraints (enforced by `SymmetryMethodResult.__post_init__`):

- `method_name` must match the registered name.
- `candidates` is a list of `SymmetryCandidate` (order is method-defined; NOT ranked here).
- `method_scores` values are finite floats OR `None`. **NaN and Inf are rejected.**
- `runtime_seconds` and `peak_memory_mb` are finite floats or `None`.
- `deterministic` is a bool asserting the output is deterministic given input + config.
- `warnings` is a list of strings.
- `backend_versions` is a mapping of `package_name -> version_string`.
- `fit_diagnostics` and `provenance` are strict-JSON.

**No `best` property. No `method_confidence` field.**

## Lazy import guarantee

The registry stores a `SymmetryMethodSpec` per registered name, containing the eagerly-constructed `SymmetryMethodMetadata` and a dotted `import_path` string of the form `"pdelie.symmetry.methods.<name>:build_method"`.

Rules:

1. Importing `pdelie.symmetry` does NOT import any adapter module (the built-in registers via `SymmetryMethodSpec`, not by importing its adapter file).
2. Importing `pdelie.symmetry.methods` does NOT import any adapter module — the package `__init__.py` is empty by design.
3. `list_symmetry_methods()` returns the metadata list WITHOUT importing any adapter module. Safe in a core-only install.
4. `get_symmetry_method(name)` and `run_symmetry_method(name, ...)` are the ONLY paths that load the adapter module. They use `importlib.import_module(...)` at call time.
5. If the adapter module fails to import (missing optional dependency), the registry raises `ScopeValidationError` with a message that names the required extras and suggests `pip install pdelie[<extras>]`.

**No `pdelie.symmetry.methods.__init__` sweep is performed.** External methods should either register via `register_symmetry_method(...)` at their own package's import time (e.g. under `pdelie_liegan.register()`) OR — for future consideration only — via Python entry points once an explicit entry-point design audit is completed. Entry-point registration is deliberately deferred.

## Built-in adapter: `polynomial_translation_svd`

Wraps `pdelie.symmetry.fitting.translation_baseline.fit_translation_generator` in the registry contract without changing its numerics.

- `method_class = "closed_form"`, `deterministic = True`, `requires_training = False`, `requires_extras = ()`.
- `supported_input_layouts = ("scalar_1d_uniform",)`.
- `supported_boundary_conditions = ("periodic",)`.
- `output_representation_types = ("generator_family",)`.
- Emits exactly one `SymmetryCandidate` wrapping the resulting `GeneratorFamily` (`representation_type = "generator_family"`, `mathematical_status = "candidate_only"`, `executable_status = "executable"`).
- `method_scores` populated with `svd_span_distance`, `selected_span_distance`, `condition_number`, `fit_residual` — all finite floats or `None`.
- `fit_diagnostics` preserves `reference_fallback_used` as a strict bool.
- `warnings` includes `"reference_fallback_used"` when the underlying fit selected the reference-fallback branch.
- Rejects nonperiodic FieldBatch, missing residual evaluator, and non-positive `epsilon` before any expensive computation.

## Explicit non-goals for v0.30.1

- No external symmetry method port (Ko-style, LieGAN, LaLiGAN, LieGG all deferred).
- No PyTorch dependency.
- No eager import of any optional method.
- No `pdelie.discover_symmetries` root API.
- No file-path input. No ndarray/xarray coercion.
- No `ArenaResult.best`. No automatic ranking. No winner selection.
- No arbitrary method-native scores called "confidence".
- No NaN or Inf in any summary output.
- No change to `GeneratorFamily` semantics or `validate_symmetry_candidate` semantics.
- No multi-D expansion (scalar 1D only, matching the surrounding pdelie stable surface).
- No new finite-transform implementation.

## References

- `src/pdelie/symmetry/candidates.py` — `SymmetryCandidate` and reserved discriminators.
- `src/pdelie/symmetry/registry.py` — Protocol, registry, `SymmetryMethodResult`.
- `src/pdelie/symmetry/methods/polynomial_translation_svd.py` — the built-in adapter.
- `tests/test_symmetry_candidate_contract.py` — 30 contract tests.
- `tests/test_symmetry_method_registry.py` — 16 registry + lazy-import tests.
- `tests/test_polynomial_translation_svd_method.py` — 15 adapter tests.
- `docs/specs/API_STABILITY.md` — v0.30.1 stable public-surface note.
- `configs/release_gate_manifest.json` — the v0.30.1 row extending the release gate.
