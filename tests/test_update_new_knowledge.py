from io import BytesIO

import streamlit as st

from pages import update_page


class NamedBytesIO(BytesIO):
    def __init__(self, value: bytes, name: str):
        super().__init__(value)
        self.name = name
        self.size = len(value)


def _reset_update_new_state():
    st.session_state.update_new_knowledge = []
    st.session_state.update_new_errors = []
    st.session_state.update_new_logs = []


def test_generate_new_knowledge_stops_when_facts_are_none(monkeypatch):
    _reset_update_new_state()
    file = NamedBytesIO(b"new material", "新增资料.txt")
    calls = []

    def fake_parse(uploaded_file):
        calls.append("parse")
        return "车型价格资料"

    def fake_extract(material):
        calls.append("facts")
        print("JSON解析失败")
        print("None")
        return None

    def fail_generate_rag(facts):
        raise AssertionError("generate_rag should not be called when facts is None")

    monkeypatch.setattr("parser.parser_factory.parse_file", fake_parse)
    monkeypatch.setattr("agents.fact_agent.extract_facts", fake_extract)
    monkeypatch.setattr("agents.rag_agent.generate_rag", fail_generate_rag)

    result = update_page._generate_new_knowledge([file])

    assert result == []
    assert calls == ["parse", "facts"]
    assert st.session_state.update_new_knowledge == []
    assert any("新增资料未能生成有效 Facts" in error for error in st.session_state.update_new_errors)
    assert any("JSON解析失败" in entry for entry in st.session_state.update_new_logs)
    assert any("Facts｜失败" in entry for entry in st.session_state.update_new_logs)


def test_generate_new_knowledge_runs_parser_facts_rag_to_knowledge(monkeypatch):
    _reset_update_new_state()
    file = NamedBytesIO(b"new material", "新增资料.txt")
    calls = []

    def fake_parse(uploaded_file):
        calls.append(("parse", uploaded_file.name))
        return "长城车型价格资料"

    def fake_extract(material):
        calls.append(("facts", "长城车型价格资料" in material))
        return {
            "facts": [
                {
                    "fact_id": "F001",
                    "brand": "长城",
                    "model": "哈弗H6",
                    "trim": "全系",
                    "category": "价格",
                    "content": "哈弗H6价格以官方资料为准",
                    "knowledge_type": "dynamic",
                    "confidence": "high",
                }
            ]
        }

    def fake_generate_rag(facts):
        calls.append(("rag", len(facts["facts"])))
        return {
            "rag_knowledge": [
                {
                    "rag_id": "RAG-001",
                    "questions": ["哈弗H6多少钱？"],
                    "answer": "哈弗H6价格以官方资料为准。",
                    "category": "价格",
                    "knowledge_type": "dynamic",
                    "brand": "长城",
                    "model": "哈弗H6",
                    "trim": "全系",
                    "fact_refs": ["F001"],
                }
            ]
        }

    monkeypatch.setattr("parser.parser_factory.parse_file", fake_parse)
    monkeypatch.setattr("agents.fact_agent.extract_facts", fake_extract)
    monkeypatch.setattr("agents.rag_agent.generate_rag", fake_generate_rag)

    result = update_page._generate_new_knowledge([file])

    assert calls == [
        ("parse", "新增资料.txt"),
        ("facts", True),
        ("rag", 1),
    ]
    assert len(result) == 1
    assert result[0].question == "哈弗H6多少钱？"
    assert result[0].model == "哈弗H6"
    assert result[0].source_files == ["新增资料.txt"]
    assert st.session_state.update_new_errors == []
    assert any("KnowledgeItem｜成功" in entry for entry in st.session_state.update_new_logs)
