"""v0.30.1 SymmetryMethod registry tests.

The registry is a module-level dict. These tests use the private
``_snapshot_registry`` / ``_restore_registry`` helpers to guard against
cross-test state leakage — each test that mutates the registry is
enclosed in a save-restore block.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator

import pytest

from pdelie.errors import ScopeValidationError
from pdelie.symmetry import (
    SymmetryMethod,
    SymmetryMethodMetadata,
    SymmetryMethodResult,
    get_symmetry_method,
    list_symmetry_methods,
    register_symmetry_method,
    run_symmetry_method,
)
from pdelie.symmetry.registry import (
    _register_builtin_methods,
    _restore_registry,
    _snapshot_registry,
)


@pytest.fixture(autouse=True)
def _registry_state_isolation() -> Iterator[None]:
    """Snapshot the registry before each test and restore afterward."""
    snapshot = _snapshot_registry()
    try:
        yield
    finally:
        _restore_registry(snapshot)


def _build_dummy_metadata(method_name: str = "dummy") -> SymmetryMethodMetadata:
    return SymmetryMethodMetadata(
        method_name=method_name,
        method_version="0.1",
        citation_key=None,
        paper_url=None,
        code_url=None,
        license="MIT",
        implementation_status="external_optional",
        method_class="generative",
        deterministic=False,
        requires_training=True,
        requires_extras=("dummy_extra",),
        supported_input_layouts=("scalar_1d_uniform",),
        supported_boundary_conditions=("periodic",),
        output_representation_types=("generator_family",),
    )


# ---------------------------------------------------------------------------
# 1. Duplicate registration rejects.
# ---------------------------------------------------------------------------


def test_duplicate_registration_rejects() -> None:
    with pytest.raises(ScopeValidationError, match="already registered"):
        register_symmetry_method(
            "polynomial_translation_svd",
            _build_dummy_metadata("polynomial_translation_svd"),
            "some.module:build_method",
        )


def test_register_then_duplicate_rejects() -> None:
    register_symmetry_method(
        "dummy_method_new",
        _build_dummy_metadata("dummy_method_new"),
        "some.module:build_method",
    )
    with pytest.raises(ScopeValidationError, match="already registered"):
        register_symmetry_method(
            "dummy_method_new",
            _build_dummy_metadata("dummy_method_new"),
            "some.other.module:build_method",
        )


# ---------------------------------------------------------------------------
# 2. Unknown method error lists available names.
# ---------------------------------------------------------------------------


def test_unknown_method_error_lists_available_names() -> None:
    with pytest.raises(ScopeValidationError) as excinfo:
        get_symmetry_method("this_method_does_not_exist")
    message = str(excinfo.value)
    assert "this_method_does_not_exist" in message
    assert "polynomial_translation_svd" in message


# ---------------------------------------------------------------------------
# 3. Listing methods does not import optional heavy dependencies.
# ---------------------------------------------------------------------------


def test_listing_methods_does_not_import_torch_or_optional_backends() -> None:
    """This is the load-bearing lazy-import guarantee.

    ``list_symmetry_methods()`` must produce the metadata list WITHOUT
    importing any adapter module. We verify by asserting the adapter
    module for the built-in polynomial_translation_svd is NOT imported
    if we call list before any get/run — and by asserting no torch /
    lie_gan / lie_gg module is imported by the list call.
    """
    # Evict the polynomial adapter module if it was imported by a prior
    # test.
    sys.modules.pop(
        "pdelie.symmetry.methods.polynomial_translation_svd", None
    )
    torch_before = "torch" in sys.modules
    listing = list_symmetry_methods()
    assert isinstance(listing, list)
    assert any(entry["method_name"] == "polynomial_translation_svd" for entry in listing)
    # torch must not have been imported by list_symmetry_methods.
    assert ("torch" in sys.modules) == torch_before, (
        "list_symmetry_methods() must not import torch"
    )
    # The adapter module for polynomial_translation_svd MUST NOT be
    # imported by list_symmetry_methods().
    assert (
        "pdelie.symmetry.methods.polynomial_translation_svd" not in sys.modules
    ), (
        "list_symmetry_methods() must not eagerly import the adapter "
        "module for polynomial_translation_svd"
    )


def test_methods_package_import_does_not_load_adapters() -> None:
    """Importing pdelie.symmetry.methods must not import any adapter."""
    sys.modules.pop(
        "pdelie.symmetry.methods.polynomial_translation_svd", None
    )
    import pdelie.symmetry.methods  # noqa: F401
    assert (
        "pdelie.symmetry.methods.polynomial_translation_svd" not in sys.modules
    ), (
        "pdelie.symmetry.methods import must not eagerly load the "
        "polynomial_translation_svd adapter"
    )


# ---------------------------------------------------------------------------
# 4. Lazy optional method failure gives actionable extra-install message.
# ---------------------------------------------------------------------------


def test_lazy_optional_method_failure_names_required_extras() -> None:
    register_symmetry_method(
        "hypothetical_torch_method",
        SymmetryMethodMetadata(
            method_name="hypothetical_torch_method",
            method_version="0.1",
            citation_key=None,
            paper_url=None,
            code_url=None,
            license="MIT",
            implementation_status="external_optional",
            method_class="generative",
            deterministic=False,
            requires_training=True,
            requires_extras=("torch_backend",),
            supported_input_layouts=("scalar_1d_uniform",),
            supported_boundary_conditions=("periodic",),
            output_representation_types=("generator_family",),
        ),
        "this.module.does.not.exist:build_method",
    )
    with pytest.raises(ScopeValidationError) as excinfo:
        get_symmetry_method("hypothetical_torch_method")
    message = str(excinfo.value)
    assert "hypothetical_torch_method" in message
    assert "torch_backend" in message
    assert "pip install pdelie[" in message


# ---------------------------------------------------------------------------
# 5. Registry ordering is deterministic.
# ---------------------------------------------------------------------------


def test_registry_order_is_deterministic_across_multiple_registrations() -> None:
    for name in ("z_method", "a_method", "m_method"):
        register_symmetry_method(
            name,
            _build_dummy_metadata(name),
            "dummy.module:build_method",
        )
    order = [entry["method_name"] for entry in list_symmetry_methods()]
    # The built-in was already registered; new registrations append.
    assert order[0] == "polynomial_translation_svd"
    assert order[1:] == ["z_method", "a_method", "m_method"]


# ---------------------------------------------------------------------------
# 6. No global-state leakage between tests.
# ---------------------------------------------------------------------------


def test_snapshot_then_restore_resets_registrations() -> None:
    initial = _snapshot_registry()
    register_symmetry_method(
        "temp_method",
        _build_dummy_metadata("temp_method"),
        "dummy.module:build_method",
    )
    assert any(
        entry["method_name"] == "temp_method"
        for entry in list_symmetry_methods()
    )
    _restore_registry(initial)
    assert not any(
        entry["method_name"] == "temp_method"
        for entry in list_symmetry_methods()
    )


def test_built_in_survives_isolation_fixture() -> None:
    """After the autouse isolation fixture teardown, the built-in
    ``polynomial_translation_svd`` remains registered. This is what
    every downstream test file depends on.
    """
    listing = [entry["method_name"] for entry in list_symmetry_methods()]
    assert "polynomial_translation_svd" in listing


# ---------------------------------------------------------------------------
# 7. run_symmetry_method rejects non-FieldBatch input.
# ---------------------------------------------------------------------------


def test_run_symmetry_method_rejects_file_path_input() -> None:
    from pdelie.errors import SchemaValidationError

    with pytest.raises(SchemaValidationError, match="FieldBatch"):
        run_symmetry_method("polynomial_translation_svd", "/tmp/some_file.nc")


def test_run_symmetry_method_rejects_ndarray_input() -> None:
    import numpy as np

    from pdelie.errors import SchemaValidationError

    with pytest.raises(SchemaValidationError, match="FieldBatch"):
        run_symmetry_method(
            "polynomial_translation_svd", np.zeros((1, 4, 8, 1))
        )


# ---------------------------------------------------------------------------
# 8. get_symmetry_method returns an object satisfying the Protocol.
# ---------------------------------------------------------------------------


def test_get_symmetry_method_returns_protocol_conforming_object() -> None:
    method = get_symmetry_method("polynomial_translation_svd")
    assert isinstance(method, SymmetryMethod)
    assert hasattr(method, "METADATA")
    assert isinstance(method.METADATA, SymmetryMethodMetadata)
    assert method.METADATA.method_name == "polynomial_translation_svd"


# ---------------------------------------------------------------------------
# 9. Idempotent bootstrap.
# ---------------------------------------------------------------------------


def test_register_builtin_methods_is_idempotent() -> None:
    _register_builtin_methods()
    _register_builtin_methods()  # second call must NOT raise
    listing = [entry["method_name"] for entry in list_symmetry_methods()]
    assert listing.count("polynomial_translation_svd") == 1


# ---------------------------------------------------------------------------
# 10. list_symmetry_methods() output is strict JSON.
# ---------------------------------------------------------------------------


def test_list_symmetry_methods_output_is_strict_json() -> None:
    listing = list_symmetry_methods()
    text = json.dumps(listing, allow_nan=False)
    roundtrip = json.loads(text)
    assert roundtrip == listing


# ---------------------------------------------------------------------------
# 11. SymmetryMethodResult rejects NaN in method_scores.
# ---------------------------------------------------------------------------


def test_method_result_rejects_nan_in_method_scores() -> None:
    from pdelie.errors import SchemaValidationError
    from pdelie.symmetry.candidates import build_symmetry_candidate
    from tests.test_symmetry_candidate_contract import _minimal_generator_family

    payload = _minimal_generator_family()
    candidate = build_symmetry_candidate(
        candidate_id="test",
        representation_type="generator_family",
        payload=payload,
        source_method="test",
    )
    with pytest.raises(SchemaValidationError, match="finite"):
        SymmetryMethodResult(
            method_name="test",
            candidates=[candidate],
            method_scores={"some_score": float("nan")},
        )
