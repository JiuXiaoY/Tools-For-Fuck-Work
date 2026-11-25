# -*- coding: utf-8 -*-
"""把本目录中的五点描述 Markdown 转为无表头的 xlsx。

直接运行 main() 即可逐个处理本目录下所有 .md 文件，输出同名 .xlsx。
根据 Markdown 表头识别语言：
- 单语：每个产品一行，A~E 为对应语言第 1~5 点。
- 多语：按表头语言顺序分块，语言块之间空两行。

单个文件处理失败时，报告错误并继续处理其他文件。
"""

import argparse
import io
import os
import re
import sys
from tempfile import TemporaryDirectory

from openpyxl import Workbook
from openpyxl.utils.exceptions import IllegalCharacterError


BASE = os.path.dirname(os.path.abspath(__file__))
LANGUAGES = ("de", "fr", "en")
LANGUAGE_NAMES = {"de": "德语", "fr": "法语", "en": "英语"}
PRODUCT_RE = re.compile(r"^##\s*产品\s*(\S+)\s*$")
ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|")


def language_of(label):
    """从表头单元格中识别语言，不依赖文件名或目录名。"""
    value = label.strip().casefold()
    if "德语" in value or "deutsch" in value or "german" in value:
        return "de"
    if "法语" in value or "français" in value or "francais" in value or "french" in value:
        return "fr"
    if "英语" in value or "anglais" in value or "english" in value:
        return "en"
    if re.match(r"^de(?:\b|[_:/-])", value):
        return "de"
    if re.match(r"^fr(?:\b|[_:/-])", value):
        return "fr"
    if re.match(r"^en(?:\b|[_:/-])", value):
        return "en"
    raise ValueError("无法从表头 %r 判断语言" % label)


def header_languages(cells, line_no):
    """返回表头中正文列的语言顺序，例如 ('de', 'fr')。"""
    if len(cells) not in (3, 5):
        raise ValueError("第 %d 行表头应为 3 列或 5 列" % line_no)
    languages = tuple(language_of(cells[i]) for i in range(1, len(cells), 2))
    if len(set(languages)) != len(languages):
        raise ValueError("第 %d 行表头的语言列重复" % line_no)
    return languages


def parse_markdown(path):
    """返回 [(产品号, 德语五点或 None, 法语五点或 None, 英语五点或 None), ...]。"""
    with io.open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    products = []
    cur_no = None
    cur_points = {lang: {} for lang in LANGUAGES}
    cur_languages = None
    seen_numbers = set()

    def flush():
        if cur_no is None:
            return
        if cur_languages is None:
            raise ValueError("产品 %s 没有可识别的五点表头" % cur_no)
        missing = [i for i in range(1, 6)
                   if any(i not in cur_points[lang] for lang in cur_languages)]
        if missing:
            raise ValueError("产品 %s 缺少第 %s 点" % (cur_no, missing))
        products.append((cur_no,) + tuple(
            [cur_points[lang][i] for i in range(1, 6)] if lang in cur_languages else None
            for lang in LANGUAGES
        ))

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        head = PRODUCT_RE.match(stripped)
        if head:
            flush()
            cur_no = head.group(1)
            if cur_no in seen_numbers:
                raise ValueError("第 %d 行重复产品号 %s" % (line_no, cur_no))
            seen_numbers.add(cur_no)
            cur_points = {lang: {} for lang in LANGUAGES}
            cur_languages = None
            continue
        if cur_no is None or not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells[0] == "要点":
            languages = header_languages(cells, line_no)
            if cur_languages is not None and cur_languages != languages:
                raise ValueError("第 %d 行产品 %s 有不一致的语言表头" % (line_no, cur_no))
            cur_languages = languages
            continue
        if not ROW_RE.match(stripped):
            continue
        if cur_languages is None:
            raise ValueError("第 %d 行产品 %s 的要点前缺少语言表头" % (line_no, cur_no))
        if len(cells) != 1 + 2 * len(cur_languages):
            raise ValueError("第 %d 行产品 %s 的列数与表头不符" % (line_no, cur_no))
        i = int(cells[0])
        if not 1 <= i <= 5:
            raise ValueError("第 %d 行产品 %s 的要点编号 %d 不在 1~5 范围内" % (line_no, cur_no, i))
        for offset, lang in enumerate(cur_languages):
            point = cells[1 + 2 * offset]
            if not point:
                raise ValueError("产品 %s 第 %d 点存在空内容" % (cur_no, i))
            if i in cur_points[lang]:
                raise ValueError("第 %d 行产品 %s 的第 %d 点重复" % (line_no, cur_no, i))
            cur_points[lang][i] = point

    flush()
    if not products:
        raise ValueError("未从 %s 中解析到任何产品" % path)
    detect_mode(products)  # 提前拒绝同一文件内混用模式
    return products


def detect_mode(products):
    """由实际解析到的语言列决定输出模式。"""
    if not products:
        raise ValueError("没有可导出的产品")
    modes = set()
    for product in products:
        fields = product[1:]
        languages = tuple(lang for lang, points in zip(LANGUAGES, fields) if points is not None)
        if not languages:
            raise ValueError("产品缺少德语和法语五点")
        modes.add("&".join(languages))
    if len(modes) != 1:
        raise ValueError("同一文件混用了不同的语言模式")
    return modes.pop()


def write_xlsx(products, out_path):
    """单语每个产品一行；多语按语言分块，语言块之间空两行。"""
    mode = detect_mode(products)
    wb = Workbook()
    ws = wb.active
    ws.title = "fivepoints"

    n = len(products)
    mode_languages = mode.split("&")
    starts = {lang: 1 + block * (n + 2) for block, lang in enumerate(mode_languages)}
    for offset, product in enumerate(products):
        for lang, points in zip(LANGUAGES, product[1:]):
            if points is not None:
                for col, point in enumerate(points, start=1):
                    ws.cell(row=starts[lang] + offset, column=col).value = point

    with TemporaryDirectory(dir=os.path.dirname(os.path.abspath(out_path))) as staging_dir:
        staged_path = os.path.join(staging_dir, "fivepoints.xlsx")
        wb.save(staged_path)
        os.replace(staged_path, out_path)
    return n, starts


def find_inputs():
    """只扫描脚本所在目录，不递归，也不读取外部路径。"""
    return sorted(
        (entry.path for entry in os.scandir(BASE)
         if entry.is_file() and not entry.is_symlink() and entry.name.lower().endswith(".md")),
        key=lambda path: os.path.basename(path).casefold(),
    )


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="批量处理本目录的五点 Markdown，逐份输出同名的 xlsx"
    )
    parser.parse_args(argv)

    inputs = find_inputs()
    if not inputs:
        print("[ERROR] %s 中没有 .md 文件" % BASE)
        return 1

    failed = False
    written_outputs = set()
    for path in inputs:
        out_path = os.path.splitext(path)[0] + ".xlsx"
        out_key = os.path.normcase(out_path)
        if out_key in written_outputs:
            print("[ERROR] %s: 产出文件名 %s 与本批已生成的文件重名" % (path, out_path))
            failed = True
            continue
        try:
            products = parse_markdown(path)
            mode = detect_mode(products)
            n, block_starts = write_xlsx(products, out_path)
        except (OSError, ValueError, IllegalCharacterError) as exc:
            print("[ERROR] %s: %s" % (path, exc))
            failed = True
            continue

        written_outputs.add(out_key)
        print("输入: %s" % path)
        print("输出: %s" % out_path)
        print("模式: %s | 产品数: %d" % (mode, n))
        if len(block_starts) > 1:
            layout = []
            for lang in mode.split("&"):
                start = block_starts[lang]
                layout.append("%s第 %d~%d 行" % (LANGUAGE_NAMES[lang], start, start + n - 1))
            print("布局: %s（语言块之间空两行）" % "；".join(layout))
        else:
            lang = mode
            print("布局: %s 第 1~%d 行（每行 5 列，无表头）" % (LANGUAGE_NAMES[lang], n))
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
