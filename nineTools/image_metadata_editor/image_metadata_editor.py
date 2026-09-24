# -*- coding: utf-8 -*-
"""给指定目录第一层的所有 JPG 写入 Windows 标记和备注。"""

import os
import sys
import tempfile
from pathlib import Path

from PIL import Image


CONTENT = "contains-synthetic-performer"
PROJECT_DIR = Path(__file__).resolve().parents[2]
# 只需修改这一行；相对于 dealExcel_refactoring 项目根目录。
TARGET_DIR = PROJECT_DIR / "nineTools/A_Plus/erusika_fr_20260924/generated_fr_20260924_v3"
XP_COMMENT = 0x9C9C
XP_KEYWORDS = 0x9C9E


def replace_jpeg_exif(data, exif_data):
    segment = b"\xff\xe1" + (len(exif_data) + 2).to_bytes(2, "big") + exif_data
    position = 2
    insert_at = 2
    old_exif = None
    while position < len(data):
        start = position
        while position < len(data) and data[position] == 0xFF:
            position += 1
        marker = data[position]
        position += 1
        if marker in (0xDA, 0xD9):
            break
        length = int.from_bytes(data[position:position + 2], "big")
        end = position + length
        payload = data[position + 2:end]
        if marker == 0xE0 and insert_at == start:
            insert_at = end
        if marker == 0xE1 and payload.startswith(b"Exif\x00\x00") and old_exif is None:
            old_exif = (start, end)
        position = end
    if old_exif:
        start, end = old_exif
        return data[:start] + segment + data[end:]
    return data[:insert_at] + segment + data[insert_at:]


def write_metadata(path):
    with Image.open(path) as image:
        image_format = image.format
        exif = image.getexif()
    value = (CONTENT + "\x00").encode("utf-16-le")
    exif[XP_KEYWORDS] = value
    exif[XP_COMMENT] = value

    original = path.read_bytes()
    if image_format != "JPEG":
        raise ValueError("不支持的实际图片格式：%s" % image_format)
    updated = replace_jpeg_exif(original, exif.tobytes())

    handle, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as temp_file:
            temp_file.write(updated)
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not TARGET_DIR.is_dir():
        print("目标目录不存在：%s" % TARGET_DIR)
        return

    # iterdir 只读取指定目录第一层，不会进入子目录。
    images = sorted(
        path for path in TARGET_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".jpg"
    )
    if not images:
        print("当前目录没有 JPG 图片：%s" % TARGET_DIR)
        return

    success = 0
    for path in images:
        try:
            write_metadata(path)
            success += 1
            print("[OK] %s" % path.name)
        except Exception as exc:
            print("[ERROR] %s：%s" % (path.name, exc))
    print("完成：%d/%d，标记和备注：%s" % (success, len(images), CONTENT))


if __name__ == "__main__":
    main()
