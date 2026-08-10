# V0.38.0 Release Readiness

## 1. Release Target

- package version: `0.38.0`
- git tag: `v0.38.0`
- release decision: `v0_38_0_all_gates_met_no_change_since_rc1`

**Git-tag-only.** Do not publish to TestPyPI or PyPI for `v0.38`. Publication
remains deferred to `v1.0`.

## 2. What changed since `v0.38.0rc1`

**Nothing, in the library.** `rc1` promised defect corrections only, and no
defect was found. The diff is the version bump, this document, and
`scripts/external_smoke.py` — which ships in neither the wheel nor the sdist.

That is the intended outcome of an RC, not a reason to doubt it was exercised.
What was exercised is recorded in §5.

## 3. Gates A–F

| Gate | Result |
|---|---|
| A — identity / environment | **PASS** |
| B — contract semantics | **PASS** — 5 signed freezes, 4 pilot blocks |
| C — adversarial values | **PASS** — 9/9 refusals fired |
| D — analytical oracles | **PASS** — registry 0 → 6 consumers |
| E — released numbers unmoved | **PASS** — 125/125 bitwise identical |
| F — cross-platform replay | **PASS** — run `31328966332`, Appendix D |

Gate F closed at three runner cells, 229 gate rows each: worst cross-platform
scaled difference `4.168e-10` against a derived `1e-8` bound, and `0.000e+00`
across a CPython patch bump with 325/325 comparisons bitwise identical.

## 4. What v0.38 shipped

### Breaking

- `inspect_pysindy_weak_pde_library` requires an explicit integer `seed`. A
  default seed is an unrecorded choice; this promise was two releases old.

### Added

- **Irregular grids.** Fornberg weights on arbitrary node sets, with
  `formal_accuracy = n − d` reported rather than assumed; grid-regularity
  description; irregular row masks; a non-uniform weak-form bridge with
  quadrature weights that are *validated*, not trusted.
- **Declared parameter-action targets.** `ParameterActionSpec` carries
  `declared_target_parameters` / `transformed_parameters` /
  `untouched_parameters`, so a rescale can no longer silently touch every
  numeric parameter.
- **One resolved residual operator.** A single `EquationForm` resolver consumed
  by both evaluator and report, **blocking** when declaration and data
  provenance disagree rather than picking one.
- **Signal-versus-floor error reporting.** At the numerical floor the relative
  statistic is *withheld* rather than reported, because a ratio between two
  numbers that are both `~1e-16` is not a number.

### Two declaration-versus-execution defects, both found by executing

Every gate in this project checked that declarations were *coherent*. None
checked that the declared thing was *executed*. Both defects found in v0.38 were
of that class, and so was the Gate F failure that delayed this release.

## 5. Verification performed for this tag

| | |
|---|---|
| release gate | all six sub-gates PASS, no `--skip-build` |
| branch-protection audit | 9/9, against the live repository |
| Gate F evidence | reproduces from `docs/evidence/v0_38_gate_f/` via an auditor importing neither generator nor comparator |
| external smoke | installed from the tag into a clean venv; base, `[downstream]` (pysindy 2.1.0), `[pdebench]` (h5py 3.16.0) |

The external smoke **refuses to run against a source checkout**. Run from the
repository it would pass on a wheel missing half its modules, since the tree is
importable and every dev dependency is present.

## 6. Known limitations

- **The portability taxonomy is corroborated on three cells, not established.**
  macOS/arm64 at CPython 3.12.11+ does not exist, so the 2×2 corner was never
  measured and is not claimed.
- **Derivative order 4 is outside the supported scope.** The 57 exploratory rows
  are evidence about future work.
- **The `1e-8` bound is derived for the workloads in scope.** Not a general
  claim about cross-platform reproducibility.
- **Nonperiodic domains and monotone coefficients are deferred to `v0.41`.**
- **The point-symmetry registry remains private.**
- **`discovery_task_result` keeps its 22-key schema**, frozen since v0.30.1.
- **Multi-batch input is out of scope** for the weak-library diagnostic, and is
  refused with a reason rather than silently reduced.

## 7. Scope discipline

`v0.38.0a1`, `v0.38.0b1` and `v0.38.0rc1` remain published. **No tag moves.**

Appendices A, B and C in
[`v0_38_platform_replay.md`](../design/v0_38_platform_replay.md) are append-only
and were not revised when D succeeded. Appendix C records a gate that passed
vacuously; keeping it is the point. A release record showing only the runs that
passed is a selection-effect document, and this project has now twice been saved
by a failure it wrote down.
