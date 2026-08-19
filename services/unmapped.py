"""Record unmapped color/size values to data/to_be_completed.json.

Entries carry a `description` stating which mapping file they should be added to,
so a human can complete the mapping later. Duplicates (same kind + value) are
not appended twice.
"""

from __future__ import annotations

import json
from pathlib import Path

# project root = parent of services/
_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = _ROOT / "data" / "to_be_completed.json"

_KIND_LABEL = {
    "color": "颜色",
    "size": "尺码",
}


def record_unmapped(kind: str, value: str, target_path: Path, source: str = "") -> None:
    """Append one unmapped value to data/to_be_completed.json.

    Format (grouped by target file, values as a simple list):

        {
          "color": [
            {"target_file": "data\\color_mapping_fr.json", "value": ["xxx", "yyy"]}
          ],
          "size": [...]
        }

    kind:        "color" | "size"
    value:       the raw unmapped value read from the sheet
    target_path: mapping data file this value should be completed into
    source:      kept for API compatibility, not persisted
    """
    value = (value or "").strip()
    if not value:
        return

    try:
        target_rel = str(target_path.resolve().relative_to(_ROOT))
    except ValueError:  # path outside project root
        target_rel = str(target_path)

    data: dict = {}
    if OUT_PATH.exists():
        try:
            data = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    if not isinstance(data, dict):
        data = {}

    bucket = data.setdefault(kind, [])
    if not isinstance(bucket, list):
        bucket = []
        data[kind] = bucket

    # find the entry for this target file
    entry = next((e for e in bucket if e.get("target_file") == target_rel), None)
    if entry is None:
        entry = {"target_file": target_rel, "value": []}
        bucket.append(entry)
    elif not isinstance(entry.get("value"), list):
        entry["value"] = []

    # dedup by lower-cased value within the same target file
    seen = {str(v).strip().lower() for v in entry["value"]}
    if value.lower() in seen:
        return

    entry["value"].append(value)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
