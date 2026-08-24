# -*- coding: utf-8 -*-
"""
id_sorting —— 对 12 位 id 数据源按每位 ASCII 值排序，结果写回文件。

数据源: nineTools/id_sorting_data
    每行一个 id，预期全部为 12 位 ASCII 可见字符。
排序规则:
    - 12 位记录：按每一位字符的 ASCII 值（ord）升序比较：
      先比第 1 位，相同再比第 2 位，依次类推；
      也即把每条记录映射为「各位 ASCII 值」的序列后按序列升序排序。
    - 非 12 位记录：不参与主排序，追加到结果文件末尾，并在该行后面打上标签"异常"
      （格式 "<id>\t异常"）。
输出:    nineTools/id_sorting_result（每行一条，保持原有行结尾风格 CRLF）

用法:
    python id_sorting.py [数据源路径] [-o 输出路径]
默认:
    数据源 = nineTools/id_sorting_data
    输出   = nineTools/id_sorting_result
"""
import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_SRC = os.path.join(BASE_DIR, "id_sorting_data")
DEFAULT_DST = os.path.join(BASE_DIR, "id_sorting_result")


def ascii_key(item: str):
    """将一条记录映射为「各位字符的 ASCII 值」元组，作为排序键。"""
    return tuple(ord(ch) for ch in item)


def sort_ids(records):
    """按每位 ASCII 值升序排序。"""
    return sorted(records, key=ascii_key)


def read_records(path):
    """读取每行一条 id；去掉末尾换行符(\n / \r\n)，忽略空白行。"""
    with open(path, "r", encoding="utf-8", newline="") as f:
        return [line.rstrip("\r\n") for line in f if line.strip("\r\n")]


def write_records(path, records):
    """写出排序结果，使用 CRLF 行结尾（与数据源一致）。"""
    with open(path, "w", encoding="utf-8", newline="") as f:
        for r in records:
            f.write(r + "\r\n")


def build_output(normal_records, abnormal_records, width=12, tag="异常"):
    """组装最终输出行列表：正常记录在前（排序），异常记录追加在末尾并打标签。

    - normal_records : 长度 == width 的记录（按每位 ASCII 值升序）。
    - abnormal_records: 长度 != width 的记录，逐个追加到末尾，格式 "<id>\t<tag>"。
    """
    output = list(sort_ids(normal_records))
    output.extend(f"{record}\t{tag}" for record in abnormal_records)
    return output


def main():
    parser = argparse.ArgumentParser(
        description="对 12 位 id 数据按每位 ASCII 值排序，结果写入输出文件"
    )
    parser.add_argument("src", nargs="?", default=DEFAULT_SRC,
                        help="数据源文件路径（默认 id_sorting_data）")
    parser.add_argument("-o", "--output", default=DEFAULT_DST,
                        help="输出文件路径（默认 id_sorting_result）")
    args = parser.parse_args()

    if not os.path.exists(args.src):
        print(f"❌ 找不到数据源: {args.src}")
        sys.exit(1)

    records = read_records(args.src)
    if not records:
        print(f"⚠️ 数据源为空，未写出")
        sys.exit(2)

    # 分离正常(12位)与异常(非12位)
    normal = [r for r in records if len(r) == 12]
    abnormal = [r for r in records if len(r) != 12]

    output = build_output(normal, abnormal)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    write_records(args.output, output)

    after = "\n".join(output[:5])
    print(f"共处理 {len(records)} 条记录：正常 {len(normal)} 条，异常 {len(abnormal)} 条")
    print(f"正常记录已按每位 ASCII 值升序排序；异常记录已追加到末尾并打上标签")
    print(f"排序结果前 5 条:")
    print(after)
    print(f"结果已写入: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
