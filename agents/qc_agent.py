import json
import re
from collections import defaultdict

from agents.llm_client import call_llm
from utils.rag_quality import is_exportable_rag


VERSION_RANGE_KEYWORDS = [
    "Pro",
    "Max",
    "旗舰",
    "黑骑士",
    "青春版",
    "+"
]


CONFIG_KEYWORDS = [
    "屏",
    "芯片",
    "内存",
    "存储",
    "气囊",
    "座椅",
    "调节",
    "快充",
    "尺寸",
    "参数"
]


DYNAMIC_CLASSIFICATION_KEYWORDS = [
    "价格",
    "售价",
    "指导价",
    "官方指导价",
    "限时",
    "活动期间",
    "下定",
    "大定",
    "购车权益",
    "现金优惠",
    "定金膨胀",
    "购置税补贴",
    "置换补贴",
    "金融方案",
    "费率",
    "立减",
    "抵扣",
    "选装减免",
    "指定现车礼",
    "活动赠品",
    "卡券有效期",
    "截止日期",
    "有效期",
    "补贴",
    "优惠",
    "金融"
]


STRONG_DYNAMIC_POLICY_KEYWORDS = [
    "限时",
    "活动期间",
    "截至",
    "截止",
    "有效期",
    "下定",
    "订车",
    "大定",
    "锁单",
    "补贴",
    "抵扣",
    "优惠价",
    "金融费率",
    "贴息",
    "首付",
    "月供",
    "政策周期",
    "活动时间",
    "定金膨胀",
    "购置税补贴",
    "置换补贴",
    "选装减免",
    "指定现车礼"
]


STATIC_SERVICE_KEYWORDS = [
    "质保",
    "保修",
    "三电",
    "整车质保",
    "道路救援",
    "救援",
    "车联网",
    "基础流量",
    "娱乐流量",
    "流量",
    "ADS",
    "智驾",
    "辅助驾驶",
    "功能包",
    "车辆配置",
    "配置",
    "座舱",
    "续航",
    "补能",
    "空间",
    "尺寸",
    "动力",
    "安全",
    "舒适",
    "售后",
    "基础保障"
]


DYNAMIC_DATE_PATTERN = re.compile(
    r"\d{4}年\d{1,2}月\d{1,2}日|"
    r"\d{4}[./-]\d{1,2}[./-]\d{1,2}"
)


POLICY_MONTH_PATTERN = re.compile(
    r"(\d{4})年(\d{1,2})月|"
    r"(\d{4})[./-](\d{1,2})[./-]\d{1,2}"
)


DATE_CONTEXT_KEYWORDS = [
    "有效期",
    "截止",
    "活动周期",
    "活动时间",
    "上线时间",
    "下线时间",
    "限时",
    "下定",
    "大定",
    "政策周期",
    "期间",
    "至"
]


ADAS_RISK_KEYWORDS = [
    "自动驾驶",
    "自己开",
    "不用管",
    "解放双手",
    "自动变道无需接管"
]


INTENT_GROUP_KEYWORDS = {
    "experience": [
        "好不好用",
        "怎么样",
        "舒服",
        "体验"
    ],
    "screen_size": [
        "屏幕多大",
        "几英寸",
        "尺寸"
    ],
    "chip": [
        "芯片",
        "内存",
        "存储"
    ],
    "price": [
        "多少钱",
        "价格",
        "售价"
    ],
    "finance": [
        "金融",
        "贷款",
        "免息"
    ]
}


PRICE_KEYWORDS = [
    "价格",
    "售价",
    "指导价",
    "多少钱",
    "价位",
    "起售价"
]


CORE_MODULE_KEYWORDS = [
    "空间",
    "动力",
    "续航",
    "补能",
    "智驾",
    "安全",
    "舒适",
    "车型"
]


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


def build_item_text(item):

    return (
        f"{item.get('category', '')} "
        f"{item.get('module', '')} "
        f"{get_question_text(item)} "
        f"{item.get('answer', '')}"
    )


def has_static_service_context(item_text):

    return any(
        keyword in item_text
        for keyword in STATIC_SERVICE_KEYWORDS
    )


def has_dynamic_policy_signal(item_text):

    has_explicit_date = (
        DYNAMIC_DATE_PATTERN.search(
            item_text
        )
        is not None
        and any(
            keyword in item_text
            for keyword in DATE_CONTEXT_KEYWORDS
        )
    )

    return (
        has_explicit_date
        or any(
            keyword in item_text
            for keyword in STRONG_DYNAMIC_POLICY_KEYWORDS
        )
    )


def extract_policy_periods(item_text):

    if not any(
        keyword in item_text
        for keyword in DATE_CONTEXT_KEYWORDS
    ):

        return set()

    periods = set()

    for match in POLICY_MONTH_PATTERN.finditer(
        item_text
    ):

        year = match.group(1) or match.group(3)

        month = match.group(2) or match.group(4)

        if year and month:

            periods.add(
                f"{year}年{int(month)}月"
            )

    return periods


def should_report_static_dynamic_mismatch(item):

    if not is_exportable_rag(
        item
    ):

        return False

    if item.get(
        "knowledge_type"
    ) != "static":

        return False

    item_text = build_item_text(
        item
    )

    if not has_dynamic_policy_signal(
        item_text
    ):

        return False

    if has_static_service_context(
        item_text
    ) and not any(
        keyword in item_text
        for keyword in STRONG_DYNAMIC_POLICY_KEYWORDS
    ) and not (
        DYNAMIC_DATE_PATTERN.search(
            item_text
        )
        is not None
        and any(
            keyword in item_text
            for keyword in DATE_CONTEXT_KEYWORDS
        )
    ):

        return False

    return True


def append_issue(data, issue):

    data.setdefault(
        "issues",
        []
    ).append(
        issue
    )

    summary = data.setdefault(
        "summary",
        {}
    )

    summary[
        "warning"
    ] = summary.get(
        "warning",
        0
    ) + 1

    if data.get(
        "overall_result",
        "通过"
    ) == "通过":

        data[
            "overall_result"
        ] = "需优化"


def refresh_summary(data, total_rag):

    issues = [
        issue
        for issue in data.get(
            "issues",
            []
        )
        if isinstance(
            issue,
            dict
        )
    ]

    warning = sum(
        1
        for issue in issues
        if issue.get(
            "risk_level"
        ) == "warning"
    )

    error = sum(
        1
        for issue in issues
        if issue.get(
            "risk_level"
        ) == "error"
    )

    data[
        "summary"
    ] = {
        "total_rag": total_rag,
        "pass": max(
            total_rag - warning - error,
            0
        ),
        "warning": warning,
        "error": error
    }

    data[
        "overall_result"
    ] = (
        "需处理"
        if error
        else
        "需优化"
        if warning
        else
        "通过"
    )

    return data


def rule_based_quality_checks(rag_data, qc_data):

    if not isinstance(
        qc_data,
        dict
    ):

        qc_data = {
            "summary": {},
            "issues": [],
            "coverage_check": {},
            "overall_result": "需优化"
        }

    rag_list = rag_data.get(
        "rag_knowledge",
        []
    )

    exportable_ids = {
        item.get(
            "rag_id"
        )
        for item in rag_list
        if isinstance(
            item,
            dict
        )
        and is_exportable_rag(
            item
        )
    }

    qc_data[
        "issues"
    ] = [
        issue
        for issue in qc_data.get(
            "issues",
            []
        )
        if isinstance(
            issue,
            dict
        )
        and (
            not issue.get(
                "rag_id"
            )
            or issue.get(
                "rag_id"
            )
            in exportable_ids
        )
    ]

    duplicate_groups = defaultdict(list)

    model_groups = defaultdict(list)

    policy_period_groups = defaultdict(set)

    for item in rag_list:

        if not isinstance(
            item,
            dict
        ):

            continue

        if not is_exportable_rag(
            item
        ):

            continue

        model = item.get(
            "model",
            ""
        )

        model_groups[
            model
        ].append(
            item
        )

        item_text_for_period = build_item_text(
            item
        )

        if item.get(
            "knowledge_type"
        ) == "dynamic":

            period_key = (
                model,
                item.get(
                    "category",
                    item.get(
                        "module",
                        ""
                    )
                )
            )

            policy_period_groups[
                period_key
            ].update(
                extract_policy_periods(
                    item_text_for_period
                )
            )

        duplicate_key = (
            model,
            item.get(
                "category",
                item.get(
                    "module",
                    ""
                )
            ),
            normalize_text(
                get_question_text(
                    item
                )
            ),
            normalize_text(
                item.get(
                    "answer",
                    ""
                )
            )[:80]
        )

        duplicate_groups[
            duplicate_key
        ].append(
            item
        )

        answer = item.get(
            "answer",
            ""
        )

        trim = item.get(
            "trim",
            ""
        )

        mentioned_versions = [
            keyword
            for keyword in VERSION_RANGE_KEYWORDS
            if keyword in answer
        ]

        if (
            trim
            and trim not in [
                "全系",
                "不同版本"
            ]
            and len(
                mentioned_versions
            ) >= 2
            and not all(
                keyword in trim
                for keyword in mentioned_versions
            )
        ):

            append_issue(
                qc_data,
                {
                    "rag_id": item.get(
                        "rag_id",
                        ""
                    ),
                    "issue_type": "版本范围不一致",
                    "risk_level": "warning",
                    "description": "RAG版本字段与回答中的适用版本范围不一致。",
                    "suggestion": "将trim改为全系、不同版本或简洁版本组名称。"
                }
            )

        if (
            item.get(
                "knowledge_type"
            ) == "dynamic"
            and len(
                answer
            ) > 180
        ):

            append_issue(
                qc_data,
                {
                    "rag_id": item.get(
                        "rag_id",
                        ""
                    ),
                    "issue_type": "回答过长",
                    "risk_level": "warning",
                    "description": "单条动态政策回答过长，不适合电话场景。",
                    "suggestion": "按金融、置换、保障、主要权益等模块拆分。"
                }
            )

        if (
            "除180系列外" in answer
            and any(
                keyword in answer
                for keyword in [
                    "Pro",
                    "Max",
                    "Pro+",
                    "Max+"
                ]
            )
        ):

            append_issue(
                qc_data,
                {
                    "rag_id": item.get(
                        "rag_id",
                        ""
                    ),
                    "issue_type": "版本范围描述冲突",
                    "risk_level": "warning",
                    "description": "回答中版本范围存在自相矛盾表达。",
                    "suggestion": "重新核对适用版本，避免同时排除和包含同一版本范围。"
                }
            )

        if should_report_static_dynamic_mismatch(
            item
        ):

            append_issue(
                qc_data,
                {
                    "rag_id": item.get(
                        "rag_id",
                        ""
                    ),
                    "issue_type": "静态动态分类可能错误",
                    "risk_level": "warning",
                    "description": "静态知识中出现明确限时、下定、补贴、金融、抵扣或日期等动态政策信号。",
                    "suggestion": "核对该知识是否应归入价格政策知识库；质保、道路救援、流量、智驾功能等固定服务不应仅因免费或赠送误判。"
                }
            )

        if any(
            keyword in answer
            for keyword in ADAS_RISK_KEYWORDS
        ):

            append_issue(
                qc_data,
                {
                    "rag_id": item.get(
                        "rag_id",
                        ""
                    ),
                    "issue_type": "智驾表达可能越界",
                    "risk_level": "warning",
                    "description": "智驾回答出现自动驾驶或无需接管等高风险表达。",
                    "suggestion": "改为辅助驾驶表达，并提示实际使用需驾驶员保持关注。"
                }
            )

        question_text = get_question_text(
            item
        )

        matched_intents = [
            intent
            for intent, keywords in INTENT_GROUP_KEYWORDS.items()
            if any(
                keyword in question_text
                for keyword in keywords
            )
        ]

        if len(
            matched_intents
        ) >= 2:

            append_issue(
                qc_data,
                {
                    "rag_id": item.get(
                        "rag_id",
                        ""
                    ),
                    "issue_type": "问题粒度过大",
                    "risk_level": "warning",
                    "description": "单条RAG混合了多个不同用户意图。",
                    "suggestion": "拆分为体验类问题和具体参数类问题。"
                }
            )

    for items in duplicate_groups.values():

        trims = set(
            item.get(
                "trim",
                ""
            )
            for item in items
        )

        if len(
            items
        ) > 1 and len(
            trims
        ) > 1:

            append_issue(
                qc_data,
                {
                    "rag_id": items[0].get(
                        "rag_id",
                        ""
                    ),
                    "issue_type": "重复知识",
                    "risk_level": "warning",
                    "description": "知识可能过度按版本拆分，建议合并。",
                    "suggestion": "将相同问题和相似回答合并为车型级或版本组知识。"
                }
            )

    for (model, category), periods in policy_period_groups.items():

        if len(
            periods
        ) <= 1:

            continue

        append_issue(
            qc_data,
            {
                "rag_id": "",
                "issue_type": "政策周期混合风险",
                "risk_level": "warning",
                "display_level": "需人工关注",
                "description": (
                    f"发现{model}存在多个{category}周期："
                    + "、".join(
                        sorted(
                            periods
                        )
                    )
                ),
                "suggestion": "建议确认当前有效政策，避免历史政策和当前政策同时进入导入文件。"
            }
        )

    for model, items in model_groups.items():

        if not model:

            continue

        config_count = 0

        core_count = 0

        for item in items:

            text = (
                f"{item.get('category', '')} "
                f"{item.get('module', '')} "
                f"{get_question_text(item)} "
                f"{item.get('answer', '')}"
            )

            if any(
                keyword in text
                for keyword in CONFIG_KEYWORDS
            ):

                config_count += 1

            if item.get(
                "trim"
            ) in [
                "全系",
                "不同版本"
            ] and any(
                keyword in text
                for keyword in CORE_MODULE_KEYWORDS
            ):

                core_count += 1

        if (
            len(
                items
            ) >= 10
            and config_count / len(
                items
            ) > 0.45
            and core_count < 4
        ):

            append_issue(
                qc_data,
                {
                    "rag_id": "",
                    "issue_type": "配置FAQ比例过高",
                    "risk_level": "warning",
                    "description": "知识库配置参数类FAQ占比过高，车型级核心销售知识偏少。",
                    "suggestion": "增加车型级空间、动力、续航、智驾、安全、舒适知识，并减少低频版本参数FAQ。"
                }
            )

        version_price_count = 0

        has_model_price = False

        for item in items:

            text = (
                f"{item.get('category', '')} "
                f"{item.get('module', '')} "
                f"{get_question_text(item)} "
                f"{item.get('answer', '')}"
            )

            is_price = any(
                keyword in text
                for keyword in PRICE_KEYWORDS
            )

            if not is_price:

                continue

            if item.get(
                "trim"
            ) in [
                "全系",
                "不同版本",
                ""
            ]:

                has_model_price = True

            else:

                version_price_count += 1

        if version_price_count >= 2 and not has_model_price:

            append_issue(
                qc_data,
                {
                    "rag_id": "",
                    "issue_type": "缺少车型级价格概览知识",
                    "risk_level": "warning",
                    "display_level": "优化建议",
                    "description": "存在多个版本级价格知识，但缺少车型级价格概览。",
                    "suggestion": "补充车型整体价格区间FAQ，例如N6多少钱、N6什么价位、起售价多少。"
                }
            )

    return refresh_summary(
        qc_data,
        len(
            exportable_ids
        )
    )


def quality_check(rag_data):

    """
    Step3:
    对RAG知识进行质量检测
    """


    with open(
        "prompts/step3_prompt.txt",
        "r",
        encoding="utf-8"
    ) as f:

        system_prompt = f.read()


    user_content = json.dumps(
        rag_data,
        ensure_ascii=False
    )


    result = call_llm(
        system_prompt,
        user_content
    )


    try:

        from utils.json_parser import parse_json
        data = parse_json(result)

        return rule_based_quality_checks(
            rag_data,
            data
        )


    except Exception:

        print("QC JSON解析失败")
        print(result)

        return rule_based_quality_checks(
            rag_data,
            {
                "summary": {
                    "total_rag": len(
                        rag_data.get(
                            "rag_knowledge",
                            []
                        )
                    ),
                    "pass": 0,
                    "warning": 0,
                    "error": 0
                },
                "issues": [],
                "coverage_check": {},
                "overall_result": "需优化"
            }
        )
