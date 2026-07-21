from __future__ import annotations

from abc import ABC, abstractmethod

from core.context import PipelineContext


class PipelineStep(ABC):
    """Base class for all pipeline steps."""

    name: str = "unnamed"
    description: str = ""

    @abstractmethod
    def run(self, context: PipelineContext) -> PipelineContext:
        ...

    def __repr__(self) -> str:
        return f"<{type(self).__name__}: {self.name}>"
