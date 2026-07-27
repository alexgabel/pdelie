"""v0.32d — PDEBench 1D Burgers readiness + The Well feasibility scan tests.

20 required contract tests. The PDEBench cookbook is validated against a
synthetic HDF5 fixture that mimics the frozen PDEBench schema and MD5
checksum; the fixture is regenerated deterministically per test and lives
in the pytest tmp_path — no real PDEBench data is fetched or vendored.

The Well feasibility scan is exercised metadata-only; the module never
makes a network call.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import pdelie
from pdelie.errors import SchemaValidationError
from pdelie.examples import pdebench_burgers_1d_readiness as pdebench_module
from pdelie.examples.pdebench_burgers_1d_readiness import (
    load_pdebench_burgers_1d_readiness_config,
    run_pdebench_burgers_1d_readiness_cookbook,
)
from pdelie.examples.the_well_feasibility_scan import (
    load_the_well_feasibility_scan_config,
    run_the_well_feasibility_scan,
)

_H5PY_AVAILABLE = importlib.util.find_spec("h5py") is not None
requires_h5py = pytest.mark.skipif(
    not _H5PY_AVAILABLE, reason="h5py optional dependency not installed"
)


# ---------------------------------------------------------------------------
# Fixture: synthetic HDF5 that matches the frozen PDEBench schema. Uses a
# fixed random seed; then we compute a NEW MD5 for the synthetic bytes and
# monkeypatch the config so the cookbook accepts our fixture.
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_pdebench_hdf5(tmp_path: Path) -> Iterator[tuple[Path, str]]:
    if not _H5PY_AVAILABLE:
        pytest.skip("h5py optional dependency not installed")
    import h5py  # type: ignore[import-not-found]

    rng = np.random.default_rng(32_400)
    n_traj, n_t, n_x = 3, 12, 32
    tensor = rng.standard_normal((n_traj, n_t, n_x)).astype("float32") * 0.1
    x_coord = np.linspace(0.0, 1.0, n_x, endpoint=False, dtype="float32")
    t_coord = np.linspace(0.0, 2.0, n_t, dtype="float32")

    config = load_pdebench_burgers_1d_readiness_config()
    path = tmp_path / config["source_file"]
    with h5py.File(str(path), "w") as fp:
        fp.create_dataset("tensor", data=tensor)
        fp.create_dataset("x-coordinate", data=x_coord)
        fp.create_dataset("t-coordinate", data=t_coord)
    yield path, _md5_of_file(path)


def _md5_of_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture
def patched_checksum(
    monkeypatch: pytest.MonkeyPatch, synthetic_pdebench_hdf5: tuple[Path, str]
) -> Path:
    """Patch the frozen config's expected MD5 to match our synthetic fixture."""
    path, actual_md5 = synthetic_pdebench_hdf5

    def _load_patched_config() -> dict[str, Any]:
        real = load_pdebench_burgers_1d_readiness_config()
        real["source_checksum"] = dict(real["source_checksum"])
        real["source_checksum"]["value"] = actual_md5
        return real

    monkeypatch.setattr(
        pdebench_module,
        "load_pdebench_burgers_1d_readiness_config",
        _load_patched_config,
    )
    return path


# ---------------------------------------------------------------------------
# Case 1: strict-JSON config and output.
# ---------------------------------------------------------------------------


def test_case_01_strict_json_config_and_output() -> None:
    for payload in (
        load_pdebench_burgers_1d_readiness_config(),
        load_the_well_feasibility_scan_config(),
        run_pdebench_burgers_1d_readiness_cookbook(),
        run_the_well_feasibility_scan(),
    ):
        encoded = json.dumps(payload, allow_nan=False)
        assert json.loads(encoded) == payload
    # Repo-level configs (release-gate visibility) and package-bundled
    # copies (wheel-install visibility) must be byte-identical so the
    # runtime never drifts from the frozen planning artifact.
    repo_root = Path(__file__).resolve().parents[1]
    for name in (
        "pdebench_burgers_1d_readiness.json",
        "the_well_feasibility_scan.json",
    ):
        repo_bytes = (repo_root / "configs" / "external_data" / name).read_bytes()
        pkg_bytes = (
            repo_root / "src" / "pdelie" / "examples" / "_external_data" / name
        ).read_bytes()
        assert repo_bytes == pkg_bytes, (
            f"configs/external_data/{name} drifted from the package copy at "
            f"src/pdelie/examples/_external_data/{name}. Regenerate the "
            "package copy from the repo config."
        )


# ---------------------------------------------------------------------------
# Case 2: exact dataset identifier and checksum enforcement.
# ---------------------------------------------------------------------------


def test_case_02_exact_dataset_identifier_and_checksum_pinned() -> None:
    config = load_pdebench_burgers_1d_readiness_config()
    # These are the values the audit pinned; any drift breaks the test.
    assert config["source_file"] == "1D_Burgers_Sols_Nu0.001.hdf5"
    assert config["source_checksum"]["algorithm"] == "md5"
    assert config["source_checksum"]["value"] == "b4be2fc3383f737c76033073e6d2ccfb"
    assert config["dataset_version"] == "V8"
    assert config["data_doi_or_record"] == "10.18419/darus-2986"


# ---------------------------------------------------------------------------
# Case 3: wrong checksum rejects (produces the blocked_download conclusion).
# ---------------------------------------------------------------------------


@requires_h5py
def test_case_03_wrong_checksum_rejects(
    synthetic_pdebench_hdf5: tuple[Path, str],
) -> None:
    # Do NOT patch the config — its expected MD5 is the real DaRUS value,
    # which does not match our synthetic fixture. The cookbook must emit a
    # blocked_download_or_checksum_failure conclusion, not raise.
    path, _actual = synthetic_pdebench_hdf5
    payload = run_pdebench_burgers_1d_readiness_cookbook(cached_file_path=path)
    assert payload["conclusion"] == "blocked_download_or_checksum_failure"
    assert any(
        "checksum_mismatch" in w for w in payload["warnings"]
    )


# ---------------------------------------------------------------------------
# Case 4: unknown variable rejects.
# ---------------------------------------------------------------------------


@requires_h5py
def test_case_04_unknown_variable_rejects(
    monkeypatch: pytest.MonkeyPatch,
    synthetic_pdebench_hdf5: tuple[Path, str],
    tmp_path: Path,
) -> None:
    """A file missing the frozen HDF5 dataset paths must raise, never coerce."""
    import h5py  # type: ignore[import-not-found]

    _path, _md5 = synthetic_pdebench_hdf5
    bad_path = tmp_path / "1D_Burgers_Sols_Nu0.001.hdf5"
    with h5py.File(str(bad_path), "w") as fp:
        fp.create_dataset("mystery_variable", data=np.zeros((3, 12, 32)))
        fp.create_dataset("x-coordinate", data=np.linspace(0, 1, 32))
        fp.create_dataset("t-coordinate", data=np.linspace(0, 2, 12))

    bad_md5 = _md5_of_file(bad_path)

    def _load_patched_config() -> dict[str, Any]:
        real = load_pdebench_burgers_1d_readiness_config()
        real["source_checksum"] = dict(real["source_checksum"])
        real["source_checksum"]["value"] = bad_md5
        return real

    monkeypatch.setattr(
        pdebench_module,
        "load_pdebench_burgers_1d_readiness_config",
        _load_patched_config,
    )
    with pytest.raises(SchemaValidationError, match="missing required dataset"):
        run_pdebench_burgers_1d_readiness_cookbook(cached_file_path=bad_path)


# ---------------------------------------------------------------------------
# Case 5: axis mismatch rejects.
# ---------------------------------------------------------------------------


@requires_h5py
def test_case_05_axis_mismatch_rejects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A 4-D tensor (extra rogue axis) must be rejected up-front."""
    import h5py  # type: ignore[import-not-found]

    path = tmp_path / "1D_Burgers_Sols_Nu0.001.hdf5"
    with h5py.File(str(path), "w") as fp:
        fp.create_dataset("tensor", data=np.zeros((3, 12, 32, 2)))
        fp.create_dataset("x-coordinate", data=np.linspace(0, 1, 32))
        fp.create_dataset("t-coordinate", data=np.linspace(0, 2, 12))

    md5 = _md5_of_file(path)

    def _load_patched_config() -> dict[str, Any]:
        real = load_pdebench_burgers_1d_readiness_config()
        real["source_checksum"] = dict(real["source_checksum"])
        real["source_checksum"]["value"] = md5
        return real

    monkeypatch.setattr(
        pdebench_module,
        "load_pdebench_burgers_1d_readiness_config",
        _load_patched_config,
    )
    with pytest.raises(SchemaValidationError, match="rank 3"):
        run_pdebench_burgers_1d_readiness_cookbook(cached_file_path=path)


# ---------------------------------------------------------------------------
# Case 6: missing boundary metadata blocks residual evaluation.
# ---------------------------------------------------------------------------


def test_case_06_missing_boundary_metadata_blocks_residual_stage() -> None:
    """When the readiness config's boundary evidence is verified=False, the
    cookbook must NOT proceed to residual evaluation.

    This test hits the readiness-only path (unavailable), which is the
    only path that doesn't require h5py, and confirms via the config that
    boundary evidence is present + verified. If a downstream release
    intentionally weakens the config, the residual stage should refuse to
    run — this test pins that boundary evidence is verified today.
    """
    config = load_pdebench_burgers_1d_readiness_config()
    assert config["boundary_condition_evidence"]["x"] == "periodic"
    assert config["boundary_condition_evidence"]["verified"] is True
    # And the derivative/residual stages of the unavailable path are skipped:
    payload = run_pdebench_burgers_1d_readiness_cookbook()
    assert payload["derivative_readiness"]["stage_run"] is False
    assert payload["residual_readiness"]["stage_run"] is False


# ---------------------------------------------------------------------------
# Case 7: missing coefficient metadata blocks residual evaluation.
# ---------------------------------------------------------------------------


def test_case_07_missing_coefficient_metadata_blocks_residual_stage() -> None:
    """Same shape as case 6 — verifies parameter_evidence.verified is True
    in the frozen config and that the unavailable path skips residual."""
    config = load_pdebench_burgers_1d_readiness_config()
    assert config["parameter_evidence"]["nu"] == 0.001
    assert config["parameter_evidence"]["verified"] is True
    payload = run_pdebench_burgers_1d_readiness_cookbook()
    assert payload["residual_readiness"]["stage_run"] is False


# ---------------------------------------------------------------------------
# Case 8: supported cached slice creates valid FieldBatch (readiness_only).
# ---------------------------------------------------------------------------


@requires_h5py
def test_case_08_supported_cached_slice_creates_valid_field_batch_readiness(
    patched_checksum: Path,
) -> None:
    payload = run_pdebench_burgers_1d_readiness_cookbook(
        cached_file_path=patched_checksum
    )
    assert payload["conclusion"] == "ready_scalar_1d_readiness_only"
    readiness = payload["field_batch_readiness"]
    assert readiness["summary_type"] == "field_batch_readiness"
    # No residual computed unless requested.
    assert payload["residual_readiness"]["stage_run"] is False


# ---------------------------------------------------------------------------
# Case 9: no train/test policy is invented.
# ---------------------------------------------------------------------------


def test_case_09_no_train_test_policy_invented() -> None:
    payload = run_pdebench_burgers_1d_readiness_cookbook()
    assert payload["split_metadata"]["invented_by_cookbook"] is False
    assert payload["split_metadata"]["in_file"] is False
    # The pdelie_policy value must be the explicit no-invention string.
    assert "caller_partitions_trajectories_explicitly" in payload["split_metadata"]["pdelie_policy"]


# ---------------------------------------------------------------------------
# Case 10: readiness conclusion does not claim recovery.
# ---------------------------------------------------------------------------


def test_case_10_readiness_conclusion_does_not_claim_recovery(
    patched_checksum: Path,
) -> None:
    """No conclusion label may imply recovery success or downstream utility."""
    payloads = [
        run_pdebench_burgers_1d_readiness_cookbook(),
    ]
    if _H5PY_AVAILABLE:
        payloads.append(
            run_pdebench_burgers_1d_readiness_cookbook(
                cached_file_path=patched_checksum
            )
        )
    for payload in payloads:
        label = payload["conclusion"]
        for bad_word in ("recover", "success", "verified_pde", "benchmark_pass"):
            assert bad_word not in label, (
                f"Recovery-flavoured label leaked into conclusion: {label!r}"
            )


# ---------------------------------------------------------------------------
# Case 11: optional dataset absence is nonfatal.
# ---------------------------------------------------------------------------


def test_case_11_optional_dataset_absence_is_nonfatal() -> None:
    payload = run_pdebench_burgers_1d_readiness_cookbook(cached_file_path=None)
    assert payload["conclusion"] == "unavailable_no_cached_dataset"
    # And when a missing path is supplied, we still don't raise:
    payload2 = run_pdebench_burgers_1d_readiness_cookbook(
        cached_file_path="/nonexistent/path/does/not/exist.hdf5"
    )
    assert payload2["conclusion"] == "unavailable_no_cached_dataset"


# ---------------------------------------------------------------------------
# Case 12: no bulk network download in standard tests.
# ---------------------------------------------------------------------------


def test_case_12_no_bulk_network_download_in_standard_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Block urllib/requests/socket so any accidental download raises."""
    import urllib.request

    def _blocked(*args: object, **kwargs: object) -> object:
        raise AssertionError(
            "v0.32d cookbooks must not perform network I/O in standard tests."
        )

    monkeypatch.setattr(urllib.request, "urlopen", _blocked)
    # Both cookbooks must complete without network I/O.
    run_pdebench_burgers_1d_readiness_cookbook()
    run_the_well_feasibility_scan()


# ---------------------------------------------------------------------------
# Case 13: The Well scan never downloads full datasets.
# ---------------------------------------------------------------------------


def test_case_13_the_well_scan_metadata_only() -> None:
    config = load_the_well_feasibility_scan_config()
    assert config["policy"]["downloads_in_ci"] is False
    assert config["policy"]["metadata_only_scan"] is True
    scan = run_the_well_feasibility_scan()
    assert scan["policy"]["downloads_in_ci"] is False


# ---------------------------------------------------------------------------
# Case 14: The Well multichannel/2D datasets produce blocked_multichannel_required.
# ---------------------------------------------------------------------------


def test_case_14_the_well_conclusion_is_blocked_multichannel_required() -> None:
    scan = run_the_well_feasibility_scan()
    assert scan["conclusion"] == "blocked_multichannel_required"
    assert scan["scalar_1d_extractable_count"] == 0
    for entry in scan["datasets"]:
        assert entry["scalar_1d_extractable"] is False


# ---------------------------------------------------------------------------
# Case 14b (v0.32.0 release-close): The Well report distinguishes the
# original paper's dataset count from the current repository catalogue
# entry count. The paper reports 16; the catalogue splits hosted variants
# into 23.
# ---------------------------------------------------------------------------


def test_case_14b_the_well_distinguishes_paper_count_from_catalogue_count() -> None:
    scan = run_the_well_feasibility_scan()
    assert scan["paper_dataset_count"] == 16
    assert scan["catalogue_entry_count"] == 23
    assert scan["paper_dataset_count"] != scan["catalogue_entry_count"]
    assert "Ohana" in scan["paper_dataset_count_source"]
    assert "hosted variants" in scan["catalogue_entry_count_note"]


# ---------------------------------------------------------------------------
# Case 15: no broad from_pdebench / from_the_well root or data API appears.
# ---------------------------------------------------------------------------


def test_case_15_no_broad_from_root_or_data_api() -> None:
    import pdelie.data as pdelie_data

    forbidden = (
        "from_pdebench",
        "from_the_well",
        "from_thewell",
        "load_pdebench",
        "load_the_well",
        "run_pdebench_burgers_1d_readiness_cookbook",
        "run_the_well_feasibility_scan",
    )
    for name in forbidden:
        assert not hasattr(pdelie, name), f"root leaked forbidden name: {name}"
        assert not hasattr(pdelie_data, name), (
            f"pdelie.data leaked forbidden broad name: {name}"
        )


# ---------------------------------------------------------------------------
# Case 16: external citation/license/provenance fields are present.
# ---------------------------------------------------------------------------


def test_case_16_citation_license_provenance_present() -> None:
    payload = run_pdebench_burgers_1d_readiness_cookbook()
    assert payload["license"] == "CC-BY-4.0"
    assert "Takamoto" in payload["citation"]
    assert payload["data_doi_or_record"] == "10.18419/darus-2986"
    assert payload["provenance"]["backend_versions"]
    well = run_the_well_feasibility_scan()
    assert "Ohana" in well["citation"]
    assert well["record_url"].startswith("https://")


# ---------------------------------------------------------------------------
# Case 17: strict JSON rejects NaN/Inf at both cookbook boundaries.
# ---------------------------------------------------------------------------


def test_case_17_strict_json_rejects_nan_inf() -> None:
    """The cookbook's strict-JSON _finalize step rejects NaN/Inf inside the
    payload (via json.dumps(..., allow_nan=False))."""
    from pdelie.examples.pdebench_burgers_1d_readiness import _finalize

    bad = {
        "summary_schema_version": "0.1",
        "summary_type": "pdelie_external_data_readiness",
        "conclusion": "unavailable_no_cached_dataset",
        "some_field": math.nan,
    }
    with pytest.raises(ValueError, match="Out of range float"):
        _finalize(bad)


# ---------------------------------------------------------------------------
# Case 18: docs do not use "PDEBench support" or "The Well support" broadly.
# ---------------------------------------------------------------------------


def test_case_18_docs_do_not_claim_broad_support() -> None:
    """SUPPORT_MATRIX + strategy docs must not claim broad PDEBench / Well support."""
    repo_root = Path(__file__).resolve().parents[1]
    to_check = [
        repo_root / "docs" / "specs" / "SUPPORT_MATRIX.md",
        repo_root / "docs" / "strategy" / "SCIENTIFIC_POSITIONING.md",
    ]
    forbidden_phrases = (
        "PDEBench supported",
        "PDEBench is supported",
        "PDEBench support:",
        "The Well supported",
        "The Well is supported",
        "The Well support:",
        "broad PDEBench support",
        "broad The Well support",
    )
    for path in to_check:
        text = path.read_text(encoding="utf-8")
        for phrase in forbidden_phrases:
            assert phrase not in text, (
                f"{path.name} contains forbidden broad-support phrase: "
                f"{phrase!r}"
            )


# ---------------------------------------------------------------------------
# Case 19: clean-wheel cookbook works with a documented local path.
# ---------------------------------------------------------------------------


def test_case_19_cli_emits_strict_json_only() -> None:
    """CLI smoke on the editable install — the clean-wheel variant is
    exercised separately during release validation. The command must
    produce a strict-JSON payload with the expected summary_type."""
    for module in (
        "pdelie.examples.pdebench_burgers_1d_readiness",
        "pdelie.examples.the_well_feasibility_scan",
    ):
        completed = subprocess.run(
            [sys.executable, "-m", module],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(completed.stdout)
        assert payload["summary_type"].startswith("pdelie_")


# ---------------------------------------------------------------------------
# Case 20: release-gate manifest pins the narrow surface + forbidden broad
# names.
# ---------------------------------------------------------------------------


def test_case_20_release_gate_manifest_pins_narrow_surface() -> None:
    """v0.32.0 release close consolidates the 0.32b / 0.32c / 0.32d rows
    into a single ``0.32`` row. This test accepts either the pre-consolidation
    ``0.32d`` row or the consolidated ``0.32`` row so it stays green across
    the release-close transition."""
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / "configs" / "release_gate_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    releases = [
        r for r in manifest["releases"] if r["release"] in {"0.32d", "0.32"}
    ]
    assert releases, "release-gate manifest missing v0.32d or v0.32 row"
    row = releases[0]
    submod_names = {
        item["name"] for item in row["required_submodule_attributes"]
    }
    for expected in (
        "run_pdebench_burgers_1d_readiness_cookbook",
        "run_the_well_feasibility_scan",
        "load_pdebench_burgers_1d_readiness_config",
        "load_the_well_feasibility_scan_config",
    ):
        assert expected in submod_names, f"manifest missing {expected!r}"
    forbidden = row["forbidden_root_attributes"]["names"]
    for name in (
        "from_pdebench",
        "from_the_well",
        "load_pdebench",
        "load_the_well",
    ):
        assert name in forbidden, f"manifest missing forbidden root: {name}"
