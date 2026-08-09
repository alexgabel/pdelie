"""Typed source of truth for replay workloads and rows.

Semantics originate here. ``row_id`` is **generated** from a
:class:`ReplayRowSpec`; nothing parses it to recover meaning.

Why this exists
===============

Twice now, scope metadata has been repaired by pattern matching, and twice it
has been wrong:

1. ``_ORDERS = (1, 2, 3, 4)`` swept on the harness's own authority, sweeping a
   derivative order the v0.38b freeze disclaims.
2. The repair threaded ``order=`` through call sites with a regex. It matched
   the ``floor_regime`` and ``none_kind`` constructors and missed the
   ``signal_regime`` ones, so ten ``d = 4`` rows emitted
   ``derivative_order: None`` and entered the gate population.

Deriving the order from a row key like ``expx3_d4`` would be the same mistake in
a new costume: a **display identifier is not a data contract**. The dependency
runs one way only:

    workload spec -> row spec -> row_id

A reverse parser exists (:func:`parse_row_id_for_audit`) and is used **only** to
assert consistency. It never supplies a value the gate consumes.

The invariants
==============

* ``order_parameterized`` and ``derivative_order`` must agree, both ways.
* A gate row from an order-parameterised family must carry ``d in {1, 2, 3}``.
* ``derivative_order == 4`` forces ``gate_use == "exploratory_only"``.
* An unknown family is rejected.
* A missing portability class is rejected.

Each is enforced at construction, so a malformed row cannot be built -- not
merely cannot be emitted.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "GATE_USES",
    "NON_ORDER_PARAMETERIZED_FAMILIES",
    "ORDER_PARAMETERIZED_FAMILIES",
    "PORTABILITY_CLASSES",
    "WORKLOAD_DECLARATIONS",
    "ReplayRowSpec",
    "ReplayWorkloadSpec",
    "declaration_for",
    "load_scope",
    "parse_row_id_for_audit",
]

PORTABILITY_CLASSES = ("exact_discrete", "tolerance_numeric", "platform_specific_diagnostic")
GATE_USES = ("gate_evidence", "exploratory_only")


class ContractViolation(ValueError):
    """A spec that cannot exist. Raised at construction, never at emission."""


def load_scope() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "configs/gate_f_replay_scope.json"
    return json.loads(path.read_text())


_SCOPE = load_scope()

#: Families whose rows are parameterised by derivative order. Frozen in the
#: scope artifact, not here: F-4 accepts ``derivative_order is None`` only
#: because a declared contract permits it for the family, never because the
#: validator cannot tell what the row means.
ORDER_PARAMETERIZED_FAMILIES = frozenset(_SCOPE["order_parameterized_families"])

#: Families that genuinely carry no derivative order.
NON_ORDER_PARAMETERIZED_FAMILIES = frozenset(_SCOPE["non_order_parameterized_families"])

#: Per workload, because a name prefix is not a contract. Four ``fornberg_*``
#: workloads are order-parameterised and ``fornberg_fn_12_uniform_spacing_ratio``
#: is not -- it measures the *grid's* spacing ratio, which has no derivative
#: order. The typed contract caught that mislabelling on its first run; a prefix
#: heuristic would have shipped it, and prefix-derived semantics is precisely the
#: defect class this module exists to end.
WORKLOAD_DECLARATIONS: dict[str, dict[str, Any]] = _SCOPE["workload_declarations"]


def declaration_for(workload_id: str) -> tuple[str, bool]:
    """Return ``(family, order_parameterized)`` as *declared*. Never inferred."""
    try:
        declared = WORKLOAD_DECLARATIONS[workload_id]
    except KeyError:
        raise ContractViolation(
            f"{workload_id!r} has no entry in workload_declarations. A workload "
            f"with no declared family cannot be classified, and guessing from its "
            f"name prefix is the defect this contract replaces."
        ) from None
    return declared["family"], bool(declared["order_parameterized"])


@dataclass(frozen=True)
class ReplayWorkloadSpec:
    """One workload: what it is, and what rows it may produce."""

    workload_id: str
    workload_family: str
    order_parameterized: bool
    derivative_orders: tuple[int, ...]
    portability_class: str
    gate_use: str

    def __post_init__(self) -> None:
        if self.workload_family not in (
            ORDER_PARAMETERIZED_FAMILIES | NON_ORDER_PARAMETERIZED_FAMILIES
        ):
            raise ContractViolation(
                f"{self.workload_id}: unknown workload family "
                f"{self.workload_family!r}. Families are frozen; an unrecognised "
                f"one is rejected rather than defaulted."
            )
        declared = self.workload_family in ORDER_PARAMETERIZED_FAMILIES
        if declared != self.order_parameterized:
            raise ContractViolation(
                f"{self.workload_id}: order_parameterized={self.order_parameterized} "
                f"contradicts family {self.workload_family!r}, which is "
                f"{'order-parameterised' if declared else 'not order-parameterised'}."
            )
        if self.order_parameterized and not self.derivative_orders:
            raise ContractViolation(
                f"{self.workload_id} is order-parameterised but declares no orders."
            )
        if not self.order_parameterized and self.derivative_orders:
            raise ContractViolation(
                f"{self.workload_id} is not order-parameterised but declares "
                f"orders {self.derivative_orders}."
            )
        if self.portability_class not in PORTABILITY_CLASSES:
            raise ContractViolation(
                f"{self.workload_id}: portability_class {self.portability_class!r} "
                f"is not one of {list(PORTABILITY_CLASSES)}."
            )
        if self.gate_use not in GATE_USES:
            raise ContractViolation(f"{self.workload_id}: bad gate_use {self.gate_use!r}.")


@dataclass(frozen=True)
class ReplayRowSpec:
    """One row. Its identity is derived from these fields, never the reverse."""

    workload_id: str
    workload_family: str
    order_parameterized: bool
    derivative_order: int | None
    portability_class: str
    gate_use: str
    #: Discriminates rows within a workload. Never carries semantics.
    label: str

    def __post_init__(self) -> None:
        if self.workload_family not in (
            ORDER_PARAMETERIZED_FAMILIES | NON_ORDER_PARAMETERIZED_FAMILIES
        ):
            raise ContractViolation(f"unknown workload family {self.workload_family!r}")
        if self.portability_class not in PORTABILITY_CLASSES:
            raise ContractViolation(f"bad portability_class {self.portability_class!r}")
        if self.gate_use not in GATE_USES:
            raise ContractViolation(f"bad gate_use {self.gate_use!r}")

        # Both directions. Either alone leaves a hole, and the hole is exactly
        # what let ten d=4 rows through with derivative_order None.
        if self.order_parameterized and self.derivative_order is None:
            raise ContractViolation(
                f"{self.workload_id}/{self.label}: family {self.workload_family!r} "
                f"is order-parameterised, so derivative_order may not be None. "
                f"This is the defect that put ten d=4 rows into the gate."
            )
        if not self.order_parameterized and self.derivative_order is not None:
            raise ContractViolation(
                f"{self.workload_id}/{self.label}: family {self.workload_family!r} "
                f"carries no derivative order, but one was supplied "
                f"({self.derivative_order})."
            )

        if self.derivative_order is not None:
            if self.derivative_order == 4 and self.gate_use != "exploratory_only":
                raise ContractViolation(
                    f"{self.workload_id}/{self.label}: derivative_order 4 is "
                    f"outside the frozen scope, so gate_use must be "
                    f"'exploratory_only', not {self.gate_use!r}."
                )
            if self.gate_use == "gate_evidence" and self.derivative_order not in (1, 2, 3):
                raise ContractViolation(
                    f"{self.workload_id}/{self.label}: gate evidence at "
                    f"derivative_order {self.derivative_order}, outside {{1,2,3}}."
                )

    @property
    def row_id(self) -> str:
        """Generated. Display and identity only.

        Nothing reads meaning back out of this. The ``_d{n}`` suffix exists so a
        human can scan a report, and :func:`parse_row_id_for_audit` asserts it
        agrees with ``derivative_order`` -- an audit, not a source.
        """
        if self.derivative_order is None:
            return self.label
        return f"{self.label}_d{self.derivative_order}"

    def as_row(self, **measurements: Any) -> dict[str, Any]:
        """The emitted JSON row. Metadata comes from the spec, not the caller."""
        return {
            "workload": self.workload_id,
            "row_key": self.row_id,
            "workload_family": self.workload_family,
            "order_parameterized": self.order_parameterized,
            "derivative_order": self.derivative_order,
            "portability_class": self.portability_class,
            "gate_use": self.gate_use,
            "scope": (
                "in_frozen_scope" if self.gate_use == "gate_evidence"
                else "outside_frozen_scope"
            ),
            **measurements,
        }


_ROW_ID_ORDER = re.compile(r"_d(\d+)$")


def parse_row_id_for_audit(row_id: str) -> int | None:
    """Recover the order a row_id *displays*, for consistency auditing only.

    **Never** call this to obtain the order a gate consumes. It exists so a test
    can assert that the generated display string agrees with the typed value --
    catching a formatting bug, not supplying semantics.
    """
    match = _ROW_ID_ORDER.search(row_id)
    return int(match.group(1)) if match else None
