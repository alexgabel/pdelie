# Runtime Compatibility Policy (v0.31.1a — research spike)

**Status:** RESEARCH — decision recorded, implementation deferred to v0.32.

**Decision label:** `spec_0_modernization_outcome_A_modern_only_future_line`.

**Outcome:** **A (modern-only future line).** v0.32 targets Python ≥3.12 + NumPy 2.x + PySINDy 2.1.x. v0.31.x remains the legacy Python 3.11 + PySINDy 1.7.x line on a maintenance branch during transition. This file is the single source of truth for the runtime-compatibility policy; the machine-readable form lives at `configs/runtime_compatibility_matrix.json`.

## SPEC 0 alignment

PDELie adopts [Scientific Python SPEC 0](https://scientific-python.org/specs/spec-0000/) as the default runtime-compatibility policy:

- **Python versions** are supported for approximately **three years after release**.
- **Core numeric dependencies** (NumPy, SciPy, scikit-learn, xarray) are supported for approximately **two years after release**.
- **Temporary exceptions** must have a named owner and a removed-by milestone.

Applied to the v0.32 target window (release target: mid-2026):

| Version | SPEC 0 status | v0.32 policy |
|---|---|---|
| Python 3.10 | released 2021-10; out of SPEC 0 window | not supported |
| Python 3.11 | released 2022-10; borderline (~3 yr) | v0.31.x legacy line only |
| Python 3.12 | released 2023-10 | blocking supported |
| Python 3.13 | released 2024-10 | blocking supported |
| Python 3.14 | released 2025-10 | advisory (exploratory) |
| NumPy 1.x | released 2015–2023; superseded by 2.0 (2024-06) | v0.31.x legacy line only |
| NumPy 2.x | released 2024-06 | blocking supported |
| PySINDy 1.7.x | released 2023-01 | v0.31.x legacy line only |
| PySINDy 2.1.x | released 2024-10 | blocking supported once v0.32 implementation lands |

## Supported runtime matrix (v0.32 target)

### Blocking lanes

- **Python 3.12** + NumPy 2.x + SciPy latest compatible + scikit-learn latest compatible + PySINDy 2.1.x.
- **Python 3.13** + NumPy 2.x + SciPy latest compatible + scikit-learn latest compatible + PySINDy 2.1.x.

### Advisory lanes

- **Python 3.14** + NumPy 2.x + PySINDy 2.1.x — exploratory. Blocking is deferred pending stability signal from the upstream stack.

### Legacy lanes (v0.31.x maintenance branch)

- **Python 3.11** + NumPy 1.26.x + PySINDy 1.7.5 + `setuptools<82` — retained on the v0.31.x maintenance branch during the transition window. Removed at v0.32 release close.

## Retirement plan for temporary exceptions

Every temporary exception carries a named owner and a removed-by milestone. Anything not on this table is not a temporary exception.

| Exception | Introduced | Owner milestone | Removed by |
|---|---|---|---|
| `pysindy>=1.7.5,<2; python_version < '3.12'` | v0.31b3 | v0.31.1 implementation PR | v0.32 |
| `scikit-learn>=1.2.2,<1.3; python_version < '3.12'` | v0.31b3 | v0.31.1 implementation PR | v0.32 |
| `setuptools<82; python_version < '3.12'` | v0.31c1 (adversarial matrix outcome B) | v0.31.1 implementation PR | v0.32 (pin retires with pysindy 1.x) |
| `numpy>=1.24,<2` core cap | pre-v0.30 | v0.31.1 pin-widening (research shows the runtime tolerates numpy 2.x already) | v0.32 |
| Python 3.11 minimum | v0.30 | v0.32 minimum-bump PR | v0.32 |
| Python 3.11 downstream lane in main CI | v0.31c1 | v0.32 | v0.32 (moves to v0.31.x maintenance branch only) |

## Legacy-lane retirement plan

`v0.31.x` remains the supported legacy line during the v0.32 modernization transition. The maintenance policy on `v0.31.x`:

- Bug-fix / security releases only; **no new scientific runtime scope**.
- Kept alive on a `release/v0.31.x` branch (created at v0.32 release close from the last v0.31.x tag).
- Retired when the last PySINDy 1.7.x wheel goes end-of-life OR the `pkg_resources` deprecation removal window (2025-11-30) forces a downstream break — whichever comes first.

## CI matrix (proposed for v0.32 implementation PR)

**Not enforced by v0.31.1a.** This section is a proposal for the v0.32 implementation PR to consume.

| Job | Python | NumPy | PySINDy | Status | Runs on |
|---|---|---|---|---|---|
| `v0_32-core-3_12` | 3.12 | 2.x | — (no [downstream]) | blocking | `main` |
| `v0_32-core-3_13` | 3.13 | 2.x | — (no [downstream]) | blocking | `main` |
| `v0_32-core-3_14` | 3.14 | 2.x | — (no [downstream]) | advisory | `main` |
| `v0_32-downstream-3_12` | 3.12 | 2.x | 2.1.x | blocking once implementation lands | `main` |
| `v0_32-downstream-3_13` | 3.13 | 2.x | 2.1.x | blocking once implementation lands | `main` |
| `v0_32-downstream-3_14` | 3.14 | 2.x | 2.1.x | advisory | `main` |
| `v0_31-release-gate` (legacy) | 3.11 | 1.26.x | 1.7.5 | blocking | `release/v0.31.x` only |

## Non-goals of the SPEC 0 policy

- No claim of correctness under arbitrary NumPy/SciPy/scikit-learn combinations outside the tested lanes.
- No claim of PyPy / GraalPy / MicroPython support.
- No claim of Windows / Linux ARM support beyond what CI exercises.
- No claim of GPU or accelerator-backed numerics.
- No policy on package-index publication (PyPI/TestPyPI remains deferred to v1.0 per the existing v0.x tag-only policy).

## Rationale (why outcome A, not B)

The v0.31.1a environment audit measured the migration cost concretely. Dual 1.x/2.x support (outcome B) would require branching every fit-call construction site AND every library construction site — see `docs/design/PYSINDY_2_MIGRATION_AUDIT.md` for the exhaustive delta. Six independent API breaks and a transitive `numpy>=2` floor conflict place the compatibility layer well past the "small and maintainable" threshold. In contrast, the *core* PDELie surface (data / derivatives / residuals / reporting / verification / examples that do NOT touch PySINDy) is Python 3.14-ready today with numpy 1.26.4 building from source — outcome A ships the modernization in one deliberate step, aligns PDELie with SPEC 0, and confines the legacy line to a maintenance branch until the pysindy 1.x wheel window closes.

## Cross-references

- `configs/runtime_compatibility_matrix.json` — machine-readable form of the tables above.
- `docs/design/PYSINDY_2_MIGRATION_AUDIT.md` — exhaustive PySINDy 2.x API delta and per-lane failure signatures.
- `docs/design/PYSINDY_COMPATIBILITY_POLICY.md` — the v0.31.x compatibility policy (kept for the legacy line).
- `docs/planning/ROADMAP.md` — v0.31.1 (implementation), v0.32 (modernization delivery), v0.30.1 (SymmetryMethod registry MVP).
- Scientific Python SPEC 0: https://scientific-python.org/specs/spec-0000/
