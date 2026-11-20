"""Select the first worksheet for pipeline output."""

from core import PipelineContext, PipelineStep
from services.excel import keep_first_worksheet


class SelectFirstSheetStep(PipelineStep):
    name = "select_first_sheet"
    description = "Keep the first worksheet in tab order"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        skipped = len(ctx.workbook.sheetnames) - 1
        ctx.worksheet = keep_first_worksheet(ctx.workbook)
        ctx.log(f"Sheet [{ctx.worksheet.title}] selected; {skipped} other sheet(s) skipped")
        return ctx
