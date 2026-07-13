# PDL-JSON-2: Strict-JSON Migration Plan for Public summarize_* Functions

**Status:** OPEN debt ticket. Filed in v0.31b0. Companion to PDL-JSON-1 which lists the inventory. Individual migrations execute per the schedule below; there is no bulk-migration release.

## Migration rules

1. **Composed summarizers migrate WITH the release that adds fields to them.**
   When a release lands new fields on a summarizer that embeds sub-summaries, that
   summarizer migrates to strict validation as part of the same PR. Example:
   `summarize_generator_confidence` migrates in v0.32b, when the additive
   `method_scores`, `uncertainty_report`, and `calibration_report` fields land.
   The rationale is that new-field PRs are already touching the payload shape and
   its tests, so folding the strict-validation flip into that PR minimises churn
   and keeps the strict boundary aligned with the point at which the schema
   actually changes.

2. **Leaf summarizers migrate on their own rolling schedule — one per release
   maximum — to avoid regression flooding.**
   Leaf summarizers (no embedded sub-summaries) can migrate independently, but
   the queue is throttled to at most one leaf migration per minor release so that
   any regression introduced by a strict-flip is easy to bisect and revert
   without dragging unrelated migrations along with it.

3. **Every migration PR must ship a per-summary NaN adversarial test.**
   The PR must include a regression test that injects `float("nan")` into a
   nested field of the summarizer's payload and asserts the strict-validated
   version raises `SchemaValidationError`. See the "Regression-test template"
   section below. The test lives beside the summarizer's existing unit tests and
   is named `test_<summary_name>_rejects_nan_strict`.

4. **Every migration PR must document a "known-emit-NaN" audit.**
   The PR description must enumerate every place in the current codebase that
   could emit `NaN` into the migrated summary's inputs (e.g. divisions by zero,
   `np.nanmean` over empty slices, missing-value sentinels, upstream fit
   residuals). For each emitter the PR must either (a) fix the emitter so it
   cannot produce `NaN` on the migrated payload's path, or (b) document a
   specific, referenced reason the migration is safe despite the emitter
   (guarded upstream, filtered before summarisation, structurally impossible for
   this call site, etc.). "No known emitters" is an acceptable audit outcome
   only if the PR author has actually looked.

5. **No migration may weaken any existing v0.NN release-gate test.**
   If a v0.NN release-gate test relies on the permissive contract for a payload
   it constructs — e.g. it hand-builds a summary with a `NaN` in it and expects
   the summariser to swallow it — that is a bug in the release-gate test and
   must be fixed in the migration PR. The correct fix is to update the test to
   construct a non-`NaN` payload (or to assert `SchemaValidationError` on the
   `NaN` path); the wrong fix is to make the summariser permissive again to
   keep the old test green.

## Per-summary migration schedule

| Function                                    | Target release   | Trigger                                                                                                                                                                | Est. size |
| ------------------------------------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| `summarize_downstream_discovery_workflow`   | v0.31b1          | Embedded in `TaskResult` via v0.31 task-bridge composition; must be strict since `underlying_discovery_result` is strict.                                                | S         |
| `summarize_generator_confidence`            | v0.32b           | Additive `method_scores` / `uncertainty_report` / `calibration_report` fields land under strict validation.                                                             | M         |
| `summarize_vertical_slice`                  | v0.32.5 or v0.33 | Composed summary embedding 3 sub-summaries; migrates after its embedded producers.                                                                                     | L         |
| `summarize_residual_batch`                  | v0.32.5          | Leaf; independently migratable.                                                                                                                                        | S         |
| `summarize_generator_family`                | v0.33            | Leaf.                                                                                                                                                                  | S         |
| `summarize_verification_report`             | v0.33            | Leaf.                                                                                                                                                                  | S         |
| `summarize_generator_fit_diagnostics`       | v0.33            | Leaf.                                                                                                                                                                  | S         |
| `summarize_field_batch_readiness`           | v0.34a           | Leaf.                                                                                                                                                                  | S         |
| `summarize_invariant_workflow`              | v0.34a           | Composed; embeds invariant sub-payloads.                                                                                                                                | M         |
| `summarize_split_leakage_provenance`        | v0.34a           | Leaf.                                                                                                                                                                  | S         |
| `summarize_formula_generator_family`        | v0.35a           | Leaf.                                                                                                                                                                  | S         |
| `summarize_weak_residual_report`            | v0.35a           | Leaf.                                                                                                                                                                  | S         |

Size legend: **S** = single-file summariser + its unit tests; **M** = summariser
plus one or two adjacent producers touched by the field-addition; **L** =
composed summariser that cannot migrate until all embedded producers have
migrated first.

## Regression-test template

Every migration PR adapts the following skeleton. Substitute `<summary_name>`
with the function being migrated, `<payload_fixture>` with a valid fixture the
summariser accepts today, and `<nested_field_path>` with a real nested numeric
field in that payload.

```python
# tests/summarizers/test_<summary_name>_strict.py

import math
import copy

import pytest

from pdelie.serialization.errors import SchemaValidationError
from pdelie.summarizers import <summary_name>


def _valid_payload():
    """Return a fresh, fully-populated payload the summariser accepts today."""
    return copy.deepcopy(<payload_fixture>)


def test_<summary_name>_accepts_valid_payload():
    """Baseline: strict validation must still pass on a clean payload."""
    result = <summary_name>(_valid_payload())
    assert result is not None


def test_<summary_name>_rejects_nan_strict():
    """
    Adversarial: inject NaN into a nested numeric field and assert the
    strict-validated summariser raises SchemaValidationError rather than
    silently passing NaN through into downstream JSON.
    """
    payload = _valid_payload()

    # Walk to the injection point. Keep this explicit — do not hide it behind
    # a helper — so future readers can see exactly which field is being
    # poisoned and why the summariser must reject it.
    target = payload
    for key in <nested_field_path>[:-1]:
        target = target[key]
    target[<nested_field_path>[-1]] = float("nan")

    with pytest.raises(SchemaValidationError) as excinfo:
        <summary_name>(payload)

    # Assert the error message mentions the offending field so operators can
    # trace it back to the emitter without re-running under a debugger.
    assert <nested_field_path>[-1] in str(excinfo.value)


@pytest.mark.parametrize("bad_value", [float("inf"), float("-inf")])
def test_<summary_name>_rejects_non_finite_strict(bad_value):
    """
    Optional companion: strict JSON also disallows +/-inf. Include this
    parametrisation if the migrated payload has any field where a runaway
    fit or division could plausibly produce inf.
    """
    payload = _valid_payload()
    target = payload
    for key in <nested_field_path>[:-1]:
        target = target[key]
    target[<nested_field_path>[-1]] = bad_value

    with pytest.raises(SchemaValidationError):
        <summary_name>(payload)
```

Notes on adapting the template:

- The `<nested_field_path>` MUST be a genuinely nested field, not a top-level
  key. The whole point of the strict flip is to catch `NaN` that escapes
  through deep sub-payloads, so a top-level injection would under-test the
  migration.
- If the summariser is composed (embeds sub-summaries), add a second injection
  test that poisons a field _inside an embedded sub-summary_ to prove strict
  validation recurses.
- If the summariser accepts an optional field, do not use that field as the
  injection site — poison a required field so the failure cannot be
  attributed to the value being dropped.

## Cross-references

- [`docs/planning/PDL_JSON_1_STRICT_JSON_INVENTORY.md`](./PDL_JSON_1_STRICT_JSON_INVENTORY.md)
  — the inventory this migration plan draws from.
- [`docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md`](../design/DISCOVERY_TASK_RESULT_SCHEMA.md)
  — schema for `TaskResult`, which pins the v0.31b1 migration of
  `summarize_downstream_discovery_workflow`.
