"""Knowledge normalization helpers used only by Diff internals."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from knowledge.models import KnowledgeItem


QUESTION_FILLERS = [
    "请问",
    "想问一下",
    "麻烦问下",
    "这个",
    "这款车",
    "的",
    "是多少",
    "多少",
    "怎么样",
    "吗",
    "呢",
    "？",
    "?",
]

QUESTION_PHRASE_MAP = {
    "多少钱": "价格",
    "什么价位": "价格",
    "价格是多少": "价格",
    "官方指导价多少": "价格",
    "官方指导价是多少": "价格",
    "起售价多少": "价格",
    "续航是多少": "续航",
    "续航多少": "续航",
}

TOPIC_KEYWORDS = {
    "official_price": ["价格", "售价", "指导价", "多少钱", "价位", "起售价", "元起", "万元"],
    "finance": ["金融", "贷款", "分期", "免息", "贴息", "首付", "月供", "费率"],
    "benefit": ["权益", "优惠", "补贴", "赠送", "抵扣", "活动", "礼包"],
    "range": ["续航", "cltc", "公里", "电池"],
    "charging": ["补能", "充电", "快充", "超充"],
    "space": ["空间", "轴距", "车长", "尺寸"],
    "power": ["动力", "电机", "扭矩", "功率", "加速"],
    "adas": ["智驾", "辅助驾驶", "领航", "泊车", "ads", "nca", "lcc"],
    "config": ["配置", "座椅", "屏幕", "音响", "车机", "功能"],
    "warranty": ["质保", "保修", "道路救援", "售后"],
}


@dataclass(slots=True)
class NormalizedKnowledge:
    item: KnowledgeItem
    normalized_question: str
    normalized_answer: str
    topic: str
    signature: str
    numbers: list[str]


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    text = re.sub(r"\s+", "", text)
    text = text.replace("，", ",").replace("。", ".").replace("？", "?")
    return text


def normalize_question_text(value: str | None) -> str:
    text = normalize_text(value)
    for source, target in QUESTION_PHRASE_MAP.items():
        text = text.replace(normalize_text(source), normalize_text(target))
    for filler in QUESTION_FILLERS:
        text = text.replace(filler, "")
    text = re.sub(r"[,.!！:：;；、]", "", text)
    return text


def normalize_answer_text(value: str | None) -> str:
    text = normalize_text(value)
    text = re.sub(r"(\d+),(\d{3})(?=元)", r"\1\2", text)
    text = re.sub(r"(\d+)\s*元", r"\1元", text)
    text = text.replace("人民币", "")
    text = re.sub(r"[，。,.!！;；]", "", text)
    return text


def extract_numbers(value: str | None) -> list[str]:
    text = normalize_text(value)
    return re.findall(r"\d+(?:\.\d+)?%?|\d+(?:\.\d+)?万?元|\d+(?:\.\d+)?公里", text)


def detect_topic(item: KnowledgeItem) -> str:
    text = normalize_text(
        " ".join(
            [
                item.question,
                item.category,
                item.module or "",
                item.knowledge_type or "",
                item.answer,
            ]
        )
    )
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(normalize_text(keyword) in text for keyword in keywords):
            return topic
    return "general"


def normalize_field(value: str | None) -> str:
    return normalize_text(value)


def build_signature(item: KnowledgeItem, topic: str | None = None) -> str:
    detected_topic = topic or detect_topic(item)
    return "|".join(
        [
            normalize_field(item.brand),
            normalize_field(item.model),
            normalize_field(item.trim),
            normalize_field(item.knowledge_type),
            detected_topic,
        ]
    )


def normalize_item(item: KnowledgeItem) -> NormalizedKnowledge:
    topic = detect_topic(item)
    return NormalizedKnowledge(
        item=item,
        normalized_question=normalize_question_text(item.question),
        normalized_answer=normalize_answer_text(item.answer),
        topic=topic,
        signature=build_signature(item, topic),
        numbers=extract_numbers(item.answer),
    )
