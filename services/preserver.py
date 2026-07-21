"""ZIP-level asset preservation: images, drawing XML, relationships."""

from __future__ import annotations

import re
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

_PREFIXES = ("xl/media/", "xl/richData/")
_EXACT    = ("xl/cellimages.xml", "xl/metadata.xml")


def extract_assets(path: Path) -> dict[str, bytes]:
    """Extract image/media assets from source xlsx."""
    assets: dict[str, bytes] = {}
    with zipfile.ZipFile(path, "r") as zf:
        for name in zf.namelist():
            if name == "[Content_Types].xml":
                assets["src::[Content_Types].xml"] = zf.read(name)
            if name.startswith(_PREFIXES) or name in _EXACT:
                assets[name] = zf.read(name)
    return assets


def _merge_ct(existing: bytes, source: bytes, valid_parts: set[str]) -> bytes:
    """Merge source Content_Types, only adding entries for parts that exist."""
    er = ET.fromstring(existing)
    sr = ET.fromstring(source)
    seen = {e.get("PartName") for e in er if e.tag.endswith("Override")}
    for e in sr:
        if not e.tag.endswith("Override"):
            continue
        pn = e.get("PartName")
        if pn and pn not in seen and pn.lstrip("/") in valid_parts:
            er.append(deepcopy(e))
    return ET.tostring(er, encoding="utf-8", xml_declaration=True)


def restore_assets(path: Path, assets: dict[str, bytes]) -> int:
    """Merge preserved media files into output xlsx.

    Only restores media/image files and Content_Types entries.
    Does NOT touch drawing XMLs or relationships — openpyxl handles those.
    """
    if not assets:
        return 0

    updates: dict[str, bytes] = {}
    for name, data in assets.items():
        if name.startswith(_PREFIXES) or name in _EXACT:
            updates[name] = data

    with zipfile.ZipFile(path, "r") as zf:
        merged = {n: zf.read(n) for n in zf.namelist()}
    merged.update(updates)

    # Merge Content_Types (only for parts that actually exist)
    if "[Content_Types].xml" in merged and "src::[Content_Types].xml" in assets:
        valid = {n for n in merged if not n.startswith("src::")}
        merged["[Content_Types].xml"] = _merge_ct(
            merged["[Content_Types].xml"],
            assets["src::[Content_Types].xml"],
            valid,
        )

    # Clean up src:: entries
    for name in list(merged):
        if name.startswith("src::"):
            del merged[name]

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in merged.items():
            zf.writestr(name, data)

    return len(updates)
