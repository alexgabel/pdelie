from __future__ import annotations

from abc import ABC, abstractmethod

from pdelie.contracts import DerivativeBatch, FieldBatch, ResidualBatch


class ResidualEvaluator(ABC):
    @abstractmethod
    def evaluate(
        self,
        field: FieldBatch,
        derivatives: DerivativeBatch | None = None,
    ) -> ResidualBatch:
        raise NotImplementedError

