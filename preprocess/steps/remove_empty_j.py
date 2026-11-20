"""Remove unmarked rows whose column J value is empty."""

from core import PipelineContext, PipelineStep
from preprocess.steps.rebuild import rebuild_sheet
from services import cell_has_fill, is_blank
from services.logger import get_logger

_log = get_logger("preprocess")


class RemoveEmptyJStep(PipelineStep):
    name = "remove_empty_j"
    description = "Remove unmarked rows where column J is empty"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        worksheet = ctx.worksheet
        to_delete = {
            row
            for row in range(1, worksheet.max_row + 1)
            if not cell_has_fill(worksheet.cell(row=row, column=1))
            and is_blank(worksheet.cell(row=row, column=10).value)
        }
        if to_delete:
            ctx.worksheet = rebuild_sheet(
                ctx.workbook,
                worksheet,
                lambda row: row not in to_delete,
            )
        removed = len(to_delete)
        _log.info("  [%s] Sheet [%s]: %d empty J-column rows removed", ctx.source_filename, ctx.worksheet.title, removed)
        ctx.metadata[f"preprocess.{self.name}.removed"] = removed
        return ctx
