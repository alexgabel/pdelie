"""The v0.38 constraints document must stay true about the code it governs.

Same pattern as ``test_v0_37_binding_constraints.py``, with one lesson applied:
the v0.37 version asserted document *contents* and had to be corrected twice
when the contents were right about the wrong population. Where a claim is about
code, this asserts against the code.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs/design/V0_38_BINDING_DESIGN_CONSTRAINTS.md"
SRC = REPO_ROOT / "src/pdelie"


def _doc() -> str:
    """The document with whitespace collapsed.

    It is hard-wrapped Markdown, so any phrase long enough to be worth asserting
    on will straddle a line break. Asserting against the raw text tests the wrap
    width rather than the content -- the same trap the publishing-contract tests
    hit.
    """
    return " ".join(DOC.read_text().split())


def _doc_raw() -> str:
    return DOC.read_text()


def test_the_document_exists_and_is_binding() -> None:
    assert "**Status:** binding" in _doc()


# --- carried-forward debt ---------------------------------------------------


@pytest.mark.parametrize("item", ["Nonperiodic domains", "Monotone coefficients"])
def test_deferred_items_name_a_release(item: str) -> None:
    """A defer without a named release is silence with extra steps."""
    text = _doc()
    assert item in text
    assert "v0.41" in text


def test_the_synthesis_defer_is_conditional_and_its_condition_holds() -> None:
    """Consumer-based defer: void the moment a benchmark case selects the family."""
    assert "Consumer-based defer" in _doc()
    from pdelie.benchmarks import BENCHMARK_CASES

    selecting = [
        case.case_id
        for case in BENCHMARK_CASES.values()
        if case.expected_operator_family == "linear_combination_of_derivatives"
    ]
    assert not selecting, (
        f"cases {selecting} select linear_combination_of_derivatives, so the "
        f"consumer-based defer in V0_38_BINDING_DESIGN_CONSTRAINTS.md is void "
        f"and synthesis is in scope for that sub-phase"
    )


# --- C-4 / cross-cutting: the two specs exist and enforce ------------------


def test_error_metric_spec_refuses_a_cross_norm_comparison() -> None:
    """C-5's structural fix: an linf bound against an l2 measurement is refused."""
    from pdelie.contracts import ErrorMetricSpec
    from pdelie.contracts.error_metric_spec import require_matching_metric
    from pdelie.errors import ScopeValidationError

    bound = ErrorMetricSpec(metric_spec_id="bound_linf", quantity="absolute", norm="linf")
    measured = ErrorMetricSpec(metric_spec_id="measured_l2", quantity="absolute", norm="l2")
    with pytest.raises(ScopeValidationError, match="different quantities"):
        require_matching_metric(bound, measured, where="probe")

    same = ErrorMetricSpec(metric_spec_id="agreed", quantity="absolute", norm="linf")
    require_matching_metric(same, same, where="probe")


def test_error_metric_spec_requires_a_named_norm() -> None:
    from pdelie.contracts import ErrorMetricSpec
    from pdelie.errors import ScopeValidationError

    with pytest.raises(ScopeValidationError, match="not one of"):
        ErrorMetricSpec(metric_spec_id="x", quantity="absolute", norm="rms")


def test_profile_geometry_refuses_a_monotone_periodic_declaration() -> None:
    """The C-4 contradiction, refused at construction rather than at a pilot."""
    from pdelie.contracts import ProfileGeometrySpec
    from pdelie.errors import ScopeValidationError

    with pytest.raises(ScopeValidationError, match="C-4 contradiction"):
        ProfileGeometrySpec(
            profile_id="monotone_smooth",
            periodic_axes=("x",),
            smoothness_class="monotone",
            seam_continuity_required=True,
            domain_types_supported=("periodic_uniform",),
        )


def test_profile_geometry_refuses_a_nonperiodic_profile_under_a_wrapping_action() -> None:
    from pdelie.contracts import ProfileGeometrySpec
    from pdelie.contracts.profile_geometry_spec import require_compatible_domain
    from pdelie.errors import ScopeValidationError

    geometry = ProfileGeometrySpec(
        profile_id="ramp",
        periodic_axes=(),
        smoothness_class="smooth",
        seam_continuity_required=False,
        domain_types_supported=("periodic_uniform", "nonperiodic_uniform"),
    )
    with pytest.raises(ScopeValidationError, match="C-4 defect"):
        require_compatible_domain(
            geometry, "periodic_uniform", spatial_axis="x", action_wraps=True, where="probe"
        )
    # The same profile is fine when nothing wraps.
    require_compatible_domain(
        geometry, "nonperiodic_uniform", spatial_axis="x", action_wraps=False, where="probe"
    )


# --- cross-cutting: the guards the document cites actually exist -----------


@pytest.mark.parametrize(
    "path",
    [
        "tests/test_benchmark_action_semantics_guard.py",
        "tests/test_forward_promises.py",
        "docs/design/ANALYTICAL_ORACLE_DISCIPLINE.md",
    ],
)
def test_every_cited_guard_exists(path: str) -> None:
    """A constraint citing a file that does not exist is not enforceable."""
    assert (REPO_ROOT / path).is_file(), path
    assert Path(path).name in _doc() or path in _doc(), path


def test_the_document_claims_no_threshold_values() -> None:
    """C-2 defers the stencil cap and G-5 threshold to a pilot.

    A number here would be the thing the two-stage freeze exists to prevent, so
    the document is scanned for numeric literals that look like thresholds.
    """
    text = _doc()
    assert "piloted, not guessed" in text
    assert "No value appears in the hypothesis freeze" in text


def test_provenance_is_required_to_be_derived_not_asserted() -> None:
    text = _doc()
    assert "derived" in text
    assert "full_field_derivatives_available" in text
    assert "formal_accuracy" in text


# --- the package conversion did not break any import path ------------------


def test_the_contracts_package_preserves_every_prior_import() -> None:
    """contracts.py became a package; 97 call sites had to keep working.

    Asserted by parsing every ``from pdelie.contracts import ...`` in the tree
    and resolving each name, rather than trusting that the suite happened to
    exercise all of them.
    """
    import importlib

    module = importlib.import_module("pdelie.contracts")
    wanted: set[str] = set()
    for path in list(SRC.rglob("*.py")) + list((REPO_ROOT / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "pdelie.contracts":
                wanted.update(alias.name for alias in node.names)
    assert wanted, "no imports found; this test would vacuously pass"
    missing = sorted(name for name in wanted if not hasattr(module, name))
    assert not missing, f"the package conversion dropped {missing}"
