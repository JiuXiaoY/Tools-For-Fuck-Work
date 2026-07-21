"""Step registry — the ordered list of pipeline steps."""

from steps.remove_header      import RemoveHeaderStep
from steps.merge_sheets       import MergeSheetsStep
from steps.validate           import ValidateStep
from steps.insert_columns     import InsertColumnsStep
from steps.fill_id            import FillIdStep
from steps.fill_col3          import FillCol3Step
from steps.fill_col10_mapping import FillCol10MappingStep
from steps.size_mapping       import SizeMappingStep
from steps.copy_mirror        import CopyMirrorStep
from steps.fill_col44         import FillCol44Step
from steps.calc_price         import CalcPriceStep
from steps.format_cells       import FormatCellsStep
from steps.finalize           import FinalizeStep

from core import PipelineStep


def get_steps() -> list[PipelineStep]:
    return [
        RemoveHeaderStep(),
        MergeSheetsStep(),
        ValidateStep(),
        InsertColumnsStep(),
        FillIdStep(),
        FillCol3Step(),
        FillCol10MappingStep(),
        SizeMappingStep(),
        CopyMirrorStep(),
        FillCol44Step(),
        CalcPriceStep(),
        FormatCellsStep(),
        FinalizeStep(),
    ]
