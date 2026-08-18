"""Step registry — the ordered list of pipeline steps."""

from steps.merge_sheets       import MergeSheetsStep
from steps.validate           import ValidateStep
from steps.insert_columns     import InsertColumnsStep
from steps.assign_ids       import AssignIdsStep
from steps.cascade_identifier import CascadeIdentifierStep
from steps.map_colors import MapColorsStep
from steps.size_mapping       import SizeMappingStep
from steps.copy_mirror        import CopyMirrorStep
from steps.mirror_category    import MirrorCategoryStep
from steps.calc_price         import CalcPriceStep
from steps.format_cells       import FormatCellsStep
from steps.finalize           import FinalizeStep

from core import PipelineStep
from config import Config


def get_steps(config: Config | None = None) -> list[PipelineStep]:
    return [
        MergeSheetsStep(config),
        ValidateStep(config),
        InsertColumnsStep(config),
        AssignIdsStep(config),
        CascadeIdentifierStep(config),
        MapColorsStep(config),
        SizeMappingStep(config),
        CopyMirrorStep(config),
        MirrorCategoryStep(config),
        CalcPriceStep(config),
        FormatCellsStep(config),
        FinalizeStep(config),
    ]
