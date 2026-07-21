"""Fill column C (3): if col A has fill → use col B, else use above cell."""

from core import PipelineContext, PipelineStep
from config import Config
from services import cell_has_fill, is_blank


class FillCol3Step(PipelineStep):
    name = "fill_col3"
    description = "Column C: cascade fill based on col A color"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        cfg = Config()
        ws = ctx.worksheet
        filled = 0
        for r in range(1, ws.max_row + 1):
            if cell_has_fill(ws.cell(row=r, column=cfg.col_a)):
                val = ws.cell(row=r, column=cfg.col_b).value
            elif r == 1:
                continue
            else:
                val = ws.cell(row=r - 1, column=cfg.col_c).value
            if not is_blank(val):
                ws.cell(row=r, column=cfg.col_c).value = val
                filled += 1
        ctx.log(f"Column {cfg.col_c}: {filled} cells filled")
        return ctx
