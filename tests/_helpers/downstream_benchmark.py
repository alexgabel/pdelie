from __future__ import annotations

import importlib
from collections.abc import Callable

import numpy as np

from pdelie import FieldBatch, GeneratorFamily, InvariantMapSpec
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.discovery import to_pysindy_trajectories
from pdelie.invariants import InvariantApplier
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator


BenchmarkBranchResult = dict[str, object]
BenchmarkResult = dict[str, object]

_HeatFactory = generate_heat_1d_field_batch
_BurgersFactory = generate_burgers_1d_field_batch
_BENCHMARK_BRANCHES = (
    "vanilla",
    "known_invariant",
    "discovered_invariant",
    "nuisance",
)

DOWNSTREAM_BENCHMARK_CONFIG: dict[str, object] = {
    "num_points": 64,
    "num_times": 33,
    "train_batch_size": 4,
    "heldout_batch_size": 3,
    "branch_names": list(_BENCHMARK_BRANCHES),
    "alignment_rule": "shift = x[argmax(values[0, 0, :, 0])] - x[0]",
    "heat_train_seed": 210,
    "heat_heldout_seed": 211,
    "heat_nuisance_train_shift_seed": 212,
    "heat_nuisance_heldout_shift_seed": 213,
    "burgers_train_seed": 310,
    "burgers_heldout_seed": 311,
    "burgers_nuisance_train_shift_seed": 312,
    "burgers_nuisance_heldout_shift_seed": 313,
    "pysindy_model": {
        "optimizer": {
            "threshold": 0.1,
            "alpha": 0.05,
            "max_iter": 20,
            "normalize_columns": False,
            "fit_intercept": False,
            "copy_X": True,
            "verbose": False,
        },
        "feature_library": {
            "degree": 2,
            "include_interaction": True,
            "interaction_only": False,
            "include_bias": True,
            "order": "C",
            "library_ensemble": False,
        },
        "differentiation_method": {
            "order": 2,
            "d": 1,
            "axis": 0,
            "is_uniform": False,
            "drop_endpoints": False,
            "periodic": False,
        },
        "discrete_time": False,
    },
    "pysindy_fit": {
        "multiple_trajectories": True,
        "unbias": True,
        "quiet": True,
        "ensemble": False,
        "library_ensemble": False,
        "replace": True,
        "n_candidates_to_drop": 1,
        "n_subset": None,
        "n_models": None,
        "ensemble_aggregator": None,
    },
    "pysindy_score": {
        "multiple_trajectories": True,
        "metric": "r2_score",
    },
}


def _benchmark_settings() -> dict[str, object]:
    model_config = dict(DOWNSTREAM_BENCHMARK_CONFIG["pysindy_model"])
    return {
        "num_points": int(DOWNSTREAM_BENCHMARK_CONFIG["num_points"]),
        "num_times": int(DOWNSTREAM_BENCHMARK_CONFIG["num_times"]),
        "train_batch_size": int(DOWNSTREAM_BENCHMARK_CONFIG["train_batch_size"]),
        "heldout_batch_size": int(DOWNSTREAM_BENCHMARK_CONFIG["heldout_batch_size"]),
        "branch_names": list(DOWNSTREAM_BENCHMARK_CONFIG["branch_names"]),
        "alignment_rule": str(DOWNSTREAM_BENCHMARK_CONFIG["alignment_rule"]),
        "pysindy_model": {
            "optimizer": dict(model_config["optimizer"]),
            "feature_library": dict(model_config["feature_library"]),
            "differentiation_method": dict(model_config["differentiation_method"]),
            "discrete_time": bool(model_config["discrete_time"]),
        },
        "pysindy_fit": dict(DOWNSTREAM_BENCHMARK_CONFIG["pysindy_fit"]),
        "pysindy_score": dict(DOWNSTREAM_BENCHMARK_CONFIG["pysindy_score"]),
    }


def _require_downstream_dependencies():
    try:
        pysindy = importlib.import_module("pysindy")
        sklearn_metrics = importlib.import_module("sklearn.metrics")
    except (ModuleNotFoundError, ImportError, ValueError) as exc:
        raise ImportError(
            "PySINDy downstream benchmark requires pdelie[test] or pdelie[downstream]."
        ) from exc
    return pysindy, sklearn_metrics.r2_score


def _known_translation_generator_metadata() -> dict[str, object]:
    generator = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]]),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )
    return generator.to_dict()


def _single_sample_fields(field: FieldBatch) -> list[FieldBatch]:
    return [
        FieldBatch(
            values=field.values[index : index + 1].copy(),
            dims=field.dims,
            coords={name: coord.copy() for name, coord in field.coords.items()},
            var_names=list(field.var_names),
            metadata=dict(field.metadata),
            preprocess_log=list(field.preprocess_log),
            mask=None if field.mask is None else field.mask[index : index + 1].copy(),
        )
        for index in range(field.values.shape[field.dims.index("batch")])
    ]


def _make_invariant_spec(generator_metadata: dict[str, object], shift: float) -> InvariantMapSpec:
    return InvariantMapSpec(
        generator_metadata=generator_metadata,
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": float(shift)},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )


def _apply_alignment(
    sample_fields: list[FieldBatch],
    generator_metadata: dict[str, object],
) -> tuple[list[FieldBatch], list[float]]:
    applier = InvariantApplier()
    transformed_fields: list[FieldBatch] = []
    shifts: list[float] = []
    for sample in sample_fields:
        x = sample.coords["x"]
        peak_index = int(np.argmax(sample.values[0, 0, :, 0]))
        shift = float(x[peak_index] - x[0])
        transformed_fields.append(applier.apply(sample, _make_invariant_spec(generator_metadata, shift)))
        shifts.append(shift)
    return transformed_fields, shifts


def _apply_nuisance_shifts(
    sample_fields: list[FieldBatch],
    generator_metadata: dict[str, object],
    *,
    seed: int,
) -> tuple[list[FieldBatch], list[float]]:
    applier = InvariantApplier()
    rng = np.random.default_rng(seed)
    transformed_fields: list[FieldBatch] = []
    shifts: list[float] = []
    for sample in sample_fields:
        shift = float(rng.choice(sample.coords["x"]))
        transformed_fields.append(applier.apply(sample, _make_invariant_spec(generator_metadata, shift)))
        shifts.append(shift)
    return transformed_fields, shifts


def _bridge_sample_fields(
    sample_fields: list[FieldBatch],
) -> tuple[list[np.ndarray], np.ndarray, list[str]]:
    trajectories: list[np.ndarray] = []
    shared_time_values: np.ndarray | None = None
    shared_feature_names: list[str] | None = None
    for sample in sample_fields:
        sample_trajectories, time_values, feature_names = to_pysindy_trajectories(sample)
        if len(sample_trajectories) != 1:
            raise AssertionError("Single-sample bridge must yield exactly one trajectory.")
        trajectories.append(sample_trajectories[0])
        if shared_time_values is None:
            shared_time_values = np.asarray(time_values, dtype=float).copy()
            shared_feature_names = list(feature_names)
            continue
        if not np.allclose(shared_time_values, time_values):
            raise AssertionError("All benchmark sample fields must share identical time coordinates.")
        if shared_feature_names != feature_names:
            raise AssertionError("All benchmark sample fields must share identical feature names.")
    if shared_time_values is None or shared_feature_names is None:
        raise AssertionError("Benchmark branches must include at least one sample field.")
    return trajectories, shared_time_values, shared_feature_names


def _build_pysindy_model(feature_names: list[str]):
    pysindy, _ = _require_downstream_dependencies()
    model_config = dict(DOWNSTREAM_BENCHMARK_CONFIG["pysindy_model"])
    return pysindy.SINDy(
        optimizer=pysindy.STLSQ(**dict(model_config["optimizer"])),
        feature_library=pysindy.PolynomialLibrary(**dict(model_config["feature_library"])),
        differentiation_method=pysindy.FiniteDifference(**dict(model_config["differentiation_method"])),
        feature_names=list(feature_names),
        discrete_time=bool(model_config["discrete_time"]),
    )


def _fit_and_score_branch(
    train_fields: list[FieldBatch],
    heldout_fields: list[FieldBatch],
) -> tuple[float, list[np.ndarray], list[np.ndarray], np.ndarray, list[str]]:
    _, r2_score = _require_downstream_dependencies()
    train_trajectories, train_time_values, train_feature_names = _bridge_sample_fields(train_fields)
    heldout_trajectories, heldout_time_values, heldout_feature_names = _bridge_sample_fields(heldout_fields)
    if not np.allclose(train_time_values, heldout_time_values):
        raise AssertionError("Training and held-out branches must share identical time coordinates.")
    if train_feature_names != heldout_feature_names:
        raise AssertionError("Training and held-out branches must share identical feature names.")

    model = _build_pysindy_model(train_feature_names)
    model.fit(
        train_trajectories,
        t=train_time_values,
        **dict(DOWNSTREAM_BENCHMARK_CONFIG["pysindy_fit"]),
    )
    score = float(
        model.score(
            heldout_trajectories,
            t=train_time_values,
            multiple_trajectories=bool(DOWNSTREAM_BENCHMARK_CONFIG["pysindy_score"]["multiple_trajectories"]),
            metric=r2_score,
        )
    )
    return (
        score,
        train_trajectories,
        heldout_trajectories,
        train_time_values,
        train_feature_names,
    )


def _build_branch_result(
    *,
    train_fields: list[FieldBatch],
    heldout_fields: list[FieldBatch],
    train_shifts: list[float],
    heldout_shifts: list[float],
    train_shift_seed: int | None,
    heldout_shift_seed: int | None,
) -> tuple[BenchmarkBranchResult, np.ndarray, list[str]]:
    score, train_trajectories, heldout_trajectories, time_values, feature_names = _fit_and_score_branch(
        train_fields,
        heldout_fields,
    )
    return (
        {
            "score": score,
            "train_trajectories": train_trajectories,
            "heldout_trajectories": heldout_trajectories,
            "train_shifts": list(train_shifts),
            "heldout_shifts": list(heldout_shifts),
            "train_shift_seed": train_shift_seed,
            "heldout_shift_seed": heldout_shift_seed,
        },
        time_values,
        feature_names,
    )


def _pipeline_for_pde(
    *,
    pde_name: str,
    field_factory: Callable[..., FieldBatch],
    residual_evaluator: HeatResidualEvaluator | BurgersResidualEvaluator,
    train_seed: int,
    heldout_seed: int,
    nuisance_train_shift_seed: int,
    nuisance_heldout_shift_seed: int,
) -> BenchmarkResult:
    training_field = field_factory(
        batch_size=int(DOWNSTREAM_BENCHMARK_CONFIG["train_batch_size"]),
        num_times=int(DOWNSTREAM_BENCHMARK_CONFIG["num_times"]),
        num_points=int(DOWNSTREAM_BENCHMARK_CONFIG["num_points"]),
        seed=train_seed,
    )
    heldout_field = field_factory(
        batch_size=int(DOWNSTREAM_BENCHMARK_CONFIG["heldout_batch_size"]),
        num_times=int(DOWNSTREAM_BENCHMARK_CONFIG["num_times"]),
        num_points=int(DOWNSTREAM_BENCHMARK_CONFIG["num_points"]),
        seed=heldout_seed,
    )
    training_samples = _single_sample_fields(training_field)
    heldout_samples = _single_sample_fields(heldout_field)

    known_generator_metadata = _known_translation_generator_metadata()
    discovered_generator_metadata = fit_translation_generator(
        training_field,
        residual_evaluator,
        epsilon=1e-4,
    ).to_dict()

    known_training_fields, known_training_shifts = _apply_alignment(training_samples, known_generator_metadata)
    known_heldout_fields, known_heldout_shifts = _apply_alignment(heldout_samples, known_generator_metadata)
    discovered_training_fields, discovered_training_shifts = _apply_alignment(
        training_samples,
        discovered_generator_metadata,
    )
    discovered_heldout_fields, discovered_heldout_shifts = _apply_alignment(
        heldout_samples,
        discovered_generator_metadata,
    )
    nuisance_training_fields, nuisance_training_shifts = _apply_nuisance_shifts(
        training_samples,
        known_generator_metadata,
        seed=nuisance_train_shift_seed,
    )
    nuisance_heldout_fields, nuisance_heldout_shifts = _apply_nuisance_shifts(
        heldout_samples,
        known_generator_metadata,
        seed=nuisance_heldout_shift_seed,
    )

    branch_inputs = {
        "vanilla": (
            training_samples,
            heldout_samples,
            [],
            [],
            None,
            None,
        ),
        "known_invariant": (
            known_training_fields,
            known_heldout_fields,
            known_training_shifts,
            known_heldout_shifts,
            None,
            None,
        ),
        "discovered_invariant": (
            discovered_training_fields,
            discovered_heldout_fields,
            discovered_training_shifts,
            discovered_heldout_shifts,
            None,
            None,
        ),
        "nuisance": (
            nuisance_training_fields,
            nuisance_heldout_fields,
            nuisance_training_shifts,
            nuisance_heldout_shifts,
            nuisance_train_shift_seed,
            nuisance_heldout_shift_seed,
        ),
    }

    shared_time_values: np.ndarray | None = None
    shared_feature_names: list[str] | None = None
    branch_results: dict[str, BenchmarkBranchResult] = {}
    for branch_name in _BENCHMARK_BRANCHES:
        branch_result, time_values, feature_names = _build_branch_result(
            train_fields=branch_inputs[branch_name][0],
            heldout_fields=branch_inputs[branch_name][1],
            train_shifts=branch_inputs[branch_name][2],
            heldout_shifts=branch_inputs[branch_name][3],
            train_shift_seed=branch_inputs[branch_name][4],
            heldout_shift_seed=branch_inputs[branch_name][5],
        )
        if shared_time_values is None:
            shared_time_values = time_values.copy()
            shared_feature_names = list(feature_names)
        else:
            if not np.allclose(shared_time_values, time_values):
                raise AssertionError("All benchmark branches must share identical time coordinates.")
            if shared_feature_names != feature_names:
                raise AssertionError("All benchmark branches must share identical feature names.")
        branch_results[branch_name] = branch_result

    if shared_time_values is None or shared_feature_names is None:
        raise AssertionError("Benchmark must produce shared time values and feature names.")

    return {
        "pde_name": pde_name,
        "settings": _benchmark_settings(),
        "data_seeds": {
            "train_seed": train_seed,
            "heldout_seed": heldout_seed,
            "nuisance_train_shift_seed": nuisance_train_shift_seed,
            "nuisance_heldout_shift_seed": nuisance_heldout_shift_seed,
        },
        "time_values": shared_time_values,
        "feature_names": shared_feature_names,
        "branches": branch_results,
    }


def run_downstream_benchmark() -> dict[str, BenchmarkResult]:
    _require_downstream_dependencies()
    return {
        "heat": _pipeline_for_pde(
            pde_name="heat",
            field_factory=_HeatFactory,
            residual_evaluator=HeatResidualEvaluator(),
            train_seed=int(DOWNSTREAM_BENCHMARK_CONFIG["heat_train_seed"]),
            heldout_seed=int(DOWNSTREAM_BENCHMARK_CONFIG["heat_heldout_seed"]),
            nuisance_train_shift_seed=int(DOWNSTREAM_BENCHMARK_CONFIG["heat_nuisance_train_shift_seed"]),
            nuisance_heldout_shift_seed=int(DOWNSTREAM_BENCHMARK_CONFIG["heat_nuisance_heldout_shift_seed"]),
        ),
        "burgers": _pipeline_for_pde(
            pde_name="burgers",
            field_factory=_BurgersFactory,
            residual_evaluator=BurgersResidualEvaluator(),
            train_seed=int(DOWNSTREAM_BENCHMARK_CONFIG["burgers_train_seed"]),
            heldout_seed=int(DOWNSTREAM_BENCHMARK_CONFIG["burgers_heldout_seed"]),
            nuisance_train_shift_seed=int(DOWNSTREAM_BENCHMARK_CONFIG["burgers_nuisance_train_shift_seed"]),
            nuisance_heldout_shift_seed=int(DOWNSTREAM_BENCHMARK_CONFIG["burgers_nuisance_heldout_shift_seed"]),
        ),
    }
