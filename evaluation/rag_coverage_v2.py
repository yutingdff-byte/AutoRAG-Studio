"""RAG coverage evaluator V2.

This module is an offline evaluation/reporting tool. It does not call LLMs and
does not participate in production generation, QC, or export.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from parser.excel_parser import parse_excel


DYNAMIC_INTENTS = ("cash", "trade_in", "finance", "benefit", "activity")

SOURCE_FIELDS = {
    "series": "车系名称",
    "vehicle": "车型名称",
    "config": "配置版本等级",
    "brand": "品牌",
    "price": "厂商指导价",
    "cash": "购车权益-购车补贴政策",
    "trade_in": "购车权益-厂家置换补贴",
    "finance": "购车权益-金融优惠",
    "benefit": "购车权益-其他权益",
    "activity": "其他活动",
}

INTENT_KEYWORDS = {
    "cash": ["现金", "现金礼", "现金优惠", "现金补贴", "购车补贴", "直降", "优惠", "购车优惠", "抵扣车款"],
    "trade_in": ["置换", "增换购", "旧车", "换购补贴", "置换补贴"],
    "finance": ["金融", "贷款", "分期", "免息", "低息", "首付", "月供", "0息", "0首付"],
    "benefit": ["权益", "礼包", "赠送", "服务", "充电权益", "保养", "流量", "道路救援", "质保", "保修"],
    "activity": ["活动", "限时", "截止", "政策", "试驾", "预约", "抽奖", "8月", "12月31日"],
}

INDEPENDENT_INTENT_KEYWORDS = {
    "cash": ["现金", "现金礼", "现金优惠", "现金补贴", "直降"],
    "trade_in": ["置换", "增换购", "旧车", "换购补贴", "置换补贴"],
    "finance": ["金融", "贷款", "分期", "免息", "低息", "首付", "月供", "0息", "0首付"],
    "benefit": ["权益", "礼包", "赠送", "服务", "充电权益", "保养", "流量", "道路救援", "质保", "保修"],
    "activity": ["活动", "限时", "截止", "政策", "试驾", "预约", "抽奖", "8月", "12月31日"],
}

PRICE_QUESTION_KEYWORDS = ["多少钱", "价位", "售价", "指导价", "价格"]


@dataclass(frozen=True)
class VehicleRecord:
    record_index: int
    series: str
    version: str
    configuration_level: str
    brand: str
    source_price: str
    dynamic_source: dict[str, str]


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value or ""))).lower()


def contains_any(text: str, keywords: list[str] | tuple[str, ...]) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(keyword) in normalized for keyword in keywords)


def version_alias_match(source_version: str, rag_version: str) -> bool:
    """Safe alias check for version labels.

    This intentionally does not match broad model families such as M6 and M6 PRO.
    It only allows containment after removing common year/style words.
    """

    source = normalize_text(source_version)
    rag = normalize_text(rag_version)
    if not source or not rag:
        return False
    if source == rag:
        return True
    stripped_source = re.sub(r"20\d{2}款|款", "", source)
    stripped_rag = re.sub(r"20\d{2}款|款", "", rag)
    if len(stripped_source) < 2 or len(stripped_rag) < 2:
        return False
    if re.fullmatch(r"[a-z0-9]+", stripped_source) or re.fullmatch(r"[a-z0-9]+", stripped_rag):
        return False
    return stripped_source in stripped_rag or stripped_rag in stripped_source


def price_variants(price: Any) -> set[str]:
    variants: set[str] = set()
    for number in re.findall(r"\d+(?:\.\d+)?", str(price or "")):
        amount = float(number)
        variants.add(str(int(amount)) if amount.is_integer() else str(amount))
        if amount >= 10000:
            wan = amount / 10000
            variants.add(f"{wan:.2f}")
            variants.add(f"{wan:.2f}".rstrip("0").rstrip("."))
            variants.add(f"{wan:g}万")
            variants.add(f"{wan:.2f}万")
            variants.add(f"{wan:g}万元")
            variants.add(f"{wan:.2f}万元")
    return variants


def price_in_text(text: str, price: Any) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(variant) in normalized for variant in price_variants(price))


def parse_vehicle_records(material: str) -> list[VehicleRecord]:
    records: list[list[str]] = []
    current: list[str] = []
    for line in material.splitlines():
        if line.startswith("【车型记录"):
            if current:
                records.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        records.append(current)

    parsed: list[VehicleRecord] = []
    for lines in records:
        match = re.search(r"车型记录(\d+)", lines[0])
        fields: dict[str, str] = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = value.strip()
        parsed.append(
            VehicleRecord(
                record_index=int(match.group(1)) if match else len(parsed) + 1,
                series=fields.get(SOURCE_FIELDS["series"], ""),
                version=fields.get(SOURCE_FIELDS["vehicle"], ""),
                configuration_level=fields.get(SOURCE_FIELDS["config"], ""),
                brand=fields.get(SOURCE_FIELDS["brand"], ""),
                source_price=fields.get(SOURCE_FIELDS["price"], ""),
                dynamic_source={
                    intent: fields.get(SOURCE_FIELDS[intent], "")
                    for intent in DYNAMIC_INTENTS
                },
            )
        )
    return parsed


def rag_text(item: dict[str, Any], *, include_answer: bool = True) -> str:
    parts = [" ".join(map(str, item.get("questions") or []))]
    if include_answer:
        parts.append(str(item.get("answer") or ""))
    parts.extend([str(item.get("category") or ""), str(item.get("intent") or "")])
    return " ".join(parts)


def source_has_intent(record: VehicleRecord, intent: str) -> bool:
    value = record.dynamic_source.get(intent, "")
    return bool(str(value).strip() and str(value).strip() not in {"-", "/", "无数据"})


def fact_has_intent(fact: dict[str, Any] | None, intent: str) -> bool:
    if not fact:
        return False
    content = str(fact.get("content") or "")
    if intent == "trade_in" and "置换" in content:
        return True
    if intent == "benefit" and "其他权益" in content:
        return True
    if intent == "cash" and ("现金" in content or "购车补贴" in content):
        return True
    return contains_any(content, INTENT_KEYWORDS[intent])


def fact_id_for_record(record_index: int, kind: str) -> str:
    offset = {"config": 1, "price": 2, "dynamic": 3}[kind]
    return f"F{(record_index - 1) * 3 + offset:03d}"


def index_rags_by_fact(rag_items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for item in rag_items:
        for fact_id in item.get("fact_refs") or []:
            index.setdefault(fact_id, []).append(item)
    return index


def evaluate_price_v2(
    records: list[VehicleRecord],
    facts_by_id: dict[str, dict[str, Any]],
    rags_by_fact: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    counts = {
        "source": 0,
        "fact": 0,
        "answerability": 0,
        "independent_faq": 0,
        "true_missing": 0,
        "ambiguous": 0,
        "wrong_value": 0,
    }
    for record in records:
        fact_id = fact_id_for_record(record.record_index, "price")
        fact = facts_by_id.get(fact_id)
        source_has_price = bool(record.source_price.strip())
        fact_price_found = bool(
            fact
            and any(
                normalize_text(variant) in normalize_text(fact.get("content", ""))
                for variant in price_variants(record.source_price)
            )
        )
        candidates = rags_by_fact.get(fact_id, [])
        answerable_rags = [
            item for item in candidates if price_in_text(rag_text(item), record.source_price)
        ]
        independent_rags = [
            item
            for item in answerable_rags
            if contains_any(" ".join(map(str, item.get("questions") or [])), PRICE_QUESTION_KEYWORDS)
        ]
        if source_has_price:
            counts["source"] += 1
        if source_has_price and fact_price_found:
            counts["fact"] += 1
        if source_has_price and answerable_rags:
            counts["answerability"] += 1
        if source_has_price and independent_rags:
            counts["independent_faq"] += 1
        if source_has_price and fact_price_found and not answerable_rags:
            counts["true_missing"] += 1

        rows.append(
            {
                "vehicle": record.series,
                "version": record.version,
                "source_price": record.source_price,
                "fact_ids": fact_id if fact else "",
                "rag_ids": ";".join(item.get("rag_id", "") for item in answerable_rags),
                "answerability": bool(answerable_rags),
                "independent_faq": bool(independent_rags),
                "reason": "TRUE_COVERED"
                if answerable_rags
                else ("TRUE_RAG_MISSING" if fact_price_found else "FACT_MISSING"),
            }
        )
    return counts, rows


def evaluate_dynamic_v2(
    records: list[VehicleRecord],
    facts_by_id: dict[str, dict[str, Any]],
    rags_by_fact: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    counts = {
        intent: {
            "source": 0,
            "fact": 0,
            "answerability": 0,
            "independent_faq": 0,
            "true_missing": 0,
        }
        for intent in DYNAMIC_INTENTS
    }
    rows: list[dict[str, Any]] = []
    for record in records:
        fact_id = fact_id_for_record(record.record_index, "dynamic")
        fact = facts_by_id.get(fact_id)
        related_rags = rags_by_fact.get(fact_id, [])
        for intent in DYNAMIC_INTENTS:
            source_exists = source_has_intent(record, intent)
            fact_exists = fact_has_intent(fact, intent)
            answerable = [
                item for item in related_rags if contains_any(rag_text(item), INTENT_KEYWORDS[intent])
            ]
            independent = [
                item
                for item in related_rags
                if contains_any(" ".join(map(str, item.get("questions") or [])), INDEPENDENT_INTENT_KEYWORDS[intent])
            ]
            if source_exists:
                counts[intent]["source"] += 1
            if source_exists and fact_exists:
                counts[intent]["fact"] += 1
            if source_exists and answerable:
                counts[intent]["answerability"] += 1
            if source_exists and independent:
                counts[intent]["independent_faq"] += 1
            if source_exists and fact_exists and not answerable:
                counts[intent]["true_missing"] += 1
            rows.append(
                {
                    "vehicle": record.series,
                    "version": record.version,
                    "intent": intent,
                    "source_exist": source_exists,
                    "fact_exist": fact_exists,
                    "answerability": bool(answerable),
                    "independent_faq": bool(independent),
                    "rag_ids": ";".join(item.get("rag_id", "") for item in answerable),
                    "reason": "TRUE_COVERED"
                    if answerable
                    else ("TRUE_RAG_MISSING" if source_exists and fact_exists else ("FACT_MISSING" if source_exists else "NOT_IN_SOURCE")),
                }
            )
    return counts, rows


def ratio(covered: int, source: int) -> float:
    return round(covered / source, 4) if source else 0.0


def build_coverage_report(
    records: list[VehicleRecord],
    facts: list[dict[str, Any]],
    rag_items: list[dict[str, Any]],
    legacy_report: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    facts_by_id = {item["fact_id"]: item for item in facts}
    rags_by_fact = index_rags_by_fact(rag_items)
    price_counts, price_rows = evaluate_price_v2(records, facts_by_id, rags_by_fact)
    dynamic_counts, dynamic_rows = evaluate_dynamic_v2(records, facts_by_id, rags_by_fact)

    answerability = {
        "price": {
            "covered": price_counts["answerability"],
            "total": price_counts["source"],
            "coverage": ratio(price_counts["answerability"], price_counts["source"]),
        }
    }
    independent = {
        "price": {
            "covered": price_counts["independent_faq"],
            "total": price_counts["source"],
            "coverage": ratio(price_counts["independent_faq"], price_counts["source"]),
        }
    }
    for intent, counts in dynamic_counts.items():
        answerability[intent] = {
            "covered": counts["answerability"],
            "total": counts["source"],
            "coverage": ratio(counts["answerability"], counts["source"]),
        }
        independent[intent] = {
            "covered": counts["independent_faq"],
            "total": counts["source"],
            "coverage": ratio(counts["independent_faq"], counts["source"]),
        }

    false_negative_fixed = {}
    legacy_price = (legacy_report or {}).get("coverage", {}).get("price", {})
    if legacy_price:
        false_negative_fixed["price"] = max(0, answerability["price"]["covered"] - int(legacy_price.get("covered", 0)))
    legacy_dynamic = (legacy_report or {}).get("coverage", {}).get("dynamic", {})
    for intent in DYNAMIC_INTENTS:
        legacy_count = int(legacy_dynamic.get(intent, {}).get("covered", 0)) if legacy_dynamic else 0
        false_negative_fixed[intent] = max(0, answerability[intent]["covered"] - legacy_count)

    true_missing = {"price": price_counts["true_missing"]}
    true_missing.update(
        {intent: counts["true_missing"] for intent, counts in dynamic_counts.items()}
    )

    report = {
        "input": {
            "vehicle_records": len(records),
            "facts": len(facts),
            "rag": len(rag_items),
            "series": len({record.series for record in records}),
        },
        "legacy_coverage": {
            "price": legacy_price,
            "dynamic": legacy_dynamic,
        },
        "answerability_coverage": answerability,
        "legacy_independent_faq_coverage": independent,
        "false_negative_fixed": false_negative_fixed,
        "true_rag_missing_cases": true_missing,
        "release_gate": {
            "hard_gate": "answerability_coverage",
            "soft_metric": "legacy_independent_faq_coverage",
            "suggested_thresholds": {
                "price": 0.95,
                "dynamic_each_intent": 0.90,
            },
        },
    }
    return report, price_rows, dynamic_rows


def write_reports(
    output_dir: Path,
    coverage: dict[str, Any],
    price_rows: list[dict[str, Any]],
    dynamic_rows: list[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    coverage_v2 = {
        "price": {
            "answerability": coverage["answerability_coverage"]["price"],
            "independent_faq": coverage["legacy_independent_faq_coverage"]["price"],
        },
        "dynamic": {
            intent: {
                "answerability": coverage["answerability_coverage"][intent],
                "independent_faq": coverage["legacy_independent_faq_coverage"][intent],
            }
            for intent in DYNAMIC_INTENTS
        },
    }
    (output_dir / "coverage_v2.json").write_text(
        json.dumps(coverage_v2, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "evaluator_diff_report.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "price_v2_reconciliation.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(price_rows[0].keys()))
        writer.writeheader()
        writer.writerows(price_rows)
    with (output_dir / "dynamic_v2_reconciliation.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(dynamic_rows[0].keys()))
        writer.writeheader()
        writer.writerows(dynamic_rows)

    lines = [
        "# RAG Coverage Evaluator V2",
        "",
        "## Input Summary",
        f"- Vehicle Records: {coverage['input']['vehicle_records']}",
        f"- Facts: {coverage['input']['facts']}",
        f"- RAG: {coverage['input']['rag']}",
        "",
        "## Legacy Coverage",
        json.dumps(coverage["legacy_coverage"], ensure_ascii=False, indent=2),
        "",
        "## Answerability Coverage",
        json.dumps(coverage["answerability_coverage"], ensure_ascii=False, indent=2),
        "",
        "## Independent FAQ Coverage",
        json.dumps(coverage["legacy_independent_faq_coverage"], ensure_ascii=False, indent=2),
        "",
        "## False Negative Analysis",
        json.dumps(coverage["false_negative_fixed"], ensure_ascii=False, indent=2),
        "",
        "## Remaining True Missing",
        json.dumps(coverage["true_rag_missing_cases"], ensure_ascii=False, indent=2),
    ]
    (output_dir / "evaluator_v2_report.md").write_text("\n".join(lines), encoding="utf-8")


def run_from_files(
    source_excel: Path,
    facts_file: Path,
    rag_file: Path,
    legacy_report_file: Path,
    output_dir: Path,
) -> dict[str, Any]:
    material = parse_excel(source_excel)
    records = parse_vehicle_records(material)
    facts_data = json.loads(facts_file.read_text(encoding="utf-8"))
    rag_data = json.loads(rag_file.read_text(encoding="utf-8"))
    legacy_report = json.loads(legacy_report_file.read_text(encoding="utf-8"))
    coverage, price_rows, dynamic_rows = build_coverage_report(
        records,
        facts_data.get("facts", []),
        rag_data.get("rag_knowledge", []),
        legacy_report,
    )
    write_reports(output_dir, coverage, price_rows, dynamic_rows)
    return coverage


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline RAG coverage evaluator V2.")
    parser.add_argument("--source-excel", required=True, type=Path)
    parser.add_argument("--facts", required=True, type=Path)
    parser.add_argument("--rag", required=True, type=Path)
    parser.add_argument("--legacy-report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    coverage = run_from_files(
        args.source_excel,
        args.facts,
        args.rag,
        args.legacy_report,
        args.output,
    )
    print(json.dumps(coverage, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
