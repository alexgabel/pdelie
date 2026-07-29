"""v0.35b: private point-symmetry catalogue."""

from __future__ import annotations

import json

import pytest

from pdelie.errors import ScopeValidationError
from pdelie.symmetry._point_symmetry_registry import (
    CANONICAL_PARAMETERS,
    CATALOGUED_PDE_NAMES,
    POINT_SYMMETRY_CLASSIFICATIONS,
    classify_point_symmetry,
    list_point_symmetries,
    point_symmetry_family,
    summarize_point_symmetry_catalogue,
)
from pdelie.symmetry.formula import FormulaGeneratorFamily

EXPECTED_COUNTS = {"heat_1d": 6, "burgers_1d": 4, "advection_diffusion_1d": 3}


# --- B-2: the module stays private -----------------------------------------


def test_registry_module_is_private() -> None:
    """No public write-up exists to cite, so the API is underscore-private.

    Un-privatising is a one-line change once a write-up lands; retracting a
    public API is not.
    """
    import pdelie.symmetry as symmetry_package

    assert not hasattr(symmetry_package, "point_symmetry_registry")
    assert "point_symmetry_registry" not in getattr(symmetry_package, "__all__", ())
    for name in ("classify_point_symmetry", "list_point_symmetries"):
        assert name not in getattr(symmetry_package, "__all__", ())


def test_registry_is_not_exported_from_the_root_namespace() -> None:
    import pdelie

    assert "point_symmetry_registry" not in pdelie.__all__
    assert not hasattr(pdelie, "point_symmetry_registry")


# --- B-4: catalogue data, not a registered SymmetryMethod ------------------


def test_catalogue_is_not_registered_as_a_symmetry_method() -> None:
    """SymmetryMethod requires fit(field, ...), which discovers from data.

    A catalogued symmetry discovers nothing. Registering one would mean a fit()
    that ignores its input, and would make list_symmetry_methods() report
    methods that never read the data they are handed.
    """
    from pdelie.symmetry.registry import list_symmetry_methods

    registered = {metadata["method_name"] for metadata in list_symmetry_methods()}
    for pde_name in CATALOGUED_PDE_NAMES:
        for entry in list_point_symmetries(pde_name):
            assert entry["symmetry_name"] not in registered
    assert registered == {"polynomial_translation_svd"}


def test_summary_states_the_registration_decision_and_its_reason() -> None:
    summary = summarize_point_symmetry_catalogue()
    assert summary["is_registered_as_symmetry_method"] is False
    assert "discovers a generator" in summary["registration_rationale"]


# --- B-1: every catalogue entry builds a valid FormulaGeneratorFamily -------


@pytest.mark.parametrize("pde_name", sorted(EXPECTED_COUNTS))
def test_catalogue_builds_a_formula_generator_family(pde_name: str) -> None:
    family = point_symmetry_family(pde_name)
    assert isinstance(family, FormulaGeneratorFamily)
    assert len(family.formula_generators) == EXPECTED_COUNTS[pde_name]


@pytest.mark.parametrize("pde_name", sorted(EXPECTED_COUNTS))
def test_catalogue_round_trips_strict_json(pde_name: str) -> None:
    payload = point_symmetry_family(pde_name).to_dict()
    encoded = json.dumps(payload, allow_nan=False)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded
    assert json.loads(encoded) == payload


def test_heat_catalogue_is_the_six_dimensional_classical_algebra() -> None:
    """The heat equation's point-symmetry algebra is six-dimensional."""
    names = [entry["symmetry_name"] for entry in list_point_symmetries("heat_1d")]
    assert names == [
        "time_translation",
        "space_translation",
        "amplitude_scaling",
        "dilation",
        "galilean_boost",
        "projective",
    ]


def test_every_entry_carries_its_canonical_parameters() -> None:
    """A catalogue entry describes the canonical equation, not an arbitrary
    parameterization, so the parameter values it holds at are recorded."""
    for pde_name in CATALOGUED_PDE_NAMES:
        assert pde_name in CANONICAL_PARAMETERS
        for entry in list_point_symmetries(pde_name):
            assert entry["canonical_parameters"] == CANONICAL_PARAMETERS[pde_name]
            assert entry["action"]
            assert entry["source"] == "classical_lie_point_symmetry"


def test_translations_are_the_expected_constant_generators() -> None:
    entries = {e["symmetry_name"]: e for e in list_point_symmetries("heat_1d")}
    time = entries["time_translation"]["components"]
    space = entries["space_translation"]["components"]
    assert time["tau"] == {"node": "const", "value": 1.0}
    assert time["xi"] == {"node": "const", "value": 0.0}
    assert space["xi"] == {"node": "const", "value": 1.0}
    assert space["tau"] == {"node": "const", "value": 0.0}


# --- B-3: the classification, and both branches ----------------------------


def test_invalid_symmetry_classifies_invalid_regardless_of_the_design() -> None:
    for constant in (0.1, 5.0, None):
        report = classify_point_symmetry(
            pde_name="heat_1d",
            symmetry_name="dilation",
            symmetry_is_valid=False,
            irrepresentability_constant=constant,
        )
        assert report["classification"] == "invalid"
        assert report["design_supports_recovery"] is None


def test_valid_symmetry_on_a_recoverable_design_is_exact_and_useful() -> None:
    """The useful branch is reachable -- measured at rho_IR 0.9634 on a real
    two-element support of the canonical heat design."""
    report = classify_point_symmetry(
        pde_name="heat_1d",
        symmetry_name="space_translation",
        symmetry_is_valid=True,
        irrepresentability_constant=0.9634,
    )
    assert report["classification"] == "exact_and_useful"
    assert report["design_supports_recovery"] is True
    assert report["warnings"] == []


def test_valid_symmetry_on_an_unrecoverable_design_is_the_wedge() -> None:
    """The wedge: valid, and still not worth acting on.

    Measured at the canonical weak-form configuration every supported PDE sits
    here -- heat 2.743, Burgers 2.194, advection-diffusion 1.178.
    """
    for constant in (2.742717168, 2.19384, 1.17817):
        report = classify_point_symmetry(
            pde_name="heat_1d",
            symmetry_name="dilation",
            symmetry_is_valid=True,
            irrepresentability_constant=constant,
        )
        assert report["classification"] == "valid_but_not_useful"
        assert report["design_supports_recovery"] is False
        assert "design_does_not_support_recovery" in report["warnings"]


def test_undefined_irrepresentability_is_inconclusive_not_a_guess() -> None:
    report = classify_point_symmetry(
        pde_name="heat_1d",
        symmetry_name="projective",
        symmetry_is_valid=True,
        irrepresentability_constant=None,
    )
    assert report["classification"] == "valid_but_not_useful"
    assert report["design_supports_recovery"] is None
    assert (
        "usefulness_axis_inconclusive_irrepresentability_undefined"
        in report["warnings"]
    )


def test_classification_threshold_is_exactly_one() -> None:
    """Strictly below 1.0 supports recovery; exactly 1.0 does not."""
    below = classify_point_symmetry(
        pde_name="heat_1d",
        symmetry_name="dilation",
        symmetry_is_valid=True,
        irrepresentability_constant=0.999999,
    )
    at = classify_point_symmetry(
        pde_name="heat_1d",
        symmetry_name="dilation",
        symmetry_is_valid=True,
        irrepresentability_constant=1.0,
    )
    assert below["classification"] == "exact_and_useful"
    assert at["classification"] == "valid_but_not_useful"


def test_validity_is_required_and_never_inferred_from_the_design() -> None:
    """The measured reason this is a required input.

    The irrepresentability constant is a property of the design matrix and
    support; it never consults the symmetry. A classification derived from it
    alone returns the same verdict for every symmetry of every PDE.
    """
    with pytest.raises(ScopeValidationError, match="deliberately not inferred"):
        classify_point_symmetry(
            pde_name="heat_1d",
            symmetry_name="dilation",
            symmetry_is_valid=None,
            irrepresentability_constant=0.5,
        )


def test_every_classification_uses_the_frozen_vocabulary() -> None:
    for valid in (True, False):
        for constant in (0.5, 2.0, None):
            report = classify_point_symmetry(
                pde_name="burgers_1d",
                symmetry_name="galilean_boost",
                symmetry_is_valid=valid,
                irrepresentability_constant=constant,
            )
            assert report["classification"] in POINT_SYMMETRY_CLASSIFICATIONS


def test_classification_composes_with_the_real_diagnostics_output() -> None:
    """End-to-end: v0.35a's payload field feeds this directly."""
    import numpy as np

    from pdelie.diagnostics import irrepresentability_constant
    from tests._helpers.regenerate_v0_35a_design_matrix import load_fixture

    matrix = load_fixture()["design_matrix"]
    diagnostics = irrepresentability_constant(matrix, support=[0, 1])
    report = classify_point_symmetry(
        pde_name="heat_1d",
        symmetry_name="space_translation",
        symmetry_is_valid=True,
        irrepresentability_constant=diagnostics["metric_value"],
    )
    assert report["classification"] == "valid_but_not_useful"
    assert report["irrepresentability_constant"] == pytest.approx(2.742717168, rel=1e-6)
    assert np.isfinite(report["irrepresentability_constant"])


# --- validation -------------------------------------------------------------


def test_unknown_pde_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="no point-symmetry catalogue"):
        list_point_symmetries("kdv_1d")


def test_empty_pde_name_is_refused() -> None:
    for bad in ("", "   ", 3):
        with pytest.raises(ScopeValidationError, match="non-empty string"):
            list_point_symmetries(bad)


def test_unknown_symmetry_name_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="is not catalogued"):
        classify_point_symmetry(
            pde_name="heat_1d",
            symmetry_name="projective_conformal_typo",
            symmetry_is_valid=True,
            irrepresentability_constant=0.5,
        )


def test_empty_symmetry_name_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="non-empty string"):
        classify_point_symmetry(
            pde_name="heat_1d",
            symmetry_name="",
            symmetry_is_valid=True,
            irrepresentability_constant=0.5,
        )


def test_non_numeric_irrepresentability_is_refused() -> None:
    for bad in ("0.5", True, [0.5]):
        with pytest.raises(ScopeValidationError, match="real number or None"):
            classify_point_symmetry(
                pde_name="heat_1d",
                symmetry_name="dilation",
                symmetry_is_valid=True,
                irrepresentability_constant=bad,
            )


# --- catalogue summary ------------------------------------------------------


def test_catalogue_summary_counts_match_the_entries() -> None:
    summary = summarize_point_symmetry_catalogue()
    assert summary["summary_type"] == "pdelie_point_symmetry_catalogue"
    assert summary["entry_counts"] == EXPECTED_COUNTS
    assert summary["total_entry_count"] == sum(EXPECTED_COUNTS.values()) == 13
    assert summary["catalogued_pde_names"] == list(CATALOGUED_PDE_NAMES)
    assert summary["diagnostic_only"] is True


def test_catalogue_summary_is_strict_json() -> None:
    encoded = json.dumps(summarize_point_symmetry_catalogue(), allow_nan=False)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded


def test_catalogue_makes_no_noise_robustness_or_wsindy_claim() -> None:
    from pdelie.symmetry import _point_symmetry_registry as module

    text = (module.__doc__ or "").lower()
    text += json.dumps(summarize_point_symmetry_catalogue()).lower()
    for forbidden in ("wsindy", "noise_robust", "noise-robust", "noise robustness"):
        assert forbidden not in text


def test_catalogue_module_does_not_import_scipy_or_pysindy() -> None:
    from pdelie.symmetry import _point_symmetry_registry as module

    assert module.__file__ is not None
    with open(module.__file__, encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            assert not stripped.startswith(("import scipy", "from scipy"))
            assert not stripped.startswith(("import pysindy", "from pysindy"))
