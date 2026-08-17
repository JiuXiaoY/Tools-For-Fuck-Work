"""All configurable parameters in one place — edit and re-run."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from decimal import Decimal
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DelayConfig:
    request_interval: float = 2.0
    retry_pause: float = 3.0
    short_pause: float = 0.5
    ui_action: float = 1.0
    page_ready: float = 2.0
    upload_processing: float = 15.0
    response_start: float = 15.0
    between_items: float = 5.0
    image_retry: float = 1.0


@dataclass(frozen=True)
class DeepSeekSelectors:
    assistant_message: str = "div.ds-assistant-message-main-content"
    stop_button: str = "button:has-text('Stop')"
    ready_input: str = "textarea, [contenteditable]"
    new_chat: str = "text=New Chat"
    vision_mode: str = 'div[data-model-type="vision"][role="radio"]'
    file_input: str = 'input[type="file"]'
    prompt_input: str = "textarea"


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
    date_override: str = "260814"
    id_factory: Callable[[str | None], str] | None = None

    # ── price calculation ─────────────────────────────────────────────
    price_multiplier: str = "1.2"
    price_subtract:  str = "7.98"
    price_add:       str = "6.00"
    price_calculator: Callable[[Decimal], tuple[Decimal, Decimal, Decimal, Decimal]] | None = None

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

    # ── mapping (color/size) ───────────────────────────────────────────
    # 映射表国家码：de / fr / us ...，对应 data/color_mapping_{code}.json 与 data/size_mapping_{code}.json
    mapping_country: str = "fr"

    # ── AI ─────────────────────────────────────────────────────────────
    ai_provider: str = "deepseek"                              # deepseek / gemini
    ai_api_key: str = "sk-39b17cf2e6a542508090bb1c8d07570d"    # API key for title_optimize etc.
    ai_model: str = "deepseek-v4-pro"                          # model name
    # legacy (used by tools/ai_fill.py)
    gemini_api_key: str = ""                                   # Google Gemini API key
    gemini_model: str = "gemini-2.5-flash"                     # model name
    gemini_category: str = "女士上衣"                            # 女士上衣/男士上衣/女士裤子/男士裤子

    # ── hotwords ───────────────────────────────────────────────────────
    hotwords_country: str = "de"                           # 目标站点国家码(如 de/us),CLI --country 默认值
    hotwords_dual_mode: bool = True                        # True=双请求(fluctuation+new_rank), False=单请求
    hotwords_single_mode: str = "new_rank"                 # 单请求时用哪个: "new_rank" / "fluctuation"
    # fluctuation 模式过滤
    hotwords_fluc_enabled: bool = True                     # 是否启用 fluctuation 过滤
    hotwords_fluc_threshold: int = -60000                  # 保留 fluctuation < 此值的词
    # new_rank 模式过滤（按返回数量分档）
    hotwords_rank_enabled: bool = True                     # 是否启用 new_rank 过滤
    hotwords_rank_threshold_high: int = 200000              # 返回 160-200 条时，保留 new_rank < 此值
    hotwords_rank_threshold_mid: int = 200000              # 返回 40-160 条时，保留 new_rank < 此值

    # ── pipeline ──────────────────────────────────────────────────────
    delete_source_after_merge: bool = True                # 合并后是否删除 public/xls_xlsx 源文件
    pipeline_continue_on_error: bool = False              # 单步骤失败后是否继续执行后续步骤
    pipeline_checkpoint_every: int = 0                    # 每 N 步保存检查点；0 表示关闭

    # ── retry ─────────────────────────────────────────────────────────
    retry_max_rounds_deepseek: int = 5                     # DeepSeek 网页端重试轮数
    retry_max_rounds_hotwords: int = 5                     # 热词采集失败重试轮数
    delays: DelayConfig = field(default_factory=DelayConfig)
    deepseek_selectors: DeepSeekSelectors = field(default_factory=DeepSeekSelectors)

    # ── preprocess ────────────────────────────────────────────────────
    preprocess_dedup_max_gap: int = 100                    # 去重：同 SKU 有色行最大间距，超此值视为新组
    preprocess_dedup_close_gap: int = 10                    # 去重：两有色锚点行之间夹的行数 ≤ 此值时，删除锚点行及其间所有行
    preprocess_remove_empty_j: bool = False                 # 是否删除 J 列为空的普通数据行

    # ── image classification ──────────────────────────────────────────
    img_classify_mode: str = "ocr"                         # "ocr" / "opencv" / "heuristic" / "all"
    img_classify_ocr_lang: str = "eng+deu"                 # OCR 语言包
    img_classify_table_min_lines: int = 10                  # OpenCV 模式最少水平线数（>此值判定为尺码图）
    img_reorder_mode: str = "inline_dual"                  # "inline_dual" / "copy_single" / "move_dual"
    _color_mapping_cache: dict[str, str] | None = field(default=None, init=False, repr=False)
    _size_mapping_cache: dict[str, str] | None = field(default=None, init=False, repr=False)

    @property
    def color_mapping_path(self) -> Path:
        return Path(__file__).resolve().parent / "data" / f"color_mapping_{self.mapping_country}.json"

    def load_color_mapping(self) -> dict[str, str]:
        if self._color_mapping_cache is not None:
            return self._color_mapping_cache
        if not self.color_mapping_path.exists():
            self._color_mapping_cache = {}
        else:
            with self.color_mapping_path.open(encoding="utf-8") as f:
                self._color_mapping_cache = {
                    str(k): str(v) for k, v in json.load(f).items()
                }
        return self._color_mapping_cache

    @property
    def size_mapping_path(self) -> Path:
        return Path(__file__).resolve().parent / "data" / f"size_mapping_{self.mapping_country}.json"

    def load_size_mapping(self) -> dict[str, str]:
        if self._size_mapping_cache is not None:
            return self._size_mapping_cache
        if not self.size_mapping_path.exists():
            self._size_mapping_cache = {}
        else:
            with self.size_mapping_path.open(encoding="utf-8") as f:
                self._size_mapping_cache = {
                    str(k): str(v) for k, v in json.load(f).items()
                }
        return self._size_mapping_cache
