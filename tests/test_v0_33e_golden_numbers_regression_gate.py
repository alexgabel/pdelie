"""v0.33e golden-numbers regression gate.

v0.30 shipped three numerically load-bearing changes -- the ``finite_difference``
derivative backend, the ``compute_derivatives(backend="auto")`` dispatcher, and
interior-only residual diagnostics. The existing per-version release gates
enforce *structural* invariants (schema shapes, forbidden root attributes,
phrase presence) but never pinned the *numerical* output of the derivative and
residual pipelines. Downstream callers depending on a reproducible number had no
protection against silent drift.

This gate replays every publicly supported PDE through
``generator -> compute_derivatives(backend="auto") -> residual evaluator`` under
a frozen seed and grid, and compares six aggregate metrics per PDE against
``tests/fixtures/v0_33e_golden_numbers.json`` at ``rtol=1e-6, atol=1e-12``.

Only aggregate norms are pinned. BLAS reduction order differs across the Linux
and macOS wheels, so element-wise equality is not a portable invariant.

Regenerating the fixture requires a named cause -- see
``tests/_helpers/regenerate_golden_fixture``. No unnamed drift is permitted in
the release-close CHANGELOG.
"""

from __future__ import annotations

import json

import pytest

from tests._helpers.regenerate_golden_fixture import (
    BATCH_SIZE,
    GENERATOR_SEED,
    GOLDEN_ATOL,
    GOLDEN_FIXTURE_PATH,
    GOLDEN_PDE_NAMES,
    GOLDEN_PDE_SPECS,
    GOLDEN_RTOL,
    NUM_POINTS,
    NUM_TIMES,
    PDE_ENTRY_KEYS,
    PINNED_METRIC_NAMES,
    SUMMARY_SCHEMA_VERSION,
    SUMMARY_TYPE,
    compute_golden_entry,
    load_fixture,
    regenerate,
)

_SPECS_BY_NAME = {spec.name: spec for spec in GOLDEN_PDE_SPECS}


@pytest.fixture(scope="module")
def fixture_payload() -> dict:
    return load_fixture()


@pytest.fixture(scope="module")
def fixture_entries(fixture_payload: dict) -> dict:
    return {entry["name"]: entry for entry in fixture_payload["pdes"]}


# --------------------------------------------------------------------------
# Fixture structure
# --------------------------------------------------------------------------


def test_fixture_is_strict_json() -> None:
    """The fixture must round-trip through strict JSON: no NaN, Infinity, or -Infinity."""
    raw = GOLDEN_FIXTURE_PATH.read_text(encoding="utf-8")
    payload = json.loads(raw)
    json.dumps(payload, allow_nan=False)


def test_fixture_header_matches_frozen_configuration(fixture_payload: dict) -> None:
    """The pinned grid in the fixture must match the grid the gate replays."""
    assert fixture_payload["summary_schema_version"] == SUMMARY_SCHEMA_VERSION
    assert fixture_payload["summary_type"] == SUMMARY_TYPE
    assert fixture_payload["generator_seed"] == GENERATOR_SEED
    assert fixture_payload["batch_size"] == BATCH_SIZE
    assert fixture_payload["num_times"] == NUM_TIMES
    assert fixture_payload["num_points"] == NUM_POINTS


def test_fixture_records_a_named_regeneration_reason(fixture_payload: dict) -> None:
    """Every regeneration names its cause; an empty reason is unnamed drift."""
    reason = fixture_payload["last_regeneration_reason"]
    assert isinstance(reason, str)
    assert reason.strip(), "last_regeneration_reason must name the cause of the drift."


def test_every_supported_pde_has_a_golden_entry(fixture_payload: dict) -> None:
    """Exit gate: all 5 publicly supported PDE generators are pinned, in spec order.

    Fisher-KPP is not a separate entry -- it is the equation
    ``generate_reaction_diffusion_1d_field_batch`` produces
    (``parameter_tags["equation"] == "reaction_diffusion_fisher_kpp"``), and
    ``docs/specs/SUPPORT_MATRIX.md`` carries a single Fisher-KPP row for it.
    """
    assert tuple(entry["name"] for entry in fixture_payload["pdes"]) == GOLDEN_PDE_NAMES


@pytest.mark.parametrize("pde_name", GOLDEN_PDE_NAMES)
def test_fixture_entry_shape(pde_name: str, fixture_entries: dict) -> None:
    """Each entry carries exactly the frozen key set, with finite float metrics."""
    entry = fixture_entries[pde_name]
    assert tuple(entry) == PDE_ENTRY_KEYS

    spec = _SPECS_BY_NAME[pde_name]
    assert entry["generator_kwargs"] == spec.generator_kwargs
    assert entry["max_spatial_order"] == spec.max_spatial_order
    assert entry["boundary_condition_x"] in {
        "periodic",
        "dirichlet",
        "neumann",
        "open_unknown",
    }
    for metric_name in PINNED_METRIC_NAMES:
        value = entry[metric_name]
        assert isinstance(value, float), f"{pde_name}.{metric_name} must be a float."


# --------------------------------------------------------------------------
# The gate itself
# --------------------------------------------------------------------------


@pytest.mark.parametrize("pde_name", GOLDEN_PDE_NAMES)
def test_golden_numbers_do_not_drift(pde_name: str, fixture_entries: dict) -> None:
    """Replay the pipeline and fail on any metric that drifts past the tolerance."""
    expected = fixture_entries[pde_name]
    observed = compute_golden_entry(_SPECS_BY_NAME[pde_name])

    drifted = []
    for metric_name in PINNED_METRIC_NAMES:
        expected_value = expected[metric_name]
        observed_value = observed[metric_name]
        tolerance = GOLDEN_ATOL + GOLDEN_RTOL * abs(expected_value)
        deviation = abs(observed_value - expected_value)
        if deviation > tolerance:
            relative = deviation / abs(expected_value) if expected_value else float("inf")
            drifted.append(
                f"  {metric_name}: expected {expected_value!r}, observed {observed_value!r} "
                f"(abs deviation {deviation:.6e}, relative {relative:.6e}, tolerance {tolerance:.6e})"
            )

    if drifted:
        raise AssertionError(
            f"Golden-numbers drift detected for {pde_name!r} "
            f"(rtol={GOLDEN_RTOL}, atol={GOLDEN_ATOL}):\n"
            + "\n".join(drifted)
            + "\n\nIf this drift is intended, regenerate with a named cause:\n"
            f"  python -m tests._helpers.regenerate_golden_fixture --pde {pde_name} "
            '--reason "<named cause>"\n'
            "and record the same cause in the release-close CHANGELOG entry."
        )


@pytest.mark.parametrize("pde_name", GOLDEN_PDE_NAMES)
def test_boundary_condition_matches_fixture(pde_name: str, fixture_entries: dict) -> None:
    """The pinned boundary condition must still describe the generated field.

    v0.33a adds nonperiodic golden fixtures; until then every pinned entry is
    periodic, and a silent flip would invalidate the backend the gate exercises.
    """
    observed = compute_golden_entry(_SPECS_BY_NAME[pde_name])
    assert observed["boundary_condition_x"] == fixture_entries[pde_name]["boundary_condition_x"]


@pytest.mark.parametrize("pde_name", GOLDEN_PDE_NAMES)
def test_replay_is_deterministic_within_a_process(pde_name: str) -> None:
    """The pinned seed must produce bit-identical metrics on repeat evaluation."""
    spec = _SPECS_BY_NAME[pde_name]
    first = compute_golden_entry(spec)
    second = compute_golden_entry(spec)
    for metric_name in PINNED_METRIC_NAMES:
        assert first[metric_name] == second[metric_name], (
            f"{pde_name}.{metric_name} is not reproducible within a single process; "
            "the golden gate requires a deterministic pipeline."
        )


# --------------------------------------------------------------------------
# Regeneration flow
# --------------------------------------------------------------------------


def test_regeneration_requires_a_named_reason() -> None:
    with pytest.raises(ValueError, match="unnamed drift is not permitted"):
        regenerate(reason="   ")


def test_regeneration_rejects_unknown_pde_names() -> None:
    with pytest.raises(ValueError, match="Unknown PDE name"):
        regenerate(reason="probing an unknown name", pde_names=["navier_stokes_3d"])


def test_targeted_regeneration_carries_other_entries_over_verbatim(
    fixture_entries: dict,
) -> None:
    """``--pde heat_1d`` must not silently re-pin the other four PDEs."""
    payload = regenerate(reason="targeted regeneration smoke test", pde_names=["heat_1d"])
    regenerated = {entry["name"]: entry for entry in payload["pdes"]}

    assert tuple(entry["name"] for entry in payload["pdes"]) == GOLDEN_PDE_NAMES
    for pde_name in GOLDEN_PDE_NAMES:
        if pde_name == "heat_1d":
            continue
        assert regenerated[pde_name] == fixture_entries[pde_name], (
            f"Targeted regeneration of heat_1d must leave {pde_name} untouched."
        )


def test_full_regeneration_reproduces_the_committed_fixture(fixture_payload: dict) -> None:
    """A no-op ``--all`` regeneration must reproduce the committed numbers exactly.

    This is the strongest form of the gate: it proves the committed fixture was
    generated by the same code path the gate replays, so the fixture cannot be
    hand-edited into agreement.
    """
    payload = regenerate(reason=fixture_payload["last_regeneration_reason"])
    assert payload == fixture_payload
