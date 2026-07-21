"""Fill column AR (44) from column L (12)."""

from core import PipelineContext, PipelineStep
from config import Config
from services import is_blank


class FillCol44Step(PipelineStep):
    name = "fill_col44"
    description = "Column AR: copy from column L"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        cfg = Config()
        ws = ctx.worksheet
        filled = 0
        for r in range(1, ws.max_row + 1):
            val = ws.cell(row=r, column=cfg.col_l).value
            if not is_blank(val):
                ws.cell(row=r, column=cfg.col_ar).value = val
                filled += 1
        ctx.log(f"Column {cfg.col_ar}: {filled} cells copied from col {cfg.col_l}")
        return ctx
