"""Intent normalization for deterministic Diff matching."""

from __future__ import annotations

import re


PRICE = "PRICE"
CASH_DISCOUNT = "CASH_DISCOUNT"
TRADE_IN = "TRADE_IN"
FINANCE = "FINANCE"
WARRANTY = "WARRANTY"
TRAFFIC_SERVICE = "TRAFFIC_SERVICE"
CHARGING_BENEFIT = "CHARGING_BENEFIT"
GENERAL_BENEFIT = "GENERAL_BENEFIT"


INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    PRICE: ("多少钱", "价格", "售价", "指导价", "卖多少钱", "现在多少钱", "起售价", "报价", "价位"),
    CASH_DISCOUNT: ("现金优惠", "现金礼", "现金钜惠", "直降", "直享", "优惠力度", "优惠多少"),
    TRADE_IN: ("置换补贴", "置换礼", "增换购", "增购", "以旧换新", "旧车置换", "换购补贴"),
    FINANCE: ("金融政策", "金融礼", "贷款", "分期", "首付", "免息", "0息", "贴息", "年化利率", "年费率"),
    WARRANTY: ("质保", "保修", "质保礼", "终身质保", "整车质保"),
    TRAFFIC_SERVICE: ("免费流量", "车机流量", "娱乐流量", "基础流量", "流量权益", "流量礼"),
    CHARGING_BENEFIT: ("送充电桩", "充电桩权益", "免费安装", "充电权益", "充电桩"),
    GENERAL_BENEFIT: ("购车权益", "购车福利", "有什么优惠", "有什么活动", "有什么礼", "购车政策", "权益政策"),
}

RELATED_INTENTS: dict[str, set[str]] = {
    GENERAL_BENEFIT: {CASH_DISCOUNT, TRADE_IN, FINANCE, WARRANTY, TRAFFIC_SERVICE, CHARGING_BENEFIT},
    CASH_DISCOUNT: {GENERAL_BENEFIT},
    TRADE_IN: {GENERAL_BENEFIT},
    FINANCE: {GENERAL_BENEFIT},
    WARRANTY: {GENERAL_BENEFIT},
    TRAFFIC_SERVICE: {GENERAL_BENEFIT},
    CHARGING_BENEFIT: {GENERAL_BENEFIT},
}

GENERIC_BENEFIT_PATTERN = re.compile(r"(有什么|有哪些|享受|包括).{0,8}(权益|优惠|活动|礼|政策)")


def normalize_for_intent(*values: str | None) -> str:
    return "".join(str(value or "") for value in values).lower().replace(" ", "")


def normalize_intents(*values: str | None) -> set[str]:
    text = normalize_for_intent(*values)
    intents: set[str] = set()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords):
            intents.add(intent)

    if "优惠" in text and not ({CASH_DISCOUNT, TRADE_IN, FINANCE} & intents):
        intents.add(GENERAL_BENEFIT)
    if GENERIC_BENEFIT_PATTERN.search(text):
        intents.add(GENERAL_BENEFIT)

    return intents


def has_same_intent(left: set[str], right: set[str]) -> bool:
    return bool(left and right and left & right)


def has_related_intent(left: set[str], right: set[str]) -> bool:
    if has_same_intent(left, right):
        return True
    for intent in left:
        if RELATED_INTENTS.get(intent, set()) & right:
            return True
    return False


def specific_intents(intents: set[str]) -> set[str]:
    return intents - {GENERAL_BENEFIT}
