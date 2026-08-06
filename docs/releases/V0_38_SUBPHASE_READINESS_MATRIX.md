# v0.38 — Sub-phase Readiness Matrix

**Status:** frozen at `v0.38.0b1`. This is the source of truth for
sub-phase-level release evidence. Prose in the readiness doc summarizes; this
table records.

Generated from the repository state at commit `10f8a13` (feature-freeze commit,
PR #170) plus the `release/v0.38.0b1` branch head. Regeneration procedure in §7.

## 1. Matrix

| Sub-phase | PR | Impl commit | Hypothesis freeze | Pilot runs | Confirmatory freeze | Amendments | Status |
|---|---:|---|---|---|---|---|---|
| day-zero — bindings + guards | [#150](https://github.com/alexgabel/pdelie/pull/150) | `8a0d88d` | n/a — policy | n/a | n/a | — | **closed** |
| day-zero — delta close | [#154](https://github.com/alexgabel/pdelie/pull/154) | `c73e0b6` | n/a — policy | n/a | n/a | — | **closed** |
| v0.38e — semantics + resolver | [#155](https://github.com/alexgabel/pdelie/pull/155) | `76e3881` | [v0_38e_hypothesis_freeze.md](../design/v0_38e_hypothesis_freeze.md) | Run 1 blocked (B-1), Run 2 signed | [v0_38e_confirmatory_freeze.md](../design/v0_38e_confirmatory_freeze.md) | E-001 seed transition | **closed** |
| v0.38e — C-7/C-8 pair | [#156](https://github.com/alexgabel/pdelie/pull/156) | `87eb149` | (shared with #155) | (shared) | (shared) | — | **closed** |
| v0.38e — seed hard-cut (breaking) | [#157](https://github.com/alexgabel/pdelie/pull/157) | `fe749f4` | forward promise | n/a | forward promise | delivered v0.37→v0.38 cut | **closed** |
| v0.38e — parameter-action targets | [#158](https://github.com/alexgabel/pdelie/pull/158) | `79bb8a8` | (extension) | (extension) | (extension) | E-002 target field | **closed** |
| v0.38e — equation-form resolver | [#159](https://github.com/alexgabel/pdelie/pull/159) | `bfe3666` | (extension) | (extension) | (extension) | E-003 disagreement blocks | **closed** |
| v0.38e — additive artifact register | [#160](https://github.com/alexgabel/pdelie/pull/160) | `f80bcaa` | (extension) | (extension) | (extension) | E-004 first oracle | **closed** |
| v0.38e — three-layer periodicity | [#161](https://github.com/alexgabel/pdelie/pull/161) | `654c3af` | (extension) | (extension) | (extension) | E-005 generated table | **closed** |
| **Tag `v0.38.0a1`** | [#162](https://github.com/alexgabel/pdelie/pull/162) | `d053959` (tag `9432bd6`) | — | — | — | action-preview | **cut 2026-08-03** |
| v0.38a — row masks | [#163](https://github.com/alexgabel/pdelie/pull/163) | `492ec0c` | [v0_38a_hypothesis_freeze.md](../design/v0_38a_hypothesis_freeze.md) | Run 1 passed | [v0_38a_confirmatory_freeze.md](../design/v0_38a_confirmatory_freeze.md) | none | **closed** |
| v0.38b — Fornberg | [#164](https://github.com/alexgabel/pdelie/pull/164) | `f26288c` | [v0_38b_hypothesis_freeze.md](../design/v0_38b_hypothesis_freeze.md) | Run 1 blocked (B-4), Run 2 signed | [v0_38b_confirmatory_freeze.md](../design/v0_38b_confirmatory_freeze.md) | B-1 FN-12 constant bounded | **closed** |
| v0.38c — irregular weak bridge | [#165](https://github.com/alexgabel/pdelie/pull/165) | `eb2cf47` | [v0_38c_hypothesis_freeze.md](../design/v0_38c_hypothesis_freeze.md) | Run 1 passed | [v0_38c_confirmatory_freeze.md](../design/v0_38c_confirmatory_freeze.md) | none | **closed** |
| v0.38d — derivative-error reference | [#166](https://github.com/alexgabel/pdelie/pull/166) | `cd275ca` | [v0_38d_hypothesis_freeze.md](../design/v0_38d_hypothesis_freeze.md) | Runs 1, 2 blocked (B-1), Run 3 signed | [v0_38d_confirmatory_freeze.md](../design/v0_38d_confirmatory_freeze.md) | D-1 signal-vs-floor convention | **closed** |
| Gate A–F freeze | [#170](https://github.com/alexgabel/pdelie/pull/170) | `10f8a13` | — | Gates A–E pass, F NOT MET | [V0_38_GATES_A_TO_F.md](V0_38_GATES_A_TO_F.md) | — | **closed for A–E; open for F** |
| **Gate F — closure plan** | (this PR) | pending | [v0_38_gate_f_closure_plan.md](../design/v0_38_gate_f_closure_plan.md) | pending | pending | — | **open** |
| **Tag `v0.38.0b1`** | [#171](https://github.com/alexgabel/pdelie/pull/171) | pending | — | — | — | feature-complete, Gate F open | **open** |
| **Gate F — extended lane** | pending | pending | (see closure plan) | pending | pending | — | **open** |
| **Tag `v0.38.0-rc1`** | pending | pending | — | — | — | Gates A–F pass | **not cut** |

## 2. What each column asserts

- **PR** — GitHub pull request number. Every entry links to a merged PR;
  `pending` indicates work not yet opened.
- **Impl commit** — dereferenced commit SHA on `main` (or, for `open` entries,
  the tracking branch).
- **Hypothesis freeze** — the document written before code, with no threshold
  values. Governance for the pilot.
- **Pilot runs** — count and outcome of pilot dispatches. Blocked runs are
  retained unedited; a blocked run is not a failure of the process but a
  successful gate rejection.
- **Confirmatory freeze** — the document written after the pilot, containing
  measured thresholds. Signed once and amended only with dated entries.
- **Amendments** — dated changes to the confirmatory freeze after signing.
  Numbered `<subphase>-NNN`. Zero is a common and legitimate value.
- **Status** — `closed` if impl merged, confirmatory freeze signed, and no
  amendment is pending. `open` otherwise.

## 3. Pilot-block accounting

| Sub-phase | Runs | Blocked runs | Retained blocks |
|---|---:|---:|---|
| v0.38a | 1 | 0 | — |
| v0.38b | 2 | 1 | B-4 in Run 1 |
| v0.38c | 1 | 0 | — |
| v0.38d | 3 | 2 | B-1 in Runs 1 and 2 |
| v0.38e | 2 | 1 | B-1 in Run 1 |
| Gate F extended lane | 0 | — | — |

**Total blocked pilots retained:** 4 across 4 sub-phases. All appear in the
respective pilot report unedited, per the anti-selection-effect discipline
established at v0.37c pilot 3.

## 4. Amendment log

Numbered from the confirmatory-freeze signature date onward.

| ID | Sub-phase | Date | Change | Governed by |
|---|---|---|---|---|
| E-001 | v0.38e | 2026-08-01 | Seed transition applies at v0.38 not v0.37 | forward-promise policy |
| E-002 | v0.38e | 2026-08-01 | Parameter-action target is a declared field | freeze §2 addition |
| E-003 | v0.38e | 2026-08-01 | Equation-form disagreement blocks execution | freeze §3 addition |
| E-004 | v0.38e | 2026-08-02 | Artifact register carries first oracle | freeze §4 addition |
| E-005 | v0.38e | 2026-08-02 | Case table generated, not hand-transcribed | freeze §5 addition |
| B-1 | v0.38b | 2026-08-03 | FN-12 constant `n·eps` bound, `0.647·n·eps` observed | pilot §3 finding |
| D-1 | v0.38d | 2026-08-04 | `sqrt(eps)·reference_scale` convention, not derivation | pilot §1 finding |

Amendments after 2026-08-06 are added by dated entry with a governing document
reference. Restating a confirmatory freeze in place is forbidden.

## 5. Cross-reference to Gates A–F

| Gate | Sub-phase evidence base |
|---|---|
| A — identity / environment | `V0_38_0B1_RELEASE_READINESS.md` §1, `pyproject.toml` @ b1 |
| B — contract semantics | Every sub-phase confirmatory freeze signed |
| C — adversarial values | v0.38e's 9 refusals; v0.38a's exclusion vocabulary |
| D — analytical oracles | Registry 0→6 across v0.38b, c, d, e |
| E — released numbers unmoved | 125 v0.37c measurements bitwise identical at `10f8a13` |
| F — cross-platform replay | Extended lane per closure plan (§ above); rc1 gate |

## 6. What this matrix is not

- **Not a substitute for the confirmatory freezes.** The matrix records that
  they exist and are signed; the freezes themselves define the contracts. A
  freeze content dispute is resolved against the freeze document, not this row.
- **Not a substitute for the release-readiness doc.** The readiness doc
  summarizes for a reader; this matrix underlies the summary.
- **Not a claim about v0.38f or later.** Only the sub-phases delivered at
  v0.38.0b1 appear.

## 7. Regeneration procedure

To regenerate this matrix after a v0.38 amendment or after cutting `rc1`:

```bash
# 1. Pull the current commit list for the v0.38 arc.
git log --oneline --format='%H %s' main | \
    grep -E "feat\(v0\.38|release: cut v0\.38"

# 2. Enumerate freeze docs and their signatures.
for f in docs/design/v0_38*_hypothesis_freeze.md \
         docs/design/v0_38*_confirmatory_freeze.md; do
    printf '%s\n' "$f: $(grep -m1 '^\*\*Status' "$f")"
done

# 3. Enumerate pilot report runs and block markers.
grep -H "^## Run\|blocked_pilot_criteria" docs/design/v0_38*_pilot_report.md

# 4. Amendment IDs come from the confirmatory freeze bodies (grep '<subphase>-\d+').
```

The matrix is edited in place with dated entries. No amendment restates a row
without preserving the prior value in an appendix.
