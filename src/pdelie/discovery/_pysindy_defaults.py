"""v0.32a default PySINDy discovery configuration.

Migrated to PySINDy 2.1.x. Every kwarg here is present in the 2.1.0
signatures audited in ``docs/design/PYSINDY_2_MIGRATION_AUDIT.md``.
The legacy 1.7.5-specific kwargs (``fit_intercept``,
``library_ensemble``, ``interaction_only``, ``is_uniform``,
``periodic``, ``discrete_time``, ``multiple_trajectories``,
``unbias``, ``quiet``, ``ensemble``, ``replace``,
``n_candidates_to_drop``, ``n_subset``, ``n_models``,
``ensemble_aggregator``) are removed — they are no longer accepted
by PySINDy 2.x and passing them would raise ``TypeError``.
"""

from __future__ import annotations

DEFAULT_PYSINDY_DISCOVERY_CONFIG: dict[str, object] = {
    "coefficient_threshold": 1e-8,
    "pysindy_model": {
        # STLSQ.__init__ in 2.1.0: threshold, alpha, max_iter, ridge_kw,
        # normalize_columns, copy_X, initial_guess, verbose, sparse_ind, unbias.
        "optimizer": {
            "threshold": 0.1,
            "alpha": 0.05,
            "max_iter": 20,
            "normalize_columns": False,
            "copy_X": True,
            "verbose": False,
        },
        # PolynomialLibrary.__init__ in 2.1.0: degree, include_interaction,
        # interaction_only, include_bias, order. This dict is fed into a
        # PolynomialLibrary which becomes the `function_library=` argument
        # on PDELibrary — the v0.31-era `library_functions`/`function_names`
        # kwargs on PDELibrary are gone.
        "feature_library": {
            "degree": 2,
            "include_interaction": True,
            "interaction_only": False,
            "include_bias": True,
            "order": "C",
        },
        # FiniteDifference.__init__ in 2.1.0: order, d, axis, is_uniform,
        # drop_endpoints, periodic. These are FiniteDifference kwargs
        # (not PDELibrary kwargs); the periodic-boundary intent is carried
        # here on the differentiation method used by PDELibrary internally
        # via `diff_kwargs`.
        "differentiation_method": {
            "order": 2,
            "d": 1,
            "axis": 0,
            "is_uniform": False,
            "drop_endpoints": False,
            "periodic": False,
        },
    },
    # SINDy.fit(x, t, x_dot=None, u=None, feature_names=None) in 2.1.0. No
    # additional keyword arguments are passed on the default path; every
    # legacy 1.x fit kwarg was removed.
    "pysindy_fit": {},
}


def get_default_pysindy_discovery_config() -> dict[str, object]:
    model_config = dict(DEFAULT_PYSINDY_DISCOVERY_CONFIG["pysindy_model"])
    return {
        "coefficient_threshold": float(DEFAULT_PYSINDY_DISCOVERY_CONFIG["coefficient_threshold"]),
        "pysindy_model": {
            "optimizer": dict(model_config["optimizer"]),
            "feature_library": dict(model_config["feature_library"]),
            "differentiation_method": dict(model_config["differentiation_method"]),
        },
        "pysindy_fit": dict(DEFAULT_PYSINDY_DISCOVERY_CONFIG["pysindy_fit"]),
    }
