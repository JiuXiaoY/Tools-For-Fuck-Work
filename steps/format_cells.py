"""Format cells: row height, alignment, column widths, formulas."""

from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from core import PipelineContext, PipelineStep
from config import Config


class FormatCellsStep(PipelineStep):
    name = "format_cells"
    description = "Apply row height, alignment, column widths, formulas"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        cfg = Config()
        ws = ctx.worksheet

        # ── column widths ──
        for c in (1, 2, 3):
            ws.column_dimensions[get_column_letter(c)].width = cfg.col_width_1_3
        ws.column_dimensions[get_column_letter(4)].width = cfg.col_width_4
        ctx.log(f"Col 1-3 width={cfg.col_width_1_3}, col 4 width={cfg.col_width_4}")

        # ── row height + alignment ──
        col_d_letter = get_column_letter(4)
        col_e_letter = get_column_letter(5)
        n = 0
        for r in range(1, ws.max_row + 1):
            ws.row_dimensions[r].height = cfg.row_height
            for c in range(1, ws.max_column + 1):
                ws.cell(row=r, column=c).alignment = Alignment(
                    horizontal=cfg.cell_h_align, vertical=cfg.cell_v_align)
            # Formula: col 5 = LEN(col 4)
            if cfg.col_5_formula:
                ws.cell(row=r, column=5).value = f"=LEN({col_d_letter}{r})"
            n += 1

        ctx.log(f"Formatted {n} rows: h={cfg.row_height}, align={cfg.cell_h_align}/{cfg.cell_v_align}")
        if cfg.col_5_formula:
            ctx.log(f"Column 5: =LEN({col_d_letter}) formula applied")
        return ctx
