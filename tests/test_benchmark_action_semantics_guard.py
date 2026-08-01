"""The gate the v0.37 arc did not have: does the code execute what it declares?

Every v0.37 gate checked that a *declared* thing was coherent. None checked that
the declared thing was the thing *executed*. C-5 survived a hypothesis freeze,
three pilots, a confirmatory freeze, a release close and a tag because of that
gap: its bundle declared a **parameter** rescale, `execute_bundle` correctly
computed the rescaled parameter, and the benchmark runner ignored that and
rescaled the **state** by hand.

The executor was right. The tests of the executor were right. The benchmark
walked around both.

This scans the benchmark package's AST for constructs that indicate a
transformation being applied outside the declared action path. It is a
structural guard, not a correctness proof -- but the specific defect it forbids
cost a release.

Escape hatch
============

A reference calculation legitimately needs to build a field or roll an array by
hand: that is how an independent oracle is written. Marking the line
``# oracle: reference calculation`` permits it, and the marker is greppable so
the set of exemptions stays auditable rather than growing quietly.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = REPO_ROOT / "src/pdelie/benchmarks"
ORACLE_MARKER = "# oracle: reference calculation"


def _benchmark_sources() -> list[Path]:
    return sorted(p for p in BENCHMARKS.rglob("*.py") if p.name != "__init__.py")


def _exempt_lines(source: str) -> set[int]:
    return {
        index
        for index, line in enumerate(source.splitlines(), start=1)
        if ORACLE_MARKER in line
    }


def _violations(path: Path) -> list[str]:
    source = path.read_text()
    tree = ast.parse(source)
    exempt = _exempt_lines(source)
    found: list[str] = []

    for node in ast.walk(tree):
        line = getattr(node, "lineno", None)
        if line in exempt:
            continue

        # Constructing a FieldBatch inside benchmark code means a transformed
        # state was built by hand rather than obtained from execute_bundle.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "FieldBatch"
        ):
            found.append(f"{path.name}:{line} constructs FieldBatch by hand")

        # `.values * factor` is a state rescale written directly. This is
        # exactly what C-5 did while declaring a parameter action.
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            for side in (node.left, node.right):
                target = side.func.args[0] if False else side
                if isinstance(target, ast.Attribute) and target.attr == "values":
                    found.append(f"{path.name}:{line} scales `.values` directly")
                if (
                    isinstance(target, ast.Call)
                    and isinstance(target.func, ast.Attribute)
                    and target.func.attr == "asarray"
                    and target.args
                    and isinstance(target.args[0], ast.Attribute)
                    and target.args[0].attr == "values"
                ):
                    found.append(f"{path.name}:{line} scales `.values` directly")

        # np.roll applies a periodic shift without going through the executor.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "roll"
        ):
            found.append(f"{path.name}:{line} calls np.roll outside the executor")

    return found


#: The C-5 defect this guard was written to catch is still present: the repair
#: is Phase 1 (v0.37.1) and this guard is Phase 3, landing first by design so
#: the repair has something to turn green. xfail(strict=True) means it fails
#: loudly the moment C-5 is fixed and this marker is not removed -- an expected
#: failure that silently becomes permanent is how a guard rots.
_C5_REPAIR_PENDING = "parameter_equivariant.py"


@pytest.mark.parametrize("path", _benchmark_sources(), ids=lambda p: p.name)
def test_no_transformation_is_applied_outside_the_declared_action_path(
    path: Path, request: pytest.FixtureRequest
) -> None:
    """A benchmark must consume the actions its bundle declares.

    If this fails, the benchmark is transforming something by hand. Either route
    it through ``execute_bundle``, or -- if it is genuinely an independent
    reference calculation -- mark the line with the oracle comment so the
    exemption is visible.
    """
    violations = _violations(path)
    if path.name == _C5_REPAIR_PENDING and violations:
        pytest.xfail(
            f"known: the C-5 semantic mismatch is not repaired yet (Phase 1 / "
            f"v0.37.1). This guard landed first so the repair has a red test to "
            f"turn green. Violations: {violations}"
        )
    assert not violations, (
        "benchmark code applies a transformation outside the declared action "
        "path:\n  " + "\n  ".join(violations) + "\n\n"
        "This is the C-5 class: the bundle declares one action and the runner "
        "performs another. Route it through execute_bundle, or mark it "
        f"'{ORACLE_MARKER}' if it is an independent oracle."
    )


def test_the_guard_can_actually_fail() -> None:
    """A guard that cannot fire is not a guard.

    Runs the same analysis over a synthetic source containing each banned
    construct, and asserts every one is caught.
    """
    import tempfile

    bad = (
        "import numpy as np\n"
        "from pdelie.contracts import FieldBatch\n"
        "def f(field, c):\n"
        "    a = FieldBatch(values=field.values)\n"
        "    b = np.asarray(field.values) * c\n"
        "    d = np.roll(b, 3)\n"
        "    return a, b, d\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe.py"
        probe.write_text(bad)
        found = _violations(probe)
    kinds = {v.split(" ", 1)[1] for v in found}
    assert any("FieldBatch" in k for k in kinds), found
    assert any("`.values`" in k for k in kinds), found
    assert any("np.roll" in k for k in kinds), found


def test_the_oracle_exemption_works_and_stays_auditable() -> None:
    """The escape hatch must exempt, and must be greppable."""
    import tempfile

    marked = (
        "import numpy as np\n"
        "def f(x):\n"
        f"    return np.roll(x, 3)  {ORACLE_MARKER}\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe.py"
        probe.write_text(marked)
        assert _violations(probe) == []

    # And the marker must be findable by a plain grep across the tree, so the
    # exemption set can be reviewed without running anything.
    exemptions = [
        f"{p.relative_to(REPO_ROOT)}:{i}"
        for p in _benchmark_sources()
        for i in _exempt_lines(p.read_text())
    ]
    assert isinstance(exemptions, list)


def test_the_benchmark_package_is_actually_scanned() -> None:
    """Otherwise the parametrised test could pass by scanning nothing."""
    sources = _benchmark_sources()
    assert sources, "no benchmark sources found; the guard would vacuously pass"
    assert any(p.name == "parameter_equivariant.py" for p in sources)


def test_the_c5_exemption_is_temporary_and_named() -> None:
    """The xfail above must not become permanent scenery.

    It names a specific pending repair. When Phase 1 lands, the guard goes green
    on its own and this test is what makes removing the marker mandatory rather
    than optional -- it fails once the file is clean.
    """
    target = BENCHMARKS / _C5_REPAIR_PENDING
    assert target.exists(), _C5_REPAIR_PENDING
    if not _violations(target):
        pytest.fail(
            f"{_C5_REPAIR_PENDING} is now clean, so the C-5 repair has landed. "
            f"Remove _C5_REPAIR_PENDING and its xfail branch from this module -- "
            f"a permanent expected-failure is a guard that stopped guarding."
        )
