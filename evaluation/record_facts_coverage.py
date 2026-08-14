from __future__ import annotations

import re
import statistics
import unicodedata
from collections import Counter
from typing import Any


DYNAMIC_KEYWORDS = {
    "cash": ["\u73b0\u91d1", "\u76f4\u964d", "\u8d2d\u8f66\u4f18\u60e0"],
    "trade_in": ["\u7f6e\u6362", "\u589e\u6362\u8d2d", "\u65e7\u8f66"],
    "finance": ["\u91d1\u878d", "\u8d37\u6b3e", "\u5206\u671f", "\u514d\u606f", "\u9996\u4ed8", "\u6708\u4f9b"],
    "benefit": ["\u6743\u76ca", "\u793c\u5305", "\u8d60\u9001", "\u670d\u52a1", "\u5145\u7535\u6743\u76ca", "\u4fdd\u517b"],
    "activity": ["\u6d3b\u52a8", "\u9650\u65f6", "\u622a\u6b62", "\u653f\u7b56"],
}

EMPTY_VALUES = {"", "-", "\u65e0", "\u6682\u65e0", "none", "null"}


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"\s+", "", text)
    return text.lower()


def normalize_record_id(index: int) -> str:
    return f"VR{int(index):03d}"


def fact_text(fact: dict) -> str:
    return " ".join(
        str(fact.get(field, ""))
        for field in [
            "brand",
            "model",
            "trim",
            "category",
            "content",
            "source",
        ]
    )


def extract_price_values(text: Any) -> set[int]:
    value = unicodedata.normalize("NFKC", str(text or ""))
    prices: set[int] = set()

    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*\u4e07(?:\u5143)?", value):
        prices.add(
            int(round(float(match.group(1)) * 10000))
        )

    for match in re.finditer(r"(?<!\d)(\d{5,7})(?:\s*\u5143)?(?!\d)", value):
        prices.add(
            int(match.group(1))
        )

    return prices


def record_identity_terms(record: dict) -> list[str]:
    values = [
        record.get("vehicle_name", ""),
        record.get("trim", ""),
    ]
    terms = []
    for value in values:
        normalized = normalize_text(value)
        if normalized and normalized not in terms:
            terms.append(normalized)
    if terms:
        return terms

    series = normalize_text(record.get("series", ""))
    if series:
        terms.append(series)
    return terms


def record_variant_terms(record: dict) -> list[str]:
    text = str(record.get("vehicle_name", "") or "")
    candidates = []
    for pattern in [
        r"([A-Za-z0-9]+\s*\u6fc0\u5149\u96f7\u8fbe\u7248)",
        r"([A-Za-z0-9]+\s*\u7248)",
        r"([\u4e00-\u9fffA-Za-z0-9]+\u7248)",
    ]:
        candidates.extend(match.group(1) for match in re.finditer(pattern, text))

    normalized = []
    for value in candidates:
        term = normalize_text(value)
        if term and term not in normalized:
            normalized.append(term)
    return normalized


def record_series_terms(record: dict) -> list[str]:
    values = [
        record.get("series", ""),
        str(record.get("series", "")).replace("PHEV", "").replace("phev", ""),
    ]
    terms = []
    for value in values:
        term = normalize_text(value)
        if term and term not in terms:
            terms.append(term)
    return terms


def source_has_value(record: dict, intent: str) -> bool:
    return normalize_text(record.get(intent, "")) not in EMPTY_VALUES


def fact_has_dynamic_intent(fact: dict, intent: str) -> bool:
    text = fact_text(fact)
    return any(
        keyword in text
        for keyword in DYNAMIC_KEYWORDS[intent]
    )


def fact_matches_record_by_text(fact: dict, record: dict) -> bool:
    text = normalize_text(fact_text(fact))
    if any(
        term and term in text
        for term in record_identity_terms(record)
    ):
        return True

    variants = record_variant_terms(record)
    series_terms = record_series_terms(record)
    return bool(
        variants
        and series_terms
        and any(variant in text for variant in variants)
        and any(series in text for series in series_terms)
    )


def fact_matches_record_price(fact: dict, record: dict) -> bool:
    expected = extract_price_values(record.get("price", ""))
    if not expected:
        return False
    actual = extract_price_values(fact_text(fact))
    return bool(expected & actual)


def map_facts_to_records(
    records: list[dict],
    facts: list[dict],
    candidate_record_ids: list[str] | None = None,
) -> dict[str, list[dict]]:
    allowed = set(candidate_record_ids or [])
    mapping = {
        normalize_record_id(record["record_index"]): []
        for record in records
        if not allowed or normalize_record_id(record["record_index"]) in allowed
    }

    records_by_id = {
        normalize_record_id(record["record_index"]): record
        for record in records
    }
    price_to_records: dict[int, list[str]] = {}
    for record_id in mapping:
        for price in extract_price_values(records_by_id[record_id].get("price", "")):
            price_to_records.setdefault(price, []).append(record_id)

    for fact in facts:
        if not isinstance(fact, dict):
            continue

        matched: list[str] = []
        allow_price_only = bool(allowed) and len(mapping) == 1
        fact_prices = extract_price_values(fact_text(fact))
        for record_id, record in records_by_id.items():
            if record_id not in mapping:
                continue
            if fact_matches_record_by_text(fact, record):
                matched.append(record_id)
                continue
            unique_price_match = any(
                price in price_to_records
                and price_to_records[price] == [record_id]
                for price in fact_prices
            )
            if (allow_price_only or (allowed and unique_price_match)) and fact_matches_record_price(fact, record):
                matched.append(record_id)

        for record_id in matched:
            mapping[record_id].append(fact)

    return mapping


def merge_record_fact_mappings(*mappings: dict[str, list[dict]]) -> dict[str, list[dict]]:
    merged: dict[str, list[dict]] = {}
    seen: dict[str, set[tuple[str, str]]] = {}

    for mapping in mappings:
        for record_id, facts in mapping.items():
            merged.setdefault(record_id, [])
            seen.setdefault(record_id, set())
            for fact in facts:
                key = (
                    str(fact.get("category", "")),
                    str(fact.get("content", "")),
                )
                if key in seen[record_id]:
                    continue
                seen[record_id].add(key)
                merged[record_id].append(fact)

    return merged


def evaluate_record_coverage(records: list[dict], mapping: dict[str, list[dict]]) -> dict:
    record_ids = [
        normalize_record_id(record["record_index"])
        for record in records
    ]
    covered = [
        record_id
        for record_id in record_ids
        if mapping.get(record_id)
    ]

    price_covered = []
    for record in records:
        record_id = normalize_record_id(record["record_index"])
        if any(
            fact_matches_record_price(fact, record)
            for fact in mapping.get(record_id, [])
        ):
            price_covered.append(record_id)

    dynamic = {}
    for intent in DYNAMIC_KEYWORDS:
        source_record_ids = [
            normalize_record_id(record["record_index"])
            for record in records
            if source_has_value(record, intent)
        ]
        intent_covered = [
            record_id
            for record_id in source_record_ids
            if any(
                fact_has_dynamic_intent(fact, intent)
                for fact in mapping.get(record_id, [])
            )
        ]
        dynamic[intent] = {
            "covered": len(intent_covered),
            "total": len(source_record_ids),
            "missing": [
                record_id
                for record_id in source_record_ids
                if record_id not in intent_covered
            ],
        }

    series_by_id = {
        normalize_record_id(record["record_index"]): normalize_text(record.get("series", ""))
        for record in records
    }
    source_series = {
        value
        for value in series_by_id.values()
        if value
    }
    covered_series = {
        series_by_id[record_id]
        for record_id in covered
        if series_by_id.get(record_id)
    }

    return {
        "vehicle": {
            "covered": len(covered),
            "total": len(record_ids),
            "missing": [
                record_id
                for record_id in record_ids
                if record_id not in covered
            ],
        },
        "version": {
            "covered": len(covered),
            "total": len(record_ids),
            "missing": [
                record_id
                for record_id in record_ids
                if record_id not in covered
            ],
        },
        "series": {
            "covered": len(covered_series),
            "total": len(source_series),
            "missing": sorted(source_series - covered_series),
        },
        "price": {
            "covered": len(price_covered),
            "total": len(record_ids),
            "missing": [
                record_id
                for record_id in record_ids
                if record_id not in price_covered
            ],
        },
        "dynamic": dynamic,
    }


def fact_distribution(mapping: dict[str, list[dict]]) -> dict:
    counts = {
        record_id: len(facts)
        for record_id, facts in mapping.items()
    }
    values = list(counts.values())
    if not values:
        return {
            "min": 0,
            "max": 0,
            "mean": 0,
            "median": 0,
            "p90": 0,
            "counts": counts,
        }
    sorted_values = sorted(values)
    p90_index = min(
        len(sorted_values) - 1,
        int(round((len(sorted_values) - 1) * 0.9)),
    )
    return {
        "min": min(values),
        "max": max(values),
        "mean": round(statistics.mean(values), 3),
        "median": statistics.median(values),
        "p90": sorted_values[p90_index],
        "counts": counts,
        "category_distribution": dict(
            Counter(
                str(fact.get("category", ""))
                for facts in mapping.values()
                for fact in facts
            )
        ),
    }
