from diff.scope_detector import detect_update_scope, item_in_scope
from knowledge.models import KnowledgeItem


def item(knowledge_id, model, category, knowledge_type="price"):
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question="多少钱？",
        answer="24.98万元起。",
        category=category,
        model=model,
        knowledge_type=knowledge_type,
        source_files=["new.xlsx"],
    )


def test_scope_detector_collects_models_and_categories():
    scope = detect_update_scope(
        [
            item("K1", "阿维塔06", "价格"),
            item("K2", "阿维塔07", "金融"),
        ]
    )

    assert scope.models == ["阿维塔06", "阿维塔07"]
    assert scope.categories == ["价格", "金融"]
    assert "阿维塔06" in scope.summary


def test_item_in_scope_is_not_absolute_deletion_signal():
    scope = detect_update_scope([item("K1", "阿维塔06", "价格")])
    old_config = item("OLD", "阿维塔06", "配置", "product")

    assert not item_in_scope(old_config, scope)
