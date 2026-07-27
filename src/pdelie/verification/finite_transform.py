from __future__ import annotations

import warnings

import numpy as np

from pdelie._boundary import get_x_boundary_type, is_x_periodic
from pdelie.contracts import FieldBatch, GeneratorFamily, VerificationReport
from pdelie.errors import ScopeValidationError
from pdelie.residuals.base import ResidualEvaluator
from pdelie.symmetry.parameterization.polynomial_translation import (
    DEFAULT_TRANSLATION_SPAN_TOLERANCE,
    _coerce_translation_coefficients,
    apply_pointwise_translation,
    evaluate_translation_xi,
    translation_span_distance,
)

DEFAULT_EPSILON_VALUES = np.logspace(-4, -1, 7)
DEFAULT_RELATIVE_L2_NORM = "relative_l2"

#: Below this overlap fraction the comparison rests on a small slice of the
#: domain and is noise-prone; a warning is emitted but a classification is
#: still produced.
MINIMUM_OVERLAP_FRACTION = 0.5

DISPATCH_PATH_PERIODIC = "periodic_fft_wrap"
DISPATCH_PATH_OVERLAP_CROP = "overlap_crop"


def _domain_length(field: FieldBatch) -> float:
    """Domain length as ``N * dx``, i.e. ``x[-1] - x[0] + dx``.

    This is the convention that makes ``overlap_fraction`` exactly equal
    ``retained_rows / num_points``: with ``N`` points and a shift of ``k * dx``
    the overlap retains ``N - k`` rows, so the fraction must be ``1 - k / N``.
    Using ``x[-1] - x[0]`` (i.e. ``(N-1) * dx``) instead gives ``1 - k/(N-1)``,
    which disagrees with the reported row count -- 0.5733 versus 0.5789 at
    ``k = 32, N = 76``. It is also the convention ``apply_pointwise_translation``
    already uses for the periodic period.
    """
    x = field.coords["x"]
    dx = float(x[1] - x[0])
    return float(x[-1] - x[0] + dx)


def _overlap_row_indices(field: FieldBatch, shift: float) -> np.ndarray:
    """Row indices whose source point lies inside the domain.

    A row at ``x`` is sourced from ``x - shift``. Outside ``[x[0], x[-1]]`` the
    translated field is clamped to the edge value rather than translated, so
    those rows carry no information about the transformation and are dropped.

    The count is symmetric in the sign of ``shift`` (both give ``N - |shift|/dx``
    rows) but the retained *region* is not: a positive shift keeps the right
    portion of the domain, a negative shift the left.
    """
    x = np.asarray(field.coords["x"], dtype=float)
    dx = float(x[1] - x[0])
    source = x - shift
    inside = (source >= x[0] - 1e-12 * dx) & (source <= x[-1] + 1e-12 * dx)
    return np.flatnonzero(inside)


def _apply_overlap_crop_translation(
    field: FieldBatch, shift: float
) -> tuple[FieldBatch, np.ndarray]:
    """Translate a nonperiodic field without wrapping, and report the overlap.

    Returns the translated field together with the row indices that are
    genuinely translated. Unlike the periodic FFT path this does **not** wrap:
    a bounded domain translated by ``shift`` maps to ``[x0 + shift, xN + shift]``,
    which shares only an overlap region with the original.
    """
    x = np.asarray(field.coords["x"], dtype=float)
    translated = np.empty_like(field.values)
    for batch_index in range(field.values.shape[0]):
        for time_index in range(field.values.shape[1]):
            for var_index in range(field.values.shape[3]):
                row = field.values[batch_index, time_index, :, var_index]
                translated[batch_index, time_index, :, var_index] = np.interp(
                    x - shift, x, row
                )

    cropped = FieldBatch(
        values=translated,
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None if field.mask is None else field.mask.copy(),
    )
    return cropped, _overlap_row_indices(field, shift)


def _apply_uniform_translation(field: FieldBatch, shift: float) -> FieldBatch:
    if not is_x_periodic(field):
        raise ScopeValidationError("Uniform translation requires periodic boundary conditions in x.")
    x = field.coords["x"]
    dx = float(x[1] - x[0])
    x_axis = field.dims.index("x")
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(x.size, d=dx)
    phase = np.exp(-1j * wavenumbers * shift)
    reshape = [1] * field.values.ndim
    reshape[x_axis] = x.size
    shifted_values = np.real(
        np.fft.ifft(np.fft.fft(field.values, axis=x_axis) * phase.reshape(tuple(reshape)), axis=x_axis)
    )
    return FieldBatch(
        values=shifted_values,
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None if field.mask is None else field.mask.copy(),
    )


def _relative_l2(error: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(error) / (np.linalg.norm(reference) + 1e-12))


def _classify_error_curve(error_curve: np.ndarray) -> str:
    e_small = float(error_curve[0])
    e_max = float(np.max(error_curve))

    monotone_curve = bool(np.all(np.diff(error_curve) >= -1e-12))
    stable_curve = monotone_curve and e_max <= 1e-4
    bounded_curve = e_max <= 1e-1

    if e_small <= 1e-6 and stable_curve:
        return "exact"
    if e_small <= 1e-2 and bounded_curve:
        return "approximate"
    return "failed"


def verify_translation_generator(
    field: FieldBatch,
    generator: GeneratorFamily,
    residual_evaluator: ResidualEvaluator,
    *,
    epsilon_values: np.ndarray | None = None,
    min_heldout_initial_conditions: int = 3,
    span_tolerance: float = DEFAULT_TRANSLATION_SPAN_TOLERANCE,
) -> VerificationReport:
    field.validate()
    generator.validate()

    if field.values.shape[0] < min_heldout_initial_conditions:
        raise ScopeValidationError(f"Held-out verification requires at least {min_heldout_initial_conditions} unseen initial conditions.")

    translation_coefficients = _coerce_translation_coefficients(generator.coefficients)
    epsilon_values = DEFAULT_EPSILON_VALUES if epsilon_values is None else np.asarray(epsilon_values, dtype=float)
    span_distance = translation_span_distance(translation_coefficients)
    baseline_residual = residual_evaluator.evaluate(field).residual

    xi = evaluate_translation_xi(field, translation_coefficients)
    use_uniform_translation = span_distance <= span_tolerance
    periodic = is_x_periodic(field)

    x_axis = field.dims.index("x")
    num_points = int(field.values.shape[x_axis])
    domain_length = _domain_length(field)

    # v0.33b: on the nonperiodic branch the comparison is restricted to
    # overlap AND interior. The interior trim comes from the residual
    # evaluator's own boundary policy -- on nonperiodic data the residual near
    # a boundary is dominated by finite-difference stencil error, so including
    # those rows would let stencil error drive the classification.
    baseline = residual_evaluator.evaluate(field)
    baseline_residual = baseline.residual
    trim = 0 if periodic else int(baseline.diagnostics.get("boundary_trim_width", 0))
    interior_indices = (
        np.arange(num_points) if trim <= 0 else np.arange(trim, num_points - trim)
    )

    batch_errors: list[list[float]] = []
    overlap_fractions: list[float] = []
    overlap_row_counts: list[int] = []
    compared_row_counts: list[int] = []

    for epsilon in epsilon_values:
        shift = float(epsilon * translation_coefficients[0])
        if periodic:
            if use_uniform_translation:
                transformed = _apply_uniform_translation(field, shift)
            else:
                transformed = apply_pointwise_translation(field, xi, float(epsilon))
            overlap_indices = np.arange(num_points)
            overlap_fraction = 1.0
        elif use_uniform_translation:
            transformed, overlap_indices = _apply_overlap_crop_translation(field, shift)
            overlap_fraction = max(0.0, 1.0 - abs(shift) / domain_length)
        else:
            transformed = apply_pointwise_translation(field, xi, float(epsilon))
            # Non-uniform xi: the per-row source position varies, so the overlap
            # is computed from the widest shift the transformation applies.
            widest_shift = float(np.max(np.abs(epsilon * xi)))
            overlap_indices = _overlap_row_indices(field, widest_shift)
            overlap_fraction = max(0.0, 1.0 - widest_shift / domain_length)

        compared_indices = np.intersect1d(overlap_indices, interior_indices)
        overlap_fractions.append(float(overlap_fraction))
        overlap_row_counts.append(int(overlap_indices.size))
        compared_row_counts.append(int(compared_indices.size))

        transformed_residual = residual_evaluator.evaluate(transformed).residual
        diff = (transformed_residual - baseline_residual)[:, :, compared_indices, :]
        reference = field.values[:, :, compared_indices, :]
        epsilon_batch_errors = [
            _relative_l2(diff[batch_index], reference[batch_index])
            for batch_index in range(field.values.shape[0])
        ]
        batch_errors.append(epsilon_batch_errors)

    error_curve = np.median(np.asarray(batch_errors, dtype=float), axis=1)
    classification = _classify_error_curve(error_curve)
    if not use_uniform_translation:
        classification = "failed"

    # Worst case across the epsilon sweep: the largest shift crops the most.
    worst_overlap_fraction = float(min(overlap_fractions))
    worst_overlap_row_count = int(min(overlap_row_counts))
    worst_compared_row_count = int(min(compared_row_counts))

    if not periodic and worst_overlap_fraction < MINIMUM_OVERLAP_FRACTION:
        warnings.warn(
            f"Overlap-crop verification retained an overlap fraction of only "
            f"{worst_overlap_fraction:.3f} at the largest epsilon; the residual "
            "comparison rests on a small slice of the domain and is noise-prone. "
            "A classification is still emitted.",
            UserWarning,
            stacklevel=2,
        )

    boundary_condition_x = get_x_boundary_type(field)
    if periodic:
        symmetry_claim = "equation_symmetry_candidate"
    elif worst_overlap_fraction <= 0.0:
        symmetry_claim = "domain_changing_action"
    elif boundary_condition_x == "open_unknown":
        symmetry_claim = "inconclusive_boundary_metadata"
    elif classification == "failed":
        # Interior verification did not succeed, so the candidate remains just a
        # candidate. This is NOT boundary_value_problem_not_preserved: the crop
        # removed the boundary rows, so nothing here speaks to the boundary.
        symmetry_claim = "equation_symmetry_candidate"
    else:
        symmetry_claim = "interior_overlap_verified"

    return VerificationReport(
        norm=DEFAULT_RELATIVE_L2_NORM,
        epsilon_values=epsilon_values,
        error_curve=error_curve,
        classification=classification,
        diagnostics={
            "heldout_initial_conditions": int(field.values.shape[0]),
            "span_distance": float(span_distance),
            "span_tolerance": float(span_tolerance),
            "transform_mode": "uniform_translation" if use_uniform_translation else "pointwise_translation",
            "batch_errors": batch_errors,
            "boundary_condition_x": boundary_condition_x,
            "dispatch_path": DISPATCH_PATH_PERIODIC if periodic else DISPATCH_PATH_OVERLAP_CROP,
            "overlap_fraction": worst_overlap_fraction,
            "overlap_fraction_by_epsilon": [float(value) for value in overlap_fractions],
            "overlap_row_count": worst_overlap_row_count,
            "compared_row_count": worst_compared_row_count,
            "interior_only_row_count": int(interior_indices.size),
            "interior_only_trim_width": int(trim),
            "symmetry_claim": symmetry_claim,
        },
    )
