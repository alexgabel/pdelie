# V0.1 Contract Drift Audit

This audit compares the implemented MVP against:

- `AGENTS.md`
- `SPEC.md`
- `CONTRACTS_AND_DEFAULTS.md`
- `API_STABILITY.md`
- `PLAN.md`
- `V0_1_SCOPE.md`

## Resolved During Hardening

- `SPEC.md` now matches the current stable slice by stating uniform rectilinear grids, not generic structured rectilinear grids.
- `CONTRACTS_AND_DEFAULTS.md` now documents the exported base validation error `PDELieValidationError`.
- `API_STABILITY.md` now lists `ResidualBatch` and `VerificationReport` explicitly in the stable API surface.
- `CONTRACTS_AND_DEFAULTS.md` now defines the concrete V0.1 meaning of verification terms `stable curve` and `bounded`, matching the implemented classifier.
- `V0_1_SCOPE.md` now quantifies held-out evaluation as at least 3 unseen initial conditions.
- Generic `ValueError` uses in the MVP path were replaced with typed validation errors where the frozen contracts require typed validation failures.

## Current Slice Alignment

The implemented V0.1 slice is internally consistent for:

- `FieldBatch`
- `DerivativeBatch`
- `ResidualBatch`
- `ResidualEvaluator`
- `GeneratorFamily`
- `VerificationReport`
- `DerivativeBatch.backend="spectral_fd"`

The current vertical slice remains:

`FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> VerificationReport`

for the synthetic 1D heat equation on a uniform periodic grid.

## Accepted Non-Issues

- `SPEC.md` still mentions later-pipeline objects such as `InvariantMap`, `InvariantLibrary`, and `DiscoveryResult` as broader v0.x concepts. They are not implemented in the MVP and remain explicitly deferred in `V0_1_SCOPE.md`.
- The implementation is intentionally target-specific to spatial translation on the heat equation. That is consistent with the V0.1 release gate and is not treated as contract drift.

## Audit Result

No remaining contract drift was found in the implemented V0.1 MVP path that blocks a release candidate.
