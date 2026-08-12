from __future__ import annotations

import re
from dataclasses import replace

from facts.models import FactChunk


DEFAULT_FACTS_CHUNK_TARGET_CHARS = 4500
DEFAULT_FACTS_CHUNK_MAX_CHARS = 6000

FILE_HEADING_PATTERN = re.compile(r"^=+\s*文件[:：].*?=+$")
IMAGE_BLOCK_PATTERN = re.compile(r"^【内嵌图片\s+\d+/\d+[:：].*】")
NUMBERED_LINE_PATTERN = re.compile(
    r"^\s*(?:\d+[\.\u3001]|[一二三四五六七八九十]+[\u3001\.]|\([0-9一二三四五六七八九十]+\)|[-•●①②③④⑤⑥⑦⑧⑨])"
)
SENTENCE_BOUNDARY_PATTERN = re.compile(r"([。！？!?；;]\s*)")


def _normalize_newlines(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n")


def _is_heading(block: str) -> bool:
    lines = [
        line.strip()
        for line in block.splitlines()
        if line.strip()
    ]
    if not lines:
        return False
    if len(lines) > 2:
        return False
    first = lines[0]
    if FILE_HEADING_PATTERN.match(first):
        return True
    if first.startswith(("【", "#")):
        return True
    if len(first) <= 40 and not re.search(r"[。！？?!；;，,]", first):
        return True
    return False


def _is_image_block(block: str) -> bool:
    first = next(
        (
            line.strip()
            for line in block.splitlines()
            if line.strip()
        ),
        "",
    )
    return IMAGE_BLOCK_PATTERN.match(first) is not None


def _split_blocks(material: str) -> list[str]:
    text = _normalize_newlines(material).strip()
    if not text:
        return []
    return [
        block.strip()
        for block in re.split(r"\n\s*\n+", text)
        if block.strip()
    ]


def _append_with_spacing(parts: list[str], block: str) -> str:
    return "\n\n".join(parts + [block]) if parts else block


def _append_unit(parts: list[str], unit: str) -> str:
    return "\n".join(parts + [unit]) if parts else unit


def _build_context_header(headings: list[str]) -> str:
    clean = []
    for heading in headings[-3:]:
        value = heading.strip()
        if value and value not in clean:
            clean.append(value)
    if not clean:
        return ""
    return "【上下文，仅用于事实抽取，不作为独立事实】\n" + "\n".join(clean)


def _finalize_chunk(chunks: list[FactChunk], parts: list[str], headings: list[str], oversized=False) -> None:
    body = "\n\n".join(parts).strip()
    if not body:
        return
    header = _build_context_header(headings)
    text = f"{header}\n\n{body}" if header else body
    chunks.append(
        FactChunk(
            chunk_index=len(chunks),
            text=text,
            input_chars=len(text),
            source_blocks=list(parts),
            context_header=header,
            oversized=oversized,
        )
    )


def _is_boundary_line(line: str) -> bool:
    value = line.strip()
    if not value:
        return False
    if value in {"{", "}"}:
        return True
    if NUMBERED_LINE_PATTERN.match(value):
        return True
    if FILE_HEADING_PATTERN.match(value):
        return True
    if value.startswith(("【", "#")):
        return True
    if len(value) <= 40 and not re.search(r"[。！？?!；;，,]", value):
        return True
    return False


def _split_long_unit(unit: str, max_chars: int) -> list[str]:
    text = unit.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    sentence_parts = []
    start = 0
    for match in SENTENCE_BOUNDARY_PATTERN.finditer(text):
        end = match.end()
        sentence_parts.append(
            text[start:end].strip()
        )
        start = end
    if start < len(text):
        sentence_parts.append(
            text[start:].strip()
        )

    if not sentence_parts:
        sentence_parts = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

    chunks = []
    current = ""
    for part in sentence_parts:
        if not part:
            continue
        candidate = f"{current}{part}" if current else part
        if current and len(candidate) > max_chars:
            chunks.append(
                current
            )
            current = part
        else:
            current = candidate

        while len(current) > max_chars:
            split_at = max(
                current.rfind(mark, 0, max_chars)
                for mark in ["。", "；", ";", "，", ",", " "]
            )
            if split_at <= 0:
                split_at = max_chars
            chunks.append(
                current[:split_at].strip()
            )
            current = current[split_at:].strip()

    if current:
        chunks.append(
            current
        )
    return [
        chunk
        for chunk in chunks
        if chunk
    ]


def _split_oversized_block(block: str, max_chars: int) -> list[str]:
    lines = [
        line.strip()
        for line in _normalize_newlines(block).splitlines()
        if line.strip()
    ]
    if not lines:
        return []

    units: list[str] = []
    current: list[str] = []
    in_json_record = False

    def flush_current() -> None:
        nonlocal current
        if current:
            units.append(
                "\n".join(current).strip()
            )
            current = []

    for line in lines:
        if line == "{":
            flush_current()
            current = [line]
            in_json_record = True
            continue

        if in_json_record:
            current.append(
                line
            )
            if line == "}":
                flush_current()
                in_json_record = False
            continue

        if _is_boundary_line(line):
            flush_current()
            current = [line]
        else:
            current.append(
                line
            )

    flush_current()

    split_units: list[str] = []
    for unit in units:
        split_units.extend(
            _split_long_unit(
                unit,
                max_chars
            )
        )
    return split_units


def _append_safe_unit_to_chunks(
    chunks: list[FactChunk],
    current: list[str],
    headings: list[str],
    unit: str,
    target_chars: int,
    max_chars: int,
) -> list[str]:
    candidate = _append_unit(
        current,
        unit
    )
    if current and len(candidate) > max_chars:
        _finalize_chunk(
            chunks,
            current,
            headings
        )
        return [unit]

    if current and len(candidate) > target_chars:
        _finalize_chunk(
            chunks,
            current,
            headings
        )
        return [unit]

    current.append(
        unit
    )
    return current


def build_fact_chunks(
    material: str,
    target_chars: int = DEFAULT_FACTS_CHUNK_TARGET_CHARS,
    max_chars: int = DEFAULT_FACTS_CHUNK_MAX_CHARS,
) -> list[FactChunk]:
    """Build safe chunks without splitting normal paragraphs or image blocks."""
    blocks = _split_blocks(material)
    if not blocks:
        return []

    chunks: list[FactChunk] = []
    current: list[str] = []
    active_headings: list[str] = []
    current_headings: list[str] = []

    for block in blocks:
        block_len = len(block)
        if _is_heading(block):
            active_headings.append(block)

        if block_len > max_chars:
            _finalize_chunk(
                chunks,
                current,
                current_headings
            )
            current = []
            current_headings = list(active_headings)
            for unit in _split_oversized_block(block, max_chars):
                if _is_heading(unit):
                    active_headings.append(unit)
                    current_headings = list(active_headings)
                if not current_headings:
                    current_headings = list(active_headings)
                current = _append_safe_unit_to_chunks(
                    chunks,
                    current,
                    current_headings,
                    unit,
                    target_chars,
                    max_chars
                )
            current_headings = list(active_headings)
            continue

        candidate = _append_with_spacing(current, block)
        if current and len(candidate) > target_chars:
            _finalize_chunk(chunks, current, current_headings)
            current = [block]
            current_headings = list(active_headings)
        else:
            current.append(block)
            if not current_headings:
                current_headings = list(active_headings)

        if _is_image_block(block) and len(_append_with_spacing(current, "")) > max_chars:
            _finalize_chunk(chunks, current, current_headings)
            current = []
            current_headings = list(active_headings)

    _finalize_chunk(chunks, current, current_headings)

    return [
        replace(chunk, chunk_index=index)
        for index, chunk in enumerate(chunks)
    ]
