from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from core.context import PipelineContext

if TYPE_CHECKING:
    from config import Config


class PipelineStep(ABC):
    """Base class for all pipeline steps."""

    name: str = "unnamed"
    description: str = ""
    requires: tuple[str, ...] = ()

    def __init__(self, config: Config | None = None):
        if config is None:
            from config import Config
            config = Config()
        self.config = config

    @abstractmethod
    def run(self, context: PipelineContext) -> PipelineContext:
        ...

    def __repr__(self) -> str:
        return f"<{type(self).__name__}: {self.name}>"
