import json
import re

from agents.llm_client import call_llm


STATIC_KEYWORDS = [
    "品牌",
    "车型",
    "定位",
    "配置",
    "参数",
    "功能",
    "体验",
    "外观",
    "内饰",
    "空间",
    "座椅",
    "舒适",
    "动力",
    "续航",
    "补能",
    "智驾",
    "智能",
    "智舱",
    "座舱",
    "安全",
    "尺寸",
    "版本"
]


DYNAMIC_KEYWORDS = [
    "价格",
    "售价",
    "金融",
    "优惠",
    "权益",
    "活动",
    "政策",
    "补贴"
]


def infer_knowledge_type(category, content=""):

    text = (
        f"{category} {content}"
    )

    if any(
        keyword in text
        for keyword in DYNAMIC_KEYWORDS
    ):

        return "dynamic"

    if any(
        keyword in text
        for keyword in STATIC_KEYWORDS
    ):

        return "static"

    return "static"


def infer_vehicle_parts(data):

    text = " ".join(
        str(value)
        for value in [
            data.get(
                "brand",
                ""
            ),
            data.get(
                "model",
                ""
            ),
            data.get(
                "trim",
                ""
            ),
            data.get(
                "vehicle",
                ""
            ),
            data.get(
                "category",
                ""
            ),
            data.get(
                "content",
                ""
            ),
            data.get(
                "source",
                ""
            )
        ]
        if value
    )

    brand = data.get(
        "brand",
        ""
    )

    model = data.get(
        "model",
        ""
    )

    trim = data.get(
        "trim",
        ""
    )

    vehicle = data.get(
        "vehicle",
        ""
    )

    if not brand and (
        "东风日产" in text
        or "日产" in text
        or "N6" in text
    ):

        brand = "东风日产"

    if not model:

        model_match = re.search(
            r"(?<![A-Za-z0-9])N6(?![A-Za-z0-9])",
            text,
            re.IGNORECASE
        )

        if model_match:

            model = model_match.group(
                0
            ).upper()

        elif vehicle and vehicle not in [
            "全系",
            "品牌级",
            "需确认"
        ]:

            vehicle_model_match = re.search(
                r"(?<![A-Za-z0-9])([A-Za-z]+\d+)(?![A-Za-z0-9])",
                vehicle
            )

            if vehicle_model_match:

                model = vehicle_model_match.group(
                    1
                ).upper()

    if not trim:

        full_series_pattern = (
            f"{model}\\s*全系"
            if model
            else r"N6\s*全系"
        )

        if re.search(
            full_series_pattern,
            text,
            re.IGNORECASE
        ):

            trim = "全系"

        elif vehicle and vehicle not in [
            model,
            "品牌级",
            "需确认"
        ]:

            trim_text = vehicle

            if model:

                trim_text = re.sub(
                    rf"\b{re.escape(model)}\b",
                    "",
                    trim_text,
                    flags=re.IGNORECASE
                ).strip()

            if trim_text:

                trim = trim_text

        elif model:

            trim_match = re.search(
                rf"\b{re.escape(model)}\b\s+([0-9A-Za-z][0-9A-Za-z\s\+\-]*?(?:Pro\+|Pro|Max|Plus|悦享版|智享版|旗舰版|版))",
                text,
                re.IGNORECASE
            )

            if trim_match:

                trim = trim_match.group(
                    1
                ).strip()

    return {
        "brand": brand,
        "model": model,
        "trim": trim
    }


def normalize_fact_vehicle_fields(fact):

    vehicle_parts = infer_vehicle_parts(
        fact
    )

    for field in [
        "brand",
        "model",
        "trim"
    ]:

        if not fact.get(
            field
        ):

            fact[
                field
            ] = vehicle_parts.get(
                field,
                ""
            )

    fact.pop(
        "vehicle",
        None
    )


def normalize_fact_knowledge_type(data):

    if not isinstance(
        data,
        dict
    ):

        return data

    facts = data.get(
        "facts",
        []
    )

    if not isinstance(
        facts,
        list
    ):

        return data

    for fact in facts:

        if not isinstance(
            fact,
            dict
        ):

            continue

        normalize_fact_vehicle_fields(
            fact
        )

        knowledge_type = fact.get(
            "knowledge_type",
            ""
        )

        if knowledge_type not in [
            "static",
            "dynamic"
        ]:

            fact[
                "knowledge_type"
            ] = infer_knowledge_type(
                fact.get(
                    "category",
                    ""
                ),
                fact.get(
                    "content",
                    ""
                )
            )

    return data


def extract_facts(material):

    """
    Step1:
    从车型资料中抽取事实信息

    参数:
        material:
            用户上传资料文本

    返回:
        facts json
    """


    # 读取Prompt

    with open(
        "prompts/step1_prompt.txt",
        "r",
        encoding="utf-8"
    ) as f:

        system_prompt = f.read()


    # 调用大模型

    result = call_llm(
        system_prompt,
        material
    )


    # 转JSON

    try:

        from utils.json_parser import parse_json
        data = parse_json(result)

        return normalize_fact_knowledge_type(
            data
        )


    except Exception:

        print("JSON解析失败")
        print(result)

        return None
