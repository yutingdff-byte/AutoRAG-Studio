from __future__ import annotations

import re
from dataclasses import replace

from facts.models import FactChunk


DEFAULT_FACTS_CHUNK_TARGET_CHARS = 4500
DEFAULT_FACTS_CHUNK_MAX_CHARS = 6000

FILE_HEADING_PATTERN = re.compile(r"^=+\s*文件[:：].*?=+$")
IMAGE_BLOCK_PATTERN = re.compile(r"^【内嵌图片\s+\d+/\d+[:：].*】$")


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
    if len(first) <= 40 and not re.search(r"[。！？!?；;，,]", first):
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
            _finalize_chunk(chunks, current, current_headings)
            current = []
            current_headings = list(active_headings)
            _finalize_chunk(chunks, [block], current_headings, oversized=True)
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
