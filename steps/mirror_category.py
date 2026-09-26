"""Copy the configured price text into the price-source column."""

from openpyxl.utils import get_column_letter

from core import PipelineContext, PipelineStep
from services import is_blank


class MirrorCategoryStep(PipelineStep):
    name = "mirror_category"
    description = "Copy price text into the price-source column"
    requires = ("insert_columns",)

    def run(self, ctx: PipelineContext) -> PipelineContext:
        cfg = self.config
        ws = ctx.worksheet
        filled = 0
        for r in range(1, ws.max_row + 1):
            val = ws.cell(row=r, column=cfg.price_text_col).value
            if not is_blank(val):
                ws.cell(row=r, column=cfg.price_source_col).value = val
                filled += 1
        source = get_column_letter(cfg.price_text_col)
        target = get_column_letter(cfg.price_source_col)
        ctx.log(f"Price source {source} -> {target}: {filled} cells copied")
        return ctx
