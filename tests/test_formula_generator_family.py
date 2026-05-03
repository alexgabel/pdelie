from __future__ import annotations

import copy
import json

import numpy as np
import pytest

import pdelie
from pdelie.errors import SchemaValidationError
from pdelie.reporting import summarize_formula_generator_family
from pdelie.symmetry import FormulaGeneratorFamily


def _zero() -> dict[str, object]:
    return {"node": "const", "value": 0.0}


def _one() -> dict[str, object]:
    return {"node": "const", "value": 1.0}


def _u() -> dict[str, object]:
    return {"node": "var", "name": "u"}


def _formula_generator(
    *,
    xi: dict[str, object] | object | None = None,
    tau: dict[str, object] | object | None = None,
    phi: dict[str, object] | object | None = None,
    name: str = "g",
) -> FormulaGeneratorFamily:
    return FormulaGeneratorFamily(
        formula_generators=[
            {
                "name": name,
                "components": {
                    "tau": _zero() if tau is None else tau,
                    "xi": _one() if xi is None else xi,
                    "phi": _zero() if phi is None else phi,
                },
            }
        ]
    )


def test_formula_generator_family_round_trips_json_payload() -> None:
    formula = FormulaGeneratorFamily(
        formula_generators=[
            {
                "name": "affine_translation",
                "components": {"tau": _zero(), "xi": _one(), "phi": _u()},
                "metadata": {"source": "unit-test"},
            },
            {
                "name": "trigonometric_fixture",
                "components": {
                    "tau": _zero(),
                    "xi": {"node": "sin", "arg": {"node": "var", "name": "x"}},
                    "phi": {"node": "cos", "arg": {"node": "var", "name": "u"}},
                },
            },
        ],
        diagnostics={"note": "runtime-only"},
    )

    payload = formula.to_dict()
    restored = FormulaGeneratorFamily.from_dict(json.loads(json.dumps(payload)))

    assert restored.to_dict() == payload
    assert restored.schema_version == "0.1"
    assert restored.parameterization == "formula_generator_family"
    assert restored.variables == ("t", "x", "u")
    assert restored.component_names == ("tau", "xi", "phi")


@pytest.mark.parametrize(
    ("field_name", "match"),
    [
        ("variables", "payload.variables"),
        ("component_names", "payload.component_names"),
        ("formula_generators", "payload.formula_generators"),
        ("diagnostics", "payload.diagnostics"),
    ],
)
def test_formula_generator_family_from_dict_rejects_malformed_container_fields(
    field_name: str,
    match: str,
) -> None:
    payload = _formula_generator().to_dict()
    payload[field_name] = None

    with pytest.raises(SchemaValidationError, match=match):
        FormulaGeneratorFamily.from_dict(payload)


def test_summarize_formula_generator_family_returns_json_summary_without_mutation() -> None:
    formula = FormulaGeneratorFamily(
        formula_generators=[
            {
                "name": "rational_fixture",
                "components": {
                    "tau": _zero(),
                    "xi": {
                        "node": "reciprocal",
                        "arg": {
                            "node": "add",
                            "terms": [
                                _one(),
                                {"node": "pow", "base": {"node": "var", "name": "u"}, "exponent": 2},
                            ],
                        },
                    },
                    "phi": {
                        "node": "symbolic_reference",
                        "label": "external_phi",
                        "metadata": {"origin": "symbolic-system"},
                    },
                },
            }
        ]
    )
    before = copy.deepcopy(formula.to_dict())

    summary = summarize_formula_generator_family(formula)

    assert json.loads(json.dumps(summary)) == summary
    assert formula.to_dict() == before
    assert summary["summary_schema_version"] == "0.1"
    assert summary["summary_type"] == "formula_generator_family"
    assert summary["parameterization"] == "formula_generator_family"
    assert summary["generator_count"] == 1
    assert summary["generator_names"] == ["rational_fixture"]
    assert summary["finite_transform_available"] is False
    assert summary["formula_kinds"]["reciprocal"] == 1
    assert summary["formula_kinds"]["pow"] == 1
    assert summary["formula_kinds"]["symbolic_reference"] == 1
    assert summary["symbolic_references"] == [
        {
            "generator_name": "rational_fixture",
            "component": "phi",
            "label": "external_phi",
            "metadata": {"origin": "symbolic-system"},
        }
    ]


@pytest.mark.parametrize(
    ("components", "match"),
    [
        ({"tau": _zero(), "xi": _one()}, "missing"),
        ({"tau": _zero(), "xi": _one(), "phi": _zero(), "eta": _zero()}, "unsupported components"),
        ({"tau": {"node": "var", "name": "y"}, "xi": _one(), "phi": _zero()}, "one of"),
        ({"tau": {"node": "const", "value": np.inf}, "xi": _one(), "phi": _zero()}, "finite float"),
        ({"tau": {"node": "raw_string", "value": "x"}, "xi": _one(), "phi": _zero()}, "unsupported"),
        ({"tau": "x", "xi": _one(), "phi": _zero()}, "mapping"),
        ({"tau": {"node": "const", "value": 0.0}, "xi": lambda value: value, "phi": _zero()}, "mapping"),
        (
            {"tau": {"node": "pow", "base": _u(), "exponent": -1}, "xi": _one(), "phi": _zero()},
            "between",
        ),
    ],
)
def test_formula_generator_family_rejects_invalid_formula_records(
    components: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(SchemaValidationError, match=match):
        FormulaGeneratorFamily(formula_generators=[{"name": "bad", "components": components}])


def test_formula_generator_family_is_submodule_only_runtime_api() -> None:
    assert FormulaGeneratorFamily is not None
    assert not hasattr(pdelie, "FormulaGeneratorFamily")
