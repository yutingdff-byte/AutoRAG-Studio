from knowledge.deduplicator import cleanup_exact_duplicates, exact_duplicate_key
from knowledge.models import KnowledgeItem


def make_item(
    knowledge_id: str,
    *,
    model: str = "坦克500",
    trim: str | None = "",
    question: str = "坦克500的续航",
    answer: str = "坦克500的WLTC纯电续航有110公里和201公里两个版本",
    category: str = "",
) -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        model=model,
        trim=trim,
        question=question,
        answer=answer,
        category=category,
    )


def test_exact_duplicate_keeps_first_and_removes_second():
    first = make_item("STD-DOCX-f442891cc2a3")
    second = make_item("STD-DOCX-d6d9017dd16b")

    result = cleanup_exact_duplicates([first, second])

    assert result.final_items == [first]
    assert result.removed_items == [second]
    assert result.removed_count == 1
    assert result.duplicate_groups[0].kept_item_id == first.knowledge_id
    assert result.duplicate_groups[0].removed_item_ids == [second.knowledge_id]
    assert result.duplicate_groups[0].reason == "EXACT_DUPLICATE"


def test_three_exact_duplicates_become_one_stably():
    items = [make_item("K1"), make_item("K2"), make_item("K3")]

    result = cleanup_exact_duplicates(items)

    assert result.final_items == [items[0]]
    assert result.removed_items == [items[1], items[2]]
    assert result.duplicate_groups[0].removed_item_ids == ["K2", "K3"]


def test_same_question_different_answer_is_not_removed():
    result = cleanup_exact_duplicates(
        [
            make_item("K1", answer="33.5万元起"),
            make_item("K2", answer="35.5万元起"),
        ]
    )

    assert [item.knowledge_id for item in result.final_items] == ["K1", "K2"]
    assert result.removed_count == 0


def test_different_version_is_not_removed():
    result = cleanup_exact_duplicates(
        [
            make_item("K1", trim="2025款"),
            make_item("K2", trim="2026款"),
        ]
    )

    assert [item.knowledge_id for item in result.final_items] == ["K1", "K2"]


def test_different_model_is_not_removed():
    result = cleanup_exact_duplicates(
        [
            make_item("K1", model="坦克500"),
            make_item("K2", model="坦克700"),
        ]
    )

    assert [item.knowledge_id for item in result.final_items] == ["K1", "K2"]


def test_same_answer_different_question_is_not_removed():
    result = cleanup_exact_duplicates(
        [
            make_item("K1", question="坦克500质保多久？", answer="5年15万公里"),
            make_item("K2", question="坦克500整车质保怎么样？", answer="5年15万公里"),
        ]
    )

    assert [item.knowledge_id for item in result.final_items] == ["K1", "K2"]


def test_none_and_empty_values_are_safely_normalized():
    first = make_item("K1", trim=None, category="")
    second = make_item("K2", trim="", category=None)

    result = cleanup_exact_duplicates([first, second])

    assert exact_duplicate_key(first) == exact_duplicate_key(second)
    assert result.final_items == [first]
    assert result.removed_items == [second]


def test_cleanup_does_not_modify_original_item():
    first = make_item("K1")
    original_metadata = dict(first.metadata)

    cleanup_exact_duplicates([first, make_item("K2")])

    assert first.knowledge_id == "K1"
    assert first.metadata == original_metadata
