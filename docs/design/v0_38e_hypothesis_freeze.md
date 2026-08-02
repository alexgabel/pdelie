# v0.38e — Hypothesis Freeze (action-semantics hardening)

**Status:** frozen. Written before any v0.38e runtime code, and before any
measurement informed it.

**Reconnaissance disclosure** (required by `V0_38_BINDING_DESIGN_CONSTRAINTS.md`):
one measurement was taken before this freeze was written, and it is the reason
the freeze exists. It is disclosed in full in §1. No tolerance, threshold or
pass criterion below was derived from it.

---

## 1. The finding this sub-phase is a response to

`execute_bundle` applies a `scalar_rescale` parameter action to **every numeric
parameter of the problem**, because `ActionRef` has no field naming which
parameter it targets.

Measured on `main` at `c73e0b6`, on a two-parameter problem:

```
declared : scalar_rescale factor=3.0   (ActionRef names no target)
original : {'nu_baseline': 0.1, 'advection_speed': 2.0}
executed : {'nu_baseline': 0.30000000000000004, 'advection_speed': 6.0}
```

`advection_speed` was rescaled by an action that meant only to rescale the
viscosity. Nothing in the bundle said it should be, and nothing in the report
would say it was.

**Why v0.37c did not catch it.** Every v0.37c case builds
`parameters={"nu_baseline": ...}` — exactly one numeric parameter
(`src/pdelie/benchmarks/parameter_equivariant.py:438`). On a one-element
population, "rescale all parameters" and "rescale the declared parameter" are
the same function. The defect is not reachable by any case in the suite.

**This is the C-5 class, one layer down.** C-5 was a runner executing something
other than what the bundle declared. Here the *declaration itself* is
incomplete: it cannot express a target, so the executor supplies one by
convention, and the convention is invisible. An audit asking "is the declared
action the one that was consumed?" passes — there is no disagreement, because
there was never a second thing to disagree with.

---

## 2. What v0.38e freezes

### 2.1 Two identities for coefficient values (CI-1 … CI-5)

Storage-representation identity and scientific identity are **separate named
helpers**. Conflating them is a defect, not a shortcut.

| Rule | Statement |
|---|---|
| **CI-1** | The two are separate public functions. Neither is implemented in terms of the other, and neither has a flag that turns it into the other. |
| **CI-2** | Storage identity is **exact**: dtype, shape, and bit content. It takes no tolerance and admits none. |
| **CI-3** | Scientific identity requires an explicit `ErrorMetricSpec`. There is **no default tolerance** — a defaulted tolerance is a claim nobody made. |
| **CI-4** | Scientific identity is **not an equivalence relation** (not transitive), so it must never back a hash, a set, or a dict key. Storage identity may. |
| **CI-5** | Storage identity implies scientific identity under every metric; the converse never holds. Asserted as a property, both directions. |

CI-4 is the one that bites. `a ≈ b` and `b ≈ c` within tolerance does not give
`a ≈ c`, so any container keyed on approximate equality has behaviour that
depends on insertion order.

### 2.2 Artifact resolution (RR-1 … RR-4)

| Rule | Statement |
|---|---|
| **RR-1** | `ArtifactResolver` is a `Protocol`, injected **explicitly** at every call site. No module-level registry, no global default, no import-time side effect. |
| **RR-2** | A resolver returns values or raises. It never returns `None` or an empty array as a "not found" signal, because a caller that forgets to check gets a silently wrong measurement instead of a traceback. |
| **RR-3** | Resolution is not caching. A resolver that memoizes must declare `is_caching = True`, because a stale cache turns a content-addressed reference into a false statement. |
| **RR-4** | The resolver never sees the action. It maps a reference to values; what is done with them belongs to the executor. A resolver that could transform could apply an action nobody declared. |

### 2.3 Co-action consistency report (CR-1 … CR-8)

A new payload from a new function, with a **16-key** schema and its own
`summary_type`. It nests; it mutates nothing.

Four **statuses** × four **diagnoses**:

| Status | Meaning |
|---|---|
| `consistent` | Declaration and execution agree on every axis. |
| `inconsistent` | They disagree, and the disagreement is identified. |
| `not_applicable` | No co-action declared; nothing to check. |
| `indeterminate` | Cannot be decided from what the bundle carries. |

| Diagnosis | Meaning |
|---|---|
| `declaration_and_execution_agree` | The confirming case. |
| `declared_not_executed` | The bundle declared an action the executor did not apply. |
| `executed_not_declared` | The executor applied an action the bundle did not declare. |
| `target_ambiguous` | A family is declared with no target, and more than one candidate exists. |

`target_ambiguous` is the diagnosis the §1 finding produces. It is
`indeterminate`, **not** `inconsistent`: nothing has yet disagreed, and calling
it a disagreement would overstate what was observed.

| Rule | Statement |
|---|---|
| **CR-1** | Exactly 16 keys. Asserted against a frozen key list. |
| **CR-2** | New `summary_type`, new payload, new function. `discovery_task_result`'s 22 keys are untouched. |
| **CR-3** | Every status × diagnosis pair that can occur is reachable, and a test constructs each. |
| **CR-4** | Pairs that cannot co-occur are refused at construction, not reported. |
| **CR-5** | `scientific_payload` is hashed; `execution_metadata` is not. |
| **CR-6** | No `None` is written where a number is expected; absence is an explicit sentinel key. |
| **CR-7** | Strict JSON, `allow_nan=False`. |
| **CR-8** | The report never decides a scientific verdict. It reports agreement between a declaration and an execution, which is a bookkeeping fact. |

### 2.4 Benchmark pair C-7 / C-8 (CB-1 … CB-4)

The conservative-form pair, and the first cases with **more than one numeric
parameter** — the population on which §1's defect is observable at all.

| Rule | Statement |
|---|---|
| **CB-1** | C-7 and C-8 each declare ≥2 numeric parameters. |
| **CB-2** | C-7 is the confirming case: a named target, the other parameter untouched. |
| **CB-3** | C-8 is the deliberate obstruction: an unnamed target on a multi-parameter problem, expected `indeterminate` / `target_ambiguous`. |
| **CB-4** | Neither case may report `consistent` for a reason the other does not distinguish. |

### 2.5 Generic conformance fixtures (CF-1, CF-2)

| Rule | Statement |
|---|---|
| **CF-1** | Six fixtures, exercising each identity helper and each resolver rule, independent of any equation family. |
| **CF-2** | The fixtures are importable by later sub-phases without importing a benchmark. |

---

## 3. Pre-registered pilot

**Artifact location:** `docs/design/v0_38e_pilot_report.md`. Append-only. A
blocked run is retained unedited.

**Block criteria — any one blocks the confirmatory freeze:**

- **B-1** Any status × diagnosis pair declared reachable in §2.3 that no
  constructed case produces.
- **B-2** C-8 reporting anything but `indeterminate` / `target_ambiguous`.
- **B-3** C-7 showing its second parameter altered.
- **B-4** A scientific-identity check passing where storage identity fails and
  the metric was not declared (CI-3 violated in practice, not just in test).
- **B-5** The 16-key schema disagreeing with the frozen key list.
- **B-6** Any measurement quoted in a norm other than the one its bound was
  derived in — the v0.37c pilot-1 defect.

`blocked_pilot_criteria_not_met` is a first-class outcome. It is not a failure
of the sub-phase; it is the sub-phase working.

**Confirmatory grid is disjoint from the pilot grid.** Seeds are frozen at the
pilot report, not chosen after seeing pilot numbers.

---

## 4. What v0.38e does not claim

- **No nonperiodic domain support.** Still deferred to v0.41.
- **No irregular-grid anything.** That is v0.38a–d, behind the `v0.38.0-rc1`
  tag gate.
- **No statement about coefficient fields with more than one coordinate
  dependency.** The v0.38e cases are 1-D in space.
- **No claim that the `target_ambiguous` diagnosis is complete.** It detects the
  one ambiguity §1 identified. Other under-specifications may exist and are not
  ruled out.
- **No cross-platform claim.** v0.38e is measured on `Darwin/arm64`. The
  portability classes are `exact_discrete` throughout — the report carries no
  floating-point threshold — so a replay is expected to agree bitwise, and that
  expectation is an argument until a replay is run.

---

## 5. Signature

Frozen before implementation. Any change to §2 or §3 after this point is an
amendment with its own dated entry, not an edit.
