"""Insert blank columns according to config."""

from core import PipelineContext, PipelineStep
from config import Config
from services import snapshot_images, restore_images


class InsertColumnsStep(PipelineStep):
    name = "insert_columns"
    description = "Insert blank columns to reach final column count"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        cfg = Config()
        ws = ctx.worksheet
        snaps = snapshot_images(ws)
        if snaps:
            ws._images.clear()
            ctx.log(f"Backed up {len(snaps)} images")

        for at, count in cfg.column_insertions:
            ws.insert_cols(at, count)
            ctx.log(f"Inserted {count} col(s) at position {at}")

        if snaps:
            restored = restore_images(ws, snaps, cfg)
            ctx.log(f"Restored {restored} images with adjusted anchors")

        ctx.metadata["final_cols"] = ws.max_column
        return ctx
