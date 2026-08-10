from diff.engine import compare
from diff.models import ChangeType, ReviewReason
from knowledge.models import KnowledgeItem


def item(
    knowledge_id: str,
    model: str,
    question: str,
    answer: str,
    category: str = "价格信息",
    knowledge_type: str = "price",
) -> KnowledgeItem:
    return KnowledgeItem(
        knowledge_id=knowledge_id,
        question=question,
        answer=answer,
        category=category,
        model=model,
        trim="全系",
        knowledge_type=knowledge_type,
        source_files=["fixture.xlsx"],
    )


def single_result(old_item: KnowledgeItem, new_item: KnowledgeItem):
    result = compare([old_item], [new_item])
    return result.results[0]


def assert_matched_not_added(result):
    assert result.change_type in {ChangeType.UPDATED, ChangeType.UNCHANGED}
    assert result.old_item is not None
    assert result.new_item is not None


def test_price_paraphrase_matches_h9():
    result = single_result(
        item("OLD", "二代哈弗H9", "二代哈弗H9的价格是多少？", "售价区间19.99万到25.79万元。"),
        item("NEW", "二代哈弗H9", "二代哈弗H9多少钱？", "限时优惠换新价17.49万元起。"),
    )

    assert result.change_type == ChangeType.UPDATED


def test_model_alias_trade_in_matches_menglong_plus():
    result = single_result(
        item("OLD", "哈弗猛龙PLUS", "哈弗猛龙PLUS置换补贴", "旧车置换可以享受8000元补贴。", "权益政策", "policy"),
        item("NEW", "猛龙PLUS", "猛龙PLUS置换补贴多少？", "置换补贴8000元。", "置换补贴", "policy"),
    )

    assert_matched_not_added(result)


def test_warranty_gift_matches_warranty_question():
    result = single_result(
        item("OLD", "哈弗H6经典版", "哈弗H6经典版的质保礼是什么？", "发动机、变速器核心零部件终身质保。", "售后质保", "policy"),
        item("NEW", "哈弗H6经典版", "哈弗H6经典版质保怎么样？", "发动机、变速器核心零部件终身质保。", "售后质保", "policy"),
    )

    assert_matched_not_added(result)


def test_cash_discount_matches_cash_gift():
    result = single_result(
        item("OLD", "哈弗H6经典版", "哈弗H6经典版的现金礼是什么？", "购车直享30000元现金钜惠。", "权益政策", "policy"),
        item("NEW", "哈弗H6经典版", "哈弗H6经典版优惠多少？", "购车直享3万元现金钜惠。", "购车权益", "policy"),
    )

    assert_matched_not_added(result)


def test_trade_in_gift_matches_trade_in_question():
    result = single_result(
        item("OLD", "哈弗H6经典版", "哈弗H6经典版的置换礼是什么/以旧换新", "本品牌置换补贴10000元，外品牌置换补贴8000元。", "权益政策", "policy"),
        item("NEW", "哈弗H6经典版", "哈弗H6经典版置换补贴多少？", "本品牌车型置换补贴1万元，外品牌车型置换补贴8000元。", "置换补贴", "policy"),
    )

    assert_matched_not_added(result)


def test_finance_gift_matches_finance_policy():
    result = single_result(
        item("OLD", "哈弗H6L", "哈弗H6L的金融礼是什么/首付/免息/金融政策", "至高5万24期0息；首付低至百分之十。", "权益政策", "finance"),
        item("NEW", "哈弗H6L", "哈弗H6L有什么金融政策？", "至高5万元24期0息，首付百分之十起。", "金融政策", "finance"),
    )

    assert_matched_not_added(result)


def test_cash_gift_matches_current_discount():
    result = single_result(
        item("OLD", "哈弗H6L", "哈弗H6L的现金礼是什么？", "买哈弗H6L享14000元现金优惠。", "权益政策", "policy"),
        item("NEW", "哈弗H6L", "哈弗H6L现在优惠多少？", "购车即享1.4万元现金优惠。", "购车权益", "policy"),
    )

    assert_matched_not_added(result)


def test_model_alias_price_is_not_added():
    result = single_result(
        item("OLD", "哈弗猛龙PLUS", "哈弗猛龙PLUS价格", "指导价区间为12.99万到16.99万元。"),
        item("NEW", "猛龙PLUS", "猛龙PLUS多少钱？", "限时换新价11.99万元起。"),
    )

    assert result.change_type == ChangeType.UPDATED


def test_short_model_alias_finance_is_review_when_generation_is_ambiguous():
    result = single_result(
        item("OLD", "二代哈弗H9", "二代哈弗H9的金融礼是什么？/首付/金融政策/贷款/利息", "支持至高8万元24期0息。", "金融政策", "finance"),
        item("NEW", "H9", "H9有免息贷款吗？", "支持至高8万元24期0息。", "金融政策", "finance"),
    )

    assert result.change_type in {ChangeType.UNCHANGED, ChangeType.REVIEW_REQUIRED}
    assert result.change_type != ChangeType.ADDED


def test_h6_and_h6l_do_not_match():
    result = single_result(
        item("OLD", "哈弗H6", "哈弗H6价格", "10万元起。"),
        item("NEW", "哈弗H6L", "哈弗H6L价格", "11万元起。"),
    )

    assert result.change_type == ChangeType.ADDED


def test_menglong_and_menglong_plus_do_not_auto_update():
    result = single_result(
        item("OLD", "哈弗猛龙", "哈弗猛龙价格", "16万元起。"),
        item("NEW", "哈弗猛龙PLUS", "哈弗猛龙PLUS价格", "17万元起。"),
    )

    assert result.change_type in {ChangeType.ADDED, ChangeType.REVIEW_REQUIRED}
    assert result.change_type != ChangeType.UPDATED


def test_same_model_different_intents_do_not_match():
    result = single_result(
        item("OLD", "哈弗H6L", "哈弗H6L有什么金融政策？", "支持24期0息。", "金融政策", "finance"),
        item("NEW", "哈弗H6L", "哈弗H6L车机流量免费吗？", "基础流量终身免费。", "流量权益", "policy"),
    )

    assert result.change_type == ChangeType.ADDED


def test_same_model_price_and_trade_in_do_not_match():
    result = single_result(
        item("OLD", "二代哈弗H9", "二代哈弗H9价格是多少？", "17.49万元起。", "价格信息", "price"),
        item("NEW", "二代哈弗H9", "二代哈弗H9置换补贴多少？", "置换补贴10000元。", "置换补贴", "policy"),
    )

    assert result.change_type == ChangeType.ADDED
