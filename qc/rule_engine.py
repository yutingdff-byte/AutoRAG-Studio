from __future__ import annotations

from utils.rag_quality import is_exportable_rag, is_missing_answer

from qc.models import RuleIssue, RuleQCResult


def _question_text(item):
    questions = item.get("questions", item.get("question", ""))
    if isinstance(questions, list):
        return " ".join(str(question) for question in questions if question)
    return str(questions or "")


def _field_value(item, field):
    return str(item.get(field, "") or "").strip()


def _non_exportable_reason(item):
    if item.get("exportable") is False:
        return "exportable=false"
    if _field_value(item, "answer_type").lower() == "need_confirm":
        return "answer_type=need_confirm"
    if _field_value(item, "need_confirm").lower() in {"是", "yes", "true", "1"}:
        return "need_confirm"
    review_type = _field_value(item, "review_type")
    if review_type in {"missing", "conflict", "inference", "range_issue"}:
        return f"review_type={review_type}"
    status = _field_value(item, "knowledge_status").lower()
    if status in {"missing", "unconfirmed", "invalid"}:
        return f"knowledge_status={status}"
    if is_missing_answer(item.get("answer", "")):
        return "missing_answer"
    return ""


def _fact_refs_are_malformed(item):
    refs = item.get("fact_refs", [])
    if refs in (None, ""):
        return True
    if not isinstance(refs, list):
        return True
    return any(not str(ref or "").strip() for ref in refs)


def run_rule_qc(rag_items):
    """Run high-confidence deterministic QC without calling the LLM."""
    result = RuleQCResult(checked_count=len(rag_items))

    for item in rag_items:
        if not isinstance(item, dict):
            continue

        rag_id = item.get("rag_id", "")
        question = _question_text(item).strip()
        answer = _field_value(item, "answer")

        if not question:
            result.issues.append(
                RuleIssue(
                    rag_id=rag_id,
                    issue_type="问题为空",
                    risk_level="error",
                    description="该知识缺少可用于匹配用户表达的问题。",
                    suggestion="补充清晰的问题表达后再导出。",
                ).to_dict()
            )
            result.issue_item_ids.add(rag_id)

        if not answer:
            result.issues.append(
                RuleIssue(
                    rag_id=rag_id,
                    issue_type="回答为空",
                    risk_level="error",
                    description="该知识缺少回答内容。",
                    suggestion="补充有效回答，或将该知识标记为待确认。",
                ).to_dict()
            )
            result.issue_item_ids.add(rag_id)

        reason = _non_exportable_reason(item)
        if reason:
            result.issues.append(
                RuleIssue(
                    rag_id=rag_id,
                    issue_type="不可导出知识",
                    risk_level="error",
                    description=f"该知识命中导出质量门禁：{reason}。",
                    suggestion="请在知识检查中心确认来源资料或补充有效知识后再导出。",
                ).to_dict()
            )
            result.issue_item_ids.add(rag_id)

        if is_exportable_rag(item) and _fact_refs_are_malformed(item):
            result.issues.append(
                RuleIssue(
                    rag_id=rag_id,
                    issue_type="Fact引用异常",
                    risk_level="warning",
                    description="该知识的 fact_refs 为空或格式异常，无法稳定追溯事实来源。",
                    suggestion="检查RAG生成结果中的fact_refs字段，确保引用有效Fact ID。",
                ).to_dict()
            )
            result.issue_item_ids.add(rag_id)

    return result
