from __future__ import annotations

import re
from dataclasses import replace

from facts.models import FactChunk


DEFAULT_FACTS_RECORD_BATCH_SIZE = 3
DEFAULT_FACTS_RECORD_BATCH_MAX_CHARS = 12000

VEHICLE_RECORD_MARKER_PATTERN = re.compile(
    r"(?=^.*(?:【车型记录|銆愯溅鍨嬭褰).*$)",
    re.MULTILINE,
)


def _normalize_newlines(text: str) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n")


def split_vehicle_records(material: str) -> tuple[str, list[str]]:
    """Split parser material into global context and complete vehicle records."""
    text = _normalize_newlines(material).strip()
    if not text:
        return "", []

    matches = list(VEHICLE_RECORD_MARKER_PATTERN.finditer(text))
    if not matches:
        return text, []

    context = text[: matches[0].start()].strip()
    records: list[str] = []

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        record = text[start:end].strip()
        if record:
            records.append(record)

    return context, records


def _record_text(context: str, records: list[str]) -> str:
    body = "\n\n".join(record.strip() for record in records if record.strip())
    if context.strip():
        return f"{context.strip()}\n\n{body}".strip()
    return body.strip()


def make_record_id(index: int) -> str:
    return f"VR{index:03d}"


def build_record_fact_chunks(
    material: str,
    batch_size: int = DEFAULT_FACTS_RECORD_BATCH_SIZE,
    max_chars: int = DEFAULT_FACTS_RECORD_BATCH_MAX_CHARS,
) -> list[FactChunk]:
    """Build fact chunks without splitting vehicle records."""
    context, records = split_vehicle_records(material)
    if not records:
        text = str(material or "").strip()
        if not text:
            return []
        return [
            FactChunk(
                chunk_index=0,
                text=text,
                input_chars=len(text),
                source_blocks=[text],
                context_header="",
                oversized=len(text) > max_chars,
                record_ids=[],
            )
        ]

    size_limit = max(1, int(batch_size or DEFAULT_FACTS_RECORD_BATCH_SIZE))
    char_limit = max(1, int(max_chars or DEFAULT_FACTS_RECORD_BATCH_MAX_CHARS))
    chunks: list[FactChunk] = []
    current: list[str] = []
    current_ids: list[str] = []

    def flush() -> None:
        nonlocal current, current_ids
        if not current:
            return
        text = _record_text(context, current)
        chunks.append(
            FactChunk(
                chunk_index=len(chunks),
                text=text,
                input_chars=len(text),
                source_blocks=list(current),
                context_header=context,
                oversized=len(text) > char_limit,
                record_ids=list(current_ids),
            )
        )
        current = []
        current_ids = []

    for record_index, record in enumerate(records, start=1):
        record_id = make_record_id(record_index)
        record_text = _record_text(context, [record])
        if len(record_text) > char_limit:
            flush()
            chunks.append(
                FactChunk(
                    chunk_index=len(chunks),
                    text=record_text,
                    input_chars=len(record_text),
                    source_blocks=[record],
                    context_header=context,
                    oversized=True,
                    record_ids=[record_id],
                )
            )
            continue

        candidate = _record_text(context, current + [record])
        if current and (len(current) >= size_limit or len(candidate) > char_limit):
            flush()

        current.append(record)
        current_ids.append(record_id)

    flush()

    return [
        replace(chunk, chunk_index=index)
        for index, chunk in enumerate(chunks)
    ]


def build_record_batch_manifest(chunks: list[FactChunk]) -> list[dict]:
    return [
        {
            "batch_index": chunk.chunk_index,
            "record_count": len(chunk.source_blocks),
            "record_ids": list(chunk.record_ids),
            "input_chars": chunk.input_chars,
            "oversized": chunk.oversized,
        }
        for chunk in chunks
    ]
