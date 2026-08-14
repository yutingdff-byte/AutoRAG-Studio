from __future__ import annotations

import re
import unicodedata


def _normalize_value(value) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[，。！？、,.!?；;：:\-_/\\|（）()【】\[\]\"']", "", text)
    return text.lower()


def _dedup_key(fact: dict) -> tuple[str, str]:
    return (
        _normalize_value(fact.get("category", "")),
        _normalize_value(fact.get("content", "")),
    )


def _record_scope(fact: dict, fallback: str) -> str:
    record_id = fact.get("_record_id") or fact.get("record_id")
    if record_id:
        return _normalize_value(record_id)

    model = _normalize_value(fact.get("model", ""))
    trim = _normalize_value(fact.get("trim", ""))
    if model or trim:
        return f"{model}|{trim}"

    brand = _normalize_value(fact.get("brand", ""))
    if brand:
        return f"{brand}|{fallback}"

    return fallback


def _record_dedup_key(fact: dict, fallback: str) -> tuple[str, str, str]:
    category, content = _dedup_key(fact)
    return (
        _record_scope(fact, fallback),
        category,
        content,
    )


def _renumber_fact(fact: dict, index: int) -> dict:
    item = dict(fact)
    item["fact_id"] = f"F{index:03d}"
    item.pop("_record_id", None)
    item.pop("record_id", None)
    return item


def merge_fact_chunk_results(chunk_results):
    """Merge chunk facts by chunk_index, exact-dedup, then renumber F001..."""
    ordered = sorted(
        chunk_results,
        key=lambda result: result.chunk_index,
    )
    raw_facts = []
    info_gaps = []

    for result in ordered:
        data = result.data or {}
        facts = data.get("facts", [])
        if isinstance(facts, list):
            raw_facts.extend(
                fact
                for fact in facts
                if isinstance(fact, dict)
            )
        gaps = data.get("info_gaps", [])
        if isinstance(gaps, list):
            info_gaps.extend(gaps)

    kept = []
    removed = []
    seen = {}
    for fact in raw_facts:
        key = _dedup_key(fact)
        if key in seen:
            removed.append(
                {
                    "kept_original_index": seen[key],
                    "removed_fact": fact,
                    "reason": "EXACT_DUPLICATE",
                }
            )
            continue
        seen[key] = len(kept)
        kept.append(fact)

    final_facts = [
        _renumber_fact(fact, index + 1)
        for index, fact in enumerate(kept)
    ]

    return {
        "facts": final_facts,
        "info_gaps": info_gaps,
        "chunk_report": {
            "raw_facts": len(raw_facts),
            "exact_duplicates_removed": len(removed),
            "final_facts": len(final_facts),
            "duplicate_records": removed,
        },
    }


def merge_record_fact_chunk_results(chunk_results, chunks):
    """Merge record-aware facts with exact dedup scoped to a vehicle record."""
    chunk_by_index = {
        chunk.chunk_index: chunk
        for chunk in chunks
    }
    ordered = sorted(
        chunk_results,
        key=lambda result: result.chunk_index,
    )
    raw_facts = []
    info_gaps = []

    for result in ordered:
        data = result.data or {}
        chunk = chunk_by_index.get(result.chunk_index)
        record_ids = list(getattr(chunk, "record_ids", []) or [])
        fallback = "|".join(record_ids) if record_ids else f"batch:{result.chunk_index}"
        facts = data.get("facts", [])
        if isinstance(facts, list):
            for fact in facts:
                if not isinstance(fact, dict):
                    continue
                item = dict(fact)
                if len(record_ids) == 1 and not item.get("_record_id") and not item.get("record_id"):
                    item["_record_id"] = record_ids[0]
                raw_facts.append((item, fallback))
        gaps = data.get("info_gaps", [])
        if isinstance(gaps, list):
            info_gaps.extend(gaps)

    kept = []
    removed = []
    seen = {}
    for fact, fallback in raw_facts:
        key = _record_dedup_key(fact, fallback)
        if key in seen:
            removed.append(
                {
                    "kept_original_index": seen[key],
                    "removed_fact": fact,
                    "reason": "EXACT_DUPLICATE",
                    "scope": key[0],
                }
            )
            continue
        seen[key] = len(kept)
        kept.append(fact)

    final_facts = [
        _renumber_fact(fact, index + 1)
        for index, fact in enumerate(kept)
    ]

    return {
        "facts": final_facts,
        "info_gaps": info_gaps,
        "chunk_report": {
            "raw_facts": len(raw_facts),
            "exact_duplicates_removed": len(removed),
            "final_facts": len(final_facts),
            "duplicate_records": removed,
        },
    }
