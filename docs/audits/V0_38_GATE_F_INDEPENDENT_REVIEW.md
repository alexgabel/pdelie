# v0.38 Gate F — Independent Review

**Status: UNSIGNED. Evidence executed; verdict not rendered.**

This document is additive post-release assurance. It does **not** modify the
`v0.38.0` tag, Appendix D, or any Gate F artifact.

---

## Why this document is unsigned

The independent review required by the corrective specification was **not
performed**. The author of the fix implemented it and reviewed it, and the
three missing behavioural tests were found only during a later audit — by the
same author, prompted by the specification being re-read.

That is the failure this document exists to close, so it cannot be closed by
the author asserting it is closed. The sections below therefore separate two
things that are usually conflated:

| | |
|---|---|
| **evidence** | mutations actually executed, with captured output — *produced by the author* |
| **verdict** | whether that evidence establishes assurance — **reserved for an independent reviewer** |

Evidence produced by the author is still useful: it makes each claim cheap to
re-execute rather than requiring the reviewer to reconstruct the harness. It is
not a substitute for the review. A reviewer who accepts this evidence without
re-running it has performed the same non-review being corrected.

---

## Review target

| field | value |
|---|---|
| reviewed tag | `v0.38.0` |
| reviewed commit | `f18c786` (tag object `bba9a35`) |
| corrective PR under review | [#175](https://github.com/alexgabel/pdelie/pull/175) |
| follow-up PR under review | [#181](https://github.com/alexgabel/pdelie/pull/181) |
| review date | *(to be filled by reviewer)* |
| reviewer role | *(to be filled by reviewer)* |
| independence statement | *(to be filled by reviewer)* |

## Reviewed artifacts

Deliberately narrow, per specification:

```
scripts/replay_contracts.py
scripts/compare_replay.py          (structural_checks and compare)
configs/gate_f_expected_rows.json
tests/test_replay_population_integrity.py
gate/exploratory partition logic
```

---

## Mutation cases executed, and observed results

Reproduce with the commands in §"How to re-execute" below. Run against
`v0.38.0` plus PR #181.

| # | case | method | observed |
|---|---|---|---|
| 0 | control: unmutated frozen population | call validator | **accepted**, no problems |
| 1 | duplicate row identity | construct actual duplicate, call validator | rejected — `duplicate row keys [('deriv_ref_floor_regime', 'cosx_d1')]` |
| 2 | floor-classified **equal** value | execute comparator | `total=1 equal=1 floor=1 signal=0` — denominator **includes** the floor row |
| 3 | floor-classified **unequal** value | execute comparator | `different=1`, row named, `worst_scaled=0.0` — F-6 breaks, F-7 unaffected |
| 4 | missing order metadata on an order-parameterised row | mutate row object | refused **at construction** |
| 5 | partition changed, total row count preserved | mutate partition | rejected — partition differs from frozen |
| 6 | unknown workload family | construct unknown family | refused — `unknown workload family 'spectral'` |
| 7 | semantics parsed from row names | source + behaviour | no gate-deciding assignment from the row-key parser; key/typed-value disagreement detected |

Case 0 is not decoration. Without it, every rejection above is consistent with a
validator that rejects everything.

Cases 2 and 3 are the ones that were previously asserted only by **source-text
inspection** — counter names present, increment ordering correct. That assertion
would pass on a comparator whose counters were correctly named, correctly
ordered, and wrong. PR #181 replaces it with the executed form above; the
source-text check is retained as a secondary architectural guard, not as the
behavioural oracle.

---

## Known residual limitations

Stated so a reviewer does not have to discover them:

1. **This evidence was produced by the author of the code it exercises.** The
   independence requirement is unmet until a reviewer re-executes it.

2. **Two defects were found *after* the corrective PR was written**, both by the
   author, and both are recorded rather than quietly folded in:
   - a family assignment derived from the workload's **name prefix**, which
     mislabelled `fornberg_fn_12_uniform_spacing_ratio` (it measures the grid's
     spacing ratio and has no derivative order). Prefix-derived semantics is the
     same defect class the PR was written to end. Families are now declared per
     workload in the scope artifact.
   - a counter conflating *"could not compare these two values"* with *"there
     were no two values"*, reported as `not_comparable = 1049` on the closing
     replay. Disclosed in Appendix D §D6, with every gate statistic diffed
     before and after and found bit-identical.

3. **The closing replay `31328966332` ran before PR #181.** Its comparator
   therefore used the source-text-tested accounting. The counters it produced
   were subsequently verified by the executed cases above, but the run itself
   was not gated on them.

4. **Gate F is corroborated on three runner cells**, not established in general.
   macOS/arm64 at CPython 3.12.11+ does not exist, so the 2×2 corner was never
   measured.

---

## How to re-execute

```sh
git checkout v0.38.0            # or main, with PR #181 merged
python -m pytest tests/test_replay_population_integrity.py -q
python scripts/audit_replay_population.py docs/evidence/v0_38_gate_f/
python scripts/compare_replay.py docs/evidence/v0_38_gate_f/
```

The mutation cases in the table are executed by the named tests. To confirm they
are **non-vacuous**, revert a guard and observe the suite go red — for example,
moving `numeric_comparisons_total += 1` after the floor branch turns cases 2 and
3 red, and replacing the `family not in NON_ORDER_FAMILIES` condition with
`False` turns ten tests red.

A reviewer who does not perform at least one such reversion has confirmed that
the tests pass, not that they can fail.

---

## Verdict

*(to be rendered by an independent reviewer)*

```
assurance_confirmed
assurance_confirmed_with_non_load_bearing_findings
assurance_not_confirmed
```

**Verdict:** *(unsigned)*

**Reviewer:** *(unsigned)*
