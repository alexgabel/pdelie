from pdelie.residuals.burgers_1d import BurgersResidualEvaluator
from pdelie.residuals.base import ResidualEvaluator
from pdelie.residuals.heat_1d import HeatResidualEvaluator
from pdelie.residuals.kdv_1d import KdVResidualEvaluator
from pdelie.residuals.weak_1d import evaluate_weak_burgers_residual, evaluate_weak_heat_residual

__all__ = [
    "BurgersResidualEvaluator",
    "HeatResidualEvaluator",
    "KdVResidualEvaluator",
    "ResidualEvaluator",
    "evaluate_weak_burgers_residual",
    "evaluate_weak_heat_residual",
]
