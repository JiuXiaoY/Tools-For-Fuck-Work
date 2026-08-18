"""Remove header rows when the first cell is not filled."""

from core import PipelineContext, PipelineStep
from preprocess.steps.rebuild import rebuild_sheet
from services import cell_has_fill
from services.logger import get_logger

_log = get_logger("preprocess")


class RemoveHeaderPreStep(PipelineStep):
    name = "remove_header"
    description = "Remove a non-marker first row from each sheet"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        workbook = ctx.workbook
        path = ctx.source_filename
        removed = 0
        for name in list(workbook.sheetnames):
            worksheet = workbook[name]
            if worksheet.max_row == 0:
                continue
            if cell_has_fill(worksheet.cell(row=1, column=1)):
                _log.info("  [%s] Sheet [%s]: row 1 has fill, skip", path, name)
                continue
            rebuild_sheet(
                workbook,
                worksheet,
                lambda row: row != 1,
            )
            removed += 1
            _log.info("  [%s] Sheet [%s]: header row removed", path, name)

        if removed == 0:
            _log.info("  [%s] All sheets: row 1 has fill, nothing to remove", path)
        ctx.metadata[f"preprocess.{self.name}.removed"] = removed
        ctx.worksheet = workbook.active
        return ctx
