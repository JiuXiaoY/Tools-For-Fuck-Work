"""Calculate price columns AS-AT- AU- AV from column AR text."""

from decimal import Decimal

from core import PipelineContext, PipelineStep
from config import Config
from rules import extract_price_before_jpy
from services import is_blank, round_decimal


class CalcPriceStep(PipelineStep):
    name = "calc_price"
    description = "Columns AS-AV: price calculation chain"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        cfg = Config()
        ws = ctx.worksheet
        filled = 0
        for r in range(1, ws.max_row + 1):
            text = ws.cell(row=r, column=cfg.col_ar).value
            if is_blank(text):
                continue
            base = extract_price_before_jpy(str(text))
            if base is None:
                continue

            v_as = round_decimal(base)
            v_at = round_decimal(base * Decimal(cfg.price_multiplier))
            v_au = round_decimal(Decimal(str(v_at)) - Decimal(cfg.price_subtract))
            v_av = round_decimal(Decimal(str(v_au)) + Decimal(cfg.price_add))

            ws.cell(row=r, column=cfg.col_as).value = v_as
            ws.cell(row=r, column=cfg.col_at).value = v_at
            ws.cell(row=r, column=cfg.col_au).value = v_au
            ws.cell(row=r, column=cfg.col_av).value = v_av
            filled += 1

        if filled:
            ctx.log(f"Columns {cfg.col_as}-{cfg.col_av}: {filled} rows calculated")
        else:
            ctx.log(f"No JPY-anchored prices found, price columns skipped")
        return ctx
