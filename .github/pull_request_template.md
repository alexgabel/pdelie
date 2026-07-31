<!--
v0.36 day-zero. Delete any section that genuinely does not apply, and say why
in one line rather than leaving it silently blank.
-->

## What this changes

<!-- One paragraph. What the reader gets that they did not have before. -->

## Why

<!-- The problem, not the patch. If a measurement motivated this, name the number. -->

---

## Checklist

### Contracts and scope

- [ ] No new root `pdelie` export (`pdelie.__all__` unchanged).
- [ ] No `discovery_task_result` schema change (still 22 top-level keys).
- [ ] No `pdelie_weak_pde_library_diagnostic` drift beyond the frozen 27/28 conditional.
- [ ] Frozen vocabularies unchanged: the four `method_scores` names, `_CONFIDENCE_LABELS`, `VerificationReport.classification`, `SymmetryCandidate` discriminators.
- [ ] Every new report is strict-JSON (`json.dumps(..., allow_nan=False)`) and carries `diagnostic_only = True`.
- [ ] No WSINDy, noise-robustness, or dataset-recovery claim introduced.

### Numerical work packages

Skip this block only if the PR adds no constant that a test asserts against.

- [ ] **Hypothesis freeze** written before implementation, with thresholds left unset.
- [ ] **Pilot** run: every quantity produced by two independent routes or against a closed form, with the spread reported — not a single draw.
- [ ] Degenerate inputs probed (empty, all, rank-deficient, zero-column, near-singular) and their returns recorded.
- [ ] **Confirmatory freeze** written, with each threshold justified from the measured spread.
- [ ] Every branch of any new vocabulary is reachable on real input, and the input that reaches it is named.

See `docs/design/DESIGN_FREEZE_PROCESS.md`.

### Cross-platform claims

- [ ] Every assertion comparing numeric artifacts declares its portability class.
- [ ] **No bit-exact comparison outside `exact_discrete`.** A `.npz` round-trip is `exact_discrete`; a comparison against a *rebuild* is not.
- [ ] `tolerance_numeric` assertions state both `rtol` and `atol`, at or above the repo floor of `rtol=1e-6`.
- [ ] Any claim of equality between two implementations either runs in the portability lane on Linux **and** macOS, or is narrowed to a tolerance or invariant claim.
- [ ] Portability lane still within its 30-test budget.

See `docs/design/CROSS_PLATFORM_PORTABILITY_CLASSES.md`.

### Verification

Paste the actual output; do not assert from memory.

- [ ] `ruff check .` — clean
- [ ] `mypy src/pdelie` — count unchanged against `configs/mypy_baseline.v0_36.json`
- [ ] `sphinx-build -b html -W --keep-going docs docs/_build/html` — clean
- [ ] `pytest` — full suite, count stated
- [ ] Ran on a CI-matched environment (Python 3.12, numpy 2.5.x, ruff 0.16.x, mypy 2.3.x)

```text
<paste tool output here>
```

### Housekeeping

- [ ] Branch deletion, if any, verified by **patch identity** (`git cherry origin/main <branch>`), never by `git diff main..<branch>`.
- [ ] Planned release identifiers still sort above every shipped version.

---

## Known limitations

<!--
State what this does NOT do, and what you chose not to fix. A limitation named
here is a decision; one discovered later is a defect.
-->
