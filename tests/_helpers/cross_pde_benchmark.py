from __future__ import annotations

from collections.abc import Callable

import numpy as np

from pdelie.contracts import FieldBatch, GeneratorFamily, VerificationReport
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import DEFAULT_EPSILON_VALUES, DEFAULT_RELATIVE_L2_NORM, verify_translation_generator


BenchmarkResult = dict[str, object]

_HeatFactory = generate_heat_1d_field_batch
_BurgersFactory = generate_burgers_1d_field_batch

CROSS_PDE_BENCHMARK_CONFIG: dict[str, object] = {
    "num_points": 64,
    "num_times": 33,
    "train_batch_size": 4,
    "heldout_batch_size": 3,
    "heat_train_seed": 210,
    "heat_heldout_seed": 211,
    "heat_noise_seed": 212,
    "burgers_train_seed": 310,
    "burgers_heldout_seed": 311,
    "burgers_noise_seed": 312,
    "noise_std_fraction": 2e-4,
    "epsilon_values": DEFAULT_EPSILON_VALUES,
    "norm": DEFAULT_RELATIVE_L2_NORM,
    "min_heldout_initial_conditions": 3,
    "backend": "spectral_fd",
}


def _benchmark_settings() -> dict[str, object]:
    return {
        "num_points": int(CROSS_PDE_BENCHMARK_CONFIG["num_points"]),
        "num_times": int(CROSS_PDE_BENCHMARK_CONFIG["num_times"]),
        "train_batch_size": int(CROSS_PDE_BENCHMARK_CONFIG["train_batch_size"]),
        "heldout_batch_size": int(CROSS_PDE_BENCHMARK_CONFIG["heldout_batch_size"]),
        "noise_std_fraction": float(CROSS_PDE_BENCHMARK_CONFIG["noise_std_fraction"]),
        "epsilon_values": np.asarray(CROSS_PDE_BENCHMARK_CONFIG["epsilon_values"], dtype=float).tolist(),
        "norm": str(CROSS_PDE_BENCHMARK_CONFIG["norm"]),
        "min_heldout_initial_conditions": int(CROSS_PDE_BENCHMARK_CONFIG["min_heldout_initial_conditions"]),
        "backend": str(CROSS_PDE_BENCHMARK_CONFIG["backend"]),
    }


def _perturb_heldout_field(field: FieldBatch, *, noise_std_fraction: float, seed: int) -> FieldBatch:
    rms = float(np.sqrt(np.mean(np.square(field.values))))
    noise_std = noise_std_fraction * rms
    rng = np.random.default_rng(seed)
    noisy_values = field.values + rng.normal(scale=noise_std, size=field.values.shape)
    return FieldBatch(
        values=noisy_values,
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log)
        + [
            {
                "transform_type": "additive_gaussian_noise",
                "parameters": {"noise_std_fraction": noise_std_fraction, "seed": seed},
                "invertible": False,
            }
        ],
        mask=None if field.mask is None else field.mask.copy(),
    )


def _pipeline_for_pde(
    *,
    pde_name: str,
    field_factory: Callable[..., FieldBatch],
    residual_evaluator: HeatResidualEvaluator | BurgersResidualEvaluator,
    train_seed: int,
    heldout_seed: int,
    noise_seed: int,
    apply_heldout_noise: bool,
) -> BenchmarkResult:
    settings = _benchmark_settings()
    training = field_factory(
        batch_size=int(CROSS_PDE_BENCHMARK_CONFIG["train_batch_size"]),
        num_times=int(CROSS_PDE_BENCHMARK_CONFIG["num_times"]),
        num_points=int(CROSS_PDE_BENCHMARK_CONFIG["num_points"]),
        seed=train_seed,
    )
    heldout = field_factory(
        batch_size=int(CROSS_PDE_BENCHMARK_CONFIG["heldout_batch_size"]),
        num_times=int(CROSS_PDE_BENCHMARK_CONFIG["num_times"]),
        num_points=int(CROSS_PDE_BENCHMARK_CONFIG["num_points"]),
        seed=heldout_seed,
    )
    if apply_heldout_noise:
        heldout = _perturb_heldout_field(
            heldout,
            noise_std_fraction=float(CROSS_PDE_BENCHMARK_CONFIG["noise_std_fraction"]),
            seed=noise_seed,
        )

    derivatives = compute_spectral_fd_derivatives(training)
    generator = fit_translation_generator(training, residual_evaluator, epsilon=1e-4)
    report = verify_translation_generator(
        heldout,
        generator,
        residual_evaluator,
        epsilon_values=np.asarray(CROSS_PDE_BENCHMARK_CONFIG["epsilon_values"], dtype=float),
        min_heldout_initial_conditions=int(CROSS_PDE_BENCHMARK_CONFIG["min_heldout_initial_conditions"]),
    )

    return {
        "pde_name": pde_name,
        "generator": generator,
        "report": report,
        "settings": settings,
        "noise_std_fraction": float(CROSS_PDE_BENCHMARK_CONFIG["noise_std_fraction"]),
        "noise_seed": int(noise_seed),
        "heldout_batch_size": int(CROSS_PDE_BENCHMARK_CONFIG["heldout_batch_size"]),
        "epsilon_values": np.asarray(CROSS_PDE_BENCHMARK_CONFIG["epsilon_values"], dtype=float),
        "backend": derivatives.backend,
        "heldout_field": heldout,
    }


def run_clean_cross_pde_benchmark() -> dict[str, BenchmarkResult]:
    return {
        "heat": _pipeline_for_pde(
            pde_name="heat",
            field_factory=_HeatFactory,
            residual_evaluator=HeatResidualEvaluator(),
            train_seed=int(CROSS_PDE_BENCHMARK_CONFIG["heat_train_seed"]),
            heldout_seed=int(CROSS_PDE_BENCHMARK_CONFIG["heat_heldout_seed"]),
            noise_seed=int(CROSS_PDE_BENCHMARK_CONFIG["heat_noise_seed"]),
            apply_heldout_noise=False,
        ),
        "burgers": _pipeline_for_pde(
            pde_name="burgers",
            field_factory=_BurgersFactory,
            residual_evaluator=BurgersResidualEvaluator(),
            train_seed=int(CROSS_PDE_BENCHMARK_CONFIG["burgers_train_seed"]),
            heldout_seed=int(CROSS_PDE_BENCHMARK_CONFIG["burgers_heldout_seed"]),
            noise_seed=int(CROSS_PDE_BENCHMARK_CONFIG["burgers_noise_seed"]),
            apply_heldout_noise=False,
        ),
    }


def run_noisy_cross_pde_benchmark() -> dict[str, BenchmarkResult]:
    return {
        "heat": _pipeline_for_pde(
            pde_name="heat",
            field_factory=_HeatFactory,
            residual_evaluator=HeatResidualEvaluator(),
            train_seed=int(CROSS_PDE_BENCHMARK_CONFIG["heat_train_seed"]),
            heldout_seed=int(CROSS_PDE_BENCHMARK_CONFIG["heat_heldout_seed"]),
            noise_seed=int(CROSS_PDE_BENCHMARK_CONFIG["heat_noise_seed"]),
            apply_heldout_noise=True,
        ),
        "burgers": _pipeline_for_pde(
            pde_name="burgers",
            field_factory=_BurgersFactory,
            residual_evaluator=BurgersResidualEvaluator(),
            train_seed=int(CROSS_PDE_BENCHMARK_CONFIG["burgers_train_seed"]),
            heldout_seed=int(CROSS_PDE_BENCHMARK_CONFIG["burgers_heldout_seed"]),
            noise_seed=int(CROSS_PDE_BENCHMARK_CONFIG["burgers_noise_seed"]),
            apply_heldout_noise=True,
        ),
    }
