"""Rename .xls to .xlsx: public/xls_src/ → public/xls_xlsx/"""

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "public" / "xls_src"
DST = BASE / "public" / "xls_xlsx"

def main():
    SRC.mkdir(parents=True, exist_ok=True)
    DST.mkdir(parents=True, exist_ok=True)
    files = sorted(SRC.glob("*.xls"))
    if not files:
        print(f"No .xls files in {SRC}")
        return
    for f in files:
        t = DST / f.with_suffix(".xlsx").name
        f.rename(t)
        print(f"{f.name} → {t.name}")
    print(f"Done: {len(files)} file(s)")

if __name__ == "__main__":
    main()
