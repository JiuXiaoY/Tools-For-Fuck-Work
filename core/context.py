from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet


@dataclass
class PipelineContext:
    """Pipeline context passed between steps."""

    workbook: Workbook
    worksheet: Worksheet
    source_path: Path | None = None
    source_filename: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)

    def log(self, message: str) -> None:
        self.logs.append(message)
