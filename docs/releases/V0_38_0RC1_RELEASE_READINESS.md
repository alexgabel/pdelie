# V0.38.0rc1 Release Readiness

## 1. Release Target

- package version: `0.38.0rc1`
- git tag: `v0.38.0rc1`
- release decision: `v0_38_0rc1_all_gates_met_defect_corrections_only`

**Git-tag-only.** Do not publish to TestPyPI or PyPI for `v0.38`. Publication
remains deferred to `v1.0`.

## 2. Why this is a release candidate and `v0.38.0b1` was not

`b1` withheld the RC designation for one stated reason: **Gate F had not
passed**, and no v0.38 code had ever been replayed on a second platform. That
was the whole of the objection, recorded in
[`V0_38_0B1_RELEASE_READINESS.md`](V0_38_0B1_RELEASE_READINESS.md) §2.

**Gate F closed on run `31328966332`.** All thirteen criteria pass on
measurements, across three runner cells, at 229 gate rows each:

| pair | isolates | worst scaled diff | bitwise |
|---|---|---|---|
| macOS/3.12.10 vs Linux/3.12.10 | platform | `4.168e-10` vs a `1e-8` bound | 122/325 |
| Linux/3.12.10 vs Linux/3.12.13 | CPython patch | `0.000e+00` | **325/325** |

Full record in [Appendix D](../design/v0_38_platform_replay.md). No planned
v0.38 feature remains. From here, **defect corrections only**.

### It took three attempts, and the two failures are not hidden

| run | outcome |
|---|---|
| `31278210299` | Appendix B — extended lane, specified a runner cell that does not exist |
| `31326189317` | Appendix C — **gate passed vacuously**; ten out-of-scope `d = 4` rows carried `derivative_order: null` and F-4 read `null` as in scope |
| `31328966332` | Appendix D — **closed** |

Appendix C is the one worth reading before trusting this tag. F-4 could not have
failed: the rows it existed to exclude were invisible to it. The repair was not
to thread the derivative order more carefully — that had already been tried, with
a regex, and is what produced the defect — but to make the malformed row
impossible to construct. Row semantics now originate in a typed `ReplayRowSpec`;
the row key is generated from it and never parsed back.

### What downstream consumers may do with this tag

**May:** produce confirmatory evidence against it, within the scope §5 states.
Every number in this tag has been replayed on a second platform and against a
CPython patch bump.

**May not:** treat the portability taxonomy as established in general. It is
corroborated on **three cells**, not proven. See §5.

## 3. Gates A–F

| Gate | Result |
|---|---|
| A — identity / environment | **PASS** |
| B — contract semantics | **PASS** — 5 signed freezes, 4 pilot blocks |
| C — adversarial values | **PASS** — 9/9 refusals fired |
| D — analytical oracles | **PASS** — registry 0 → 6 consumers |
| E — released numbers unmoved | **PASS** — 125/125 bitwise identical |
| F — cross-platform replay | **PASS** — run `31328966332`, Appendix D |

## 4. What changed since `v0.38.0b1`

No library behaviour changed. Every commit is gate, harness, or record.

| | |
|---|---|
| Gate F closure | typed `ReplayRowSpec`; frozen expected-row manifest; F-3a partition check; non-vacuous F-4a; independent audit (F-11) that imports neither generator nor comparator |
| accounting | bitwise comparison now runs before and independently of floor classification, so F-6's denominator no longer excludes the small-magnitude rows a libm change perturbs first |
| release gate | interpreter pinned against `requires-python`, aborting with exit 3 **before** any sub-gate — an environment fault previously presented as three code faults |
| CI | release-gate job renamed to the stable `release-gate`; the versioned name deadlocked branch protection at every cut |
| protection | `release/*` ruleset applied; `required_conversation_resolution` enabled — §3 of the policy had specified it and the repository had it `false` |
| record | Appendices C and D; roadmap rows for `v0.38` and `v0.41`, both previously absent |

## 5. Known limitations carried forward

Unchanged from `b1` except where Gate F now speaks:

- **The portability taxonomy is corroborated, not established.** Three
  platform/patch cells. macOS/arm64 at CPython 3.12.11+ is an **impossible
  cell** — it does not exist — so the 2×2 corner was never measured and is not
  claimed.
- **Derivative order 4 is outside the supported scope.** The 57 exploratory rows
  are evidence about future work, not about this release.
- **The `1e-8` cross-platform bound is derived for the workloads in scope.** It
  is not a general claim about PDELie's cross-platform reproducibility.
- **Nonperiodic domains and monotone coefficients are deferred to `v0.41`**, per
  [`V0_38_BINDING_DESIGN_CONSTRAINTS.md`](../design/V0_38_BINDING_DESIGN_CONSTRAINTS.md).
- **The point-symmetry registry remains private.**
- **`discovery_task_result` keeps its 22-key schema**, frozen since v0.30.1.

## 6. Verification

Run externally, from a shell, never from pytest — see
[`RELEASE_ENFORCEMENT.md`](../design/RELEASE_ENFORCEMENT.md):

```sh
./scripts/release_gate_local.sh                                  # all six, no --skip-build
python -m pytest tests/test_branch_protection_policy.py -m network
python scripts/audit_replay_population.py docs/evidence/v0_38_gate_f/
python scripts/compare_replay.py docs/evidence/v0_38_gate_f/
```

`--skip-build` prints `PASSED WITH SKIPS` and is **not sufficient for a release
tag**. The branch-protection audit is `network`-marked and deselected by default;
**a skipped audit is not a passing audit**, which is why it is named here rather
than assumed.

The Gate F evidence is archived under `docs/evidence/v0_38_gate_f/`
([on GitHub](https://github.com/alexgabel/pdelie/tree/main/docs/evidence/v0_38_gate_f))
because GitHub expires action artifacts. That directory is deliberately
excluded from this documentation build -- it is raw measurement data, not
prose -- so it is linked by URL rather than as a cross-reference. The verdict
reproduces from those files alone.

## 7. Scope discipline

`v0.38.0a1` and `v0.38.0b1` remain published as historical prereleases. Neither
tag moves. Appendices A, B and C are append-only and were not revised when D
succeeded — a record showing only the run that passed is a selection-effect
document.
