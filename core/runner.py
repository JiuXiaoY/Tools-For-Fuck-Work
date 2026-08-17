from __future__ import annotations

from pathlib import Path
from collections.abc import Callable

from openpyxl import load_workbook

from config import Config
from core.context import PipelineContext
from core.pipeline import PipelineStep
from services.excel import save
from services.logger import get_logger

CheckpointCallback = Callable[[PipelineContext, int, PipelineStep], None]


def process_file(xlsx_path: Path, config: Config | None = None) -> PipelineContext:
    """Load a single .xlsx, run pipeline, save result."""
    config = config or Config()

    wb = load_workbook(xlsx_path)
    try:
        ws = wb.active
        context = PipelineContext(
            workbook=wb,
            worksheet=ws,
            source_path=xlsx_path,
            source_filename=xlsx_path.name,
        )

        result = process_context(context, config, checkpoint_source=xlsx_path)
        save(result.workbook, xlsx_path)
        return result
    finally:
        wb.close()


def process_context(
    context: PipelineContext,
    config: Config | None = None,
    *,
    checkpoint_source: Path | None = None,
) -> PipelineContext:
    """Run the main pipeline against an existing in-memory context."""
    from steps import get_steps

    config = config or Config()
    checkpoint_callback: CheckpointCallback | None = None
    if checkpoint_source is not None:
        checkpoint_dir = checkpoint_source.parent / ".checkpoints"

        def save_checkpoint(ctx: PipelineContext, index: int, step: PipelineStep) -> None:
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
            checkpoint = checkpoint_dir / (
                f"{checkpoint_source.stem}.step-{index:02d}-{step.name}{checkpoint_source.suffix}"
            )
            ctx.workbook.save(checkpoint)
            ctx.metadata.setdefault("checkpoints", []).append(str(checkpoint))
        checkpoint_callback = save_checkpoint

    pipeline = Pipeline(
        get_steps(config),
        continue_on_error=config.pipeline_continue_on_error,
        checkpoint_every=config.pipeline_checkpoint_every,
        checkpoint_callback=checkpoint_callback,
    )
    return pipeline.run(context)


class Pipeline:
    """Ordered sequence of steps executed on a context."""

    def __init__(
        self,
        steps: list[PipelineStep] | None = None,
        *,
        continue_on_error: bool = False,
        checkpoint_every: int = 0,
        checkpoint_callback: CheckpointCallback | None = None,
    ):
        if steps is None:
            from steps import get_steps
            steps = get_steps()
        self.steps = steps
        self._validate_order()
        self.continue_on_error = continue_on_error
        self.checkpoint_every = max(0, checkpoint_every)
        self.checkpoint_callback = checkpoint_callback
        self._log = get_logger("pipeline")

    def _validate_order(self) -> None:
        seen: set[str] = set()
        for step in self.steps:
            if step.name in seen:
                raise ValueError(f"Duplicate pipeline step: {step.name}")
            missing = [name for name in step.requires if name not in seen]
            if missing:
                raise ValueError(
                    f"Step '{step.name}' must follow: {', '.join(missing)}"
                )
            seen.add(step.name)

    def run(self, context: PipelineContext) -> PipelineContext:
        self._log.info("Starting pipeline: %d step(s)", len(self.steps))
        for i, step in enumerate(self.steps, 1):
            self._log.info("[%d/%d] %s", i, len(self.steps), step.name)
            try:
                context = step.run(context)
            except Exception as exc:
                failed = context.metadata.setdefault("failed_steps", [])
                failed.append({"step": step.name, "error": str(exc)})
                self._log.exception("Step %s failed", step.name)
                if not self.continue_on_error:
                    raise PipelineStepError(step.name) from exc
                continue
            # Also write step's own logs to file
            for msg in context.logs:
                self._log.info("  %s", msg)
            context.logs.clear()
            if (
                self.checkpoint_callback is not None
                and self.checkpoint_every > 0
                and i % self.checkpoint_every == 0
            ):
                self.checkpoint_callback(context, i, step)
                self._log.info("Checkpoint saved after step %s", step.name)
        self._log.info("Pipeline complete")
        return context


class PipelineStepError(RuntimeError):
    """Raised when a named pipeline step fails in fail-fast mode."""

    def __init__(self, step_name: str):
        super().__init__(f"Pipeline step failed: {step_name}")
        self.step_name = step_name
