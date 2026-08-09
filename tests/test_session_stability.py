from streamlit.testing.v1 import AppTest

from diff.engine import compare
from knowledge.models import KnowledgeItem
from knowledge.restore_manager import RestoreFileResult, RestoreResult


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

    app.radio[0].set_value("generate").run(timeout=60)
    assert any(tab.label == "下载" for tab in app.tabs)
    assert app.session_state["generate_result"]["run_id"] == "session-test"

    app.radio[0].set_value("home").run(timeout=60)
    app.radio[0].set_value("generate").run(timeout=60)

    assert any(tab.label == "下载" for tab in app.tabs)
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

    app.radio[0].set_value("update").run(timeout=60)
    assert app.session_state["update_restore_result"].restored_count == 1
    assert app.session_state["update_diff_result"].total_count == 1
    assert any(tab.label == "全部" for tab in app.tabs)

    app.radio[0].set_value("home").run(timeout=60)
    app.radio[0].set_value("update").run(timeout=60)

    assert app.session_state["update_restore_result"].restored_count == 1
    assert len(app.session_state["update_new_knowledge"]) == 1
    assert app.session_state["update_diff_result"].total_count == 1
    assert any(tab.label == "全部" for tab in app.tabs)
    assert not app.exception


def test_page_header_does_not_render_literal_html():
    app = AppTest.from_file("../app.py", default_timeout=60)
    app.run(timeout=60)

    assert all("<h1" not in markdown.value for markdown in app.markdown)
    assert not app.exception
