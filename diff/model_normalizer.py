"""Model normalization and conservative relation detection for Diff."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from utils.rag_quality import normalize_model_name


class ModelRelation(str, Enum):
    EXACT = "EXACT"
    ALIAS = "ALIAS"
    FAMILY = "FAMILY"
    VARIANT = "VARIANT"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"


BRAND_PREFIXES = ("哈弗", "长城", "魏牌", "坦克")
VARIANT_WORDS = ("燃油版", "PHEV", "插混版", "纯电版", "经典版", "国潮版", "汽油版")


@dataclass(slots=True)
class NormalizedModel:
    raw: str
    canonical: str
    without_brand: str
    family: str
    variant: str
    is_short_alias: bool = False


def _clean(value: str | None) -> str:
    text = normalize_model_name(str(value or "").strip())
    text = text.replace(" ", "").replace("＋", "+")
    text = re.sub(r"(?i)plus", "PLUS", text)
    return text


def _strip_brand(value: str) -> str:
    for prefix in BRAND_PREFIXES:
        if value.startswith(prefix) and len(value) > len(prefix):
            return value[len(prefix) :]
    return value


def _split_variant(value: str) -> tuple[str, str]:
    for word in VARIANT_WORDS:
        if value.endswith(word) and len(value) > len(word):
            return value[: -len(word)], word
    return value, ""


def normalize_model(value: str | None) -> NormalizedModel:
    canonical = _clean(value)
    without_brand = _strip_brand(canonical)
    family, variant = _split_variant(without_brand)
    is_short_alias = bool(re.fullmatch(r"[A-Za-z]?\d+[A-Za-z]?", without_brand))
    return NormalizedModel(
        raw=str(value or ""),
        canonical=canonical,
        without_brand=without_brand,
        family=family,
        variant=variant,
        is_short_alias=is_short_alias,
    )


def model_relation(left: str | None, right: str | None) -> ModelRelation:
    left_model = normalize_model(left)
    right_model = normalize_model(right)

    if not left_model.canonical or not right_model.canonical:
        return ModelRelation.UNKNOWN
    if left_model.canonical == right_model.canonical:
        return ModelRelation.EXACT
    if left_model.without_brand == right_model.without_brand:
        return ModelRelation.ALIAS

    if left_model.is_short_alias or right_model.is_short_alias:
        short = left_model.without_brand if left_model.is_short_alias else right_model.without_brand
        long = right_model.without_brand if left_model.is_short_alias else left_model.without_brand
        if short and long.endswith(short):
            return ModelRelation.ALIAS

    if left_model.family and right_model.family and left_model.family == right_model.family:
        if left_model.variant != right_model.variant:
            return ModelRelation.VARIANT
        return ModelRelation.FAMILY

    if left_model.without_brand and right_model.without_brand:
        pairs = [
            (left_model.without_brand, right_model.without_brand),
            (right_model.without_brand, left_model.without_brand),
        ]
        for longer, shorter in pairs:
            if longer.startswith(shorter):
                suffix = longer[len(shorter) :]
                if re.fullmatch(r"[A-Za-z0-9]+", shorter) and re.fullmatch(r"[A-Za-z0-9]+", suffix):
                    return ModelRelation.CONFLICT
                return ModelRelation.FAMILY

    return ModelRelation.CONFLICT


def is_strong_model_relation(relation: ModelRelation) -> bool:
    return relation in {ModelRelation.EXACT, ModelRelation.ALIAS}


def is_related_model_relation(relation: ModelRelation) -> bool:
    return relation in {ModelRelation.EXACT, ModelRelation.ALIAS, ModelRelation.FAMILY, ModelRelation.VARIANT}
