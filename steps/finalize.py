"""Final check: report final dimensions."""

from core import PipelineContext, PipelineStep
from config import Config


class FinalizeStep(PipelineStep):
    name = "finalize"
    description = "Report final sheet dimensions"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        ws = ctx.worksheet
        cfg = Config()
        ctx.log(f"Done: {ws.max_row} rows x {ws.max_column} cols (target: {cfg.final_columns})")
        return ctx
