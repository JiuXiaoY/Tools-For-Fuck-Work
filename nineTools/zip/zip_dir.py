# -*- coding: utf-8 -*-
"""
zip_dir —— 把指定目录（默认 besskyproject/Means_of_production）整体压缩为 zip，
输出到 dealExcel_refactoring/zip_by_ec/{当天日期}_{操作用户}.zip。

用法:
    python zip_dir.py                          # 默认压缩 Means_of_production
    python zip_dir.py <源目录> [-o 输出.zip]   # 指定目录 / 指定输出
    python zip_dir.py --force                  # 同名 zip 已存在时覆盖
    python zip_dir.py --level 1                # 压缩级别 1~9（默认 6；大文件建议低级别提速）
"""

import argparse
import datetime
import getpass
import os
import sys
import time
import zipfile

BASE = os.path.dirname(os.path.abspath(__file__))


def _find_repo(start):
    """从脚本所在目录向上找含 zip_by_ec 的仓库根（脚本可放仓库内任意子目录）。"""
    d = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(d, "zip_by_ec")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise RuntimeError("未找到仓库根（缺少 zip_by_ec 目录）")
        d = parent


REPO = _find_repo(BASE)
BESSKY = os.path.dirname(REPO)
DEFAULT_SOURCE = os.path.join(BESSKY, "Means_of_production")
DEFAULT_OUT_DIR = os.path.join(REPO, "zip_by_ec")


def _stamp() -> str:
    date = datetime.date.today().strftime("%Y-%m-%d")
    try:
        user = getpass.getuser()
    except Exception:
        user = os.environ.get("USERNAME", "unknown")
    return f"{date}_{user}"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="压缩目录为 zip：zip_by_ec/{当天日期}_{操作用户}.zip"
    )
    parser.add_argument("source", nargs="?", default=DEFAULT_SOURCE,
                        help=f"要压缩的目录（默认 {DEFAULT_SOURCE}）")
    parser.add_argument("-o", "--output", default=None,
                        help="输出 zip 路径（默认 zip_by_ec/{日期}_{用户}.zip）")
    parser.add_argument("--force", action="store_true",
                        help="同名 zip 已存在时覆盖（默认拒绝，防误覆盖）")
    parser.add_argument("--level", type=int, default=6, choices=range(0, 10),
                        help="压缩级别 0~9（默认 6）")
    args = parser.parse_args()

    if not os.path.isdir(args.source):
        print(f"❌ 源目录不存在: {args.source}")
        sys.exit(1)

    out = args.output or os.path.join(DEFAULT_OUT_DIR, _stamp() + ".zip")
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    if os.path.exists(out) and not args.force:
        print(f"❌ 输出已存在（可用 --force 覆盖）: {out}")
        sys.exit(1)

    top = os.path.basename(os.path.normpath(args.source))  # zip 内顶层文件夹名
    t0 = time.time()
    n_files = 0
    n_skip = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=args.level) as zf:
        for dp, _, fn in os.walk(args.source):
            for f in fn:
                fp = os.path.join(dp, f)
                arc = os.path.join(top, os.path.relpath(fp, args.source))
                try:
                    zf.write(fp, arc)
                    n_files += 1
                except Exception as exc:  # noqa: BLE001 单文件失败不影响整体
                    print(f"⚠️ 跳过 {arc}: {exc}")
                    n_skip += 1
                if n_files % 200 == 0:
                    print(f"  已打包 {n_files} 个文件（{time.time() - t0:.0f}s）…")

    size_mb = os.path.getsize(out) / 1024 / 1024
    print(f"✅ 压缩完成: {out}")
    print(f"📊 文件 {n_files} 个（跳过 {n_skip}），耗时 {time.time() - t0:.0f}s，zip 大小 {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
