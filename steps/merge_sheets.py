"""Merge all sheets in a workbook into one, migrating images and styles."""

import re
from copy import copy as copy_style
from io import BytesIO

from openpyxl.drawing.image import Image
from openpyxl.drawing.spreadsheet_drawing import OneCellAnchor, TwoCellAnchor

from core import PipelineContext, PipelineStep
from services.images import ImageSnapshot

_DRAWING_RE = re.compile(r"^xl/drawings/drawing\d+\.xml$")


def _copy_style(src, dst) -> None:
    if not src.has_style:
        return
    for attr in ("font", "border", "fill", "number_format", "protection", "alignment"):
        setattr(dst, attr, copy_style(getattr(src, attr)))


class MergeSheetsStep(PipelineStep):
    name = "merge_sheets"
    description = "Merge all sheets into one, preserving images and styles"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        names = ctx.workbook.sheetnames
        if len(names) <= 1:
            ctx.log("Single sheet, nothing to merge")
            return ctx

        target = ctx.worksheet
        nxt = target.max_row + 1
        copied = 0
        merged_imgs: list[ImageSnapshot] = []

        for name in names:
            if name == target.title:
                continue
            src = ctx.workbook[name]
            rows = src.max_row
            if rows == 0:
                ctx.log(f"Sheet [{name}]: empty, skip")
                continue

            offset = nxt - 1

            for i, sr in enumerate(range(1, rows + 1)):
                tr = nxt + i
                for c in range(1, src.max_column + 1):
                    sc = src.cell(row=sr, column=c)
                    tc = target.cell(row=tr, column=c)
                    tc.value = sc.value
                    _copy_style(sc, tc)
                if src.row_dimensions[sr].height:
                    target.row_dimensions[tr].height = src.row_dimensions[sr].height

            copied += rows

            for img in src._images:
                a = img.anchor
                if not isinstance(a, (OneCellAnchor, TwoCellAnchor)):
                    continue
                s = ImageSnapshot(data=img._data(), width=img.width, height=img.height,
                                  from_col=a._from.col, from_row=a._from.row + offset,
                                  from_col_off=a._from.colOff, from_row_off=a._from.rowOff)
                if isinstance(a, OneCellAnchor) and a.ext is not None:
                    s.ext_cx, s.ext_cy = a.ext.cx, a.ext.cy
                if isinstance(a, TwoCellAnchor) and a.to is not None:
                    s.to_col, s.to_row = a.to.col, a.to.row + offset
                    s.to_col_off, s.to_row_off = a.to.colOff, a.to.rowOff
                merged_imgs.append(s)

            for mr in src.merged_cells.ranges:
                parts = str(mr).split(":")
                np = []
                for p in parts:
                    cl = p.rstrip("0123456789")
                    rn = int(p[len(cl):]) + offset
                    np.append(f"{cl}{rn}")
                try:
                    target.merge_cells(":".join(np))
                except Exception:
                    pass

            ctx.log(f"Sheet [{name}]: {rows} rows, {len(src._images)} images")
            nxt += rows

        for name in list(ctx.workbook.sheetnames):
            if name != target.title:
                del ctx.workbook[name]

        for s in merged_imgs:
            img = Image(BytesIO(s.data))
            img.width, img.height = s.width, s.height
            if s.to_col is not None and s.to_row is not None:
                a = TwoCellAnchor()
                a._from.col, a._from.row = s.from_col, s.from_row
                a._from.colOff, a._from.rowOff = s.from_col_off, s.from_row_off
                a.to.col, a.to.row = s.to_col, s.to_row
                a.to.colOff, a.to.rowOff = s.to_col_off or 0, s.to_row_off or 0
            else:
                a = OneCellAnchor()
                a._from.col, a._from.row = s.from_col, s.from_row
                a._from.colOff, a._from.rowOff = s.from_col_off, s.from_row_off
                if s.ext_cx and s.ext_cy:
                    a.ext.cx, a.ext.cy = s.ext_cx, s.ext_cy
            img.anchor = a
            target.add_image(img)

        assets = ctx.metadata.get("assets", {})
        if assets:
            filtered = {k: v for k, v in assets.items() if not _DRAWING_RE.match(k)}
            ctx.metadata["assets"] = filtered
            skipped = len(assets) - len(filtered)
            if skipped:
                ctx.log(f"Skipped {skipped} source drawing file(s)")

        ctx.worksheet = target
        ctx.log(f"Merged {len(names)} sheets -> 1, {copied} data rows, {len(merged_imgs)} images")
        return ctx
