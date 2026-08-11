"""The derivative-reference hypothesis freeze binds the implementation.

Written alongside the freeze and BEFORE the implementation, so the frozen
decisions are executable from the moment they are made rather than becoming
executable once someone remembers.

These tests assert the freeze's own coherence. They will grow assertions
against the emitted payload when the layer lands; until then they hold the
contract that the payload must satisfy.

Why the freeze needs tests at all
=================================

v0.38d was specified in a plan and did not ship. Nothing failed when it didn't,
because a plan is not executable. The gap was found months later by comparing
the plan to the repository by hand.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE = REPO_ROOT / "docs/design/v0_39_0_derivative_reference_hypothesis_freeze.md"

BACKENDS = (
    "spectral_periodic_uniform",
    "fd_uniform",
    "fd_nonuniform",
    "weak_uniform",
    "weak_irregular",
)

INAPPLICABILITY = (
    "not_applicable_geometry",
    "not_applicable_boundary_condition",
    "not_applicable_missing_full_field",
    "not_applicable_unsupported_derivative_order",
)

FORBIDDEN_KEYS = ("best_backend", "recommended_backend", "winner", "optimal_backend")

FIXTURES = (
    "periodic_fourier_mode",
    "polynomial_exactness",
    "smooth_gaussian",
    "boundary_sensitive_nonperiodic",
    "nonuniform_manufactured",
    "weak_integral_manufactured",
)


def _text() -> str:
    return FREEZE.read_text(encoding="utf-8")


def _prose() -> str:
    """Emphasis stripped, dashes normalised, whitespace collapsed.

    Matching raw markdown couples a check to presentation: ``not new\nnumerics``
    and ``not new numerics`` are the same claim, and a line rewrap should not
    turn a passing guard red. This is the same normalisation the Gate F audit
    tests use, for the same reason.
    """
    # NOT `_`: these documents use `*` for emphasis, and stripping
    # underscores would destroy every snake_case identifier the
    # assertions look for -- `spectral_periodic_uniform` became
    # `spectralperiodicuniform` and eight tests failed for a reason
    # unrelated to the document's content.
    text = re.sub(r"[*`]", "", _text())
    text = text.replace("\u2014", "--").replace("\u2013", "--")
    return re.sub(r"\s+", " ", text)


def test_the_freeze_exists_and_precedes_implementation() -> None:
    """No module may exist before the freeze that governs it.

    The order matters: a freeze written after the code describes the code, it
    does not constrain it.
    """
    assert FREEZE.exists()
    implementation = REPO_ROOT / "src/pdelie/differentiation/backend_reference.py"
    if implementation.exists():
        assert "Status: frozen" in _text(), (
            "the implementation exists but the freeze is not marked frozen"
        )


def test_all_five_backends_are_named() -> None:
    prose = _prose()
    for backend in BACKENDS:
        assert backend in prose, f"{backend} is not in the frozen backend matrix"


def test_every_backend_class_it_names_actually_exists() -> None:
    """A freeze that binds a backend the repository does not have is a plan.

    v0.38d's specification named five backends and shipped none of the
    comparison; this asserts the five are real before anything depends on them.
    """
    for module in (
        "pdelie.derivatives.spectral_fd",
        "pdelie.differentiation.fornberg",
        "pdelie.residuals.weak_1d",
        "pdelie.residuals.irregular_weak",
    ):
        __import__(module)


def test_inapplicability_is_a_result_not_an_error_value() -> None:
    """The distinction the whole report rests on."""
    prose = _prose()
    for outcome in INAPPLICABILITY:
        assert outcome in prose
    assert "never assigned an infinite, large, or sentinel error" in prose
    assert "Not zero, not infinity" in prose


def test_a_raising_backend_is_distinct_from_an_inapplicable_one() -> None:
    """Folding an exception into inapplicability hides a defect as a capability."""
    prose = _prose()
    assert "backend_error" in prose
    assert "not silently folded" in prose


def test_the_no_global_best_policy_is_enforced_on_payloads_not_source() -> None:
    """A substring check on source cannot tell a key from a comment saying the
    key is absent. This repository has caught that defect repeatedly."""
    prose = _prose()
    for key in FORBIDDEN_KEYS:
        assert key in prose, f"{key} is not listed as forbidden"
    assert "walking the emitted payload, not by scanning source text" in prose


def test_every_fixture_is_named_with_the_property_it_exercises() -> None:
    prose = _prose()
    for fixture in FIXTURES:
        assert fixture in prose, f"fixture {fixture} is not frozen"
    assert "span applicability, not difficulty" in prose


def test_the_pilot_can_block_and_names_the_blocking_status() -> None:
    """A pilot that cannot block is a formality."""
    prose = _prose()
    assert "blocked_pilot_derivative_reference_criteria_not_met" in prose
    for criterion in ("PV-1", "PV-2", "PV-3", "PV-4"):
        assert criterion in prose
    assert "no confirmatory freeze is written" in prose


def test_pv2_guards_against_an_unreachable_vocabulary() -> None:
    """The freeze's own most likely failure, named in the freeze.

    A vocabulary richer than the fixtures can reach reads as thorough and is
    untested. That is the shape of the ten leaked d=4 rows and of F-4 itself.
    """
    prose = _prose()
    assert "reached by at least one fixture" in prose
    assert "unreachable outcome" in prose


def test_the_closure_gate_records_what_is_deferred_to_v0_39b() -> None:
    """Requirements 1-3 concern an artifact that does not exist yet.

    Freezing them abstractly is deliberate; claiming they are satisfied would
    not be.
    """
    prose = _prose()
    assert "validated at v0.39b" in prose
    assert "not satisfied until the v0.39b validation runs" in prose
    assert "does not discharge it" in prose


def test_the_freeze_does_not_claim_v0_38d_shipped() -> None:
    """The record stays honest about the gap this work closes."""
    prose = _prose()
    assert "That did not ship." in prose
    assert "is not amended" in prose


def test_the_freeze_forbids_touching_backend_numerics() -> None:
    """A harness that repairs what it measures cannot measure it."""
    prose = _prose()
    assert "not new numerics" in prose
    assert "cannot measure it" in prose


def test_runtime_requires_warmups_and_a_distribution() -> None:
    """A single wall-clock reading is not a runtime measurement."""
    prose = _prose()
    for field in ("runtime_median_seconds", "runtime_iqr_seconds", "warmup_runs", "measured_runs"):
        assert field in prose
    assert "single wall-clock reading is not a runtime measurement" in prose

    # And the primitive it depends on already exists, with those fields.
    from dataclasses import fields

    from pdelie.differentiation.error_reference import RuntimeStats

    names = {f.name for f in fields(RuntimeStats)}
    assert {"warmup_runs", "measured_runs", "median_seconds", "iqr_seconds"} <= names


def test_interior_and_boundary_errors_are_not_pooled() -> None:
    prose = _prose()
    assert "interior_error" in prose and "boundary_error" in prose
    assert "never pooled" in prose
