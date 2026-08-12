"""Word format detection for historical knowledge restore."""

from __future__ import annotations

from typing import Any

from knowledge.standard_word_restore import (
    FORMAT_ID as SYSTEM_STANDARD_WORD_V1,
    FormatDetectionResult,
    detect_system_standard_word_v1,
)


UNKNOWN_WORD_FORMAT = "UNKNOWN_WORD_FORMAT"


def detect_word_format(file: Any) -> FormatDetectionResult:
    """Detect known historical Word export formats."""

    detected = detect_system_standard_word_v1(file)
    if detected.format_id == SYSTEM_STANDARD_WORD_V1:
        return detected
    return detected
