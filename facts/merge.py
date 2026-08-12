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


def _renumber_fact(fact: dict, index: int) -> dict:
    item = dict(fact)
    item["fact_id"] = f"F{index:03d}"
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
