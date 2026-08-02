"""v0.36 day-zero: new v0.36 production paths must not make forbidden claims.

PDELie reports empirical diagnostics. It does not claim noise robustness, does
not implement WSINDy, and does not decide benchmark or manuscript outcomes.
Sub-milestones have asserted this per-module since v0.33; this file makes it a
standing guard for the v0.36 arc so a new module cannot introduce the claim by
omission.

Scope, and why it is narrow
===========================

**Only the v0.36 source paths in** :data:`V0_36_SOURCE_PATHS` **are scanned.**
A repo-wide grep is not merely noisy here -- it is backwards. Measured on the
current tree, every occurrence of the forbidden vocabulary in shipped code is a
*disclaimer* or a negative-valued key:

* ``tasks/weak_pde_library.py`` -- "It is not WSINDy and makes no
  noise-robustness claim."
* ``reporting/summaries.py`` -- ``"supports_wsindy": False`` and the warning
  *name* ``"noise_robustness_claimed"``.
* ``tasks/__init__.py`` -- "does not constitute a WSINDy benchmark ... or any
  noise-robustness certification."
* the support matrices -- ``wsindy_benchmark_claim`` in their deferred lists.

Scanning those flags the disclaimer as the violation and would force the
codebase to stop naming what it refuses to claim. Prose documentation is
excluded for the same reason.

New v0.36 modules follow the stricter v0.35 convention instead: the vocabulary
does not appear at all, and the module's own test asserts its emitted payload is
clean. That is what this file enforces going forward, without relitigating the
shipped disclaim-explicitly convention behind it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Source paths introduced by the v0.36 arc. Extend as sub-milestones land
#: (v0.36a adds ``src/pdelie/audit``).
V0_36_SOURCE_PATHS: tuple[str, ...] = (
    "src/pdelie/artifact",
    "src/pdelie/audit",
    "src/pdelie/observation",
    "src/pdelie/differentiation",
    "src/pdelie/actions",
    # v0.36c modules only. The `design` package predates v0.36 (v0.35c) and
    # its __init__ follows the disclaim-explicitly convention -- it states
    # that the selectors make no noise-robustness claim. Scanning the whole
    # package would flag that disclaimer, which is the pattern this file's
    # docstring exists to prevent.
    "src/pdelie/design/attainability.py",
    "src/pdelie/design/candidate_record.py",
    "src/pdelie/design/comparators.py",
    "src/pdelie/design/statistics.py",
)

#: Generated JSON introduced by the v0.36 arc. Empty until a sub-milestone
#: emits one; the mechanism is wired now so the first producer is covered.
V0_36_GENERATED_JSON_GLOBS: tuple[str, ...] = ()

#: Terms that must not appear in v0.36 production paths.
#:
#: NOTE FOR REVIEW: this is the vocabulary already asserted repo-wide by the
#: v0.33/v0.34/v0.35 sub-milestone tests. The v0.36 planning note refers to a
#: "§15 forbidden vocabulary" that was not supplied; if §15 is broader, extend
#: this tuple -- it is the single point of control.
#:
#: One term to settle before extending: **"oracle"**. The v0.36 risk note uses
#: it as its example of a forbidden term, but ``pdelie.design.row_selection``
#: (shipped in v0.35.0) uses "SciPy oracle" five times in its module docstring
#: to mean a reference implementation used in tests. Adding it here fails
#: shipped code and requires a rename first, so it is NOT included.
FORBIDDEN_TERMS: tuple[str, ...] = (
    # v0.36 and earlier.
    "wsindy",
    "noise_robust",
    "noise-robust",
    "noise robustness",
    # v0.37. The first three name methods PDELie does not implement; the last
    # four name claims v0.37 specifically does not make. The library handles
    # three declared coefficient profiles on declared domains -- not arbitrary
    # coefficient fields, not boundary-value symmetries, and not
    # parameter-free equivariance.
    "ko_sparse",
    "wsindy_bridge",
    "learned_symmetry_recovery",
    "parameter_free",
    "coefficient_agnostic",
    "arbitrary_coefficient_field",
    "boundary_value_symmetry_guaranteed",
    # v0.38. The first three name methods PDELie does not implement; the last
    # three name claims v0.38 specifically does not make. The irregular layer
    # handles 1-D scattered coordinates on a declared axis -- not unstructured
    # meshes, not arbitrary geometry, and it makes no discovery claim at all.
    "unstructured_mesh",
    "arbitrary_geometry",
    "rbf_fd",
    "meshfree_sindy",
    "noise_robust_derivative",
    "meshfree_pde_discovery",
)

#: Terms already caught by a shorter entry. Matching is substring-based, so
#: these add no detection -- they are retained because naming them explicitly is
#: how a reader learns the claim is refused. Asserted, so nobody "optimises" the
#: list by deleting a term believing it does work it does not do, and nobody
#: adds a term believing it does work already covered.
SUBSUMED_TERMS: dict[str, str] = {
    "wsindy_bridge": "wsindy",
    # v0.38. Named in the battleplan and kept for documentary value -- a reader
    # scanning this table should find the exact phrase v0.38 refuses -- but it
    # detects nothing "noise_robust" would not already catch.
    "noise_robust_derivative": "noise_robust",
}


def _v0_36_python_files() -> list[Path]:
    files: list[Path] = []
    for relative in V0_36_SOURCE_PATHS:
        root = REPO_ROOT / relative
        if root.is_dir():
            files.extend(sorted(root.rglob("*.py")))
        elif root.is_file():
            files.append(root)
    return files


def _v0_36_generated_json() -> list[Path]:
    files: list[Path] = []
    for pattern in V0_36_GENERATED_JSON_GLOBS:
        files.extend(sorted(REPO_ROOT.glob(pattern)))
    return files


def _hits(text: str) -> list[str]:
    lowered = text.lower()
    return [term for term in FORBIDDEN_TERMS if term in lowered]


def test_declared_v0_36_paths_exist() -> None:
    """Guard the guard: a path typo makes every scan below vacuous."""
    missing = [
        relative for relative in V0_36_SOURCE_PATHS if not (REPO_ROOT / relative).exists()
    ]
    assert not missing, f"declared v0.36 source paths do not exist: {missing}"
    assert _v0_36_python_files(), "no Python files found under the declared v0.36 paths"


@pytest.mark.parametrize(
    "path", _v0_36_python_files(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_v0_36_source_makes_no_forbidden_claim(path: Path) -> None:
    hits = _hits(path.read_text(encoding="utf-8"))
    assert not hits, (
        f"{path.relative_to(REPO_ROOT)} contains forbidden vocabulary {hits}. "
        f"PDELie reports empirical diagnostics and makes no such claim."
    )


@pytest.mark.parametrize(
    "path", _v0_36_generated_json(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_v0_36_generated_json_makes_no_forbidden_claim(path: Path) -> None:  # pragma: no cover - no producers yet
    payload = json.loads(path.read_text(encoding="utf-8"))
    hits = _hits(json.dumps(payload))
    assert not hits, f"{path.relative_to(REPO_ROOT)} contains forbidden vocabulary {hits}."


def test_forbidden_terms_are_lowercase_and_unique() -> None:
    """The scan lowercases its input, so an uppercase entry would never match."""
    assert list(FORBIDDEN_TERMS) == [term.lower() for term in FORBIDDEN_TERMS]
    assert len(set(FORBIDDEN_TERMS)) == len(FORBIDDEN_TERMS)


def test_scan_detects_a_planted_violation() -> None:
    """A guard that cannot fail is the defect it is meant to prevent."""
    assert _hits("this module is noise-robust") == ["noise-robust"]
    assert _hits("Implements WSINDy weak forms") == ["wsindy"]
    assert _hits("mutual coherence of the design matrix") == []


def test_shipped_disclaimers_are_deliberately_out_of_scope() -> None:
    """Pins the reason this test is scoped rather than repo-wide.

    If a future edit widens the scan to all of ``src/``, this test fails and
    says why: the shipped modules below name the forbidden vocabulary in order
    to refuse it, and flagging them would be flagging the disclaimer.
    """
    disclaiming = [
        "src/pdelie/tasks/weak_pde_library.py",
        "src/pdelie/tasks/__init__.py",
        "src/pdelie/reporting/summaries.py",
    ]
    for relative in disclaiming:
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert _hits(text), (
            f"{relative} was expected to name a forbidden term while refusing it; "
            f"if that disclaimer was removed, this exclusion is no longer justified"
        )
        assert relative not in V0_36_SOURCE_PATHS

    scanned = {str(path.relative_to(REPO_ROOT)) for path in _v0_36_python_files()}
    assert not scanned.intersection(disclaiming)


# --- v0.37 additions --------------------------------------------------------


def test_the_table_only_grows() -> None:
    """Every term the project has ever forbidden is still forbidden.

    The cross-sub-phase invariant is 'extend, never contract'. A term dropped
    here silently re-permits a claim the library previously refused to make.
    """
    for term in (
        "wsindy",
        "noise_robust",
        "noise-robust",
        "noise robustness",
        "ko_sparse",
        "wsindy_bridge",
        "learned_symmetry_recovery",
        "parameter_free",
        "coefficient_agnostic",
        "arbitrary_coefficient_field",
        "boundary_value_symmetry_guaranteed",
        "unstructured_mesh",
        "arbitrary_geometry",
        "rbf_fd",
        "meshfree_sindy",
        "noise_robust_derivative",
        "meshfree_pde_discovery",
    ):
        assert term in FORBIDDEN_TERMS, f"forbidden term removed: {term}"


def test_subsumed_terms_are_declared_as_subsumed() -> None:
    """A redundant entry must be marked, not left to look load-bearing.

    Matching is substring-based, so a term containing a shorter forbidden term
    can never fire on its own. Recording which entries are in that position
    keeps the table honest about what it actually detects.
    """
    for term, covering in SUBSUMED_TERMS.items():
        assert term in FORBIDDEN_TERMS, term
        assert covering in FORBIDDEN_TERMS, covering
        assert covering in term, f"{term!r} is not actually subsumed by {covering!r}"

    for term in FORBIDDEN_TERMS:
        shorter = [
            other for other in FORBIDDEN_TERMS if other != term and other in term
        ]
        if shorter:
            assert term in SUBSUMED_TERMS, (
                f"{term!r} is subsumed by {shorter} but is not declared in "
                f"SUBSUMED_TERMS; declare it so the table's real coverage is visible"
            )


def test_v0_37_terms_are_clean_on_the_current_tree() -> None:
    """Measured before the terms were added; asserted so it stays true."""
    for path in _v0_36_python_files():
        hits = _hits(path.read_text())
        assert not hits, f"{path}: {hits}"
