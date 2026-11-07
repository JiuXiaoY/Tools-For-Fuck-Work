"""Collect Amazon DE/FR API suggestions; vocabulary files contain one phrase per line."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import runpy
import string
import sys
import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parent
LOCAL_TIME = timezone(timedelta(hours=8))
MARKETS = {
    "de": {"completion": "completion.amazon.de", "mid": "A1PA6795UKMFR9", "locale": "de-DE"},
    "fr": {"completion": "completion.amazon.fr", "mid": "A13V1IB3VIYZZH", "locale": "fr-FR"},
}


@dataclass
class Settings:
    markets: tuple[str, ...] = ("de", "fr")
    category: str = "aps"
    expand: str = "none"
    interval: float = 1.2
    timeout: float = 15
    retries: int = 2
    cache_hours: float = 24
    save_process_files: bool = False


@dataclass
class Query:
    market: str
    prefix: str
    seeds: list[str] = field(default_factory=list)


@dataclass
class Result:
    market: str
    category: str
    prefix: str
    collected_at: str
    source: str
    url: str
    suggestions: list[str]
    raw: str = ""


class SuggestionError(Exception):
    def __init__(self, message: str, *, retryable: bool = False,
                 rate_limited: bool = False, retry_after: float = 0):
        super().__init__(message)
        self.retryable = retryable
        self.rate_limited = rate_limited
        self.retry_after = retry_after


def now_text() -> str:
    return datetime.now(LOCAL_TIME).isoformat(timespec="seconds")


def require_txt(path: Path) -> Path:
    if path.suffix.lower() != ".txt":
        raise ValueError(f"输入文件必须为 .txt：{path}")
    return path


def read_config(path: Path) -> Settings:
    if path.suffix.lower() != ".py":
        raise ValueError(f"配置文件必须为 .py：{path}")
    try:
        values = runpy.run_path(str(path)).get("SETTINGS")
    except Exception as exc:
        raise ValueError(f"无法加载配置 {path}：{exc}") from exc
    if not isinstance(values, dict):
        raise ValueError("config.py 需要定义 SETTINGS 字典")
    unknown = set(values) - set(Settings.__dataclass_fields__)
    if unknown:
        raise ValueError("未知配置项：" + ", ".join(sorted(map(str,unknown))))
    settings = Settings(**values)
    if not isinstance(settings.markets, (list,tuple)) or not all(isinstance(m,str) for m in settings.markets):
        raise ValueError('markets 需要为站点列表，例如 ["de", "fr"]')
    settings.markets = tuple(dict.fromkeys(m.strip().lower() for m in settings.markets))
    validate_settings(settings)
    return settings


def validate_settings(settings: Settings) -> None:
    if not settings.markets or any(m not in MARKETS for m in settings.markets):
        raise ValueError("markets 只能填写 de、fr，例如 de,fr")
    if not isinstance(settings.expand,str) or settings.expand not in {"none", "letters", "letters-digits"}:
        raise ValueError("expand 只能填写 none、letters、letters-digits")
    if not isinstance(settings.category,str) or not settings.category or any(c.isspace() for c in settings.category):
        raise ValueError("category 必须为有效的搜索类别，全部类别填写 aps")
    for name in ("interval", "timeout", "cache_hours"):
        value = getattr(settings, name)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} 必须为有限的非负数")
    if settings.interval < 0.5:
        raise ValueError("interval 不得小于 0.5 秒")
    if settings.timeout <= 0:
        raise ValueError("timeout 必须大于 0")
    if type(settings.retries) is not int or not 0 <= settings.retries <= 5:
        raise ValueError("retries 必须在 0 到 5 之间")
    if type(settings.save_process_files) is not bool:
        raise ValueError("save_process_files 必须为 True 或 False")


def read_keywords(path: Path) -> list[str]:
    require_txt(path)
    words = []
    seen = set()
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        word = line.strip()
        if not word:
            continue
        if any(ord(c) < 32 for c in word):
            raise ValueError(f"{path.name} 第 {number} 行包含控制字符，请每行只填写一个词或词组")
        if word not in seen:
            seen.add(word)
            words.append(word)
    return words


def build_queries(market: str, seeds: list[str], expansion: str) -> list[Query]:
    """Generate query prefixes only; never manufacture output suggestions."""
    prefixes: dict[str, Query] = {}
    suffixes = [] if expansion == "none" else ["", *string.ascii_lowercase]
    if expansion == "letters-digits":
        suffixes.extend(string.digits)
    for seed in seeds:
        for prefix in [seed, *(seed + " " + s for s in suffixes)]:
            query = prefixes.setdefault(prefix, Query(market, prefix))
            if seed not in query.seeds:
                query.seeds.append(seed)
    return list(prefixes.values())


def parse_suggestions(body: str) -> list[str]:
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError) as exc:
        raise SuggestionError("接口未返回有效数据，可能是访问验证页或接口已变化") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("suggestions"), list):
        raise SuggestionError("接口响应结构不符：缺少 suggestions 列表")
    suggestions = []
    seen = set()
    for item in payload["suggestions"]:
        if not isinstance(item, dict):
            raise SuggestionError("接口响应结构不符：建议条目不是对象")
        if item.get("type", "KEYWORD") != "KEYWORD":
            continue
        value = item.get("value")
        if (not isinstance(value,str) or not value.strip() or any(ord(c)<32 for c in value)
                or len(value.splitlines()) != 1):
            raise SuggestionError("接口返回了无效的建议原文")
        if value not in seen:
            seen.add(value)
            suggestions.append(value)
    return suggestions


def api_url(query: Query, category: str) -> str:
    params = {"limit": "11", "prefix": query.prefix, "suggestion-type": "KEYWORD",
              "alias": category, "mid": MARKETS[query.market]["mid"]}
    return f"https://{MARKETS[query.market]['completion']}/api/2017/suggestions?{urlencode(params)}"


class RateLimiter:
    def __init__(self, interval: float):
        self.interval = interval
        self.last = float("-inf")

    def wait(self) -> None:
        delay = self.interval - (time.monotonic() - self.last)
        if delay > 0:
            time.sleep(delay)
        self.last = time.monotonic()


def retry_after_seconds(value: str | None) -> float:
    if not value:
        return 0
    try:
        seconds = float(value)
        return max(0, seconds) if math.isfinite(seconds) else 0
    except ValueError:
        try:
            return max(0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return 0


def request_api(query: Query, settings: Settings) -> Result:
    url = api_url(query, settings.category)
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json",
                                   "Accept-Language": MARKETS[query.market]["locale"]})
    try:
        with urlopen(request, timeout=settings.timeout) as response:
            data = response.read(2_000_001)
            if len(data) > 2_000_000:
                raise SuggestionError("接口响应过大，未保存为建议词")
            body = data.decode("utf-8-sig")
    except HTTPError as exc:
        raise SuggestionError(f"HTTP {exc.code}：亚马逊建议接口请求失败",
                              retryable=exc.code in {408, 429, 500, 502, 503, 504},
                              rate_limited=exc.code == 429,
                              retry_after=retry_after_seconds(exc.headers.get("Retry-After"))) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise SuggestionError(f"网络连接失败：{exc}", retryable=True) from exc
    except UnicodeError as exc:
        raise SuggestionError("接口响应不是有效的 UTF-8 文本") from exc
    return Result(query.market, settings.category, query.prefix, now_text(), "api", url,
                  parse_suggestions(body), body)


class Fetcher:
    def __init__(self, settings: Settings, log: Callable[[str], None]):
        self.settings = settings
        self.log = log
        self.limiter = RateLimiter(settings.interval)

    def fetch(self, query: Query) -> Result:
        last_error = None
        for attempt in range(self.settings.retries + 1):
            self.limiter.wait()
            try:
                return request_api(query, self.settings)
            except SuggestionError as exc:
                last_error = exc
                if not exc.retryable or attempt >= self.settings.retries:
                    break
                delay = max(2 ** attempt, exc.retry_after)
                if delay > 60:
                    self.log(f"[暂停重试] 服务端要求等待 {delay:.0f} 秒，请稍后续跑")
                    break
                self.log(f"[重试 {attempt+1}/{self.settings.retries}] {query.market.upper()} {query.prefix!r}，等待 {delay:g} 秒：{exc}")
                time.sleep(delay)
        raise last_error


def cache_path(root: Path, query: Query, category: str) -> Path:
    key = "\0".join((query.market, category, query.prefix))
    return root / query.market / (hashlib.sha256(key.encode("utf-8")).hexdigest() + ".json")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + f".writing_{os.getpid()}" + path.suffix)
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_json(path: Path, value) -> None:
    if path.suffix.lower() != ".json":
        raise ValueError(f"元数据文件必须为 .json：{path}")
    atomic_write(path,json.dumps(value,ensure_ascii=False,indent=2)+"\n")


def word_text(words: list[str]) -> str:
    if any(not isinstance(w,str) or not w.strip() or any(ord(c)<32 for c in w)
           or len(w.splitlines()) != 1 for w in words):
        raise ValueError("词表需要每行一个有效的词或词组")
    return "\n".join(words) + ("\n" if words else "")


def write_words(path: Path, words: list[str]) -> None:
    require_txt(path)
    atomic_write(path,word_text(words))


def save_cache(path: Path, result: Result) -> None:
    words = word_text(result.suggestions)
    metadata = {
        "version": 2, "market": result.market, "category": result.category,
        "prefix": result.prefix, "collected_at": result.collected_at,
        "source": result.source, "url": result.url,
        "suggestion_count": len(result.suggestions),
        "words_sha256": hashlib.sha256(words.encode("utf-8")).hexdigest(),
        "raw_response": result.raw,
    }
    # Commit metadata last. A partial update cannot be mistaken for a valid word cache.
    write_words(path.with_suffix(".txt"),result.suggestions)
    write_json(path,metadata)


def read_cache(path: Path, query: Query, settings: Settings) -> Result | None:
    if settings.cache_hours == 0:
        return None
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        if (metadata["version"] != 2 or metadata["market"] != query.market
                or metadata["category"] != settings.category or metadata["prefix"] != query.prefix
                or metadata["source"] != "api"):
            return None
        collected = datetime.fromisoformat(metadata["collected_at"])
        if collected.tzinfo is None:
            return None
        age = (datetime.now(LOCAL_TIME) - collected).total_seconds()
        if age < -60 or age > settings.cache_hours * 3600:
            return None
        count = metadata["suggestion_count"]
        data = path.with_suffix(".txt").read_bytes()
        if hashlib.sha256(data).hexdigest() != metadata["words_sha256"]:
            return None
        words = data.decode("utf-8").splitlines()
        if type(count) is not int or not 0 <= count <= 1000 or len(words) != count:
            return None
        word_text(words)
        raw = metadata["raw_response"]
        if not isinstance(raw,str) or (raw and parse_suggestions(raw) != words):
            return None
        return Result(query.market,settings.category,query.prefix,metadata["collected_at"],
                      "api",metadata["url"],words,raw)
    except (OSError, ValueError, KeyError, IndexError, TypeError, SuggestionError):
        return None


def export_results(directory: Path, queries: list[Query], results: dict[tuple[str, str], Result],
                   errors: dict[tuple[str, str], str], markets: tuple[str, ...], category: str,
                   *, save_process_files: bool = False) -> dict:
    summary = {}
    for market in markets:
        market_queries = [q for q in queries if q.market == market]
        words = []
        word_lines = {}
        details = []
        unfinished = []
        failures = []
        empty = 0
        successful = 0
        for query in market_queries:
            key = (market, query.prefix)
            result = results.get(key)
            if result is None:
                unfinished.append(query.prefix)
                failures.append({"seeds":query.seeds,"prefix":query.prefix,
                                 "reason":errors.get(key,"尚未执行"),
                                 "status":"failed" if key in errors else "pending"})
                continue
            successful += 1
            empty += not result.suggestions
            positions = []
            for position, word in enumerate(result.suggestions, 1):
                if word not in word_lines:
                    words.append(word)
                    word_lines[word] = len(words)
                positions.append({"rank":position,"word_line":word_lines[word]})
            details.append({"seeds":query.seeds,"prefix":query.prefix,
                            "collected_at":result.collected_at,"source":result.source,"url":result.url,
                            "suggestion_count":len(result.suggestions),"suggestions":positions})
        write_words(directory/f"{market}_suggestions.txt",words)
        if save_process_files:
            write_words(directory/f"{market}_unfinished.txt",unfinished)
            write_json(directory/f"{market}_details.json",{
                "market":market,"category":category,"word_file":f"{market}_suggestions.txt","queries":details})
            write_json(directory/f"{market}_failures.json",failures)
        summary[market] = {"planned": len(market_queries), "successful": successful,
                           "empty": empty, "failed": sum((market,q.prefix) in errors for q in market_queries),
                           "pending": len(market_queries)-successful,
                           "words": len(words)}
    if not save_process_files:
        return summary
    lines = ["# 采集汇总", "", "生成时间: " + now_text(), "", "搜索类别: " + category, "",
             "建议词来自亚马逊实际响应；出现顺序不是搜索量，也不能用于判断买家所在地。", ""]
    for market, counts in summary.items():
        lines.extend(["## " + market.upper(), "",
                      f"计划查询 {counts['planned']} 个，成功 {counts['successful']} 个，其中无建议 {counts['empty']} 个",
                      f"失败 {counts['failed']} 个，待完成 {counts['pending']} 个（包含失败），去重建议 {counts['words']} 条", ""])
    atomic_write(directory/"summary.md", "\n".join(lines))
    return summary


def run_collection(settings: Settings, queries: list[Query], output: Path, cache: Path,
                   log: Callable[[str], None], *, refresh: bool = False, max_queries: int = 0,
                   fetcher=None) -> int:
    results = {}
    errors = {}
    cached = 0
    for query in queries:
        result = None if refresh or not settings.save_process_files else read_cache(cache_path(cache,query,settings.category),query,settings)
        if result is not None:
            results[(query.market,query.prefix)] = result
            cached += 1
    log(f"[计划] 查询 {len(queries)} 个，使用有效缓存 {cached} 个，待请求 {len(queries)-cached} 个")
    fetcher = fetcher or Fetcher(settings,log)
    requested = 0
    interrupted = False
    paused_markets = set()
    try:
        for query in queries:
            key = (query.market,query.prefix)
            if key in results or query.market in paused_markets:
                continue
            if max_queries and requested >= max_queries:
                break
            requested += 1
            log(f"[采集 {requested}] {query.market.upper()} 前缀 {query.prefix!r}")
            try:
                result = fetcher.fetch(query)
                if settings.save_process_files:
                    save_cache(cache_path(cache,query,settings.category),result)
                results[key] = result
                log(f"[成功] {len(result.suggestions)} 条建议，来源 {result.source}")
            except SuggestionError as exc:
                errors[key] = str(exc).replace("\n"," ").replace("\r"," ")
                log(f"[失败] {query.market.upper()} {query.prefix!r}：{exc}")
                if exc.rate_limited:
                    paused_markets.add(query.market)
                    log(f"[暂停站点] {query.market.upper()} 受到频率限制，剩余前缀留待下次运行")
    except KeyboardInterrupt:
        interrupted = True
        log("[已中断] 正在导出已完成的结果")
    finally:
        summary = export_results(output,queries,results,errors,settings.markets,settings.category,
                                 save_process_files=settings.save_process_files)
        for market, counts in summary.items():
            log(f"[结果 {market.upper()}] 去重词 {counts['words']} 条，成功查询 {counts['successful']} 个，待完成 {counts['pending']} 个")
        log("[输出目录] " + str(output.resolve()))
    return 130 if interrupted else 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    parser = argparse.ArgumentParser(description="通过 API 抓取亚马逊德法站搜索建议，词表使用 .txt")
    parser.add_argument("--config", type=Path, default=BASE/"config.py", help="Python 配置文件")
    parser.add_argument("--market", nargs="+", choices=sorted(MARKETS), help="选择站点，例如 --market de fr")
    parser.add_argument("--input", type=Path, help="自定义关键词 .txt（须只选择一个站点）")
    parser.add_argument("--expand", choices=["none","letters","letters-digits"], help="扩展查询方式")
    parser.add_argument("--max-queries", type=int, default=0, help="本次最多请求多少个未缓存前缀，0=不限制")
    parser.add_argument("--refresh", action="store_true", help="忽略有效缓存，重新采集")
    parser.add_argument("--dry-run", action="store_true", help="只显示计划，不联网、不写输出")
    args = parser.parse_args(argv)
    try:
        settings = read_config(args.config.resolve())
        if args.market:
            settings.markets = tuple(dict.fromkeys(args.market))
        if args.expand:
            settings.expand = args.expand
        validate_settings(settings)
        if args.max_queries < 0:
            raise ValueError("--max-queries 不得小于 0")
        if args.input and len(settings.markets) != 1:
            raise ValueError("--input 需要使用 --market 指定单个站点")
        queries = []
        for market in settings.markets:
            path = args.input.resolve() if args.input else BASE/f"keywords_{market}.txt"
            seeds = read_keywords(path)
            if not seeds:
                raise ValueError(f"关键词文件为空：{path}")
            planned = build_queries(market,seeds,settings.expand)
            queries.extend(planned)
            print(f"[输入 {market.upper()}] {len(seeds)} 个关键词，{len(planned)} 个查询前缀：{path}")
        if args.dry_run:
            print(f"[计划] 共 {len(queries)} 个查询前缀；未联网，未写输出")
            return 0
        output = BASE/"outputs"/datetime.now(LOCAL_TIME).strftime("%Y%m%d_%H%M%S_%f")
        output.mkdir(parents=True)
        log_context = (output/"run.log").open("a",encoding="utf-8",buffering=1) if settings.save_process_files else nullcontext(None)
        with log_context as log_file:
            def log(message):
                print(message,flush=True)
                if log_file is not None:
                    log_file.write(now_text()+" "+message+"\n")
            return run_collection(settings,queries,output,BASE/"cache",log,
                                  refresh=args.refresh,max_queries=args.max_queries)
    except (OSError, ValueError) as exc:
        print(f"[错误] {exc}",file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
