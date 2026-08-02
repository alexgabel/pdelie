"""v0.36e: three-state seed semantics — **superseded at v0.38**.

The behaviour this module asserted no longer exists. It is retained, reduced to
a record of what changed, rather than deleted: a reader tracing why the weak
diagnostic's signature moved should find the transition documented where the old
contract lived, not an absence.

What v0.36e asserted, and what replaced it
==========================================

===================================  ==========================================
v0.36e                               v0.38
===================================  ==========================================
Seed omitted -> ``FutureWarning``,   Seed omitted -> ``TypeError`` from the
legacy nondeterminism retained       signature
``seed=None`` -> explicit opt-in     ``seed=None`` -> ``ScopeValidationError``
to nondeterminism
``seed=<int>`` -> deterministic      unchanged, and now the only path
Three seed states in the payload     One; the two flags are constant False
===================================  ==========================================

The live contract is ``tests/test_v0_38_seed_required.py``.

Why the flip took two releases
==============================

v0.36e promised it for v0.37. v0.37a's freeze scoped the transition out, on the
grounds that an unscoped breaking change during a release close is worse than a
deferred one — and the notice was re-dated to v0.38. That slip is the reason
``tests/test_forward_promises.py`` exists.
"""

from __future__ import annotations

import inspect

from pdelie.tasks.weak_pde_library import inspect_pysindy_weak_pde_library


def test_the_three_state_seed_contract_is_gone() -> None:
    """The single assertion this module still makes."""
    parameter = inspect.signature(inspect_pysindy_weak_pde_library).parameters["seed"]
    assert parameter.default is inspect.Parameter.empty, (
        "seed has a default again, which would restore the omitted state and "
        "with it the legacy nondeterminism v0.38 removed"
    )


def test_this_module_points_at_its_successor() -> None:
    """So the pointer cannot rot into a reference to a deleted file."""
    from pathlib import Path

    successor = Path(__file__).with_name("test_v0_38_seed_required.py")
    assert successor.exists(), (
        "the superseding suite is missing; this module is now the only record "
        "of a contract that no longer holds"
    )
