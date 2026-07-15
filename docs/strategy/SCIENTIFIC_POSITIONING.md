# Scientific Positioning

**Status:** advisory, not a stable contract. Updated at `v0.30.0` to reflect the current tooling landscape and to explicitly name adjacent projects as not-competitors.

## What PDELie is

PDELie is a small public research library for **empirical Lie-symmetry evidence and downstream-task supportability reports** on controlled PDE time-series data. Its reports combine derivative and residual checks, fitted or supplied generator evidence, configured validation, finite-transform verification for uniform periodic x-translation, boundary and readiness diagnostics, split-leakage provenance, and downstream discovery task summaries. These reports are **evidence records, not mathematical proofs of symmetry**, and PDELie is not a broad data-adapter, benchmark, or solver framework.

The `v0.30.0` public surface delivers:

- structured `BoundaryConditionSpec` and `FieldBatch` schema `0.2` with a backwards-compatible loader
- a low-order finite-difference derivative backend (`u_t`, `u_x`, `u_xx` only) on scalar 1D nonperiodic uniform grids
- a `compute_derivatives(backend="auto")` dispatcher that routes periodic → `spectral_fd` and nonperiodic → `finite_difference`
- interior-only residual diagnostics for the Heat / Burgers / advection-diffusion / reaction-diffusion strong evaluators
- readiness reports emitting `boundary_condition_warnings` and downgrading `readiness_label` accordingly
- non-blocking ruff/mypy/coverage hygiene (advisory) with a documented promotion plan
- a narrow declarative release-gate manifest replayed by a single parametrized test

Deferred, per the ROADMAP: multi-channel, 2D, nonperiodic KdV/KS/weak, external dataset loaders, symmetry-method registry, root API, and trained-model extraction. The current stable target is **scalar 1D uniform periodic and structured nonperiodic**.

## The wedge chain (v0.30 scope)

PDELie's defensible wedge is a single evidence chain, expressed only in terms of what is actually implemented at `v0.30.0`:

```
canonical PDE data / readiness
  → derivative evidence (spectral_fd for periodic; finite_difference for nonperiodic)
  → residual evidence (strong-form for supported PDEs; frozen weak-report slices for Heat/Burgers)
  → symmetry / generator candidate evidence (polynomial GeneratorFamily, FormulaGeneratorFamily, InvariantMapSpec)
  → finite-transform verification (uniform periodic x-translation only) and split-leakage provenance
  → downstream discovery task summaries (v0.31 target)
  → explicit supportability labels
```

Deliberate scope narrowings that appear in earlier drafts of the wedge but are **not shipped and not planned** through `v1.0`:

- **prolongation calculus** — no prolongation module exists or is planned in `src/pdelie/`. Prolongation of vector fields is a classical Lie-theoretic operation; PDELie does not implement it.
- **obstruction / compatibility tests** — no algebraic obstruction machinery ships. PDELie does not claim to certify that a candidate generator satisfies compatibility conditions beyond the empirical residual-preservation check its finite-transform verifier already runs.
- **nonperiodic finite-transform verification** — periodic-only, per `pdelie.verification.verify_translation_generator` and `_apply_uniform_translation`. Overlap-crop is a `v0.31.5` design topic.

Any claim beyond this chain in public marketing or documentation is a wedge drift and should be corrected against `docs/specs/API_STABILITY.md` and `docs/specs/support_matrix.v0_30.json`.

**v0.32c anchor (submodule-only, not a stable contract).** `pdelie.reporting.summarize_candidate_to_discovery_workflow` composes the chain above into a strict-JSON payload with 15 explicit stages; `pdelie.examples.candidate_to_discovery_workflow` is a JSON-only runnable example wired against the built-in `polynomial_translation_svd` method. The example is not a general workflow engine, not a benchmark harness, and not an automatic augmentation policy — action parameters (shifts, orbit cardinality, augmentation budget, train/test split) are always caller-configured and NEVER inferred from method scores. The example is scoped to periodic scalar 1D data with the built-in translation method only. See `docs/strategy/VALID_BUT_NOT_USEFUL.md`.

## What PDELie is not

PDELie is not, and does not aim to be, any of the following:

- a general-purpose numerical PDE solver
- a PINN or neural-PDE framework
- a benchmark suite or evaluation harness for PDE discovery methods
- a broad file-loader / adapter framework for PDE datasets
- an automated symmetry-discovery tool
- a symbolic computer algebra system for Lie theory
- an ML-experiment tracker or model registry
- a training or inference layer for neural PDE models

Each of these has serious, well-maintained tools already; PDELie interoperates through **typed reports and strict support boundaries** rather than reimplementing them.

## Adjacent-not-competitor tools

The following projects operate in overlapping or upstream/downstream space. PDELie treats each as **adjacent, not competitor** — meaning PDELie's public surface may consume its outputs (as candidate inputs) or emit outputs consumable by it (as bridge summaries), but PDELie does not aspire to replace it. Attempts to reframe PDELie as a competing implementation to any of these are wedge drift.

### Sparse PDE discovery

- **PySINDy** (Kaptanoglu et al.) — comprehensive sparse identification, `PDELibrary`, `WeakPDELibrary`, robust formulations, ensembling, and optimizer variants. **PDELie's `v0.31` task bridge consumes PySINDy as an external discovery backend under `pdelie.tasks.discovery`.** PDELie does not reimplement sparse regression, robust formulations, or the library design; it emits standardized `TaskResult` summaries around PySINDy fits and can add a `WeakPDELibrary` diagnostic wrapper (v0.31, diagnostic-only, no WSINDy noise-robustness claim).
- **WSINDy** (Messenger and Bortz) — weak/Galerkin-transform-based sparse identification with strong claims for noisy data. **PDELie will not implement WSINDy internally.** The v0.31 WeakPDELibrary wrapper is a *diagnostic* around PySINDy's implementation, not a WSINDy alternative.

### Neural PDE solving

- **DeepXDE** (Lu et al.) and **IDRLnet**-style PINN frameworks — explicit initial/boundary conditions, complex geometries, neural residual losses, adaptive refinement. **PDELie does not solve PDEs**; it does not model boundary/initial-condition surfaces beyond metadata. If you need a PINN, use DeepXDE.

### PDE datasets and benchmarks

- **PDEBench** (Takamoto et al.) — multi-PDE benchmark suite with initial/boundary conditions, parameter variation, ML baselines, APIs, and metrics. **PDELie's `v0.32` will ship at most one honest scalar-1D readiness cookbook** against a PDEBench slice, and will explicitly refuse to fake broader support from a cherry-picked slice.
- **The Well** (Ohana et al.) — 15TB, 16-dataset multi-physics collection with a unified PyTorch interface. **Most of The Well cannot fit PDELie's current scalar-1D `("batch","time","x","var")` contract.** `v0.32` will run a feasibility scan; if no honest scalar 1D slice exists in a given Well dataset, PDELie records `blocked_multichannel_required` rather than manufacturing readiness. Multi-channel widening is a `v0.34`+ decision-only scope.

### Symmetry discovery from data / trained models

- **LieGAN** (Yang, Walters, Dehmamy, Yu) — generative adversarial discovery of Lie group symmetries. Represents learned symmetries as Lie algebra bases.
- **LaLiGAN** (Yang et al.) — latent-space nonlinear symmetry discovery.
- **Ko-style methods** (Ko et al., "Learning Infinitesimal Generators of Continuous Symmetries from Data") — one-parameter generator flows.
- **LieGG** (Moskalev et al.) — extraction of Lie group generators from trained neural networks.

**PDELie treats every output of these methods as a `SymmetryCandidate` (v0.30.1 contract), not as a trusted symmetry.** Candidates must still pass PDELie's residual-preservation and finite-transform-verification checks before they are treated as evidence, and their `TrainedModelArtifact` inputs (v0.35a) must carry a first-class `input_layout: str` field so the current scalar-1D lock is honest. Attempts to promote a raw LieGG or LieGAN output to a supportability claim without re-verification are a wedge violation.

### Symmetry augmentation

- **LPSDA** (Brandstetter et al., "Lie Point Symmetry Data Augmentation for Neural PDE Solvers") — uses known Lie point symmetries to derive valid PDE transformations for augmentation. **PDELie is closer in spirit to the evidence discipline that LPSDA-style work requires upstream**; it does not construct augmentation datasets or orbit-materialization frameworks beyond the report-only `build_uniform_translation_orbit_batch` shipped in `v0.15`.

### Symbolic Lie theory

- **SymPy** (`sympy.liealgebras`), **Maple `DifferentialGeometry`**, **`rifsimp`** (Reid, Wittkopf, Boulton) — classical symbolic computer algebra for Lie groups, prolongations, determining-equation reductions, and equivalence. **PDELie explicitly does not compete with these systems.** If a user needs a symbolic determining-equation solve, they should reach for SymPy or Maple. PDELie's role is to consume symbolic candidates (via `FormulaGeneratorFamily`, from a symbolic pipeline outside PDELie) and produce empirical residual/verification evidence around them.

### Provenance and experiment tracking

- **MLflow**, **DVC**, **Weights & Biases** — general-purpose ML-experiment / dataset provenance tracking. **PDELie's provenance surfaces (`preprocess_log`, `summarize_split_leakage_provenance`) are report-only and self-contained.** PDELie will not become an experiment tracker. Downstream users who need cross-run tracking should serialize PDELie's strict-JSON summaries into their tracker of choice.

## Vocabulary boundaries

PDELie currently emits four label vocabularies:

- **readiness**: `ready`, `needs_attention`, `not_ready`
- **generator confidence**: `strong`, `qualified`, `failed`, `insufficient_evidence`
- **weak-form supportability**: `supported_existing_slice`, `diagnostic_only`, `failed`, `insufficient_evidence`
- **split-leakage risk**: `no_detected_overlap`, `traceable_overlap`, `missing_provenance`, `inconclusive`

The `v0.31` downstream discovery task bridge is scoped to reuse these vocabularies rather than introduce a fifth `discovery_task_supportability` label lattice. If a fifth vocabulary genuinely becomes necessary, it will be documented as a public contract before it ships.

## References

The Lie-symmetry vocabulary follows the classical differential-equation literature: Olver, *Applications of Lie Groups to Differential Equations*; Hydon, *Symmetry Methods for Differential Equations*; Bluman and Kumei, *Symmetries and Differential Equations*. The numerical differentiation choices for the periodic spectral path follow standard spectral-method practice (Trefethen, *Spectral Methods in MATLAB*). Sparse discovery context and downstream bridging follows Brunton, Proctor, and Kutz on sparse identification and Rudy et al. on data-driven PDE discovery.

The `v0.30.0` release readiness document is at `docs/releases/V0_30_RELEASE_READINESS.md`. The stable public-surface note is at `docs/specs/API_STABILITY.md`. The current release theme is `nonperiodic_readiness_and_low_order_finite_difference_diagnostics`.
