"""Validate sheet dimensions."""

from core import PipelineContext, PipelineStep
class ValidateStep(PipelineStep):
    name = "validate"
    description = "Report sheet row and column counts"
    requires = ("merge_sheets",)

    def run(self, ctx: PipelineContext) -> PipelineContext:
        ws = ctx.worksheet
        cfg = self.config
        if ws.max_row == 0:
            ctx.log("Warning: sheet has no data")
        else:
            ctx.log(f"Validated: {ws.max_row} rows, {ws.max_column} cols (expect ~{cfg.initial_columns})")
        return ctx
