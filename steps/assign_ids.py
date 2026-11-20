"""Generate product IDs for the configured marketplace."""

import secrets
import string
from datetime import date

from core import PipelineContext, PipelineStep

_UPPER_ALNUM = string.digits + string.ascii_uppercase
_BASE62 = _UPPER_ALNUM + string.ascii_lowercase

# digit → letter mapping: 0→z, 1→a, 2→b, ..., 9→i
_DIGIT_MAP = dict(zip("0123456789", "zabcdefghi"))


def _date_code(yymmdd: str | None = None) -> str:
    """Generate 6-char date code. Uses yymmdd if given, else today."""
    if yymmdd:
        raw = yymmdd
    else:
        today = date.today()
        raw = f"{today.year % 100:02d}{today.month:02d}{today.day:02d}"
    return "".join(_DIGIT_MAP[d] for d in raw)


def anch_id_factory(yymmdd: str | None = None) -> str:
    """Build an ID in the shared Anch format."""
    prefix = "".join(secrets.choice(_BASE62) for _ in range(6))
    middle = _date_code(yymmdd)
    suffix = "".join(secrets.choice(_BASE62) for _ in range(4))
    return f"Anch{prefix}{middle}{suffix}"


def de_id_factory(yymmdd: str | None = None) -> str:
    return anch_id_factory(yymmdd)


def fr_id_factory(yymmdd: str | None = None) -> str:
    return anch_id_factory(yymmdd)

def uk_id_factory(yymmdd: str | None = None) -> str:
    """Build a hyphenated Anch ID with uppercase date and random segments."""
    prefix = "".join(secrets.choice(_UPPER_ALNUM) for _ in range(4))
    middle = _date_code(yymmdd).upper()
    suffix = "".join(secrets.choice(_UPPER_ALNUM) for _ in range(3))
    return f"Anch-{prefix}-{middle}-{suffix}"


_SITE_ID_FACTORIES = {
    "de": de_id_factory,
    "fr": fr_id_factory,
    "uk": uk_id_factory,
}


class AssignIdsStep(PipelineStep):
    name = "assign_ids"
    description = "Column B: fill with random IDs (middle = date code)"
    requires = ("insert_columns",)

    def run(self, ctx: PipelineContext) -> PipelineContext:
        cfg = self.config
        ws = ctx.worksheet
        override = cfg.date_override.strip() or None
        factory = _SITE_ID_FACTORIES.get(cfg.mapping_country.lower(), anch_id_factory)
        count = 0
        for r in range(1, ws.max_row + 1):
            ws.cell(row=r, column=cfg.col_b).value = factory(override)
            count += 1
        ctx.log(f"Column {cfg.col_b}: {count} IDs generated")
        return ctx
