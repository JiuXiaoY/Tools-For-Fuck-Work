"""Fill column K (11) from size_mapping.json — modify in-place."""

from core import PipelineContext, PipelineStep
from config import Config
from services import is_blank, cell_has_fill


class SizeMappingStep(PipelineStep):
    name = "size_mapping"
    description = "Column K: in-place size lookup from size_mapping.json"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        cfg = Config()
        ws = ctx.worksheet
        mapping = cfg.load_size_mapping()
        if not mapping:
            ctx.log("Size mapping is empty, skipping column 11 fill")
            return ctx

        filled = 0
        cleared = 0
        skipped = 0
        for r in range(1, ws.max_row + 1):
            if cell_has_fill(ws.cell(row=r, column=cfg.col_a)):
                ws.cell(row=r, column=cfg.col_k).value = None
                cleared += 1
                continue
            val = ws.cell(row=r, column=cfg.col_k).value
            if is_blank(val):
                continue
            key = str(val).strip()
            if key in mapping:
                ws.cell(row=r, column=cfg.col_k).value = mapping[key]
                filled += 1
            else:
                skipped += 1
        ctx.log(f"Column {cfg.col_k}: {filled} mapped, {cleared} cleared (col A has fill), {skipped} no match")
        return ctx
