"""Deduplicate filled rows by column C value and configured distance."""

from core import PipelineContext, PipelineStep
from preprocess.steps.rebuild import rebuild_sheet
from services import cell_has_fill
from services.logger import get_logger

_log = get_logger("preprocess")


class DedupFilledRowsStep(PipelineStep):
    name = "dedup_filled_rows"
    description = "Remove close or duplicate filled rows using configured gaps"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        workbook = ctx.workbook
        worksheet = ctx.worksheet
        path = ctx.source_filename
        max_gap = self.config.preprocess_dedup_max_gap
        close_gap = self.config.preprocess_dedup_close_gap

        filled = [
            (row, worksheet.cell(row=row, column=3).value)
            for row in range(1, worksheet.max_row + 1)
            if cell_has_fill(worksheet.cell(row=row, column=1))
        ]
        if len(filled) < 2:
            _log.info("  [%s] Less than 2 filled rows, nothing to dedup", path)
            ctx.metadata[f"preprocess.{self.name}.removed"] = 0
            return ctx

        to_delete: set[int] = set()
        anchor_row, anchor_value = filled[0]
        for current_row, current_value in filled[1:]:
            between = current_row - anchor_row - 1
            if between <= close_gap:
                to_delete.update(range(anchor_row, current_row))
                anchor_row, anchor_value = current_row, current_value
            elif _same_value(anchor_value, current_value) and current_row - anchor_row <= max_gap:
                to_delete.add(current_row)
            else:
                anchor_row, anchor_value = current_row, current_value

        if not to_delete:
            _log.info("  [%s] No duplicate filled rows to remove", path)
            ctx.metadata[f"preprocess.{self.name}.removed"] = 0
            return ctx

        ctx.worksheet = rebuild_sheet(
            workbook,
            worksheet,
            lambda row: row not in to_delete,
        )
        removed = len(to_delete)
        ctx.metadata[f"preprocess.{self.name}.removed"] = removed
        _log.info("  [%s] Dedup: %d filled rows, %d deleted", path, len(filled), removed)
        return ctx


def _same_value(left: object, right: object) -> bool:
    if left is None or right is None:
        return left is right
    return str(left).strip() == str(right).strip()
