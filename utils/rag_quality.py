import re


BLOCKING_REVIEW_TYPES = {
    "missing",
    "conflict",
    "inference",
    "range_issue"
}

BLOCKING_STATUS_VALUES = {
    "missing",
    "unconfirmed",
    "invalid"
}

MISSING_ANSWER_PHRASES = [
    "资料未提供",
    "暂未提供",
    "目前没有",
    "目前还没有",
    "没有相关信息",
    "无法确认",
    "尚不清楚",
    "需要人工确认",
    "未找到",
    "未提供",
    "缺少"
]

MISSING_HINT_PHRASES = [
    "建议咨询门店",
    "建议您咨询门店",
    "建议咨询当地门店",
    "建议您咨询当地门店",
    "参考后续官方信息"
]


HIGH_RISK_CONFIRM_TOPICS = [
    "金融",
    "贷款",
    "分期",
    "首付",
    "利率",
    "费率",
    "质保",
    "保养",
    "售后",
]

TOPIC_KEYWORDS = {
    "价格": [
        "价格",
        "售价",
        "指导价",
        "建议零售价",
        "官方价",
        "多少钱",
        "价位",
        "起售价"
    ],
    "金融政策": [
        "金融",
        "贷款",
        "分期",
        "免息",
        "0息",
        "贴息",
        "费率",
        "月供",
        "首付"
    ],
    "续航": [
        "续航",
        "CLTC",
        "纯电续航",
        "综合续航",
        "电池"
    ],
    "购车权益": [
        "购车权益",
        "权益",
        "限时权益",
        "下定权益",
        "优惠",
        "补贴",
        "置换",
        "增购",
        "定金",
        "抵扣",
        "选装减免",
        "现车礼"
    ],
    "智驾": [
        "智驾",
        "辅助驾驶",
        "智能驾驶",
        "领航",
        "泊车"
    ],
    "动力": [
        "动力",
        "电机",
        "发动机",
        "扭矩",
        "功率",
        "加速"
    ],
    "补能": [
        "补能",
        "充电",
        "快充",
        "对外供电"
    ],
    "空间": [
        "空间",
        "轴距",
        "车长",
        "尺寸"
    ]
}


def join_questions(item):

    questions = item.get(
        "questions",
        item.get(
            "question",
            []
        )
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


def normalize_model_name(value):

    text = str(
        value or ""
    ).strip()

    text = re.sub(
        r"\s+",
        "",
        text
    )

    if text.startswith(
        "新阿维塔"
    ):

        return text[1:]

    return text


def get_item_text(item):

    return " ".join(
        str(
            item.get(
                field,
                ""
            )
        )
        for field in [
            "brand",
            "model",
            "trim",
            "category",
            "module",
            "intent",
            "answer_type",
            "answer",
            "review_type",
            "knowledge_status"
        ]
    ) + " " + join_questions(
        item
    )


def normalize_topic(item):

    text = get_item_text(
        item
    )

    for topic, keywords in TOPIC_KEYWORDS.items():

        if any(
            keyword in text
            for keyword in keywords
        ):

            return topic

    category = item.get(
        "category",
        ""
    ) or item.get(
        "module",
        ""
    )

    return str(
        category or "其他"
    )


def is_missing_answer(answer):

    text = str(
        answer or ""
    )

    if not text.strip():

        return True

    if any(
        phrase in text
        for phrase in MISSING_ANSWER_PHRASES
    ):

        return True

    return (
        any(
            phrase in text
            for phrase in MISSING_HINT_PHRASES
        )
        and any(
            phrase in text
            for phrase in [
                "没有",
                "缺少",
                "未找到",
                "未提供",
                "无法确认"
            ]
        )
    )


def is_high_risk_unconfirmed_item(item):

    text = get_item_text(
        item
    )

    if str(
        item.get(
            "trim",
            ""
        )
    ).strip() != "需确认":

        return False

    return any(
        keyword in text
        for keyword in HIGH_RISK_CONFIRM_TOPICS
    )


def is_exportable_rag(item):

    if not isinstance(
        item,
        dict
    ):

        return False

    if item.get(
        "exportable"
    ) is False:

        return False

    if str(
        item.get(
            "answer_type",
            ""
        )
    ).lower() == "need_confirm":

        return False

    if str(
        item.get(
            "need_confirm",
            ""
        )
    ).strip() in [
        "是",
        "yes",
        "true",
        "1"
    ]:

        return False

    if item.get(
        "review_type",
        ""
    ) in BLOCKING_REVIEW_TYPES:

        return False

    if is_high_risk_unconfirmed_item(
        item
    ):

        return False

    if str(
        item.get(
            "knowledge_status",
            ""
        )
    ).lower() in BLOCKING_STATUS_VALUES:

        return False

    if is_missing_answer(
        item.get(
            "answer",
            ""
        )
    ):

        return False

    return True


def has_effective_answer(item):

    if not is_exportable_rag(
        item
    ):

        return False

    if item.get(
        "answer_type"
    ) in [
        "fact_answer",
        "sales_translation"
    ]:

        return True

    refs = item.get(
        "fact_refs",
        []
    )

    return bool(
        refs
    )


def mark_non_exportable(item, reason, review_type="missing"):

    item[
        "exportable"
    ] = False

    item[
        "review_type"
    ] = review_type

    item[
        "knowledge_status"
    ] = (
        "missing"
        if review_type == "missing"
        else
        "unconfirmed"
    )

    item[
        "export_block_reason"
    ] = reason

    return item


def get_topic_key(item):

    return (
        item.get(
            "brand",
            ""
        ),
        normalize_model_name(
            item.get(
                "model",
                ""
            )
        ),
        normalize_topic(
            item
        )
    )


def extract_price_values(text):

    values = set()

    for match in re.finditer(
        r"(\d+(?:\.\d+)?)万元",
        str(
            text or ""
        )
    ):

        values.add(
            round(
                float(
                    match.group(
                        1
                    )
                ),
                2
            )
        )

    for match in re.finditer(
        r"(?<!\d)([1-9]\d{1,2}(?:,\d{3})+|[1-9]\d{4,6})元",
        str(
            text or ""
        )
    ):

        raw = match.group(
            1
        ).replace(
            ",",
            ""
        )

        values.add(
            round(
                float(
                    raw
                ) / 10000,
                2
            )
        )

    return values


def append_detected_conflicts(rag_data, rag_items):

    price_groups = {}

    for item in rag_items:

        if not has_effective_answer(
            item
        ):

            continue

        if normalize_topic(
            item
        ) != "价格":

            continue

        prices = extract_price_values(
            item.get(
                "answer",
                ""
            )
        )

        if len(
            prices
        ) != 1:

            continue

        key = (
            item.get(
                "brand",
                ""
            ),
            normalize_model_name(
                item.get(
                    "model",
                    ""
                )
            ),
            item.get(
                "trim",
                ""
            ) or "全系"
        )

        price_groups.setdefault(
            key,
            []
        ).append(
            (
                item,
                next(
                    iter(
                        prices
                    )
                )
            )
        )

    existing_conflicts = {
        (
            item.get(
                "model",
                ""
            ),
            item.get(
                "trim",
                ""
            ),
            item.get(
                "item",
                ""
            )
        )
        for item in rag_data.get(
            "review_items",
            []
        )
        if isinstance(
            item,
            dict
        )
        and item.get(
            "review_type"
        ) == "conflict"
    }

    for (_brand, _model_key, trim), items in price_groups.items():

        prices = {
            price
            for _item, price in items
        }

        if len(
            prices
        ) <= 1:

            continue

        first_item = items[0][0]

        item_text = (
            f"{first_item.get('model', '')}{trim}存在多个价格："
            + "、".join(
                f"{price:g}万元"
                for price in sorted(
                    prices
                )
            )
        )

        conflict_key = (
            first_item.get(
                "model",
                ""
            ),
            trim,
            item_text
        )

        if conflict_key in existing_conflicts:

            continue

        rag_data.setdefault(
            "review_items",
            []
        ).append(
            {
                "review_type": "conflict",
                "brand": first_item.get(
                    "brand",
                    ""
                ),
                "model": first_item.get(
                    "model",
                    ""
                ),
                "trim": trim,
                "category": "价格",
                "item": item_text,
                "reason": "同车型同版本存在不同价格表达，系统不自动删除任何一条有效知识。",
                "suggestion": "人工确认当前有效价格后再导入或更新知识库。"
            }
        )


def apply_export_quality_gate(rag_data):

    if not isinstance(
        rag_data,
        dict
    ):

        return rag_data

    rag_items = [
        item
        for item in rag_data.get(
            "rag_knowledge",
            []
        )
        if isinstance(
            item,
            dict
        )
    ]

    effective_topics = {
        get_topic_key(
            item
        )
        for item in rag_items
        if has_effective_answer(
            item
        )
    }

    for item in rag_items:

        item[
            "model_normalized"
        ] = normalize_model_name(
            item.get(
                "model",
                ""
            )
        )

        if not item.get(
            "model_display_name"
        ):

            item[
                "model_display_name"
            ] = item.get(
                "model",
                ""
            )

        if not is_exportable_rag(
            item
        ):

            reason = item.get(
                "export_block_reason",
                "待确认或缺失型知识不进入正式Excel"
            )

            if get_topic_key(
                item
            ) in effective_topics:

                reason = "同车型同主题已有有效知识，缺失型RAG不进入正式Excel"

            mark_non_exportable(
                item,
                reason,
                item.get(
                    "review_type",
                    "missing"
                )
                if item.get(
                    "review_type"
                ) in BLOCKING_REVIEW_TYPES
                else
                "missing"
            )

            continue

        item[
            "exportable"
        ] = True

    append_detected_conflicts(
        rag_data,
        rag_items
    )

    return rag_data


def price_to_wan(match):

    raw = match.group(
        1
    ).replace(
        ",",
        ""
    )

    try:

        value = float(
            raw
        ) / 10000

    except ValueError:

        return match.group(
            0
        )

    text = f"{value:.2f}".rstrip(
        "0"
    ).rstrip(
        "."
    )

    return f"{text}万元"


CN_NUMBERS = {
    "0": "零",
    "1": "一",
    "2": "二",
    "3": "三",
    "4": "四",
    "5": "五",
    "6": "六",
    "7": "七",
    "8": "八",
    "9": "九"
}


def number_to_chinese(value):

    text = str(
        value
    )

    if "." in text:

        left, right = text.split(
            ".",
            1
        )

        return (
            number_to_chinese(
                left
            )
            + "点"
            + "".join(
                CN_NUMBERS.get(
                    char,
                    char
                )
                for char in right
            )
        )

    try:

        number = int(
            text
        )

    except ValueError:

        return text

    if number < 10:

        return CN_NUMBERS.get(
            str(number),
            str(number)
        )

    if number < 100:

        tens = number // 10

        ones = number % 10

        prefix = "" if tens == 1 else CN_NUMBERS[str(tens)]

        suffix = "" if ones == 0 else CN_NUMBERS[str(ones)]

        return f"{prefix}十{suffix}"

    return "".join(
        CN_NUMBERS.get(
            char,
            char
        )
        for char in text
    )


def percent_to_chinese(match):

    return "百分之" + number_to_chinese(
        match.group(
            1
        )
    )


def normalize_answer_for_tts(answer):

    text = str(
        answer or ""
    )

    text = re.sub(
        r"[¥￥]\s*([0-9,]+(?:\.\d+)?)",
        price_to_wan,
        text
    )

    text = re.sub(
        r"(?<!\d)([1-9]\d{1,2}(?:,\d{3})+|[1-9]\d{4,6})元",
        price_to_wan,
        text
    )

    replacements = [
        ("N·m", "牛米"),
        ("N.m", "牛米"),
        ("kWh", "度电"),
        ("kW", "千瓦"),
        ("km", "公里"),
        ("mm", "毫米"),
        ("Ps", "匹"),
        ("ADS智能驾驶辅助系统", "智能驾驶辅助系统"),
        ("ADS", "智能驾驶辅助系统"),
        ("LCC", "车道居中辅助"),
        ("NCA", "领航辅助驾驶"),
        ("APA", "自动泊车"),
        ("RPA", "遥控泊车"),
        ("CDC", "可变阻尼悬架"),
        ("OTA", "在线升级"),
        ("NAPPA", "Nappa"),
        ("Nappa", "Nappa"),
        ("LED", "LED"),
        ("USB", "USB")
    ]

    for old, new in replacements:

        text = text.replace(
            old,
            new
        )

    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*V",
        r"\1伏",
        text
    )

    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*%",
        percent_to_chinese,
        text
    )

    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*G(?![A-Za-z])",
        r"\1GB流量",
        text
    )

    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*GB(?!流量)",
        r"\1GB流量",
        text
    )

    text = re.sub(
        r"4K(?!高清)",
        "4K高清",
        text
    )

    text = text.replace(
        "智能驾驶辅助系统智能驾驶辅助系统",
        "智能驾驶辅助系统"
    )

    return text


def normalize_review_item(
        item,
        default_review_type="missing",
        default_model="全部车型"
):

    if isinstance(
        item,
        dict
    ):

        review_type = item.get(
            "review_type",
            default_review_type
        ) or default_review_type

        model = item.get(
            "model",
            ""
        ) or item.get(
            "vehicle",
            ""
        ) or default_model

        item_text = (
            item.get(
                "item",
                ""
            )
            or item.get(
                "missing_content",
                ""
            )
            or item.get(
                "question",
                ""
            )
            or item.get(
                "description",
                ""
            )
            or "待人工关注事项"
        )

        reason = (
            item.get(
                "reason",
                ""
            )
            or item.get(
                "description",
                ""
            )
            or "资料中未找到可直接确认的信息"
        )

        suggestion = (
            item.get(
                "suggestion",
                ""
            )
            or item.get(
                "confirm_content",
                ""
            )
            or "补充资料或人工核查"
        )

        return {
            "review_type": review_type,
            "brand": item.get(
                "brand",
                ""
            ),
            "model": model,
            "trim": item.get(
                "trim",
                ""
            ) or "未指定",
            "category": item.get(
                "category",
                ""
            ) or item.get(
                "impact_module",
                ""
            ),
            "item": item_text,
            "reason": reason,
            "suggestion": suggestion,
            "source_file": item.get(
                "source_file",
                ""
            )
        }

    text = str(
        item or ""
    ).strip() or "待人工关注事项"

    return {
        "review_type": default_review_type,
        "brand": "",
        "model": default_model,
        "trim": "未指定",
        "category": "",
        "item": text,
        "reason": "资料中未找到对应信息",
        "suggestion": "补充资料"
    }
