"""Final check: report final dimensions."""

from core import PipelineContext, PipelineStep
class FinalizeStep(PipelineStep):
    name = "finalize"
    description = "Report final sheet dimensions"
    requires = ("format_cells",)

    def run(self, ctx: PipelineContext) -> PipelineContext:
        ws = ctx.worksheet
        cfg = self.config
        ctx.log(f"Done: {ws.max_row} rows x {ws.max_column} cols (target: {cfg.final_columns})")
        return ctx
