from diff.intent_normalizer import (
    CASH_DISCOUNT,
    FINANCE,
    GENERAL_BENEFIT,
    PRICE,
    TRADE_IN,
    TRAFFIC_SERVICE,
    WARRANTY,
    normalize_intents,
)


def test_intent_normalizer_maps_price_phrases():
    assert PRICE in normalize_intents("这车多少钱？", "价格信息")
    assert PRICE in normalize_intents("官方指导价是多少？")


def test_intent_normalizer_splits_specific_benefits():
    assert CASH_DISCOUNT in normalize_intents("现金礼是什么？")
    assert TRADE_IN in normalize_intents("置换补贴多少？")
    assert FINANCE in normalize_intents("贷款免息吗？")
    assert WARRANTY in normalize_intents("质保礼是什么？")
    assert TRAFFIC_SERVICE in normalize_intents("车机流量免费吗？")


def test_general_benefit_does_not_force_cash_discount():
    intents = normalize_intents("有什么购车权益？")

    assert GENERAL_BENEFIT in intents
    assert CASH_DISCOUNT not in intents
