"""站点配置：采集与独立清洗共用同一套词根及输出目录。"""

from dataclasses import dataclass
from pathlib import Path


# 直接点 hotwords_fashion.py / clean_fashion.py 的 main 时，只需修改这里。
# 可选值："de"（德国站）、"fr"（法国站）。命令行 --country 可临时覆盖。
DEFAULT_COUNTRY = "de"

BASE_DIR = Path(__file__).resolve().parent
SUPPORTED_COUNTRIES = ("de", "fr")


@dataclass(frozen=True)
class SiteConfig:
    country: str
    categories: Path
    attributes: Path
    excludes: Path
    brands: Path
    raw_dir: Path
    result_dir: Path


def site_config(country: str) -> SiteConfig:
    if country not in SUPPORTED_COUNTRIES:
        raise ValueError(f"不支持站点 {country!r}，请选择 {', '.join(SUPPORTED_COUNTRIES)}")
    rules = BASE_DIR / country
    return SiteConfig(
        country=country,
        categories=rules / "fashion_categories.txt",
        attributes=rules / "fashion_attributes.txt",
        excludes=rules / "fashion_excludes.txt",
        brands=rules / "fashion_brands.txt",
        raw_dir=BASE_DIR / "raw" / country,
        result_dir=BASE_DIR / "result" / country,
    )


def available_path(directory: Path, prefix: str, date_str: str) -> Path:
    """同日多次执行时不覆盖已有结果。"""
    directory.mkdir(parents=True, exist_ok=True)
    first = directory / f"{prefix}_{date_str}.txt"
    if not first.exists():
        return first
    from datetime import datetime

    return directory / f"{prefix}_{date_str}_{datetime.now():%H%M%S_%f}.txt"
