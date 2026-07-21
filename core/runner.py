from __future__ import annotations

from pathlib import Path

from openpyxl import load_workbook

from config import Config
from core.context import PipelineContext
from core.pipeline import PipelineStep
from services.excel import save
from services.logger import get_logger


def process_file(xlsx_path: Path, config: Config | None = None) -> PipelineContext:
    """Load a single .xlsx, run pipeline, save result."""
    from steps import get_steps

    if config is None:
        config = Config()

    wb = load_workbook(xlsx_path)
    ws = wb.active
    context = PipelineContext(
        workbook=wb,
        worksheet=ws,
        source_path=xlsx_path,
        source_filename=xlsx_path.name,
    )

    pipeline = Pipeline(get_steps())
    result = pipeline.run(context)
    save(result.workbook, xlsx_path)
    return result


class Pipeline:
    """Ordered sequence of steps executed on a context."""

    def __init__(self, steps: list[PipelineStep] | None = None):
        if steps is None:
            from steps import get_steps
            steps = get_steps()
        self.steps = steps
        self._log = get_logger("pipeline")

    def run(self, context: PipelineContext) -> PipelineContext:
        self._log.info("Starting pipeline: %d step(s)", len(self.steps))
        for i, step in enumerate(self.steps, 1):
            self._log.info("[%d/%d] %s", i, len(self.steps), step.name)
            context = step.run(context)
            # Also write step's own logs to file
            for msg in context.logs:
                self._log.info("  %s", msg)
            context.logs.clear()
        self._log.info("Pipeline complete")
        return context
