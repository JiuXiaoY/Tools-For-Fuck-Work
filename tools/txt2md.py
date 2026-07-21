"""Rename .txt to .md: public/txt_src/ → public/txt_md/"""

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / "public" / "txt_src"
DST = BASE / "public" / "txt_md"

def main():
    SRC.mkdir(parents=True, exist_ok=True)
    DST.mkdir(parents=True, exist_ok=True)
    files = sorted(SRC.glob("*.txt"))
    if not files:
        print(f"No .txt files in {SRC}")
        return
    for f in files:
        t = DST / f.with_suffix(".md").name
        f.rename(t)
        print(f"{f.name} → {t.name}")
    print(f"Done: {len(files)} file(s)")

if __name__ == "__main__":
    main()
