__all__ = [
    "run_advection_diffusion_vertical_slice_example",
    "run_heat_vertical_slice_example",
    "run_formula_generator_validation_example",
    "run_invariant_workflow_summary_example",
    "run_kdv_vertical_slice_example",
    "run_orbit_coverage_diagnostics_example",
    "run_reaction_diffusion_vertical_slice_example",
    "run_symmetry_candidate_validation_example",
    "run_translation_orbit_batch_example",
]


def run_advection_diffusion_vertical_slice_example() -> dict[str, object]:
    from pdelie.examples.advection_diffusion_vertical_slice import (
        run_advection_diffusion_vertical_slice_example as _impl,
    )

    return _impl()


def run_formula_generator_validation_example() -> dict[str, object]:
    from pdelie.examples.formula_generator_validation import run_formula_generator_validation_example as _impl

    return _impl()


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


def run_reaction_diffusion_vertical_slice_example() -> dict[str, object]:
    from pdelie.examples.reaction_diffusion_vertical_slice import (
        run_reaction_diffusion_vertical_slice_example as _impl,
    )

    return _impl()


def run_symmetry_candidate_validation_example() -> dict[str, object]:
    from pdelie.examples.symmetry_candidate_validation import run_symmetry_candidate_validation_example as _impl

    return _impl()


def run_translation_orbit_batch_example() -> dict[str, object]:
    from pdelie.examples.translation_orbit_batch import run_translation_orbit_batch_example as _impl

    return _impl()
