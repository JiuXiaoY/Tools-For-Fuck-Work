"""Fill column J (10) from column I (9) via color mapping table."""

from core import PipelineContext, PipelineStep
from services import is_blank, cell_has_fill
from services.unmapped import record_unmapped


class MapColorsStep(PipelineStep):
    name = "map_colors"
    description = "Column J: lookup from color mapping table based on column I"
    requires = ("insert_columns",)

    def run(self, ctx: PipelineContext) -> PipelineContext:
        cfg = self.config
        ws = ctx.worksheet
        mapping = cfg.load_color_mapping()
        if not mapping:
            ctx.log(f"{cfg.color_mapping_path.name} is empty, skipping column 10 fill")
            return ctx

        # Build case-insensitive mapping (lowercase keys)
        ci_mapping: dict[str, str] = {k.lower(): v for k, v in mapping.items()}
        filled = 0
        skipped = 0
        unmapped = 0
        for r in range(1, ws.max_row + 1):
            if cell_has_fill(ws.cell(row=r, column=cfg.col_a)):
                skipped += 1
                continue
            val = ws.cell(row=r, column=cfg.col_i).value
            if is_blank(val):
                continue
            key = str(val).strip().lower()
            if key in ci_mapping:
                ws.cell(row=r, column=cfg.col_j).value = ci_mapping[key]
                filled += 1
            else:
                unmapped += 1
                record_unmapped("color", str(val).strip(), cfg.color_mapping_path, source="map_colors")
        ctx.log(f"Column {cfg.col_j}: {filled} cells mapped, {skipped} rows skipped (col A has fill), {unmapped} no match (recorded)")
        return ctx
