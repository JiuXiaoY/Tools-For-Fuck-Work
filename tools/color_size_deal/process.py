"""Process check_.txt: prefix duplicates per group, then strip size column.

Input:  tools/color_size_deal/check_.txt
Output: tools/color_size_deal/check_.txt (in-place)

Logic (per group):
  - Group = consecutive data lines, separated by whitespace-only lines
  - Each data line = "颜色\t尺码"
  - 1st occurrence of a unique line → keep only color
  - Nth occurrence (N>1) → "{N-1:02d} {color}"
  - Separator lines preserved as-is in output
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from services.logger import get_logger

BASE = Path(__file__).resolve().parent
SRC = BASE / "check_.txt"
_log = get_logger("color_size_deal")


def is_separator(line: str) -> bool:
    """A line is a separator if it's whitespace-only (includes bare \t)."""
    return line.strip() == ""


def process_group(group: list[str]) -> list[str]:
    """Add occurrence prefix, strip size."""
    seen: dict[str, int] = {}
    result: list[str] = []
    for line in group:
        seen[line] = seen.get(line, 0) + 1
        n = seen[line]
        color = line.split("\t")[0]
        if n == 1:
            result.append(color)
        else:
            result.append(f"{n - 1:02d} {color}")
    return result


def main() -> None:
    if not SRC.exists():
        _log.error("File not found: %s", SRC)
        return

    lines = SRC.read_text(encoding="utf-8").split("\n")

    # Walk line by line, preserving separators
    out_lines: list[str] = []
    current_group: list[str] = []
    total_groups = 0

    for line in lines:
        if is_separator(line):
            if current_group:
                out_lines.extend(process_group(current_group))
                current_group = []
                total_groups += 1
            out_lines.append(line)  # keep separator
        else:
            current_group.append(line)

    # Trailing group (no separator after last group)
    if current_group:
        out_lines.extend(process_group(current_group))
        total_groups += 1

    SRC.write_text("\n".join(out_lines), encoding="utf-8")

    # Stats
    total = sum(1 for l in out_lines if not is_separator(l))
    pfx = Counter()
    for line in out_lines:
        if len(line) >= 2 and line[:2].isdigit() and " " in line:
            pfx[line.split()[0]] += 1

    _log.info("Groups: %d, lines: %d (file: %d)", total_groups, total, len(out_lines))
    _log.info("Prefixes: %s", dict(sorted(pfx.items())) if pfx else "none")
    _log.info("Done.")


if __name__ == "__main__":
    main()
