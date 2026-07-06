from pdelie.residuals.advection_diffusion_1d import AdvectionDiffusionResidualEvaluator
from pdelie.residuals.base import ResidualEvaluator
from pdelie.residuals.burgers_1d import BurgersResidualEvaluator
from pdelie.residuals.heat_1d import HeatResidualEvaluator
from pdelie.residuals.kdv_1d import KdVResidualEvaluator
from pdelie.residuals.reaction_diffusion_1d import ReactionDiffusionResidualEvaluator
from pdelie.residuals.weak_1d import evaluate_weak_burgers_residual, evaluate_weak_heat_residual

__all__ = [
    "AdvectionDiffusionResidualEvaluator",
    "BurgersResidualEvaluator",
    "HeatResidualEvaluator",
    "KdVResidualEvaluator",
    "ReactionDiffusionResidualEvaluator",
    "ResidualEvaluator",
    "evaluate_weak_burgers_residual",
    "evaluate_weak_heat_residual",
]
