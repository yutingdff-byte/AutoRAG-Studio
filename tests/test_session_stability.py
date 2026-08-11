from streamlit.testing.v1 import AppTest

from diff.engine import compare
from knowledge.models import KnowledgeItem
from knowledge.restore_manager import RestoreFileResult, RestoreResult
from merge.engine import MergeResult
from review.decisions import build_default_decisions


def _radio_by_key(app, key: str):
    return next(radio for radio in app.radio if getattr(radio, "key", None) == key)


def _knowledge(knowledge_id: str, answer: str) -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question="这款车多少钱？",
        answer=answer,
        category="价格",
        brand="测试品牌",
        model="测试车型",
        trim="全系",
        knowledge_type="price",
        source_files=["fixture.docx"],
    )


def _generate_result() -> dict:
    return {
        "run_id": "session-test",
        "facts": {
            "facts": [],
            "info_gaps": [],
            "confirm_items": [],
        },
        "rag": {
            "rag_knowledge": [],
            "export_excluded_count": 0,
        },
        "qc": {
            "overall_result": "PASS",
            "issues": [],
            "summary": {"total_rag": 0, "warning": 0, "error": 0},
        },
        "excel_paths": {"static": "cached.xlsx", "dynamic": "cached-policy.xlsx"},
    }


def test_generate_result_survives_navigation_reruns():
    app = AppTest.from_file("../app.py", default_timeout=60)
    app.run(timeout=60)
    app.session_state["generate_result"] = _generate_result()
    app.session_state["generate_input_file_count"] = 2
    app.session_state["generate_export_files"] = {
        "static": {"file_name": "config.xlsx", "data": b"config"},
        "dynamic": {"file_name": "policy.xlsx", "data": b"policy"},
    }

    _radio_by_key(app, "navigation_mode").set_value("generate").run(timeout=60)
    assert _radio_by_key(app, "_generate_active_section_widget").value == "overview"
    assert app.session_state["generate_result"]["run_id"] == "session-test"

    _radio_by_key(app, "_generate_active_section_widget").set_value("dynamic_knowledge").run(timeout=60)
    assert app.session_state["generate_active_section"] == "dynamic_knowledge"

    _radio_by_key(app, "navigation_mode").set_value("home").run(timeout=60)
    _radio_by_key(app, "navigation_mode").set_value("generate").run(timeout=60)

    assert app.session_state["generate_active_section"] == "dynamic_knowledge"
    assert app.session_state["generate_export_files"]["static"]["data"] == b"config"
    assert not app.exception


def test_update_results_and_diff_survive_navigation_reruns():
    old_item = _knowledge("OLD-001", "10万元起")
    new_item = _knowledge("NEW-001", "9万元起")
    restore_result = RestoreResult(
        items=[old_item],
        files=[
            RestoreFileResult(
                file_name="history.docx",
                file_type=".docx",
                success=True,
                items=[old_item],
                report={"format_id": "SYSTEM_STANDARD_WORD_V1"},
            )
        ],
    )

    app = AppTest.from_file("../app.py", default_timeout=60)
    app.run(timeout=60)
    app.session_state["update_restore_result"] = restore_result
    app.session_state["update_new_knowledge"] = [new_item]
    app.session_state["update_diff_result"] = compare([old_item], [new_item])

    _radio_by_key(app, "navigation_mode").set_value("update").run(timeout=60)
    assert app.session_state["update_restore_result"].restored_count == 1
    assert app.session_state["update_diff_result"].total_count == 1

    _radio_by_key(app, "navigation_mode").set_value("home").run(timeout=60)
    _radio_by_key(app, "navigation_mode").set_value("update").run(timeout=60)

    assert app.session_state["update_restore_result"].restored_count == 1
    assert len(app.session_state["update_new_knowledge"]) == 1
    assert app.session_state["update_diff_result"].total_count == 1
    assert not app.exception


def test_update_review_merge_export_survive_navigation_reruns():
    old_item = _knowledge("OLD-001", "10万元起")
    new_item = _knowledge("NEW-001", "9万元起")
    diff_result = compare([old_item], [new_item])
    merge_result = MergeResult(final_items=[new_item], updated_accepted=1)

    app = AppTest.from_file("../app.py", default_timeout=60)
    app.run(timeout=60)
    app.session_state["update_restore_result"] = RestoreResult(items=[old_item])
    app.session_state["update_new_knowledge"] = [new_item]
    app.session_state["update_diff_result"] = diff_result
    app.session_state["update_review_decisions"] = build_default_decisions(diff_result.results)
    app.session_state["update_review_completed"] = True
    app.session_state["update_merge_result"] = merge_result
    app.session_state["update_export_files"] = {
        "static": {"file_name": "config.xlsx", "data": b"config"},
        "dynamic": {"file_name": "policy.xlsx", "data": b"policy"},
    }

    _radio_by_key(app, "navigation_mode").set_value("update").run(timeout=60)
    assert app.session_state["update_review_completed"]
    assert app.session_state["update_export_files"]["dynamic"]["data"] == b"policy"

    _radio_by_key(app, "navigation_mode").set_value("home").run(timeout=60)
    _radio_by_key(app, "navigation_mode").set_value("update").run(timeout=60)

    assert app.session_state["update_merge_result"].updated_accepted == 1
    assert app.session_state["update_export_files"]["static"]["data"] == b"config"
    assert not app.exception


def test_page_header_does_not_render_literal_html():
    app = AppTest.from_file("../app.py", default_timeout=60)
    app.run(timeout=60)

    assert all("<h1" not in markdown.value for markdown in app.markdown)
    assert not app.exception
