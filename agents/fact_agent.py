import json
import re

from agents.llm_client import call_llm
from facts.chunker import (
    DEFAULT_FACTS_CHUNK_MAX_CHARS,
    DEFAULT_FACTS_CHUNK_TARGET_CHARS,
    build_fact_chunks,
)
from facts.executor import execute_fact_chunks
from utils.config import get_config


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


POLICY_DATE_RANGE_PATTERN = re.compile(
    r"(\d{4})年(\d{1,2})月(\d{1,2})日"
    r"(?:至|到|-|—|~)"
    r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日"
)


POLICY_DATE_SLASH_RANGE_PATTERN = re.compile(
    r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})"
    r".{0,30}?"
    r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})"
)


POLICY_MONTH_PATTERN = re.compile(
    r"(\d{4})年(\d{1,2})月|"
    r"(\d{4})[/-](\d{1,2})[/-]\d{1,2}"
)


def format_date(year, month, day):

    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def infer_policy_dates(text):

    text = str(
        text or ""
    )

    match = POLICY_DATE_RANGE_PATTERN.search(
        text
    )

    if match:

        start_year = match.group(1)
        start_month = match.group(2)
        start_day = match.group(3)
        end_year = match.group(4) or start_year
        end_month = match.group(5)
        end_day = match.group(6)

        return {
            "policy_period": f"{start_year}年{int(start_month)}月",
            "effective_date": format_date(
                start_year,
                start_month,
                start_day
            ),
            "expire_date": format_date(
                end_year,
                end_month,
                end_day
            )
        }

    match = POLICY_DATE_SLASH_RANGE_PATTERN.search(
        text
    )

    if match:

        return {
            "policy_period": f"{match.group(1)}年{int(match.group(2))}月",
            "effective_date": format_date(
                match.group(1),
                match.group(2),
                match.group(3)
            ),
            "expire_date": format_date(
                match.group(4),
                match.group(5),
                match.group(6)
            )
        }

    match = POLICY_MONTH_PATTERN.search(
        text
    )

    if match:

        year = match.group(1) or match.group(3)
        month = match.group(2) or match.group(4)

        return {
            "policy_period": f"{year}年{int(month)}月",
            "effective_date": "unknown",
            "expire_date": "unknown"
        }

    return {
        "policy_period": "unknown",
        "effective_date": "unknown",
        "expire_date": "unknown"
    }


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

        if not fact.get(
            "source_file"
        ):

            fact[
                "source_file"
            ] = "unknown"

        policy_dates = infer_policy_dates(
            " ".join(
                str(
                    fact.get(
                        field,
                        ""
                    )
                )
                for field in [
                    "content",
                    "source"
                ]
            )
        )

        for field in [
            "policy_period",
            "effective_date",
            "expire_date"
        ]:

            if not fact.get(
                field
            ):

                fact[
                    field
                ] = policy_dates[
                    field
                ]

    return data


def _read_fact_prompt():
    with open(
        "prompts/step1_prompt.txt",
        "r",
        encoding="utf-8"
    ) as f:

        return f.read()


def _extract_facts_single(material):

    system_prompt = _read_fact_prompt()


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


def _get_int_config(name, default):
    value = get_config(
        name,
        str(default)
    )
    try:
        return int(
            value
        )
    except (TypeError, ValueError):
        return default


def _extract_facts_chunked(material):
    target_chars = _get_int_config(
        "FACTS_CHUNK_TARGET_CHARS",
        DEFAULT_FACTS_CHUNK_TARGET_CHARS
    )
    max_chars = _get_int_config(
        "FACTS_CHUNK_MAX_CHARS",
        DEFAULT_FACTS_CHUNK_MAX_CHARS
    )
    max_concurrency = _get_int_config(
        "FACTS_MAX_CONCURRENCY",
        2
    )

    chunks = build_fact_chunks(
        material,
        target_chars=target_chars,
        max_chars=max_chars
    )

    print("[FACTS Performance]")
    print("mode: chunked")
    print(f"document_chars: {len(str(material or ''))}")
    print(f"chunk_count: {len(chunks)}")
    print(f"chunk_target_chars: {target_chars}")
    print(f"chunk_max_chars: {max_chars}")
    print(f"max_concurrency: {max_concurrency}")

    result = execute_fact_chunks(
        chunks,
        _extract_facts_single,
        max_concurrency=max_concurrency
    )
    report = result.get(
        "chunk_report",
        {}
    )
    print(f"request_count: {report.get('request_count', 0)}")
    print(f"raw_facts: {report.get('raw_facts', 0)}")
    print(f"exact_duplicates_removed: {report.get('exact_duplicates_removed', 0)}")
    print(f"final_facts: {report.get('final_facts', 0)}")
    print(f"facts_wall_time: {report.get('wall_time', 0)}")
    return normalize_fact_knowledge_type(
        result
    )


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

    mode = get_config(
        "FACTS_MODE",
        "single"
    ).strip().lower()

    if mode == "chunked":
        return _extract_facts_chunked(
            material
        )

    return _extract_facts_single(
        material
    )
