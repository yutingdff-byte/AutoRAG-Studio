"""Offline Diff quality audit tooling.

This module intentionally does not modify production Diff behavior. It rebuilds
the current rule-based Diff output from existing Old/New KnowledgeItem inputs,
then performs a wider independent candidate retrieval over ADDED items.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from diff.candidate_builder import build_index, build_candidates_for_new
from diff.engine import compare
from diff.models import ChangeType, DiffResult, DiffRunResult
from knowledge.adapter import rag_to_knowledge
from knowledge.models import KnowledgeItem
from knowledge.restore_manager import restore
from utils.rag_quality import normalize_model_name


DEFAULT_OLD_WORD = Path(r"C:\Users\huyut\Downloads\长城所有车型政策&基础信息.docx")
DEFAULT_NEW_RAG = Path("output/20260809_145827/rag.json")
DEFAULT_OUTPUT_DIR = Path("output/diff_quality_audit")

INTENT_SYNONYMS = {
    "价格": {"价格", "多少钱", "指导价", "售价", "价位", "起售价", "报价"},
    "金融": {"金融", "分期", "贷款", "免息", "0息", "贴息", "月供", "首付"},
    "现金优惠": {"现金", "现金礼", "优惠", "钜惠", "直享"},
    "权益": {"权益", "活动", "礼", "礼包", "补贴", "购车"},
    "置换": {"置换", "增换购", "换购", "旧车", "增购"},
    "质保": {"质保", "保修", "三电", "整车质保"},
    "流量": {"流量", "基础服务", "娱乐", "尊享服务"},
    "续航": {"续航", "能跑", "公里", "CLTC"},
    "配置": {"配置", "功能", "配备", "装备"},
    "智驾": {"智驾", "辅助驾驶", "领航", "泊车", "NOA", "LCC", "NCA"},
    "保养": {"保养", "首保", "二保"},
}

BUSINESS_RISK_TOPICS = {"价格", "金融", "权益", "置换"}
BRAND_ONLY_TOKENS = {"哈弗", "长城", "魏牌", "坦克"}
TOKEN_PATTERN = re.compile(r"[A-Za-z]+[0-9A-Za-z+-]*|[\u4e00-\u9fff]{2,}|\d+(?:\.\d+)?")
NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")
PUNCT_PATTERN = re.compile(r"[\s，。！？、,.!?；;：:\-_/\\|（）()【】\[\]\"'“”‘’]")


@dataclass(slots=True)
class AuditCandidate:
    new_id: str
    old_id: str
    rank: int
    question_similarity: float
    token_overlap: float
    entity_score: float
    intent_overlap: float
    audit_score: float
    model_match: bool
    category_match: bool
    number_change: bool
    suspected_type: str
    audit_suggestion: str
    suspected_root_cause: str
    layer_diagnosis: str


def normalize_text(value: str | None) -> str:
    text = str(value or "").lower()
    text = text.replace("plus", "+")
    text = text.replace("ＰＬＵＳ".lower(), "+")
    text = text.replace("hi4", "hi4")
    return PUNCT_PATTERN.sub("", text)


def display_model(value: str | None) -> str:
    return normalize_model_name(str(value or "").strip())


def model_tokens(value: str | None) -> set[str]:
    model = display_model(value)
    if not model:
        return set()
    tokens = {model}
    for prefix in ["哈弗", "长城", "魏牌", "坦克"]:
        if model.startswith(prefix) and len(model) > len(prefix):
            tokens.add(model[len(prefix) :])
    return {token.lower() for token in tokens if token and token not in BRAND_ONLY_TOKENS}


def text_tokens(*values: str | None) -> set[str]:
    text = " ".join(str(value or "") for value in values)
    normalized = normalize_text(text)
    raw_tokens = set(TOKEN_PATTERN.findall(text))
    raw_tokens.update(TOKEN_PATTERN.findall(normalized))
    return {token.lower() for token in raw_tokens if len(token.strip()) >= 2}


def intent_tags(*values: str | None) -> set[str]:
    text = "".join(str(value or "") for value in values)
    tags = set()
    for tag, words in INTENT_SYNONYMS.items():
        if any(word in text for word in words):
            tags.add(tag)
    return tags


def extract_numbers(*values: str | None) -> set[str]:
    return set(NUMBER_PATTERN.findall(" ".join(str(value or "") for value in values)))


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def question_similarity(new_item: KnowledgeItem, old_item: KnowledgeItem) -> float:
    return SequenceMatcher(None, normalize_text(new_item.question), normalize_text(old_item.question)).ratio()


def entity_score(new_item: KnowledgeItem, old_item: KnowledgeItem) -> float:
    score = 0.0
    new_model_tokens = model_tokens(new_item.model)
    old_model_tokens = model_tokens(old_item.model)
    if new_model_tokens and old_model_tokens and new_model_tokens & old_model_tokens:
        score += 0.45
    if new_item.trim and old_item.trim and new_item.trim == old_item.trim:
        score += 0.10
    if new_item.category and old_item.category and new_item.category == old_item.category:
        score += 0.20
    if new_item.knowledge_type and old_item.knowledge_type and new_item.knowledge_type == old_item.knowledge_type:
        score += 0.10
    new_intents = intent_tags(new_item.question, new_item.category, new_item.answer)
    old_intents = intent_tags(old_item.question, old_item.category, old_item.answer)
    if new_intents and old_intents and new_intents & old_intents:
        score += 0.15
    return min(score, 1.0)


def number_change(new_item: KnowledgeItem, old_item: KnowledgeItem) -> bool:
    new_numbers = extract_numbers(new_item.answer)
    old_numbers = extract_numbers(old_item.answer)
    return bool(new_numbers and old_numbers and new_numbers != old_numbers)


def model_match(new_item: KnowledgeItem, old_item: KnowledgeItem) -> bool:
    new_tokens = model_tokens(new_item.model)
    old_tokens = model_tokens(old_item.model)
    return bool(new_tokens and old_tokens and new_tokens & old_tokens)


def category_match(new_item: KnowledgeItem, old_item: KnowledgeItem) -> bool:
    if new_item.category and old_item.category and new_item.category == old_item.category:
        return True
    shared_tags = intent_tags(new_item.question, new_item.category) & intent_tags(old_item.question, old_item.category)
    return bool(shared_tags - {"权益"})


def audit_score(new_item: KnowledgeItem, old_item: KnowledgeItem) -> tuple[float, float, float, float]:
    q_sim = question_similarity(new_item, old_item)
    token_overlap = jaccard(
        text_tokens(new_item.question, new_item.category),
        text_tokens(old_item.question, old_item.category),
    )
    entities = entity_score(new_item, old_item)
    intents = jaccard(
        intent_tags(new_item.question, new_item.category, new_item.answer),
        intent_tags(old_item.question, old_item.category, old_item.answer),
    )
    score = 0.38 * q_sim + 0.22 * token_overlap + 0.28 * entities + 0.12 * intents
    if new_item.model and old_item.model and not model_match(new_item, old_item):
        score *= 0.55
    return score, q_sim, token_overlap, intents


def suspected_root_cause(new_item: KnowledgeItem, old_item: KnowledgeItem, in_candidate_builder: bool) -> str:
    roots: list[str] = []
    if not model_match(new_item, old_item):
        roots.append("MODEL_ALIAS")
    if not category_match(new_item, old_item):
        roots.append("CATEGORY_MISMATCH")
    new_intents = intent_tags(new_item.question, new_item.category, new_item.answer)
    old_intents = intent_tags(old_item.question, old_item.category, old_item.answer)
    if new_intents & old_intents and question_similarity(new_item, old_item) < 0.72:
        roots.append("QUESTION_PARAPHRASE")
    if len(new_intents) == 1 and len(old_intents) >= 2:
        roots.append("QUESTION_SPLIT")
    if len(new_intents) >= 2 and len(old_intents) == 1:
        roots.append("QUESTION_MERGE")
    if not in_candidate_builder:
        roots.append("CANDIDATE_NOT_BUILT")
    elif roots:
        roots.append("THRESHOLD_TOO_STRICT")
    return "|".join(dict.fromkeys(roots)) or "THRESHOLD_TOO_STRICT"


def audit_suggestion(new_item: KnowledgeItem, old_item: KnowledgeItem, score: float) -> str:
    same_model = model_match(new_item, old_item)
    same_topic = category_match(new_item, old_item)
    if new_item.model and old_item.model and not same_model:
        return "REVIEW_REQUIRED" if score >= 0.68 and same_topic else "TRUE_ADDED"
    if same_model and same_topic and number_change(new_item, old_item) and score >= 0.55:
        return "SHOULD_UPDATE"
    if same_model and same_topic and not number_change(new_item, old_item) and score >= 0.58:
        return "DUPLICATE"
    if same_model and score >= 0.80 and not number_change(new_item, old_item):
        return "DUPLICATE"
    if same_model and score >= 0.72 and number_change(new_item, old_item):
        return "SHOULD_UPDATE"
    if score >= 0.68:
        new_intents = intent_tags(new_item.question, new_item.category, new_item.answer)
        old_intents = intent_tags(old_item.question, old_item.category, old_item.answer)
        if len(new_intents) == 1 and len(old_intents) >= 2:
            return "ONE_TO_MANY"
        if len(new_intents) >= 2 and len(old_intents) == 1:
            return "MANY_TO_ONE"
        return "REVIEW_REQUIRED"
    if score >= 0.58 and model_match(new_item, old_item) and category_match(new_item, old_item):
        return "REVIEW_REQUIRED"
    return "TRUE_ADDED"


def suspected_type(new_item: KnowledgeItem, old_item: KnowledgeItem, suggestion: str) -> str:
    tags = intent_tags(new_item.question, new_item.category, new_item.answer, old_item.question, old_item.category)
    if "价格" in tags:
        return "价格更新候选" if number_change(new_item, old_item) else "价格重复候选"
    if "金融" in tags:
        return "金融政策候选"
    if "置换" in tags:
        return "置换政策候选"
    if "权益" in tags:
        return "购车权益候选"
    if suggestion in {"ONE_TO_MANY", "MANY_TO_ONE"}:
        return suggestion
    return "语义相似候选"


def load_old_knowledge(path: Path) -> list[KnowledgeItem]:
    result = restore(str(path))
    if not result.items:
        raise RuntimeError(f"未能恢复历史知识：{path}")
    return result.items


def load_new_knowledge(rag_path: Path) -> list[KnowledgeItem]:
    rag_data = json.loads(rag_path.read_text(encoding="utf-8"))
    return rag_to_knowledge(rag_data, source_file=rag_path.name)


def production_candidate_ids(old_items: list[KnowledgeItem], new_items: list[KnowledgeItem]) -> dict[str, set[str]]:
    index = build_index(old_items, new_items)
    return {
        item.knowledge_id: set(build_candidates_for_new(item, index, max_candidates_per_item=20))
        for item in new_items
    }


def retrieve_candidates_for_added(
    added_results: list[DiffResult],
    old_items: list[KnowledgeItem],
    production_candidates: dict[str, set[str]],
    top_k: int = 5,
) -> dict[str, list[AuditCandidate]]:
    by_new_id: dict[str, list[AuditCandidate]] = {}
    for result in added_results:
        new_item = result.new_item
        if not new_item:
            continue
        scored: list[tuple[float, float, float, float, float, KnowledgeItem]] = []
        for old_item in old_items:
            score, q_sim, token_overlap, intents = audit_score(new_item, old_item)
            if score < 0.25 and not (model_match(new_item, old_item) and category_match(new_item, old_item)):
                continue
            scored.append((score, q_sim, token_overlap, intents, entity_score(new_item, old_item), old_item))
        scored.sort(key=lambda row: row[0], reverse=True)

        candidates = []
        for rank, (score, q_sim, token_overlap, intents, entities, old_item) in enumerate(scored[:top_k], start=1):
            in_builder = old_item.knowledge_id in production_candidates.get(new_item.knowledge_id, set())
            suggestion = audit_suggestion(new_item, old_item, score)
            layer = "Match Decision问题" if in_builder else "Candidate Recall问题"
            candidates.append(
                AuditCandidate(
                    new_id=new_item.knowledge_id,
                    old_id=old_item.knowledge_id,
                    rank=rank,
                    question_similarity=round(q_sim, 4),
                    token_overlap=round(token_overlap, 4),
                    entity_score=round(entities, 4),
                    intent_overlap=round(intents, 4),
                    audit_score=round(score, 4),
                    model_match=model_match(new_item, old_item),
                    category_match=category_match(new_item, old_item),
                    number_change=number_change(new_item, old_item),
                    suspected_type=suspected_type(new_item, old_item, suggestion),
                    audit_suggestion=suggestion,
                    suspected_root_cause=suspected_root_cause(new_item, old_item, in_builder),
                    layer_diagnosis=layer,
                )
            )
        by_new_id[new_item.knowledge_id] = candidates
    return by_new_id


def item_by_id(items: list[KnowledgeItem]) -> dict[str, KnowledgeItem]:
    return {item.knowledge_id: item for item in items}


def result_rows(
    added_results: list[DiffResult],
    candidates: dict[str, list[AuditCandidate]],
    old_by_id: dict[str, KnowledgeItem],
) -> list[dict[str, Any]]:
    rows = []
    for result in added_results:
        new_item = result.new_item
        if not new_item:
            continue
        new_candidates = candidates.get(new_item.knowledge_id, [])
        if not new_candidates:
            rows.append(base_row("ALL", result.diff_id, new_item, None, None))
            continue
        for candidate in new_candidates:
            old_item = old_by_id[candidate.old_id]
            rows.append(base_row("ALL", result.diff_id, new_item, old_item, candidate))
    return rows


def base_row(
    sample_group: str,
    diff_id: str,
    new_item: KnowledgeItem,
    old_item: KnowledgeItem | None,
    candidate: AuditCandidate | None,
) -> dict[str, Any]:
    return {
        "sample_group": sample_group,
        "diff_id": diff_id,
        "new_id": new_item.knowledge_id,
        "new_model": new_item.model or "",
        "new_category": new_item.category or "",
        "new_question": new_item.question,
        "new_answer": new_item.answer,
        "old_candidate_id": old_item.knowledge_id if old_item else "",
        "old_model": old_item.model if old_item else "",
        "old_category": old_item.category if old_item else "",
        "old_question": old_item.question if old_item else "",
        "old_answer": old_item.answer if old_item else "",
        "candidate_rank": candidate.rank if candidate else "",
        "question_similarity": candidate.question_similarity if candidate else "",
        "audit_score": candidate.audit_score if candidate else "",
        "model_match": "是" if candidate and candidate.model_match else "否",
        "category_match": "是" if candidate and candidate.category_match else "否",
        "number_change": "是" if candidate and candidate.number_change else "否",
        "system_status": "ADDED",
        "audit_suggestion": candidate.audit_suggestion if candidate else "TRUE_ADDED",
        "suspected_root_cause": candidate.suspected_root_cause if candidate else "NO_OBVIOUS_CANDIDATE",
        "layer_diagnosis": candidate.layer_diagnosis if candidate else "无明显历史候选",
        "final_label": "",
        "review_note": "",
    }


def top_candidate_for(new_id: str, candidates: dict[str, list[AuditCandidate]]) -> AuditCandidate | None:
    values = candidates.get(new_id) or []
    return values[0] if values else None


def sample_added(
    added_results: list[DiffResult],
    candidates: dict[str, list[AuditCandidate]],
    old_by_id: dict[str, KnowledgeItem],
    seed: int = 20260810,
) -> list[dict[str, Any]]:
    suspicious = [
        result
        for result in added_results
        if (top := top_candidate_for(result.new_item.knowledge_id, candidates)) is not None
        and top.audit_suggestion in {"SHOULD_UPDATE", "DUPLICATE", "REVIEW_REQUIRED"}
    ]
    suspicious.sort(key=lambda result: top_candidate_for(result.new_item.knowledge_id, candidates).audit_score, reverse=True)

    business = [
        result
        for result in added_results
        if intent_tags(result.new_item.question, result.new_item.category, result.new_item.answer) & BUSINESS_RISK_TOPICS
    ]
    business.sort(key=lambda result: (top_candidate_for(result.new_item.knowledge_id, candidates).audit_score if top_candidate_for(result.new_item.knowledge_id, candidates) else 0), reverse=True)

    rng = random.Random(seed)
    random_pool = list(added_results)
    rng.shuffle(random_pool)

    selected: list[tuple[str, DiffResult]] = []
    used: set[str] = set()

    def add(group: str, items: list[DiffResult], limit: int) -> None:
        for result in items:
            new_id = result.new_item.knowledge_id
            if new_id in used:
                continue
            selected.append((group, result))
            used.add(new_id)
            if sum(1 for existing_group, _ in selected if existing_group == group) >= limit:
                break

    add("A_最高疑似漏匹配", suspicious, 10)
    add("B_高风险业务知识", business, 10)
    add("C_随机ADDED", random_pool, 10)

    rows = []
    for group, result in selected:
        new_item = result.new_item
        candidate = top_candidate_for(new_item.knowledge_id, candidates)
        old_item = old_by_id.get(candidate.old_id) if candidate else None
        rows.append(base_row(group, result.diff_id, new_item, old_item, candidate))
    return rows


def summarize_diff(diff_result: DiffRunResult) -> dict[str, int]:
    return {
        "ADDED": diff_result.added_count,
        "UPDATED": diff_result.updated_count,
        "UNCHANGED": diff_result.unchanged_count,
        "REVIEW_REQUIRED": diff_result.review_required_count,
        "TOTAL": diff_result.total_count,
    }


def summarize_candidates(
    added_results: list[DiffResult],
    candidates: dict[str, list[AuditCandidate]],
) -> dict[str, Any]:
    top_candidates = [top_candidate_for(result.new_item.knowledge_id, candidates) for result in added_results]
    top_candidates = [candidate for candidate in top_candidates if candidate]
    suggestions = Counter(candidate.audit_suggestion for candidate in top_candidates)
    layers = Counter(candidate.layer_diagnosis for candidate in top_candidates)
    root_causes = Counter(
        root
        for candidate in top_candidates
        for root in candidate.suspected_root_cause.split("|")
        if root
    )
    return {
        "added_with_any_candidate": len(top_candidates),
        "added_without_obvious_candidate": len(added_results) - len(top_candidates),
        "high_similarity_candidate_count": sum(candidate.audit_score >= 0.72 for candidate in top_candidates),
        "suspicious_candidate_count": sum(
            candidate.audit_suggestion
            in {"SHOULD_UPDATE", "DUPLICATE", "ONE_TO_MANY", "MANY_TO_ONE", "REVIEW_REQUIRED"}
            for candidate in top_candidates
        ),
        "suggestions": dict(suggestions),
        "layers": dict(layers),
        "root_causes": dict(root_causes),
    }


def inspect_updated(results: list[DiffResult]) -> list[dict[str, Any]]:
    rows = []
    for result in results:
        if result.change_type != ChangeType.UPDATED:
            continue
        old_item = result.old_item
        new_item = result.new_item
        rows.append(
            {
                "diff_id": result.diff_id,
                "old_id": old_item.knowledge_id if old_item else "",
                "new_id": new_item.knowledge_id if new_item else "",
                "old_question": old_item.question if old_item else "",
                "new_question": new_item.question if new_item else "",
                "model_match": model_match(new_item, old_item) if old_item and new_item else False,
                "category_match": category_match(new_item, old_item) if old_item and new_item else False,
                "number_change": number_change(new_item, old_item) if old_item and new_item else False,
                "audit_note": "匹配关系看起来合理" if old_item and new_item else "缺少匹配项",
            }
        )
    return rows


def inspect_review_required(results: list[DiffResult]) -> list[dict[str, Any]]:
    rows = []
    for result in results:
        if result.change_type != ChangeType.REVIEW_REQUIRED:
            continue
        item = result.new_item or result.old_item
        rows.append(
            {
                "diff_id": result.diff_id,
                "item_id": item.knowledge_id if item else "",
                "model": item.model if item else "",
                "question": item.question if item else "",
                "reason_code": result.reason_code,
                "review_reason": result.review_reason.value if result.review_reason else "",
                "audit_note": result.change_summary,
            }
        )
    return rows


def inspect_unchanged_sample(results: list[DiffResult], seed: int = 20260810, limit: int = 10) -> list[dict[str, Any]]:
    unchanged = [result for result in results if result.change_type == ChangeType.UNCHANGED]
    rng = random.Random(seed)
    rng.shuffle(unchanged)
    rows = []
    for result in unchanged[:limit]:
        item = result.old_item or result.new_item
        rows.append(
            {
                "diff_id": result.diff_id,
                "item_id": item.knowledge_id if item else "",
                "model": item.model if item else "",
                "category": item.category if item else "",
                "question": item.question if item else "",
                "answer": item.answer if item else "",
                "audit_note": "抽样未发现明显状态异常",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_badcases(
    path: Path,
    sample_rows: list[dict[str, Any]],
    all_rows: list[dict[str, Any]],
    updated_rows: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    unchanged_rows: list[dict[str, Any]],
) -> None:
    candidates = [
        row
        for row in all_rows
        if row.get("candidate_rank") == 1
        and row.get("audit_suggestion") in {"SHOULD_UPDATE", "DUPLICATE", "REVIEW_REQUIRED", "ONE_TO_MANY", "MANY_TO_ONE"}
    ]
    candidates.sort(key=lambda row: float(row.get("audit_score") or 0), reverse=True)
    lines = ["# Diff Quality Audit Badcases", ""]
    lines.append("## Top 10 Missed Match candidates")
    for idx, row in enumerate(candidates[:10], start=1):
        lines.extend(
            [
                "",
                f"### BC-{idx:03d}",
                "",
                "System: ADDED",
                "",
                f"New: {row['new_question']}",
                "",
                row["new_answer"],
                "",
                f"Closest Old: {row['old_question']}",
                "",
                row["old_answer"],
                "",
                f"Audit suggestion: {row['audit_suggestion']}",
                f"Possible root cause: {row['suspected_root_cause']}",
                f"Layer diagnosis: {row['layer_diagnosis']}",
            ]
        )
    lines.extend(["", "## Sample Rows", ""])
    for row in sample_rows:
        lines.append(
            f"- {row['sample_group']} | {row['audit_suggestion']} | {row['new_model']} | {row['new_question']} -> {row['old_question']}"
        )
    lines.extend(["", "## UPDATED Check", ""])
    if updated_rows:
        for row in updated_rows:
            lines.append(f"- {row['diff_id']} | {row['audit_note']} | {row['old_question']} -> {row['new_question']}")
    else:
        lines.append("- 本轮无 UPDATED。")
    lines.extend(["", "## REVIEW_REQUIRED Check", ""])
    if review_rows:
        for row in review_rows:
            lines.append(f"- {row['diff_id']} | {row['review_reason']} | {row['question']}")
    else:
        lines.append("- 本轮无 REVIEW_REQUIRED。")
    lines.extend(["", "## UNCHANGED Random Sample", ""])
    for row in unchanged_rows:
        lines.append(f"- {row['diff_id']} | {row['model']} | {row['question']} | {row['audit_note']}")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_audit(old_word: Path, new_rag: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    old_items = load_old_knowledge(old_word)
    new_items = load_new_knowledge(new_rag)
    diff_result = compare(old_items, new_items)

    added_results = [result for result in diff_result.results if result.change_type == ChangeType.ADDED]
    production_candidates = production_candidate_ids(old_items, new_items)
    candidates = retrieve_candidates_for_added(added_results, old_items, production_candidates)
    old_by_id = item_by_id(old_items)

    all_rows = result_rows(added_results, candidates, old_by_id)
    sample_rows = sample_added(added_results, candidates, old_by_id)
    updated_rows = inspect_updated(diff_result.results)
    review_rows = inspect_review_required(diff_result.results)
    unchanged_rows = inspect_unchanged_sample(diff_result.results)

    write_csv(output_dir / "audit_all_added.csv", all_rows)
    write_csv(output_dir / "audit_sample.csv", sample_rows)
    write_csv(output_dir / "audit_updated.csv", updated_rows)
    write_csv(output_dir / "audit_review_required.csv", review_rows)
    write_csv(output_dir / "audit_unchanged_sample.csv", unchanged_rows)
    write_badcases(output_dir / "audit_badcases.md", sample_rows, all_rows, updated_rows, review_rows, unchanged_rows)

    summary = {
        "data_source": {
            "old_word": str(old_word),
            "new_rag": str(new_rag),
            "diff_rebuilt_offline": True,
            "llm_called": False,
        },
        "counts": {
            "old_knowledge": len(old_items),
            "new_knowledge": len(new_items),
            "diff": summarize_diff(diff_result),
        },
        "added_candidate_summary": summarize_candidates(added_results, candidates),
        "sample": {
            "total": len(sample_rows),
            "groups": dict(Counter(row["sample_group"] for row in sample_rows)),
            "seed": 20260810,
        },
        "updated_check": updated_rows,
        "review_required_check": review_rows,
        "unchanged_sample_count": len(unchanged_rows),
        "outputs": {
            "audit_all_added": str(output_dir / "audit_all_added.csv"),
            "audit_sample": str(output_dir / "audit_sample.csv"),
            "audit_badcases": str(output_dir / "audit_badcases.md"),
            "audit_summary": str(output_dir / "audit_summary.json"),
        },
    }
    (output_dir / "audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline Diff quality audit.")
    parser.add_argument("--old-word", type=Path, default=DEFAULT_OLD_WORD)
    parser.add_argument("--new-rag", type=Path, default=DEFAULT_NEW_RAG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    summary = run_audit(args.old_word, args.new_rag, args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
