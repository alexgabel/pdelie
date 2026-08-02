# v0.38 — Binding Design Constraints (pre-registered)

**Status:** binding. Written before v0.38a opens.

Every frozen decision below has a machine-checkable target, asserted by
`tests/test_v0_38_binding_constraints.py`. A constraint nothing can check is a
preference.

---

## Carried-forward debt

Recorded as **deferred with a named release**, not as silence. An unlisted
limitation reads as an oversight.

| Item | Disposition |
|---|---|
| Nonperiodic domains | **Deferred to v0.41.** `execute_state_action` refuses them today; lifting that needs a crop-based action family, which is its own arc. |
| Monotone coefficients | **Deferred to v0.41.** Follows the above: a monotone profile is not periodic, so the axis cannot return before nonperiodic actions do. |
| `linear_combination_of_derivatives` synthesis | **Consumer-based defer.** No v0.38 consumer identified as of signing. It stays declared-but-unsynthesised, reporting `inconclusive` with a stated reason. If a v0.38 sub-phase selects the family, this defer is void and synthesis becomes in-scope for that sub-phase. |

The third is deliberately conditional rather than dated. Dating a defer nobody
needs invents work; leaving it silent invites someone to select the family and
get `inconclusive` with no warning. A test asserts no shipped benchmark case
selects it.

---

## C-1 (v0.38a) — Provenance is derived, never asserted

`full_field_derivatives_available` must be **derived** from what was actually
computed. A caller-supplied boolean is a claim about someone else's state, and
the v0.37 C-5 defect is what happens when a declaration and an execution are
allowed to disagree.

**Row identity: semantic IDs are primary, integer indices secondary and
derived.** An integer index means nothing after a filter, a sort, or a
concatenation, and every one of those is a legal operation on a design matrix.

---

## C-2 (v0.38b) — Accuracy is derived; degenerate grids are rejected here

**`formal_accuracy` is derived, not caller-declared** — same rule as C-1, same
reason.

**Duplicate or unsorted coordinates are rejected at v0.38**, not repaired. A
silent sort changes which row is which, and a silent dedup changes the count.
Rejecting is recoverable; repairing is not.

**G-5 is defined as `max_spacing / min_spacing > threshold`** — a ratio, so it
is scale-free. An absolute spacing test would classify the same grid differently
in metres and in kilometres.

**The stencil-size cap and the G-5 threshold are piloted, not guessed.** Both
are frozen only at a confirmatory freeze, after a pilot measures them. No value
appears in the hypothesis freeze.

**The convergence gate requires §6-style traceability *and* a declared
oracle source.** Per `ANALYTICAL_ORACLE_DISCIPLINE.md`, the Fornberg
convergence-order bound needs two independent derivations, and the secondary one
is named before the pilot runs.

---

## C-3 (v0.38c) — Quadrature is narrowed; `diagnostic_only` is release-scoped

**Quadrature narrows to `{nonuniform_trapezoidal, user_supplied_validated_weights}`.**
Anything else is refused rather than approximated.

**`diagnostic_only` becomes `diagnostic_only_v0_38`** — release-scoped, not
permanently immutable. A flag asserting a property forever cannot be revisited
when the property changes, and "this payload made no numerical claim in v0.38"
is the honest statement.

---

## C-4 (v0.38d) — Timing and error metrics are declared

**`per_backend_runtime_stats` carries warmup, repeats, median and IQR.** A
single timing is a sample of one, and a mean without a spread hides bimodality
from JIT warmup.

**Every error metric declares its norm via `ErrorMetricSpec`.** This is C-5's
structural fix, landed at day-zero: `pdelie.contracts.ErrorMetricSpec` plus
`require_matching_metric`, which refuses a bound and a measurement carrying
different `metric_spec_id`s.

---

## Cross-cutting

**Reconnaissance before pilot, disclosed.** Any sub-phase using a two-stage
freeze must state whether measurement informed the hypothesis, and keep the
confirmatory grid disjoint from anything already looked at. v0.37c did this and
said so; the discipline is now required rather than exemplary.

**Pilot reports are append-only.** Blocked runs are retained unedited. A report
showing only the passing run is a selection-effect document.

**Profile geometry is validated against the domain before any run.**
`pdelie.contracts.ProfileGeometrySpec` plus `require_compatible_domain` refuse a
nonperiodic profile under a wrapping action — the C-4 defect, made structurally
impossible rather than documented.

**Forward promises name a future version.** Every "will change at version X"
notice in `src/` is checked by `tests/test_forward_promises.py` against the
packaged version read from `pyproject.toml`. v0.37 shipped a notice promising
v0.37, because the promise and the release drifted apart with nothing watching.

**The refused vocabulary names v0.38's methods explicitly.** Six terms added
to `tests/test_forbidden_language.py`: `unstructured_mesh`, `arbitrary_geometry`,
`rbf_fd`, `meshfree_sindy`, `noise_robust_derivative`, `meshfree_pde_discovery`.
The first three name methods PDELie does not implement; the rest name claims the
irregular layer does not make. `noise_robust_derivative` is declared **subsumed**
by the existing `noise_robust` — it is retained so a reader finds the exact
phrase, and marked so nobody mistakes it for doing detection work it does not do.

**`periodic_smooth` is a distinct smoothness class.** `smooth` says nothing about
the wrap: C-4 was smooth on the interior and still carried a `1.9998` seam jump.
`periodic_smooth` asserts smoothness *across* the seam, and
`ProfileGeometrySpec` refuses it when no periodic axis is named — a claim about a
seam the same declaration says does not exist.

**Load-bearing analytical bounds declare their oracle at the marker.**
`@pytest.mark.load_bearing_analytical(oracle_source="method: location")` is
registered and enforced by `tests/test_analytical_oracle_marker.py`, which parses
the decorator with `ast`, requires a method from a closed three-item vocabulary,
and requires a location. Its population is empty until v0.38b, so it carries
sentinels proving the guard can fire rather than passing vacuously.

**Execution must match declaration.**
`tests/test_benchmark_action_semantics_guard.py` scans benchmark code for
transformations applied outside the declared action path. This is the gate the
v0.37 arc did not have.

---

## What this document does not do

It does not schedule v0.38 sub-phases, size them, or pick their thresholds.
Every number here is either measured elsewhere or explicitly deferred to a
pilot.
