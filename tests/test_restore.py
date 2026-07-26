from io import BytesIO
from types import SimpleNamespace

import pandas as pd
import pytest

from knowledge.excel_restore import KnowledgeRestoreError, restore_excel
from knowledge.restore_manager import restore
from knowledge.word_restore import restore_word


class NamedBytesIO(BytesIO):
    def __init__(self, value: bytes, name: str):
        super().__init__(value)
        self.name = name


def make_excel_file(rows, name="历史知识.xlsx"):
    buffer = BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False)
    buffer.seek(0)
    return NamedBytesIO(buffer.getvalue(), name)


def test_restore_standard_excel_to_knowledge_items():
    file = make_excel_file(
        [
            {
                "车型": "理想MEGA",
                "版本": "全系",
                "问题": "MEGA多少钱？",
                "回答": "官方指导价52.98万元起。",
                "分类": "价格",
            }
        ]
    )

    items = restore_excel(file)

    assert len(items) == 1
    assert items[0].question == "MEGA多少钱？"
    assert items[0].model == "理想MEGA"
    assert items[0].trim == "全系"
    assert items[0].category == "价格"
    assert items[0].knowledge_type == "price"
    assert items[0].source_files == ["历史知识.xlsx"]


def test_restore_excel_rejects_non_standard_columns():
    file = make_excel_file(
        [
            {
                "问题": "多少钱？",
                "回答": "52.98万元起。",
            }
        ],
        name="非标准.xlsx",
    )

    with pytest.raises(KnowledgeRestoreError, match="不是标准知识库"):
        restore_excel(file)


def test_restore_word_reuses_existing_parser_and_agents(monkeypatch):
    calls = []

    def fake_parse(file):
        calls.append(("parse", file.name))
        return "历史Word资料"

    def fake_extract(material):
        calls.append(("facts", material))
        return {
            "facts": [
                {
                    "fact_id": "F001",
                    "content": "MEGA官方指导价52.98万元起。",
                }
            ]
        }

    def fake_rag(facts):
        calls.append(("rag", facts["facts"][0]["fact_id"]))
        return {
            "rag_knowledge": [
                {
                    "rag_id": "RAG-001",
                    "questions": ["MEGA多少钱？"],
                    "answer": "官方指导价52.98万元起。",
                    "category": "价格",
                    "knowledge_type": "dynamic",
                    "model": "理想MEGA",
                    "trim": "全系",
                    "fact_refs": ["F001"],
                }
            ]
        }

    monkeypatch.setattr("knowledge.word_restore.parse_file", fake_parse)
    monkeypatch.setattr("knowledge.word_restore.extract_facts", fake_extract)
    monkeypatch.setattr("knowledge.word_restore.generate_rag", fake_rag)

    items = restore_word(SimpleNamespace(name="产品FAQ.docx"))

    assert calls == [
        ("parse", "产品FAQ.docx"),
        ("facts", "历史Word资料"),
        ("rag", "F001"),
    ]
    assert len(items) == 1
    assert items[0].source_files == ["产品FAQ.docx"]
    assert items[0].fact_refs == ["F001"]


def test_restore_manager_combines_success_and_failure():
    valid = make_excel_file(
        [
            {
                "车型": "理想MEGA",
                "版本": "全系",
                "问题": "MEGA多少钱？",
                "回答": "官方指导价52.98万元起。",
                "分类": "价格",
            }
        ],
        name="标准知识.xlsx",
    )
    invalid = SimpleNamespace(name="历史资料.pdf")

    result = restore([valid, invalid])

    assert result.restored_count == 1
    assert result.model_count == 1
    assert len(result.files) == 2
    assert result.files[0].success
    assert not result.files[1].success
