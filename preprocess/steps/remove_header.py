"""Remove header rows when the first cell is not filled."""

from core import PipelineContext, PipelineStep
from preprocess.steps.rebuild import rebuild_sheet
from services import cell_has_fill
from services.logger import get_logger

_log = get_logger("preprocess")


class RemoveHeaderPreStep(PipelineStep):
    name = "remove_header"
    description = "Remove a non-marker first row from the selected worksheet"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        worksheet = ctx.worksheet
        path = ctx.source_filename
        removed = 0
        if cell_has_fill(worksheet.cell(row=1, column=1)):
            _log.info("  [%s] Sheet [%s]: row 1 has fill, skip", path, worksheet.title)
        elif worksheet.max_row > 0:
            ctx.worksheet = rebuild_sheet(
                ctx.workbook,
                worksheet,
                lambda row: row != 1,
            )
            removed = 1
            _log.info("  [%s] Sheet [%s]: header row removed", path, ctx.worksheet.title)
        ctx.metadata[f"preprocess.{self.name}.removed"] = removed
        return ctx
