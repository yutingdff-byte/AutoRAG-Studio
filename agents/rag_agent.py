import json
import re
from collections import defaultdict

from agents.llm_client import call_llm
from utils import rag_quality


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


VERSION_SPECIFIC_DYNAMIC_KEYWORDS = [
    "价格",
    "售价",
    "指导价"
]


PRICE_KEYWORDS = [
    "价格",
    "售价",
    "指导价",
    "多少钱",
    "价位",
    "起售价"
]


VERSION_RANGE_KEYWORDS = [
    "Pro",
    "Max",
    "旗舰",
    "黑骑士",
    "青春版",
    "+"
]


ANSWER_REPLACEMENTS = [
    ("N·m", "牛米"),
    ("N.m", "牛米"),
    ("kWh", "度电"),
    ("kW", "千瓦"),
    ("km", "公里"),
    ("mm", "毫米"),
    ("Ps", "匹"),
    (" V", " 伏"),
    ("ADS", "ADS智能驾驶辅助系统"),
    ("APA", "自动泊车"),
    ("RPA", "遥控泊车"),
    ("LCC", "车道居中辅助"),
    ("NCA", "高速领航辅助")
]


def normalize_answer_for_tts(answer):

    return rag_quality.normalize_answer_for_tts(
        answer
    )


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


def normalize_text(value):

    text = str(
        value or ""
    ).lower()

    text = re.sub(
        r"\s+",
        "",
        text
    )

    text = re.sub(
        r"[，。！？、,.!?；;：:\-_/\\|（）()【】\[\]\"']",
        "",
        text
    )

    return text


def get_question_text(item):

    questions = item.get(
        "questions",
        []
    )

    if isinstance(
        questions,
        list
    ):

        return " ".join(
            str(question)
            for question in questions
            if question
        )

    return str(
        questions or ""
    )


def is_version_specific_dynamic_fact(fact):

    if fact.get(
        "knowledge_type"
    ) != "dynamic":

        return False

    text = (
        f"{fact.get('category', '')} "
        f"{fact.get('content', '')}"
    )

    return any(
        keyword in text
        for keyword in VERSION_SPECIFIC_DYNAMIC_KEYWORDS
    )


def summarize_trim_values(trims):

    cleaned = []

    for trim in trims:

        if not trim:

            continue

        if trim not in cleaned:

            cleaned.append(
                trim
            )

    if not cleaned:

        return ""

    if "全系" in cleaned:

        return "全系"

    if len(
        cleaned
    ) == 1:

        return cleaned[0]

    if len(
        cleaned
    ) <= 3:

        return " / ".join(
            cleaned
        )

    if all(
        "180" in trim
        for trim in cleaned
    ):

        return "180系列部分版本"

    return "不同版本"


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
                "module",
                ""
            ),
            data.get(
                "answer",
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


def normalize_vehicle_fields(item, ref_facts=None):

    ref_facts = ref_facts or []

    vehicle_parts = infer_vehicle_parts(
        item
    )

    for field in [
        "brand",
        "model",
        "trim"
    ]:

        if not item.get(
            field
        ):

            inherited_value = ""

            for fact in ref_facts:

                inherited_value = fact.get(
                    field,
                    ""
                )

                if inherited_value:

                    break

            item[
                field
            ] = (
                inherited_value
                or
                vehicle_parts.get(
                    field,
                    ""
                )
            )

    item.pop(
        "vehicle",
        None
    )

    item[
        "model_normalized"
    ] = rag_quality.normalize_model_name(
        item.get(
            "model",
            ""
        )
    )

    if item.get(
        "model"
    ) and not item.get(
        "model_display_name"
    ):

        item[
            "model_display_name"
        ] = item.get(
            "model",
            ""
        )


def build_fact_index(facts):

    fact_index = {}

    for fact in facts:

        if not isinstance(
            fact,
            dict
        ):

            continue

        fact_id = fact.get(
            "fact_id"
        )

        if fact_id:

            fact_index[
                fact_id
            ] = fact

    return fact_index


def normalize_rag_metadata(result, fact_index):

    if not isinstance(
        result,
        dict
    ):

        return result

    for rag in result.get(
        "rag_knowledge",
        []
    ):

        if not isinstance(
            rag,
            dict
        ):

            continue

        refs = rag.get(
            "fact_refs",
            []
        )

        if not isinstance(
            refs,
            list
        ):

            refs = [
                refs
            ]

        ref_facts = [
            fact_index.get(
                ref
            )
            for ref in refs
            if fact_index.get(
                ref
            )
        ]

        normalize_vehicle_fields(
            rag,
            ref_facts
        )

        if rag.get(
            "knowledge_type"
        ) not in [
            "static",
            "dynamic"
        ]:

            if any(
                fact.get(
                    "knowledge_type"
                ) == "dynamic"
                for fact in ref_facts
            ):

                rag[
                    "knowledge_type"
                ] = "dynamic"

            elif ref_facts:

                rag[
                    "knowledge_type"
                ] = "static"

            else:

                rag[
                    "knowledge_type"
                ] = infer_knowledge_type(
                    rag.get(
                        "category",
                        rag.get(
                            "module",
                            ""
                        )
                    ),
                    rag.get(
                        "answer",
                        ""
                    )
                )

        if not rag.get(
            "category"
        ):

            if ref_facts:

                rag[
                    "category"
                ] = ref_facts[0].get(
                    "category",
                    rag.get(
                        "module",
                        ""
                    )
                )

            else:

                rag[
                    "category"
                ] = rag.get(
                    "module",
                    ""
                )

        normalize_trim_scope(
            rag
        )

        rag[
            "answer"
        ] = normalize_answer_for_tts(
            rag.get(
                "answer",
                ""
            )
        )

    return result


def normalize_trim_scope(rag):

    answer = rag.get(
        "answer",
        ""
    )

    scope = rag.get(
        "适用范围",
        ""
    )

    text = (
        f"{answer} {scope}"
    )

    mentioned_versions = [
        keyword
        for keyword in VERSION_RANGE_KEYWORDS
        if keyword in text
    ]

    trim = rag.get(
        "trim",
        ""
    )

    if trim in [
        "",
        "需确认"
    ]:

        return

    if trim == "全系":

        return

    if len(
        mentioned_versions
    ) >= 2 and not all(
        keyword in trim
        for keyword in mentioned_versions
    ):

        rag[
            "trim"
        ] = "不同版本"


def make_generation_group_key(fact):

    category = fact.get(
        "category",
        "其他"
    )

    if is_version_specific_dynamic_fact(
        fact
    ):

        return (
            fact.get(
                "brand",
                ""
            ),
            fact.get(
                "model",
                ""
            ),
            fact.get(
                "trim",
                ""
            ),
            category,
            fact.get(
                "knowledge_type",
                ""
            )
        )

    return (
        fact.get(
            "brand",
            ""
        ),
        fact.get(
            "model",
            ""
        ),
        category,
        fact.get(
            "knowledge_type",
            ""
        )
    )


def add_aggregation_hints(groups):

    for group in groups:

        trims = [
            fact.get(
                "trim",
                ""
            )
            for fact in group
            if isinstance(
                fact,
                dict
            )
        ]

        trim_scope = summarize_trim_values(
            trims
        )

        content_groups = defaultdict(list)

        for fact in group:

            if not isinstance(
                fact,
                dict
            ):

                continue

            content_groups[
                normalize_text(
                    fact.get(
                        "content",
                        ""
                    )
                )
            ].append(
                fact.get(
                    "trim",
                    ""
                )
            )

        repeated_content = any(
            len(
                set(
                    trim
                    for trim in trim_list
                    if trim
                )
            ) > 1
            for trim_list in content_groups.values()
        )

        for fact in group:

            if not isinstance(
                fact,
                dict
            ):

                continue

            fact[
                "trim_scope"
            ] = trim_scope

            if repeated_content:

                fact[
                    "aggregation_hint"
                ] = (
                    "多个版本存在相同或相近事实，RAG层应合并为车型级或版本组知识，"
                    "不要逐版本重复生成FAQ。"
                )

            else:

                fact[
                    "aggregation_hint"
                ] = (
                    "优先生成车型级知识；只有影响购车决策的明显版本差异才拆成版本级RAG。"
                )


    return groups


def dedupe_rag_items(rag_items):

    deduped = []

    seen = {}

    for item in rag_items:

        if not isinstance(
            item,
            dict
        ):

            continue

        question_key = normalize_text(
            get_question_text(
                item
            )
        )

        answer_key = normalize_text(
            item.get(
                "answer",
                ""
            )
        )

        key = (
            item.get(
                "model",
                ""
            ),
            item.get(
                "category",
                item.get(
                    "module",
                    ""
                )
            ),
            item.get(
                "module",
                ""
            ),
            question_key,
            answer_key[:80]
        )

        if key in seen:

            existing = seen[
                key
            ]

            existing[
                "trim"
            ] = summarize_trim_values(
                [
                    existing.get(
                        "trim",
                        ""
                    ),
                    item.get(
                        "trim",
                        ""
                    )
                ]
            ) or existing.get(
                "trim",
                ""
            )

            existing_refs = existing.get(
                "fact_refs",
                []
            )

            item_refs = item.get(
                "fact_refs",
                []
            )

            if not isinstance(
                existing_refs,
                list
            ):

                existing_refs = [
                    existing_refs
                ]

            if not isinstance(
                item_refs,
                list
            ):

                item_refs = [
                    item_refs
                ]

            existing[
                "fact_refs"
            ] = list(
                dict.fromkeys(
                    existing_refs
                    + item_refs
                )
            )

            continue

        seen[
            key
        ] = item

        deduped.append(
            item
        )

    for index, item in enumerate(
        deduped,
        start=1
    ):

        item[
            "rag_id"
        ] = f"RAG-{index:03d}"

    return deduped


def parse_price_number(text):

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*万",
        text
    )

    if match:

        return float(
            match.group(1)
        )

    match = re.search(
        r"(\d{5,6})\s*元",
        text
    )

    if match:

        return int(
            match.group(1)
        ) / 10000

    return None


def format_price(value):

    text = f"{value:.2f}".rstrip("0").rstrip(".")

    return f"{text}万元"


def is_price_rag(item):

    text = (
        f"{item.get('category', '')} "
        f"{item.get('module', '')} "
        f"{get_question_text(item)} "
        f"{item.get('answer', '')}"
    )

    return any(
        keyword in text
        for keyword in PRICE_KEYWORDS
    )


def has_model_price_overview(rag_items, model):

    for item in rag_items:

        if not isinstance(
            item,
            dict
        ):

            continue

        if item.get(
            "model"
        ) != model:

            continue

        if item.get(
            "trim"
        ) not in [
            "全系",
            "不同版本",
            ""
        ]:

            continue

        if is_price_rag(
            item
        ):

            return True

    return False


def collect_price_facts(facts):

    price_facts_by_model = defaultdict(list)

    for fact in facts:

        if not isinstance(
            fact,
            dict
        ):

            continue

        text = (
            f"{fact.get('category', '')} "
            f"{fact.get('content', '')}"
        )

        if not any(
            keyword in text
            for keyword in PRICE_KEYWORDS
        ):

            continue

        model = fact.get(
            "model",
            ""
        )

        if model:

            price_facts_by_model[
                model
            ].append(
                fact
            )

    return price_facts_by_model


def build_model_price_answer(price_facts):

    prices = [
        parse_price_number(
            fact.get(
                "content",
                ""
            )
        )
        for fact in price_facts
    ]

    prices = [
        price
        for price in prices
        if price is not None
    ]

    combined_content = "；".join(
        fact.get(
            "content",
            ""
        )
        for fact in price_facts
    )

    if prices:

        low = min(
            prices
        )

        high = max(
            prices
        )

        if low != high:

            price_text = (
                f"{format_price(low)}-{format_price(high)}"
            )

        elif "起" in combined_content:

            price_text = (
                f"{format_price(low)}起"
            )

        else:

            price_text = format_price(
                low
            )

    else:

        price_text = combined_content

    return (
        f"这款车目前资料中的价格信息为{price_text}，"
        "不同版本价格会有差异，具体成交价格以门店实际报价为准。"
    )


def ensure_model_price_overview(final_result, facts):

    rag_items = final_result.get(
        "rag_knowledge",
        []
    )

    price_facts_by_model = collect_price_facts(
        facts
    )

    for model, price_facts in price_facts_by_model.items():

        if has_model_price_overview(
            rag_items,
            model
        ):

            continue

        first_fact = price_facts[0]

        rag_items.insert(
            0,
            {
                "rag_id": "",
                "brand": first_fact.get(
                    "brand",
                    ""
                ),
                "model": model,
                "trim": "全系",
                "category": "价格",
                "knowledge_type": "dynamic",
                "module": "价格",
                "faq_priority": "高",
                "intent": "model_price_overview",
                "questions": [
                    f"{model}多少钱？",
                    f"{model}什么价位？",
                    "起售价多少？"
                ],
                "answer_type": "fact_answer",
                "answer": build_model_price_answer(
                    price_facts
                ),
                "fact_refs": [
                    fact.get(
                        "fact_id",
                        ""
                    )
                    for fact in price_facts
                    if fact.get(
                        "fact_id"
                    )
                ],
                "guardrails": [
                    "禁止承诺最终成交价格",
                    "优惠政策以门店实际信息为准"
                ],
                "need_confirm": "否",
                "review_type": "dynamic_notice",
                "confidence": "高",
                "适用范围": f"{model}全系价格概览"
            }
        )

    final_result[
        "rag_knowledge"
    ] = dedupe_rag_items(
        rag_items
    )

    return final_result



def load_prompt():

    with open(
        "prompts/step2_prompt.txt",
        "r",
        encoding="utf-8"
    ) as f:

        return f.read()



def parse_result(result):

    """
    解析模型JSON
    """

    try:

        from utils.json_parser import parse_json

        data = parse_json(result)

        return data


    except Exception as e:

        print("======================")
        print("RAG JSON解析失败")
        print(e)
        print("======================")

        print(result)

        return None



def normalize_facts(facts):

    """
    兼容不同facts结构

    支持：

    {
      "facts":[]
    }

    或

    []
    """

    if isinstance(facts, dict):

        return facts.get(
            "facts",
            []
        )


    return facts



def group_facts(facts):

    """
    按车型 + category优先聚合

    优先保证：

    同车型
    同类型知识

    有足够上下文合并版本共性知识

    """


    groups = defaultdict(list)



    for fact in facts:


        key = make_generation_group_key(
            fact
        )


        groups[key].append(
            fact
        )



    return add_aggregation_hints(
        list(
            groups.values()
        )
    )



def merge_small_groups(
        groups,
        max_size=30
):

    """
    避免过小batch过多

    小于max_size的相邻组进行合并

    """


    merged=[]

    current=[]


    current_size=0



    for group in groups:


        if (
            current_size + len(group)
            <= max_size
        ):

            current.extend(
                group
            )

            current_size += len(group)


        else:

            if current:

                merged.append(
                    current
                )


            current=list(group)

            current_size=len(group)



    if current:

        merged.append(
            current
        )


    return merged



def generate_batch(
        facts_batch,
        system_prompt
):


    user_content=json.dumps(
        {
            "facts":facts_batch
        },
        ensure_ascii=False
    )



    result = call_llm(
        system_prompt,
        user_content
    )


    if not result:

        return None



    return parse_result(
        result
    )



def merge_results(results):


    final = {

        "rag_knowledge":[],

        "info_gaps":[],

        "confirm_items":[]

    }



    rag_index=1



    for result in results:


        if not result:

            continue



        rag_list=result.get(
            "rag_knowledge",
            []
        )



        for rag in rag_list:


            rag["rag_id"] = (
                f"RAG-{rag_index:03d}"
            )


            final[
                "rag_knowledge"
            ].append(
                rag
            )


            rag_index += 1



        final[
            "info_gaps"
        ].extend(
            result.get(
                "info_gaps",
                []
            )
        )


        final[
            "confirm_items"
        ].extend(
            result.get(
                "confirm_items",
                []
            )
        )



    return final




def generate_rag(facts):

    """
    Step2:

    Facts
      |
      ↓
    model/category聚合分组
      |
      ↓
    Batch生成RAG
      |
      ↓
    Merge

    """



    system_prompt = load_prompt()



    facts = normalize_facts(
        facts
    )


    for fact in facts:

        if isinstance(
            fact,
            dict
        ):

            normalize_vehicle_fields(
                fact
            )


    fact_index = build_fact_index(
        facts
    )



    print(
        "===== Step2 Facts数量 ====="
    )

    print(
        len(facts)
    )



    # 1. 按车型/category拆分

    groups = group_facts(
        facts
    )



    print(
        "初始分组数量:",
        len(groups)
    )



    # 2. 合并小组，控制batch规模

    batches = merge_small_groups(
        groups,
        max_size=30
    )



    print(
        "最终Batch数量:",
        len(batches)
    )



    results=[]



    for index,batch in enumerate(
        batches
    ):


        print(
            f"===== Step2 Batch {index+1}/{len(batches)} ====="
        )


        print(
            "Facts数量:",
            len(batch)
        )



        result = generate_batch(
            batch,
            system_prompt
        )



        if result:


            results.append(
                normalize_rag_metadata(
                    result,
                    fact_index
                )
            )


        else:

            print(
                f"Batch {index+1}生成失败"
            )



    final_result = normalize_rag_metadata(
        merge_results(
            results
        ),
        fact_index
    )


    final_result[
        "rag_knowledge"
    ] = dedupe_rag_items(
        final_result.get(
            "rag_knowledge",
            []
        )
    )


    final_result = ensure_model_price_overview(
        final_result,
        facts
    )


    final_result = rag_quality.apply_export_quality_gate(
        final_result
    )



    print(
        "===== Step2完成 ====="
    )

    print(
        "最终RAG数量:",
        len(
            final_result[
                "rag_knowledge"
            ]
        )
    )



    return final_result
