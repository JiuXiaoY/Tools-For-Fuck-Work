# ======================== 手动配置区 ========================
# 留空：自动读取本程序同目录下唯一的 xlsx/xlsm 文件。
# 也可以填写文件名，例如：INPUT_FILE = "Hemerocallis@.xlsm"
INPUT_FILE = ""

TARGET_SHEET = "Vorlage"
OUTPUT_DIR_NAME = "split_output"
OVERWRITE_OUTPUT = True

# 每个输出文件最多包含多少个完整分组。
MAX_GROUPS_PER_FILE = 1

# 每个输出文件最多包含多少条数据行（不计算黄色起始行之前的表头）。
# 单个分组本身超过此行数时，该分组仍会单独生成一个文件。
MAX_DATA_ROWS_PER_FILE = 200

# Excel 中纯黄色 #FFFF00 对应的颜色值。
YELLOW_COLOR = 65535
# ==========================================================


import gc
import re
import shutil
import sys
from pathlib import Path

try:
    import pythoncom
    import win32com.client
except ImportError as exc:
    raise SystemExit(
        "缺少 pywin32，请先运行：python -m pip install pywin32"
    ) from exc


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def find_source() -> Path:
    folder = Path(__file__).resolve().parent
    if INPUT_FILE.strip():
        source = Path(INPUT_FILE.strip())
        if not source.is_absolute():
            source = folder / source
        source = source.resolve()
    else:
        candidates = [
            path.resolve()
            for path in folder.iterdir()
            if path.is_file()
            and path.suffix.lower() in {".xlsx", ".xlsm"}
            and not path.name.startswith("~$")
        ]
        if len(candidates) != 1:
            raise RuntimeError(
                f"程序目录下应当只有一个 xlsx/xlsm，当前找到 {len(candidates)} 个。"
                "请在 INPUT_FILE 中指定源文件。"
            )
        source = candidates[0]

    if not source.is_file():
        raise FileNotFoundError(f"找不到源文件：{source}")
    return source


def safe_file_part(value: object, fallback: str) -> str:
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(value or ""))
    text = re.sub(r"\s+", "_", text.strip()).rstrip("._")
    return (text or fallback)[:80]


def validate_config() -> None:
    for name, value in (
        ("MAX_GROUPS_PER_FILE", MAX_GROUPS_PER_FILE),
        ("MAX_DATA_ROWS_PER_FILE", MAX_DATA_ROWS_PER_FILE),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} 必须填写大于 0 的整数，当前值：{value!r}")


def build_batches(
    groups: list[tuple[int, int, int, str]],
) -> list[list[tuple[int, int, int, str]]]:
    batches: list[list[tuple[int, int, int, str]]] = []
    current: list[tuple[int, int, int, str]] = []
    current_rows = 0

    for group in groups:
        _, start_row, end_row, _ = group
        group_rows = end_row - start_row + 1
        exceeds_group_limit = len(current) >= MAX_GROUPS_PER_FILE
        exceeds_row_limit = current_rows + group_rows > MAX_DATA_ROWS_PER_FILE

        if current and (exceeds_group_limit or exceeds_row_limit):
            batches.append(current)
            current = []
            current_rows = 0

        current.append(group)
        current_rows += group_rows

    if current:
        batches.append(current)
    return batches


def main() -> int:
    excel = None
    workbook = None
    sheet = None
    pythoncom.CoInitialize()

    try:
        validate_config()
        source = find_source()
        output_dir = source.parent / OUTPUT_DIR_NAME
        output_dir.mkdir(parents=True, exist_ok=True)

        # 直接由 Python 启动独立 Excel 实例，不再经过 PowerShell。
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.AskToUpdateLinks = False
        excel.EnableEvents = False
        excel.ScreenUpdating = False

        # 源文件只读打开一次，用 A 列黄色单元格确定各组边界。
        workbook = excel.Workbooks.Open(str(source), 0, True)
        sheet = workbook.Worksheets(TARGET_SHEET)
        used_range = sheet.UsedRange
        last_row = int(used_range.Row + used_range.Rows.Count - 1)
        del used_range

        starts: list[int] = []
        group_names: list[str] = []
        for row in range(1, last_row + 1):
            if int(sheet.Cells(row, 1).Interior.Color) == YELLOW_COLOR:
                starts.append(row)
                group_names.append(
                    safe_file_part(sheet.Cells(row, 1).Value, f"group_{len(starts):03d}")
                )

        if not starts:
            raise RuntimeError(f"在工作表 {TARGET_SHEET!r} 的 A 列没有找到黄色起始行。")

        groups = [
            (
                index + 1,
                start,
                starts[index + 1] - 1 if index + 1 < len(starts) else last_row,
                group_names[index],
            )
            for index, start in enumerate(starts)
        ]
        batches = build_batches(groups)
        first_data_row = starts[0]

        workbook.Close(False)
        sheet = None
        workbook = None

        for file_number, batch in enumerate(batches, start=1):
            first_group_number, start_row, _, _ = batch[0]
            last_group_number, _, end_row, _ = batch[-1]
            data_rows = end_row - start_row + 1
            output_file = output_dir / f"{source.stem}{file_number}{source.suffix}"

            if output_file.exists():
                if not OVERWRITE_OUTPUT:
                    raise FileExistsError(f"输出文件已存在：{output_file}")
                output_file.unlink()

            # 完整复制原文件，只在复制件中删除 Vorlage 的非本批次数据行。
            shutil.copy2(source, output_file)
            workbook = excel.Workbooks.Open(str(output_file), 0, False)
            sheet = workbook.Worksheets(TARGET_SHEET)

            # 从下往上删除，避免前面的原始行号发生变化。
            if end_row < last_row:
                sheet.Range(f"A{end_row + 1}:A{last_row}").EntireRow.Delete()
            if start_row > first_data_row:
                sheet.Range(f"A{first_data_row}:A{start_row - 1}").EntireRow.Delete()

            workbook.Save()
            workbook.Close(False)
            sheet = None
            workbook = None
            oversized = (
                "（单组超过行数上限，按规则独占文件）"
                if len(batch) == 1 and data_rows > MAX_DATA_ROWS_PER_FILE
                else ""
            )
            print(
                f"{file_number:03d}: 组 {first_group_number}-{last_group_number}，"
                f"{len(batch)} 组，{data_rows} 数据行{oversized} -> {output_file}"
            )

        print(f"\n完成，输出目录：{output_dir}")
        return 0
    except Exception as exc:
        print(f"\n错误：{exc}", file=sys.stderr)
        return 1
    finally:
        if workbook is not None:
            try:
                workbook.Close(False)
            except Exception:
                pass
        sheet = None
        workbook = None

        if excel is not None:
            try:
                excel.Quit()
            except Exception:
                pass
        excel = None
        gc.collect()
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    raise SystemExit(main())
