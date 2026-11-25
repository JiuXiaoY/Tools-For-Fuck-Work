"""Verify the split image archive and restore its original files under A_Plus."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryFile
from zipfile import BadZipFile, ZipFile


ARCHIVE = Path(__file__).resolve().parent
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def restore(destination: Path, *, check_only: bool) -> int:
    manifest = json.loads((ARCHIVE / "manifest.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256()
    with TemporaryFile() as stream:
        for number in range(1, manifest["parts"] + 1):
            part = (ARCHIVE / f"images_{number:04d}.part").read_bytes()
            stream.write(part)
            digest.update(part)
        if digest.hexdigest() != manifest["sha256"]:
            raise ValueError("图片归档校验失败")

        stream.seek(0)
        with ZipFile(stream) as archive:
            entries = archive.infolist()
            if len(entries) != manifest["images"]:
                raise ValueError("归档图片数量与清单不符")
            for entry in entries:
                target = (destination / entry.filename).resolve()
                if not target.is_relative_to(destination) or target.suffix.lower() not in IMAGE_SUFFIXES:
                    raise ValueError(f"无效的图片路径：{entry.filename}")
                data = archive.read(entry)
                if check_only:
                    continue
                if target.exists():
                    if target.read_bytes() != data:
                        raise FileExistsError(f"本地文件与归档内容不同：{target}")
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = NamedTemporaryFile(dir=target.parent, delete=False)
                try:
                    with temporary:
                        temporary.write(data)
                    os.replace(temporary.name, target)
                finally:
                    Path(temporary.name).unlink(missing_ok=True)
        return len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验或还原 A+ 图片归档")
    parser.add_argument("--dest", type=Path, default=ARCHIVE.parent, help="还原目录，默认是 A_Plus")
    parser.add_argument("--check", action="store_true", help="只校验归档")
    args = parser.parse_args()
    try:
        count = restore(args.dest.resolve(), check_only=args.check)
    except (BadZipFile, OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"{'已校验' if args.check else '已还原'} {count} 张图片")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
