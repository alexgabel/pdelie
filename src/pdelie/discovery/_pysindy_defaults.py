from __future__ import annotations

DEFAULT_PYSINDY_DISCOVERY_CONFIG: dict[str, object] = {
    "coefficient_threshold": 1e-8,
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
}


def get_default_pysindy_discovery_config() -> dict[str, object]:
    model_config = dict(DEFAULT_PYSINDY_DISCOVERY_CONFIG["pysindy_model"])
    return {
        "coefficient_threshold": float(DEFAULT_PYSINDY_DISCOVERY_CONFIG["coefficient_threshold"]),
        "pysindy_model": {
            "optimizer": dict(model_config["optimizer"]),
            "feature_library": dict(model_config["feature_library"]),
            "differentiation_method": dict(model_config["differentiation_method"]),
            "discrete_time": bool(model_config["discrete_time"]),
        },
        "pysindy_fit": dict(DEFAULT_PYSINDY_DISCOVERY_CONFIG["pysindy_fit"]),
    }
