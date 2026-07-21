"""All configurable parameters in one place — edit and re-run."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """Typed configuration for the Excel processing pipeline."""

    # ── column layout ─────────────────────────────────────────────────
    initial_columns: int = 32
    final_columns: int = 48

    col_a:  int = 1
    col_b:  int = 2
    col_c:  int = 3
    col_i:  int = 9
    col_j:  int = 10
    col_k:  int = 11
    col_l:  int = 12
    col_m:  int = 13
    col_ar: int = 44
    col_as: int = 45
    col_at: int = 46
    col_au: int = 47
    col_av: int = 48

    # ── column insertions ─────────────────────────────────────────────
    # (insert-at-1based, count) executed in order
    column_insertions: list[tuple[int, int]] = field(default_factory=lambda: [
        (2, 5), (10, 1), (14, 10),
    ])

    # ── mirror column copy ────────────────────────────────────────────
    # {source_col: target_col}
    copy_targets: dict[int, int] = field(default_factory=lambda: {
        15: 26, 16: 28, 17: 30, 18: 32,
        19: 34, 20: 36, 21: 38, 22: 40, 23: 42,
    })

    # ── random ID ─────────────────────────────────────────────────────
    # Middle 6 digits: YYMMDD date code mapped 0→z,1→a,...,9→i
    # Set date_override to a specific date string (e.g. "260702") to fix the code;
    # leave empty to auto-use today''s date.
    date_override: str = "260731"

    # ── price calculation ─────────────────────────────────────────────
    price_multiplier: str = "1.2"
    price_subtract:  str = "7.98"
    price_add:       str = "1.50"

    # ── formatting ────────────────────────────────────────────────────
    row_height:    int    = 50
    cell_h_align:  str    = "left"
    cell_v_align:  str    = "center"
    col_width_1_3: float  = 17.75   # 第 1-3 列列宽
    col_width_4:   float  = 100.0   # 第 4 列列宽
    col_5_formula: bool   = True    # 第 5 列写入 =LEN(第4列) 公式

    # ── I/O ───────────────────────────────────────────────────────────
    src_dir:   Path = Path("public/xls_xlsx")
    out_dir:   Path = Path("outputs")

    # ── AI ─────────────────────────────────────────────────────────────
    ai_provider: str = "deepseek"                              # deepseek / gemini
    ai_api_key: str = ""    # API key for title_optimize etc.
    ai_model: str = "deepseek-v4-pro"                          # model name
    # legacy (used by tools/ai_fill.py)
    gemini_api_key: str = ""                                   # Google Gemini API key
    gemini_model: str = "gemini-2.5-flash"                     # model name
    gemini_category: str = "女士上衣"                            # 女士上衣/男士上衣/女士裤子/男士裤子

    # ── hotwords ───────────────────────────────────────────────────────
    hotwords_dual_mode: bool = True                        # True=双请求(fluctuation+new_rank), False=单请求
    hotwords_single_mode: str = "new_rank"                 # 单请求时用哪个: "new_rank" / "fluctuation"
    # fluctuation 模式过滤
    hotwords_fluc_enabled: bool = True                     # 是否启用 fluctuation 过滤
    hotwords_fluc_threshold: int = -90000                  # 保留 fluctuation < 此值的词
    # new_rank 模式过滤（按返回数量分档）
    hotwords_rank_enabled: bool = True                     # 是否启用 new_rank 过滤
    hotwords_rank_threshold_high: int = 20000              # 返回 160-200 条时，保留 new_rank < 此值
    hotwords_rank_threshold_mid: int = 200000              # 返回 40-160 条时，保留 new_rank < 此值

    # ── pipeline ──────────────────────────────────────────────────────
    delete_source_after_merge: bool = False                # 合并后是否删除 public/xls_xlsx 源文件

    # ── retry ─────────────────────────────────────────────────────────
    retry_max_rounds_deepseek: int = 5                     # DeepSeek 网页端重试轮数
    retry_max_rounds_hotwords: int = 5                     # 热词采集失败重试轮数

    @property
    def color_mapping_path(self) -> Path:
        return Path(__file__).resolve().parent / "data" / "color_mapping.json"

    def load_color_mapping(self) -> dict[str, str]:
        if not self.color_mapping_path.exists():
            return {}
        with self.color_mapping_path.open(encoding="utf-8") as f:
            return {str(k): str(v) for k, v in json.load(f).items()}

    @property
    def size_mapping_path(self) -> Path:
        return Path(__file__).resolve().parent / "data" / "size_mapping.json"

    def load_size_mapping(self) -> dict[str, str]:
        if not self.size_mapping_path.exists():
            return {}
        with self.size_mapping_path.open(encoding="utf-8") as f:
            return {str(k): str(v) for k, v in json.load(f).items()}
