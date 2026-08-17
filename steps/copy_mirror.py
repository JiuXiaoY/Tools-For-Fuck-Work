"""Mirror-copy: source col → target col per config.copy_targets.
   copy_targets is {target_col: source_col}, so copy from value to key."""

from core import PipelineContext, PipelineStep
from services import is_blank


class CopyMirrorStep(PipelineStep):
    name = "copy_mirror"
    description = "Copy source columns to target columns"
    requires = ("insert_columns",)

    def run(self, ctx: PipelineContext) -> PipelineContext:
        cfg = self.config
        ws = ctx.worksheet
        total = 0
        for r in range(1, ws.max_row + 1):
            for dst, src in cfg.copy_targets.items():
                val = ws.cell(row=r, column=src).value
                if not is_blank(val):
                    ws.cell(row=r, column=dst).value = val
                    total += 1
        ctx.log(f"Mirror copy: {total} cells written")
        return ctx
