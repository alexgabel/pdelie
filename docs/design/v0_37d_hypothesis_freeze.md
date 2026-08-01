# v0.37d — Hypothesis Freeze: Downstream Crash Test

**Status:** frozen.

Opens only because `v0_37c_confirmatory_freeze.md` is signed. Three of the
seven branches below are the downstream face of the obstruction cases that
freeze validated.

---

## 1. Seven branches — frozen

| Branch | Bundle state | Outcome |
|---|---|---|
| B-1 | no bundle | passthrough — the original 22-key `discovery_task_result`, unchanged |
| B-2 | valid, coefficient `fixed` | augmented, emits `pdelie_downstream_task_with_action_bundle` |
| B-3 | valid, coefficient `co_transformed` | augmented; the transformed target is used, never compared as unchanged |
| B-4 | `fixed_background` declared while the relation claims co-transformation | **blocked** — `blocked_fixed_background_state_mismatch` |
| B-5 | coefficient action opposes the state action | **blocked** — `blocked_action_direction_wrong` |
| B-6 | parameter action with no state action | **blocked** — `blocked_parameter_only_without_state` |
| B-7 | coefficient present, treatment `unknown` | **blocked** — `blocked_coefficient_treatment_unspecified` |

Each block **names its own reason**. "Invalid" is not actionable; a caller has
to know what to fix.

B-4 is the v0.34b non-equivalence case arriving declared as if it were an
equivalence. B-5 is runtime path P-4.

---

## 2. Blocking happens before discovery — and it is measured

For B-4 through B-7, the discovery task **must not run**. A bundle whose claims
contradict each other describes a problem nobody asked for, and running
discovery on it produces a well-formed result about nothing.

This is enforced by making it observable rather than by inspection:

- `run_downstream_with_action_bundle` takes a **zero-argument callable**, not a
  precomputed result. A result cannot express ordering; a callable can.
- The test hands it a task that **raises on call** and asserts it never fires.
- A second test **counts** invocations across all four blocked branches and
  asserts zero.
- A third points the same sentinel at B-2, where the task *is* supposed to run,
  and asserts it fires. A guard that cannot fail is not a guard.

---

## 3. The 22-key schema does not move

`discovery_task_result` has had a 22-key top level since v0.30.1 and keeps it.

- **B-1** returns the task's payload unchanged — not wrapped, not coerced, not
  re-keyed. A caller who passes no bundle gets exactly what the task produced.
- **B-2 / B-3** emit a **new** `summary_type` carrying the same 22 keys plus
  exactly two: `action_bundle_hash` and `bundle_relation_status`. Twenty-four,
  not twenty-two-plus-a-nested-blob.

A shape-invariant test asserts no branch mutates the task's own payload.

---

## 4. One summary type, two shapes, one discriminator

`pdelie_downstream_task_with_action_bundle` is emitted in two shapes: the 24-key
augmented result, and a shorter blocked report with no task result to augment.
Conditional shapes have precedent here — the weak diagnostic's 27/28-key
conditional — but are only usable if a consumer can tell which it holds without
probing for key presence.

**`bundle_relation_status` is that discriminator, present in both.** It carries
a value from `BLOCK_STATUSES` exactly when the payload is the blocked shape and
never otherwise, and a test asserts the two value sets are disjoint so the
discriminator cannot become ambiguous.

---

## 5. Non-goals

- No change to `discovery_task_result`.
- No change to the v0.37b report schema.
- No new PDE, no new action family.
- No root export.
