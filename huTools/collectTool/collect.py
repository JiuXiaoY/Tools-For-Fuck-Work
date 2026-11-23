"""Collect AMZ123 keywords and clean fashion results using the local config.py."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import re
import time
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path
from runpy import run_path

import requests


HOME = Path(__file__).resolve().parent
OUTPUT = HOME / "output"
API_URL = "https://api.amz123.com/search/v1/hotwords/search"
TASKS = ("keywords", "fashion", "clean")
SORTS = ("new_rank", "fluctuation", "both")
FASHION_SITES = ("de", "fr", "uk")
GENDER_LABELS = {
    "de": ("herren", "damen", "other"),
    "fr": ("homme", "femme", "other"),
    "uk": ("men", "women", "other"),
}
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    task: str = "keywords"
    country: str = "fr"
    category: str = ""
    keyword: str | None = None
    input: Path | None = None
    out: Path | None = None
    sort: str | None = None
    attempts: int = 5
    timeout: float = 30
    interval: float = 2
    page_size: int = 200
    fluctuation_below: int | None = -90000
    rank_below: int | list[int] | None = 200000
    pages: int = 5
    min_gain: int | None = None
    limit: int = 0
    keep_attributes: bool = True
    use_excludes: bool = True
    plain: bool = False

    @property
    def sort_modes(self) -> tuple[str, ...]:
        mode = self.sort or ("new_rank" if self.keyword is not None else "fluctuation")
        return ("fluctuation", "new_rank") if mode == "both" else (mode,)


def load_settings() -> Settings:
    values = run_path(str(HOME / "config.py")).get("SETTINGS")
    if not isinstance(values, dict):
        raise ValueError("请在本目录 config.py 的 SETTINGS 中填写配置")
    unknown = values.keys() - {field.name for field in fields(Settings)}
    if unknown:
        raise ValueError(f"未知配置项：{', '.join(sorted(unknown))}")

    options = {key: value for key, value in values.items() if value not in (None, "")}
    for key in ("input", "out"):
        value = options.get(key)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f"{key} 必须是路径字符串")
            options[key] = (HOME / value).resolve() if value.strip() else None
    options.setdefault("min_gain", 1 if options.get("task") == "fashion" else None)
    for key in ("fluctuation_below", "rank_below", "min_gain"):
        if options.get(key) is False:
            options[key] = None
    country = options.get("country", "fr")
    if not isinstance(country, str) or not re.fullmatch(r"[a-zA-Z]{2}", country):
        raise ValueError("country 必须是两位站点代码，例如 de、fr、uk")
    options["country"] = country.lower()
    cfg = Settings(**options)
    validate(cfg)
    return cfg


def validate(cfg: Settings) -> None:
    if cfg.task not in TASKS:
        raise ValueError(f"task 支持 {', '.join(TASKS)}")
    if cfg.task != "keywords" and cfg.country not in FASHION_SITES:
        raise ValueError(f"服装热词任务支持 {', '.join(FASHION_SITES)}")
    if cfg.sort is not None and cfg.sort not in SORTS:
        raise ValueError(f"sort 支持 {', '.join(SORTS)}")
    if not isinstance(cfg.category, str) or (cfg.keyword is not None and not isinstance(cfg.keyword, str)):
        raise ValueError("category 和 keyword 必须是文本")
    if cfg.keyword is not None and (cfg.task != "keywords" or cfg.input is not None):
        raise ValueError("keyword 仅用于关键词单查，不能与 input 同时设置")
    if cfg.input is not None and cfg.task not in ("keywords", "clean"):
        raise ValueError("input 仅用于批量关键词采集或离线清洗")
    if cfg.out is not None and cfg.out.suffix.lower() != ".md":
        raise ValueError("out 必须使用 .md 扩展名")
    for key, minimum in (("attempts", 1), ("pages", 1), ("page_size", 1), ("limit", 0)):
        value = getattr(cfg, key)
        if type(value) is not int or value < minimum:
            raise ValueError(f"{key} 必须是大于等于 {minimum} 的整数")
    if type(cfg.timeout) not in (int, float) or not math.isfinite(cfg.timeout) or cfg.timeout <= 0:
        raise ValueError("timeout 必须是正数")
    if type(cfg.interval) not in (int, float) or not math.isfinite(cfg.interval) or cfg.interval < 0:
        raise ValueError("interval 必须是非负数")
    for key in ("min_gain", "fluctuation_below"):
        value = getattr(cfg, key)
        if value is not None and type(value) is not int:
            raise ValueError(f"{key} 必须是整数、False 或空字符串")
    for key in ("keep_attributes", "use_excludes", "plain"):
        if type(getattr(cfg, key)) is not bool:
            raise ValueError(f"{key} 必须是 true 或 false")
    ranks = cfg.rank_below
    if ranks is not None and type(ranks) is not int:
        if not isinstance(ranks, list) or len(ranks) != 2 or any(type(value) is not int for value in ranks):
            raise ValueError("rank_below 必须是整数、两项整数列表、False 或空字符串")


# AMZ123 requests


class RequestError(RuntimeError):
    """The service rejected the request or returned an invalid response."""


class SignatureError(RequestError):
    """The service rejected the request signature."""


REQUEST_FAILURES = (requests.RequestException, RequestError)


def number(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def payload(cfg: Settings, sort: str, page: int = 1, keyword: str | None = None) -> dict:
    body = {
        "word": keyword or "",
        "country": cfg.country,
        "ranking_this_week": [],
        "fluctuation_range": [],
        "word_len_range": [],
        "click_range": [],
        "conversion_range": [],
        "ne_word": "",
        "top3_brand": "",
        "top3_category": cfg.category,
        "page": {"size": cfg.page_size, "num": page, "sorts": [{"condition": sort, "order": 1}]},
    }
    if keyword is not None:
        body["fluctuation_use_abs"] = 1
    return body


def response_rows(response: requests.Response) -> list[dict]:
    response.raise_for_status()
    try:
        result = response.json()
    except ValueError as exc:
        raise RequestError("AMZ123 未返回有效 JSON") from exc
    if not isinstance(result, dict):
        raise RequestError("AMZ123 返回的顶层数据不是对象")
    status = result.get("status")
    if status == 107:
        raise SignatureError("AMZ123 签名验证失败（107）")
    if type(status) is not int or status != 0:
        raise RequestError(f"AMZ123 请求失败，业务状态 {status!r}")
    data = result.get("data")
    rows = data.get("rows") if isinstance(data, dict) else None
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise RequestError("AMZ123 返回的 data.rows 不是对象列表")
    return rows


def load_request_config(session: requests.Session, page_url: str, timeout: float) -> dict:
    response = session.get(page_url, timeout=timeout)
    response.raise_for_status()
    config = {}
    for key in ("projectId", "appId", "secretKey"):
        matches = re.findall(rf'(?<![A-Za-z0-9_])(?:"{key}"|{key})\s*:\s*("(?:\\.|[^"\\])*"|\d+)', response.text)
        if not matches:
            raise RequestError(f"AMZ123 网页请求配置缺少 {key}")
        try:
            config[key] = json.loads(matches[-1])
        except ValueError as exc:
            raise RequestError(f"AMZ123 网页请求配置中的 {key} 无效") from exc
    if any(not isinstance(config[key], str) or not config[key] for key in ("projectId", "secretKey")):
        raise RequestError("AMZ123 网页请求配置格式异常")
    return config


class HotwordClient:
    def __init__(self, session: requests.Session, cfg: Settings):
        self.session = session
        self.cfg = cfg
        self.page_url = f"https://www.amz123.com/{cfg.country}topkeywords"
        self.request_config: dict | None = None

    def fetch(self, sort: str, page: int = 1, *, keyword: str | None = None) -> list[dict]:
        if self.request_config is None:
            self.request_config = load_request_config(self.session, self.page_url, self.cfg.timeout)
        config = self.request_config
        query = payload(self.cfg, sort, page, keyword)
        body = json.dumps(query, ensure_ascii=False, separators=(",", ":"))
        timestamp = str(int(time.time()))
        signature = hashlib.md5(f"{body}_{timestamp}_{config['secretKey']}".encode("utf-8")).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "PROJECT-ID": config["projectId"],
            "APP-ID": str(config["appId"]),
            "T": timestamp,
            "S": signature,
            "Authorization": "",
            "Origin": "https://www.amz123.com",
            "Referer": self.page_url,
        }
        response = self.session.post(API_URL, data=body.encode("utf-8"), headers=headers, timeout=self.cfg.timeout)
        try:
            return response_rows(response)
        except SignatureError:
            self.request_config = None
            raise


def fetch_fashion(session: requests.Session, cfg: Settings) -> list[tuple[str, int]]:
    client = HotwordClient(session, cfg)
    gains: dict[str, tuple[str, int]] = {}
    for page in range(1, cfg.pages + 1):
        rows = client.fetch("fluctuation", page)
        log.info("第 %d/%d 页，收到 %d 条", page, cfg.pages, len(rows))
        for row in rows:
            word = str(row.get("word") or "").strip()
            if word:
                key = word.casefold()
                gain = -number(row.get("fluctuation"))
                if key not in gains or gain > gains[key][1]:
                    gains[key] = (word, gain)
        if len(rows) < cfg.page_size:
            break
        if page < cfg.pages:
            time.sleep(cfg.interval)
    return sorted(gains.values(), key=lambda item: item[1], reverse=True)


# Keyword and fashion rules


def drop_reordered(words: list[str]) -> list[str]:
    """Keep the first occurrence of two-word token sets."""
    seen = set()
    kept = []
    for word in words:
        tokens = frozenset(word.split())
        if len(tokens) == 2 and tokens in seen:
            continue
        seen.add(tokens)
        kept.append(word)
    return kept


def load_brands(country: str) -> list[str]:
    brands = []
    active = True
    for line in read_lines(HOME / "rules" / "brands.md"):
        if line.startswith("## "):
            sites = line[3:].lower().split()
            active = "common" in sites or country in sites
        elif active and not line.startswith("#"):
            brand = line.removeprefix("- ").strip().lower()
            if brand:
                brands.append(brand)
    return list(dict.fromkeys(brands))


def clean_with_report(words: list[str], country: str) -> tuple[list[str], list[str]]:
    brands = load_brands(country)
    patterns = [re.compile(rf"\b{re.escape(brand)}\b") for brand in brands]
    steps = (
        ("strip_whitespace", lambda items: [word.strip() for word in items]),
        ("normalize_case", lambda items: [word.lower() for word in items]),
        ("drop_single_word", lambda items: [word for word in items if " " in word]),
        ("drop_brands", lambda items: [word for word in items if not any(pattern.search(word) for pattern in patterns)]),
        ("drop_reordered", drop_reordered),
        ("deduplicate", lambda items: list(dict.fromkeys(items))),
    )
    report = []
    for name, step in steps:
        before = len(words)
        words = step(words)
        report.append(f"  {name}: {before} → {len(words)} ({before - len(words)} removed)")
    return words, report


def classify(words: list[str], country: str) -> dict[str, list[str]]:
    male, female, other = GENDER_LABELS.get(country, GENDER_LABELS["de"])
    buckets: dict[str, list[str]] = {male: [], female: [], other: []}
    patterns = (re.escape(male), re.escape(female))
    if country == "uk":
        patterns = (r"\bmens?\b", r"\b(?:womens?|ladies)\b")
    for word in words:
        for label, pattern in zip((male, female), patterns):
            if re.search(pattern, word):
                buckets[label].append(word)
                break
        else:
            buckets[other].append(word)
    return buckets


def strip_brands(word: str, brand_roots: list[str]) -> tuple[str, list[str]]:
    """从词中移除品牌/商标(token 级匹配),返回 (剩余部分, 移除的品牌列表)。

    - 品牌可能在词的开头/中间/结尾,可能是多个单词(如 helly hansen)。
    - 多词品牌按"词数多→少"优先匹配短语;单品牌按独立 token 匹配。
    - 大小写不敏感;输出保留原词其余 token 的大小写。
    """
    tokens = word.split()
    if not tokens:
        return word, []
    lower = [t.lower() for t in tokens]
    keep = [True] * len(tokens)
    removed: list[str] = []

    # 多词品牌:按 token 数降序,短语匹配
    multi = sorted((b for b in brand_roots if " " in b), key=lambda b: b.count(" "), reverse=True)
    for brand in multi:
        bt = brand.split()
        n = len(bt)
        for i in range(len(tokens) - n + 1):
            if keep[i] and lower[i : i + n] == bt:
                for j in range(i, i + n):
                    keep[j] = False
                removed.append(brand)

    # 单品牌:独立 token 匹配
    single = {b for b in brand_roots if " " not in b}
    for i, t in enumerate(lower):
        if keep[i] and t in single:
            keep[i] = False
            removed.append(tokens[i])

    # 去重(保序)
    seen: set[str] = set()
    removed_uniq = [b for b in removed if not (b in seen or seen.add(b))]
    stripped = " ".join(t for i, t in enumerate(tokens) if keep[i]).strip()
    return stripped, removed_uniq


def clean_pairs(
    pairs: list[tuple[str, int]],
    cat_roots: list[str],
    strong_attrs: list[str],
    weak_attrs: list[str],
    excl_roots: list[str],
    brand_roots: list[str],
    keep_attributes: bool,
    use_excludes: bool,
    *,
    whole_words: bool = False,
) -> tuple[list[tuple[str, int, str]], dict[str, int]]:
    """逐词判定,返回 (保留项[词,涨幅,备注], 统计)。

    流程: 黑名单 → 品牌移除(token 级,去任意位置/多词品牌) → 品类词根(必保留)
          → 强属性(可独立保留,开关控制) → 弱属性单独出现丢弃(防误报)。
    备注格式: 品类:jacke;属性:wasserdicht;去品牌:adidas
    """
    kept: list[tuple[str, int, str]] = []
    stats = {"cat": 0, "attr": 0, "excluded": 0, "irrelevant": 0}
    patterns = {}
    if whole_words:
        patterns = {
            root: re.compile(rf"\b{re.escape(root)}\b")
            for root in (*cat_roots, *strong_attrs, *weak_attrs, *excl_roots)
        }

    def matches(root: str, text: str) -> bool:
        return bool(patterns[root].search(text)) if whole_words else root in text

    for word, fluc in pairs:
        w = word.lower()

        # 1) 黑名单(明确非服装噪声)→ 丢弃
        if use_excludes and any(matches(root, w) for root in excl_roots):
            stats["excluded"] += 1
            continue

        # 2) 品牌移除:品牌可能在词的开头/中间/结尾,可能是多个单词
        stripped, brands = strip_brands(word, brand_roots)
        s = stripped.lower()
        if whole_words:
            s = s.replace("’", "'")
        brand_note = f"去品牌:{','.join(brands)}" if brands else ""

        # 3) 品类词根 → 必保留(强/弱属性作为备注补充)
        cats = [r for r in cat_roots if matches(r, s)]
        sattrs = [r for r in strong_attrs if matches(r, s)]
        if cats:
            note = "品类:" + ",".join(cats)
            attrs = sattrs + [r for r in weak_attrs if matches(r, s)]
            if attrs:
                note += ";属性:" + ",".join(attrs)
            if brand_note:
                note += ";" + brand_note
            kept.append((stripped, fluc, note))
            stats["cat"] += 1
            continue

        # 4) 强属性 → 可独立保留(开关控制);弱属性单独出现 → 丢弃(防误报)
        if keep_attributes and sattrs:
            note = "属性:" + ",".join(sattrs)
            if brand_note:
                note += ";" + brand_note
            kept.append((stripped, fluc, note))
            stats["attr"] += 1
            continue

        # 5) 未命中任何规则 → 丢弃
        stats["irrelevant"] += 1

    return kept, stats


# Input, output and task execution


def retry(action, cfg: Settings):
    for attempt in range(1, cfg.attempts + 1):
        try:
            return action()
        except REQUEST_FAILURES as exc:
            if attempt == cfg.attempts:
                raise
            log.warning("第 %d/%d 次请求失败，稍后重试：%s", attempt, cfg.attempts, exc)
            time.sleep(cfg.interval)


def read_lines(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def read_keywords(path: Path) -> list[str]:
    words = []
    linked_section = False
    for line in read_lines(path):
        if line.startswith("## "):
            linked_section = bool(re.match(r"##\s+link(?:\s|[(（]|$)", line, re.IGNORECASE))
        elif not linked_section and not line.startswith("#"):
            words.append(line.removeprefix("- ").strip())
    return list(dict.fromkeys(words))


def write_result(directory: Path, stem: str, lines: list[str], path: Path | None = None) -> Path:
    if path is None:
        path = directory / f"{stem}_{datetime.now():%Y%m%d_%H%M%S_%f}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write("\n".join(lines))
    log.info("已保存 %s", path)
    return path


def filtered_words(rows: list[dict], sort: str, cfg: Settings) -> list[str]:
    ranks = cfg.rank_below
    threshold = ranks[0 if len(rows) < 160 else 1] if isinstance(ranks, list) else ranks
    words = []
    for row in rows:
        word = str(row.get("word") or "").strip()
        if not word:
            continue
        if sort == "fluctuation":
            if cfg.fluctuation_below is None or number(row.get("fluctuation")) < cfg.fluctuation_below:
                words.append(f"{word} 【Hot】")
        elif threshold is None or len(rows) < 40 or number(row.get("new_rank")) < threshold:
            words.append(word)
    return words


def collect_keywords(cfg: Settings, site_dir: Path) -> int:
    if cfg.keyword is None:
        keywords = read_keywords(cfg.input or HOME / "keywords.md")
    else:
        keywords = ["" if cfg.keyword == "*" else cfg.keyword]
    if not keywords:
        raise ValueError("关键词文件中没有可采集的词")
    queries = [(keyword, sort) for keyword in keywords for sort in cfg.sort_modes]
    by_sort: dict[str, list[str]] = {sort: [] for sort in cfg.sort_modes}
    failed = 0
    with requests.Session() as session:
        client = HotwordClient(session, cfg)
        for index, (keyword, sort) in enumerate(queries, 1):
            log.info("[%d/%d] %s (%s)", index, len(queries), keyword or "全部热词", sort)
            try:
                rows = retry(lambda: client.fetch(sort, keyword=keyword), cfg)
                by_sort[sort].extend(filtered_words(rows, sort, cfg))
            except REQUEST_FAILURES as exc:
                failed += 1
                log.error("查询失败 %s (%s)：%s", keyword or "全部热词", sort, exc)
            if index < len(queries):
                time.sleep(cfg.interval)

    if failed == len(queries):
        return 1
    cleaned, report = clean_with_report([word for words in by_sort.values() for word in words], cfg.country)
    for line in report:
        log.info(line)
    lines = []
    for label, words in classify(cleaned, cfg.country).items():
        lines.extend([f"【{label}】", *words, ""])
    write_result(site_dir / "keywords", "hotwords", lines, cfg.out)
    if failed:
        log.warning("%d 项查询失败，已保存其余结果", failed)
    return int(bool(failed))


def load_fashion_rules(country: str) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    rule_dir = HOME / "rules" / country
    files = {part: rule_dir / f"{part}.md" for part in ("categories", "attributes", "excludes")}
    missing = [path.name for path in files.values() if not path.is_file()]
    if missing:
        raise ValueError(f"{country} 缺少服装词根文件：{', '.join(missing)}。可放入 {rule_dir}")
    roots = {
        part: [line.removeprefix("- ").strip().lower() for line in read_lines(path) if not line.startswith("#")]
        for part, path in files.items()
    }
    strong = [line[1:].strip() for line in roots["attributes"] if line.startswith("!") and line[1:].strip()]
    weak = [line for line in roots["attributes"] if not line.startswith("!")]
    return roots["categories"], strong, weak, roots["excludes"], load_brands(country)


def read_pairs(path: Path) -> list[tuple[str, int]]:
    pairs = []
    for line in read_lines(path):
        word, _, gain = line.partition("\t")
        if word.strip():
            pairs.append((word.strip(), number(gain.partition("\t")[0])))
    return pairs


def run_fashion(cfg: Settings, site_dir: Path) -> None:
    rules = load_fashion_rules(cfg.country)
    if cfg.task == "clean":
        if cfg.input is None:
            raise ValueError("离线清洗请在 config.py 的 input 指定待清洗文件")
        pairs = read_pairs(cfg.input)
        log.info("读取 %s，共 %d 条", cfg.input, len(pairs))
    else:
        with requests.Session() as session:
            pairs = retry(lambda: fetch_fashion(session, cfg), cfg)

    if not pairs:
        log.info("没有待处理的热词")
        return
    kept, stats = clean_pairs(
        pairs,
        *rules,
        keep_attributes=cfg.keep_attributes,
        use_excludes=cfg.use_excludes,
        whole_words=cfg.country == "uk",
    )
    kept.sort(key=lambda item: item[1], reverse=True)
    if cfg.min_gain is not None:
        kept = [item for item in kept if item[1] >= cfg.min_gain]
    if cfg.limit:
        kept = kept[:cfg.limit]
    lines = [word if cfg.plain else f"{word}\t{gain}\t{note}" for word, gain, note in kept]
    write_result(site_dir, "hotwords_fashion", lines, cfg.out)
    log.info("保留 %d/%d 条（品类命中 %d，属性命中 %d，黑名单 %d）", len(kept), len(pairs), stats["cat"], stats["attr"], stats["excluded"])


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="热词采集与离线清洗，请在同目录 config.py 设置任务").parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    try:
        cfg = load_settings()
        if cfg.out is not None and cfg.out.exists():
            raise FileExistsError(f"输出文件已存在：{cfg.out}")
        site_dir = OUTPUT / cfg.country
        log.info("任务 %s，站点 %s", cfg.task, cfg.country)
        if cfg.task == "keywords":
            return collect_keywords(cfg, site_dir)
        run_fashion(cfg, site_dir / "fashion")
    except (OSError, ValueError, *REQUEST_FAILURES) as exc:
        log.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
