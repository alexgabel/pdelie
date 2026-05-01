__all__ = [
    "run_heat_vertical_slice_example",
    "run_invariant_workflow_summary_example",
    "run_kdv_vertical_slice_example",
    "run_orbit_coverage_diagnostics_example",
]


def run_heat_vertical_slice_example() -> dict[str, object]:
    from pdelie.examples.heat_vertical_slice import run_heat_vertical_slice_example as _impl

    return _impl()


def run_invariant_workflow_summary_example() -> dict[str, object]:
    from pdelie.examples.invariant_workflow_summary import run_invariant_workflow_summary_example as _impl

    return _impl()


def run_kdv_vertical_slice_example() -> dict[str, object]:
    from pdelie.examples.kdv_vertical_slice import run_kdv_vertical_slice_example as _impl

    return _impl()


def run_orbit_coverage_diagnostics_example() -> dict[str, object]:
    from pdelie.examples.orbit_coverage_diagnostics import run_orbit_coverage_diagnostics_example as _impl

    return _impl()
