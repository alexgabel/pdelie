"""External smoke test: exercise an INSTALLED PDELie, never the working tree.

Why this is not part of the test suite
======================================

The test suite runs against the repository, with the source tree importable and
every dev dependency present. That is exactly the environment a release must not
be trusted in. This script is meant to be run from a throwaway virtualenv that
has installed PDELie the way a user would:

    uv venv --python 3.12 /tmp/smoke && \\
      VIRTUAL_ENV=/tmp/smoke uv pip install \\
        "git+https://github.com/alexgabel/pdelie.git@v0.38.0rc1" && \\
      /tmp/smoke/bin/python scripts/external_smoke.py

It refuses to run if PDELie resolves to a source checkout, because a smoke test
that silently measured the working tree would pass on a broken wheel.

What it checks, and why each one
================================

Not an import check. A package can import cleanly and still be missing a
submodule from the sdist, or carry a dependency that is only present because the
dev environment installed it.

Each check exercises a v0.38 surface end to end and asserts a property that
would break if packaging were wrong.

A note on the checks themselves
===============================

Written for the v0.38.0rc1 smoke, and three of the five had to be corrected
because they called APIs that do not exist -- a keyword that was never there, a
module path that was invented, a dataclass field guessed rather than read. Each
failure looked exactly like a packaging defect until the source was checked.

That is the trap this file exists inside: a smoke test failing against a
release candidate is the most alarming possible signal, and the first instinct
is to believe it. Read the source before believing this script.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

FAILURES: list[str] = []


def check(name: str, fn) -> None:
    try:
        fn()
        print(f"  PASS  {name}")
    except Exception as exc:  # noqa: BLE001 - a smoke reports, it does not raise
        FAILURES.append(f"{name}: {type(exc).__name__}: {exc}")
        print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")


def refuse_if_running_against_a_checkout() -> None:
    """A smoke test that measured the working tree would pass on a broken wheel."""
    import pdelie

    location = Path(pdelie.__file__).resolve()
    if (location.parents[2] / "pyproject.toml").exists():
        raise SystemExit(
            f"REFUSING TO RUN: pdelie resolves to a source checkout\n"
            f"  {location}\n"
            f"This script must run against an installed distribution. Create a "
            f"throwaway venv, install from the tag, and run it with that "
            f"interpreter."
        )
    print(f"  installed at {location.parent}")


# --------------------------------------------------------------------------
# The checks
# --------------------------------------------------------------------------


def fornberg_weights_are_exact_on_a_nonuniform_grid() -> None:
    """v0.38b. The second derivative of x^2 is exactly 2, on any node set."""
    from pdelie.differentiation.fornberg import (
        describe_grid_regularity,
        fornberg_weights,
    )

    x = np.array([0.0, 0.1, 0.25, 0.5, 0.9])
    w = fornberg_weights(x, 0.25, 2)
    got = float(np.dot(w.weights, x**2))
    assert abs(got - 2.0) < 1e-9, f"expected 2.0, got {got}"
    assert w.formal_accuracy == len(x) - 2, w.formal_accuracy
    assert describe_grid_regularity(x).is_uniform is False


def irregular_weak_quadrature_integrates_a_constant_exactly() -> None:
    """v0.38c. A rule that cannot integrate 1 over its own interval is not a rule."""
    from pdelie.residuals.irregular_weak import (
        nonuniform_trapezoidal_weights,
        validate_quadrature_weights,
    )

    x = np.array([0.0, 0.3, 0.4, 1.0])
    w = nonuniform_trapezoidal_weights(x)
    assert abs(float(w.sum()) - 1.0) < 1e-12, float(w.sum())
    validate_quadrature_weights(w, x, rule="nonuniform_trapezoidal")


def the_relative_statistic_is_withheld_at_the_floor() -> None:
    """v0.38d. A ratio between two numbers that are both ~1e-16 is not a number.

    The report must return None rather than a large, meaningless value.
    """
    from pdelie.contracts.error_metric_spec import ErrorMetricSpec
    from pdelie.differentiation.error_reference import measure_derivative_error

    linf = ErrorMetricSpec(
        metric_spec_id="smoke_linf_absolute", quantity="absolute", norm="linf"
    )
    report = measure_derivative_error(
        np.array([1e-17]),
        np.array([0.0]),
        metric=linf,
        reference_kind="analytical",
        reference_scale=1.0,
    )
    assert report.reporting_regime == "floor", report.reporting_regime
    assert report.relative_error is None, report.relative_error
    assert report.absolute_error is not None


def the_seed_is_required_and_the_result_is_reproducible() -> None:
    """v0.38's breaking change, exercised rather than introspected.

    Omitting the seed must raise. A default seed is an unrecorded choice, and
    this promise was two releases old before it was kept.
    """
    from pdelie.data import generate_heat_1d_field_batch
    from pdelie.tasks.weak_pde_library import inspect_pysindy_weak_pde_library

    # 64x64 is the documented lower bound for K=16 weak-library subdomains.
    batch = generate_heat_1d_field_batch(
        batch_size=1, num_times=64, num_points=64, seed=7
    )
    first = inspect_pysindy_weak_pde_library(batch, task_name="smoke", seed=13)
    assert first["summary_type"] == "pdelie_weak_pde_library_diagnostic"

    try:
        inspect_pysindy_weak_pde_library(batch, task_name="smoke")
    except TypeError:
        pass
    else:
        raise AssertionError("seed was omitted and no error was raised")

    second = inspect_pysindy_weak_pde_library(batch, task_name="smoke", seed=13)
    assert json.dumps(first, sort_keys=True, default=str) == json.dumps(
        second, sort_keys=True, default=str
    ), "the same seed produced two different summaries"


def out_of_scope_input_is_refused_with_a_reason() -> None:
    """A refusal that does not say why is a crash with better manners."""
    from pdelie.data import generate_heat_1d_field_batch
    from pdelie.errors import ScopeValidationError
    from pdelie.tasks.weak_pde_library import inspect_pysindy_weak_pde_library

    multi = generate_heat_1d_field_batch(batch_size=2, num_times=64, num_points=64)
    try:
        inspect_pysindy_weak_pde_library(multi, task_name="smoke", seed=13)
    except ScopeValidationError as exc:
        message = str(exc)
        assert "batch" in message and "out of scope" in message, message
    else:
        raise AssertionError("multi-batch input was accepted; it is out of scope")


def the_root_surface_is_frozen() -> None:
    """11 exports, and no __version__.

    Adding ``pdelie.__version__`` would widen the frozen root surface to satisfy
    a release check. The gate reads ``importlib.metadata`` instead.
    """
    import pdelie

    assert len(pdelie.__all__) == 11, sorted(pdelie.__all__)
    assert not hasattr(pdelie, "__version__")


def the_installed_version_is_what_it_claims() -> None:
    import importlib.metadata

    version = importlib.metadata.version("pdelie")
    print(f"        installed version {version}")
    assert version, "no version recorded on the installed distribution"


def main() -> None:
    print("=== PDELie external smoke ===")
    refuse_if_running_against_a_checkout()
    print(f"  interpreter {'.'.join(map(str, sys.version_info[:3]))}\n")

    for name, fn in (
        ("installed version is recorded", the_installed_version_is_what_it_claims),
        ("root surface frozen at 11 exports", the_root_surface_is_frozen),
        ("v0.38b  Fornberg weights exact on a non-uniform grid",
         fornberg_weights_are_exact_on_a_nonuniform_grid),
        ("v0.38c  irregular weak quadrature integrates a constant",
         irregular_weak_quadrature_integrates_a_constant_exactly),
        ("v0.38d  relative statistic withheld at the floor",
         the_relative_statistic_is_withheld_at_the_floor),
        ("v0.38   seed required, and the same seed reproduces",
         the_seed_is_required_and_the_result_is_reproducible),
        ("        out-of-scope input refused with a reason",
         out_of_scope_input_is_refused_with_a_reason),
    ):
        check(name, fn)

    print()
    if FAILURES:
        print(f"SMOKE FAILED — {len(FAILURES)} check(s)")
        print("Read the source before concluding the release is broken; three of "
              "these checks were wrong before they were right.")
        raise SystemExit(1)
    print("SMOKE PASSED — the installed distribution exercises the v0.38 surface")


if __name__ == "__main__":
    main()
