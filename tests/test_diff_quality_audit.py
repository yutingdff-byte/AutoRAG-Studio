import json

from diff.engine import compare
from diff.models import ChangeType
from evaluation.diff_quality_audit import (
    audit_score,
    retrieve_candidates_for_added,
    run_audit,
    sample_added,
)
from knowledge.models import KnowledgeItem


def item(knowledge_id, model, question, answer, category="价格", knowledge_type="price"):
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        model=model,
        trim="全系",
        question=question,
        answer=answer,
        category=category,
        knowledge_type=knowledge_type,
    )


def test_audit_retrieves_paraphrased_price_candidate():
    old_item = item("OLD-1", "哈弗H5", "哈弗H5价格是多少？", "11.79万元起")
    new_item = item("NEW-1", "哈弗H5", "哈弗H5多少钱？", "12.78万元起")

    score, *_ = audit_score(new_item, old_item)

    assert score > 0.7


def test_audit_candidate_ranking_prefers_same_model():
    old_same = item("OLD-SAME", "哈弗H5", "哈弗H5价格是多少？", "11.79万元起")
    old_other = item("OLD-OTHER", "坦克300", "坦克300价格是多少？", "19.98万元起")
    new_item = item("NEW-1", "哈弗H5", "哈弗H5多少钱？", "12.78万元起")
    diff_result = compare([], [new_item])
    added = [result for result in diff_result.results if result.change_type == ChangeType.ADDED]

    candidates = retrieve_candidates_for_added(
        added,
        [old_other, old_same],
        production_candidates={new_item.knowledge_id: set()},
        top_k=2,
    )

    assert candidates[new_item.knowledge_id][0].old_id == "OLD-SAME"


def test_audit_sampling_is_deterministic():
    old_item = item("OLD-1", "哈弗H5", "哈弗H5价格是多少？", "11.79万元起")
    new_items = [
        item(f"NEW-{index}", "哈弗H5", f"哈弗H5多少钱{index}？", f"{index}.78万元起")
        for index in range(20)
    ]
    diff_result = compare([], new_items)
    added = [result for result in diff_result.results if result.change_type == ChangeType.ADDED]
    candidates = retrieve_candidates_for_added(
        added,
        [old_item],
        production_candidates={new_item.knowledge_id: set() for new_item in new_items},
    )

    first = sample_added(added, candidates, {"OLD-1": old_item}, seed=42)
    second = sample_added(added, candidates, {"OLD-1": old_item}, seed=42)

    assert [row["new_id"] for row in first] == [row["new_id"] for row in second]


def test_run_audit_writes_reports_without_llm(tmp_path, monkeypatch):
    old_item = item("OLD-1", "哈弗H5", "哈弗H5价格是多少？", "11.79万元起")
    rag_data = {
        "rag_knowledge": [
            {
                "rag_id": "NEW-1",
                "model": "哈弗H5",
                "trim": "全系",
                "questions": ["哈弗H5多少钱？"],
                "answer": "12.78万元起",
                "category": "价格",
                "knowledge_type": "dynamic",
            }
        ]
    }
    rag_path = tmp_path / "rag.json"
    rag_path.write_text(json.dumps(rag_data, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr("evaluation.diff_quality_audit.load_old_knowledge", lambda path: [old_item])

    summary = run_audit(tmp_path / "history.docx", rag_path, tmp_path / "audit")

    assert summary["data_source"]["llm_called"] is False
    assert (tmp_path / "audit" / "audit_all_added.csv").exists()
    assert (tmp_path / "audit" / "audit_sample.csv").exists()
    assert (tmp_path / "audit" / "audit_badcases.md").exists()
    assert (tmp_path / "audit" / "audit_summary.json").exists()
