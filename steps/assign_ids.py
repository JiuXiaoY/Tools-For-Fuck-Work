"""Fill column B (2) with random 16-char IDs. Middle 6 digits encode date."""

import secrets
import string
from collections.abc import Callable
from datetime import date

from core import PipelineContext, PipelineStep
_BASE62 = string.digits + string.ascii_uppercase + string.ascii_lowercase

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


def _random_id(middle: str) -> str:
    prefix = "".join(secrets.choice(_BASE62) for _ in range(6))
    suffix = "".join(secrets.choice(_BASE62) for _ in range(4))
    return f"{prefix}{middle}{suffix}"


def default_id_factory(yymmdd: str | None = None) -> str:
    """Build one ID using the legacy base62/date-code format."""
    return _random_id(_date_code(yymmdd))

def anch_id_factory(yymmdd: str | None = None) -> str:
    # 生成原有的16位ID
    base_id = default_id_factory(yymmdd)  # 调用默认工厂
    return "Anch" + base_id  # 总长度20


# 可用的 ID 工厂注册表：字符串配置名 -> 回调
ID_FACTORIES: dict[str, Callable[[str | None], str]] = {
    "default_id_factory": default_id_factory,
    "anch_id_factory": anch_id_factory,
}


def resolve_id_factory(name: str | None) -> Callable[[str | None], str] | None:
    """按字符串名解析出 ID 工厂回调（config.id_factory 存的是字符串）。"""
    if not name:
        return None
    return ID_FACTORIES.get(name)


class AssignIdsStep(PipelineStep):
    name = "assign_ids"
    description = "Column B: fill with random IDs (middle = date code)"
    requires = ("insert_columns",)

    def run(self, ctx: PipelineContext) -> PipelineContext:
        cfg = self.config
        ws = ctx.worksheet
        override = cfg.date_override.strip() or None
        factory = resolve_id_factory(cfg.id_factory) or default_id_factory
        count = 0
        for r in range(1, ws.max_row + 1):
            ws.cell(row=r, column=cfg.col_b).value = factory(override)
            count += 1
        ctx.log(f"Column {cfg.col_b}: {count} IDs generated")
        return ctx
