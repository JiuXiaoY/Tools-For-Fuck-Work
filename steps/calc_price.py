"""Calculate price columns AS-AT- AU- AV from column AR text."""

from decimal import Decimal

from core import PipelineContext, PipelineStep
from rules import extract_price_before_jpy
from services import is_blank, round_decimal


def _default_price_chain(base: Decimal, config) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return the legacy AS→AV calculation chain with rounded intermediates."""
    value_as = base
    value_at = Decimal(str(round_decimal(base * Decimal(config.price_multiplier))))
    value_au = Decimal(str(round_decimal(value_at - Decimal(config.price_subtract))))
    value_av = Decimal(str(round_decimal(value_au + Decimal(config.price_add))))
    return value_as, value_at, value_au, value_av


class CalcPriceStep(PipelineStep):
    name = "calc_price"
    description = "Columns AS-AV: price calculation chain"
    requires = ("mirror_category",)

    def run(self, ctx: PipelineContext) -> PipelineContext:
        cfg = self.config
        ws = ctx.worksheet
        calculator = cfg.price_calculator or (lambda value: _default_price_chain(value, cfg))
        filled = 0
        for r in range(1, ws.max_row + 1):
            text = ws.cell(row=r, column=cfg.col_ar).value
            if is_blank(text):
                continue
            base = extract_price_before_jpy(str(text))
            if base is None:
                continue

            v_as, v_at, v_au, v_av = (round_decimal(value) for value in calculator(base))

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
