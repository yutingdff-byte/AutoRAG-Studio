import json
import re

from agents.llm_client import call_llm
from facts.chunker import (
    DEFAULT_FACTS_CHUNK_MAX_CHARS,
    DEFAULT_FACTS_CHUNK_TARGET_CHARS,
    build_fact_chunks,
)
from facts.executor import execute_fact_chunks
from facts.merge import merge_record_fact_chunk_results
from facts.record_chunker import (
    DEFAULT_FACTS_RECORD_BATCH_MAX_CHARS,
    DEFAULT_FACTS_RECORD_BATCH_SIZE,
    build_record_batch_manifest,
    build_record_fact_chunks,
)
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


SOURCE_UNCERTAIN_PHRASES = [
    "图片内容无法确认",
    "无法确认",
    "未提供",
    "缺少",
]


PROTECTED_SOURCE_TERMS = [
    "CarPlay",
    "Android Auto",
    "HUAWEI HiCar",
    "ICCOA Carlink",
    "座椅通风",
    "通风",
    "后排座椅加热",
    "后排独立空调",
    "单独调温",
    "整车质保",
    "质保",
    "保养周期",
    "首付",
    "年化利率",
    "贷款",
    "最长可贷",
    "利率",
]


HIGH_RISK_FACT_CATEGORIES = [
    "金融",
    "权益",
    "活动",
    "政策",
    "售后",
    "质保",
    "保养",
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


def _normalize_grounding_text(value):

    return re.sub(
        r"\s+",
        "",
        str(
            value or ""
        ).lower()
    )


def _extract_numeric_tokens(value):

    tokens = []

    for match in re.finditer(
        r"(?<![A-Za-z])\d+(?:\.\d+)?(?![A-Za-z])",
        str(
            value or ""
        )
    ):

        token = match.group(
            0
        )

        if token not in tokens:

            tokens.append(
                token
            )

    return tokens


def _has_source_uncertainty_near_topic(material, fact):

    category_text = " ".join(
        str(
            fact.get(
                field,
                ""
            )
        )
        for field in [
            "category",
            "content",
            "source"
        ]
    )

    if not any(
        keyword in category_text
        for keyword in HIGH_RISK_FACT_CATEGORIES
    ):

        return False

    material_text = str(
        material or ""
    )

    for keyword in HIGH_RISK_FACT_CATEGORIES:

        if keyword not in category_text:

            continue

        pattern = re.compile(
            rf"{re.escape(keyword)}.{{0,30}}("
            + "|".join(
                re.escape(
                    phrase
                )
                for phrase in SOURCE_UNCERTAIN_PHRASES
            )
            + ")"
        )

        if pattern.search(
            material_text
        ):

            return True

    return False


def _find_ungrounded_fact_reason(fact, material):

    if not isinstance(
        fact,
        dict
    ):

        return "fact is not a dict"

    material_norm = _normalize_grounding_text(
        material
    )

    content = str(
        fact.get(
            "content",
            ""
        )
    )

    category = str(
        fact.get(
            "category",
            ""
        )
    )

    trim = str(
        fact.get(
            "trim",
            ""
        )
    )

    material_text = str(
        material or ""
    )

    if "座椅" in content and "通风" in content:

        if not re.search(
            r"座椅.{0,12}通风|通风.{0,12}座椅",
            material_text
        ):

            return "seat ventilation is not grounded in material"

    if "后排座椅" in content and "加热" in content:

        if not re.search(
            r"后排座椅.{0,12}加热|加热.{0,12}后排座椅",
            material_text
        ):

            return "rear seat heating is not grounded in material"

    if "后排独立空调" in content:

        if "后排独立空调" not in material_text:

            return "rear independent air conditioning is not grounded in material"

    if any(
        keyword in content
        for keyword in [
            "手机互联",
            "车机",
            "HiCar",
            "Carlink",
            "CarPlay",
            "Android Auto",
        ]
    ):

        has_cn_ecosystem = any(
            keyword in content
            for keyword in [
                "HUAWEI HiCar",
                "ICCOA Carlink",
            ]
        )

        has_foreign_ecosystem = any(
            keyword in content
            for keyword in [
                "CarPlay",
                "Android Auto",
            ]
        )

        if has_cn_ecosystem and has_foreign_ecosystem:

            return "mixed mobile interconnect systems require source confirmation"

    should_check_numbers = any(
        keyword in f"{category} {content}"
        for keyword in [
            "价格",
            "售价",
            "后备箱",
            "空间",
            "尺寸",
            "轴距",
            "金融",
            "权益",
            "活动",
            "质保",
            "保养",
        ]
    )

    if should_check_numbers:

        number_text = content

        if "版本" in category or "差异" in category:

            number_text = f"{trim} {content}"

        for token in _extract_numeric_tokens(
            number_text
        ):

            if token not in material_norm:

                return f"numeric token not found in material: {token}"

    for term in PROTECTED_SOURCE_TERMS:

        if term.lower() not in content.lower():

            continue

        if _normalize_grounding_text(
            term
        ) not in material_norm:

            return f"protected term not found in material: {term}"

    if (
        any(
            version in f"{trim} {content}"
            for version in [
                "豪华版",
                "尊贵版",
            ]
        )
        and (
            "版本" in category
            or "差异" in category
            or "豪华版" in content
            or "尊贵版" in content
        )
        and not all(
            version in str(
                material or ""
            )
            for version in [
                "豪华版",
                "尊贵版",
            ]
        )
    ):

        return "trim versions not found in material"

    if _has_source_uncertainty_near_topic(
        material,
        fact
    ):

        return "material marks this high-risk topic as uncertain"

    return ""


def _renumber_facts(facts):

    for index, fact in enumerate(
        facts,
        start=1
    ):

        if isinstance(
            fact,
            dict
        ):

            fact[
                "fact_id"
            ] = f"F{index:03d}"


def apply_material_grounding_guard(data, material):

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

    kept = []

    removed = []

    for fact in facts:

        reason = _find_ungrounded_fact_reason(
            fact,
            material
        )

        if reason:

            removed.append(
                {
                    "fact": fact,
                    "reason": reason
                }
            )

            continue

        kept.append(
            fact
        )

    if not removed:

        return data

    data[
        "facts"
    ] = kept

    _renumber_facts(
        kept
    )

    info_gaps = data.setdefault(
        "info_gaps",
        []
    )

    for index, item in enumerate(
        removed,
        start=len(
            info_gaps
        ) + 1
    ):

        fact = item[
            "fact"
        ]

        info_gaps.append(
            {
                "gap_id": f"G{index:03d}",
                "gap_type": "业务规则缺失",
                "missing_content": (
                    "疑似缺少原始资料支撑的事实已被阻断："
                    + str(
                        fact.get(
                            "content",
                            ""
                        )
                    )
                ),
                "impact_module": fact.get(
                    "category",
                    ""
                ),
                "impact_level": "高",
                "description": item[
                    "reason"
                ]
            }
        )

    data[
        "material_grounding_removed"
    ] = len(
        removed
    )

    data[
        "material_grounding_removed_items"
    ] = [
        {
            "fact_id": item["fact"].get(
                "fact_id",
                ""
            ),
            "category": item["fact"].get(
                "category",
                ""
            ),
            "content": item["fact"].get(
                "content",
                ""
            ),
            "reason": item[
                "reason"
            ]
        }
        for item in removed
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

        data = normalize_fact_knowledge_type(
            data
        )

        return apply_material_grounding_guard(
            data,
            material
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


def _record_chunks_for_material(material):
    batch_size = _get_int_config(
        "FACTS_RECORD_BATCH_SIZE",
        DEFAULT_FACTS_RECORD_BATCH_SIZE
    )
    max_chars = _get_int_config(
        "FACTS_RECORD_BATCH_MAX_CHARS",
        DEFAULT_FACTS_RECORD_BATCH_MAX_CHARS
    )
    return build_record_fact_chunks(
        material,
        batch_size=batch_size,
        max_chars=max_chars
    )


def _has_vehicle_record_chunks(chunks):
    return any(
        bool(chunk.record_ids)
        for chunk in chunks
    )


def _extract_facts_record_aware(material, chunks=None):
    chunks = chunks if chunks is not None else _record_chunks_for_material(
        material
    )
    if not chunks or not _has_vehicle_record_chunks(
        chunks
    ):
        raise RuntimeError(
            "Record-aware Facts preparation failed: no vehicle records found"
        )

    max_concurrency = _get_int_config(
        "FACTS_MAX_CONCURRENCY",
        2
    )
    manifest = build_record_batch_manifest(
        chunks
    )

    print("[FACTS Performance]")
    print("mode: record_aware")
    print(f"document_chars: {len(str(material or ''))}")
    print(f"vehicle_records: {sum(item['record_count'] for item in manifest)}")
    print(f"batch_count: {len(chunks)}")
    print(f"record_batch_size: {_get_int_config('FACTS_RECORD_BATCH_SIZE', DEFAULT_FACTS_RECORD_BATCH_SIZE)}")
    print(f"record_batch_max_chars: {_get_int_config('FACTS_RECORD_BATCH_MAX_CHARS', DEFAULT_FACTS_RECORD_BATCH_MAX_CHARS)}")
    print(f"max_concurrency: {max_concurrency}")

    result = execute_fact_chunks(
        chunks,
        _extract_facts_single,
        max_concurrency=max_concurrency,
        merge_func=lambda results: merge_record_fact_chunk_results(
            results,
            chunks
        )
    )
    report = result.get(
        "chunk_report",
        {}
    )
    report[
        "record_batch_manifest"
    ] = manifest
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
        "auto"
    ).strip().lower()

    if mode == "auto":
        chunks = _record_chunks_for_material(
            material
        )
        if _has_vehicle_record_chunks(
            chunks
        ):
            return _extract_facts_record_aware(
                material,
                chunks=chunks
            )
        return _extract_facts_single(
            material
        )

    if mode == "chunked":
        return _extract_facts_chunked(
            material
        )

    if mode == "record_aware":
        return _extract_facts_record_aware(
            material
        )

    return _extract_facts_single(
        material
    )
