import os

import pandas as pd
import streamlit as st

from main import run_pipeline
from parser.image_parser import IMAGE_EXTENSIONS, get_vision_model_name
from parser.parser_factory import parse_file
from ui.components import render_file_card, render_page_header, render_step_navigation
from utils.rag_quality import is_exportable_rag, normalize_review_item


def join_questions(item):

    questions = item.get(
        "questions",
        []
    )

    if isinstance(
        questions,
        list
    ):

        return " / ".join(
            str(question)
            for question in questions
            if question
        )

    return str(
        questions or ""
    )


def build_knowledge_rows(rag_data, knowledge_type):

    rows = []

    for item in rag_data.get(
        "rag_knowledge",
        []
    ):

        if item.get(
            "knowledge_type"
        ) != knowledge_type:

            continue

        if not is_exportable_rag(
            item
        ):

            continue

        rows.append(
            {
                "车型": item.get(
                    "model",
                    ""
                ),
                "版本": item.get(
                    "trim",
                    ""
                ),
                "问题": join_questions(
                    item
                ),
                "回答": item.get(
                    "answer",
                    ""
                ),
                "分类": (
                    item.get(
                        "category",
                        ""
                    )
                    or
                    item.get(
                        "module",
                        ""
                    )
                )
            }
        )

    return rows


def get_project_info(facts_data, rag_data):

    candidates = []

    candidates.extend(
        rag_data.get(
            "rag_knowledge",
            []
        )
    )

    candidates.extend(
        facts_data.get(
            "facts",
            []
        )
    )

    for item in candidates:

        if not isinstance(
            item,
            dict
        ):

            continue

        brand = item.get(
            "brand",
            ""
        )

        model = item.get(
            "model",
            ""
        )

        if brand or model:

            return {
                "brand": brand or "未识别",
                "model": model or "未识别"
            }

    return {
        "brand": "未识别",
        "model": "未识别"
    }


REVIEW_TOPIC_KEYWORDS = {
    "金融": ["金融", "0息", "免息", "贷款", "费率"],
    "权益": ["权益", "赠送", "赠", "补贴", "置换", "优惠"],
    "空间": ["空间", "轴距", "车长", "尺寸"],
    "动力": ["动力", "发动机", "电机", "扭矩", "功率", "马力"],
    "价格": ["价格", "售价", "指导价"],
    "智驾": ["智驾", "辅助驾驶"],
    "续航": ["续航", "电池"],
    "补能": ["补能", "快充", "充电"]
}


def collect_coverage_text(facts_data, rag_data):

    values = []

    for fact in facts_data.get("facts", []):

        if isinstance(fact, dict):

            values.extend(
                [
                    fact.get("category", ""),
                    fact.get("content", "")
                ]
            )

    for item in rag_data.get("rag_knowledge", []):

        if isinstance(item, dict):

            values.extend(
                [
                    item.get("category", ""),
                    item.get("module", ""),
                    join_questions(item),
                    item.get("answer", "")
                ]
            )

    return " ".join(
        str(value)
        for value in values
        if value
    )


def normalize_review_model(value):

    return str(
        value or ""
    ).replace(
        "新",
        ""
    ).replace(
        " ",
        ""
    )


def build_coverage_index(facts_data, rag_data):

    coverage = set()

    for fact in facts_data.get(
        "facts",
        []
    ):

        if not isinstance(
            fact,
            dict
        ):

            continue

        coverage.add(
            (
                normalize_review_model(
                    fact.get(
                        "model",
                        ""
                    )
                ),
                fact.get(
                    "category",
                    ""
                )
            )
        )

    for item in rag_data.get(
        "rag_knowledge",
        []
    ):

        if not isinstance(
            item,
            dict
        ):

            continue

        model = normalize_review_model(
            item.get(
                "model",
                ""
            )
        )

        coverage.add(
            (
                model,
                item.get(
                    "category",
                    ""
                )
            )
        )

        coverage.add(
            (
                model,
                item.get(
                    "module",
                    ""
                )
            )
        )

    return coverage


REVIEW_TOPIC_CATEGORIES = {
    "金融": ["金融政策", "金融方案"],
    "权益": ["权益政策", "购车权益", "活动政策"],
    "空间": ["空间信息", "尺寸信息", "空间"],
    "动力": ["动力信息", "动力"],
    "价格": ["价格信息", "价格"],
    "智驾": ["智驾信息", "智能驾驶", "智驾"],
    "续航": ["续航信息", "续航"],
    "补能": ["补能信息", "补能"]
}


def get_review_text(item):

    if isinstance(item, dict):

        return " ".join(
            str(item.get(field, ""))
            for field in [
                "gap_type",
                "missing_content",
                "impact_module",
                "description",
                "item",
                "reason",
                "suggestion",
                "confirm_content"
            ]
        )

    return str(item)


def get_review_model(item):

    if isinstance(
        item,
        dict
    ):

        return normalize_review_model(
            item.get(
                "model",
                ""
            )
            or
            item.get(
                "vehicle",
                ""
            )
        )

    return ""


def is_gap_resolved(item, coverage_text, coverage_index):

    text = get_review_text(item)

    if not text:

        return False

    for keywords in REVIEW_TOPIC_KEYWORDS.values():

        if any(keyword in text for keyword in keywords):

            matched_topic = None

            for topic, topic_keywords in REVIEW_TOPIC_KEYWORDS.items():

                if any(
                    keyword in text
                    for keyword in topic_keywords
                ):

                    matched_topic = topic

                    break

            model = get_review_model(
                item
            )

            if matched_topic:

                categories = REVIEW_TOPIC_CATEGORIES.get(
                    matched_topic,
                    []
                )

                if model:

                    if any(
                        (
                            model,
                            category
                        )
                        in coverage_index
                        for category in categories
                    ):

                        return True

                elif any(
                    category in coverage_text
                    for category in categories
                ):

                    return True

            return any(keyword in coverage_text for keyword in keywords)

    return False


def classify_review_item(item):

    if isinstance(item, dict):

        review_type = item.get("review_type", "")

        if review_type in [
            "missing",
            "conflict",
            "inference",
            "dynamic_notice"
        ]:

            return review_type

    text = get_review_text(item)

    if any(keyword in text for keyword in ["冲突", "不一致", "矛盾"]):

        return "conflict"

    if any(
        keyword in text
        for keyword in ["推断", "无法判断", "需确认", "适用范围", "版本归属"]
    ):

        return "inference"

    return "missing"


def build_review_center_rows(facts_data, rag_data):

    rows = []

    coverage_text = collect_coverage_text(facts_data, rag_data)

    coverage_index = build_coverage_index(
        facts_data,
        rag_data
    )

    gaps = []
    gaps.extend(facts_data.get("info_gaps", []))
    gaps.extend(rag_data.get("info_gaps", []))
    gaps.extend(rag_data.get("review_items", []))

    for item in gaps:

        normalized_item = normalize_review_item(
            item
        )

        if is_gap_resolved(
            normalized_item,
            coverage_text,
            coverage_index
        ):

            continue

        review_type = classify_review_item(
            normalized_item
        )

        rows.append(
            {
                "检查类型": review_type,
                "车型": normalized_item.get(
                    "model",
                    "全部车型"
                ) or "全部车型",
                "事项": normalized_item.get(
                    "item",
                    "待人工关注事项"
                ) or "待人工关注事项",
                "说明": normalized_item.get(
                    "reason",
                    "资料中未找到可直接确认的信息"
                ) or "资料中未找到可直接确认的信息",
                "处理动作": normalized_item.get(
                    "suggestion",
                    "补充资料"
                ) or "补充资料"
            }
        )

    for item in rag_data.get("confirm_items", []):

        normalized_item = normalize_review_item(
            item,
            default_review_type="inference"
        )

        review_type = classify_review_item(
            normalized_item
        )

        rows.append(
            {
                "检查类型": review_type,
                "车型": normalized_item.get(
                    "model",
                    "全部车型"
                ) or "全部车型",
                "事项": normalized_item.get(
                    "item",
                    "待人工关注事项"
                ) or "待人工关注事项",
                "说明": normalized_item.get(
                    "reason",
                    "资料中未找到可直接确认的信息"
                ) or "资料中未找到可直接确认的信息",
                "处理动作": normalized_item.get(
                    "suggestion",
                    (
                        "人工确认"
                        if review_type == "conflict"
                        else
                        "人工核查"
                    )
                ) or (
                    "人工确认"
                    if review_type == "conflict"
                    else
                    "人工核查"
                )
            }
        )

    for item in rag_data.get(
        "export_excluded",
        []
    ):

        if not isinstance(
            item,
            dict
        ):

            continue

        rows.append(
            {
                "检查类型": item.get(
                    "review_type",
                    "missing"
                ) or "missing",
                "车型": item.get(
                    "model",
                    "全部车型"
                ) or "全部车型",
                "事项": join_questions(
                    item
                ) or item.get(
                    "category",
                    "待确认知识"
                ),
                "说明": item.get(
                    "export_block_reason",
                    "该知识不适合进入正式导出文件"
                ),
                "处理动作": "补充资料或人工核查"
            }
        )

    for item in rag_data.get("rag_knowledge", []):

        if item.get("knowledge_type") == "dynamic":

            if not is_exportable_rag(
                item
            ):

                continue

            rows.append(
                {
                    "检查类型": "dynamic_notice",
                    "车型": item.get("model", ""),
                    "事项": join_questions(item),
                    "说明": "已识别为动态知识，未来可能随市场政策变化更新。",
                    "处理动作": "未来支持自动更新"
                }
            )

    return rows


def count_review_rows(rows, review_type):

    return sum(
        1
        for row in rows
        if row.get("检查类型") == review_type
    )


def get_dynamic_notice_stats(rows):

    stats = {
        "价格知识": 0,
        "金融政策": 0,
        "购车权益": 0,
        "活动政策": 0
    }

    for row in rows:

        if row.get("检查类型") != "dynamic_notice":

            continue

        text = (
            f"{row.get('事项', '')} "
            f"{row.get('说明', '')}"
        )

        if any(keyword in text for keyword in ["价格", "售价", "指导价", "多少钱", "价位"]):

            stats["价格知识"] += 1

        elif any(keyword in text for keyword in ["金融", "贷款", "免息", "0息", "费率"]):

            stats["金融政策"] += 1

        elif any(keyword in text for keyword in ["活动", "限时", "政策"]):

            stats["活动政策"] += 1

        else:

            stats["购车权益"] += 1

    return stats


def get_attention_stats(rows):

    stats = {
        "信息缺失": 0,
        "信息冲突": 0,
        "AI推断": 0,
        "范围异常": 0
    }

    label_map = {
        "missing": "信息缺失",
        "conflict": "信息冲突",
        "inference": "AI推断",
        "range_issue": "范围异常"
    }

    for row in rows:

        label = label_map.get(
            row.get(
                "检查类型"
            ),
            "信息缺失"
        )

        if label in stats:

            stats[
                label
            ] += 1

    return stats


def get_attention_label(review_type):

    return {
        "missing": "信息缺失",
        "conflict": "信息冲突",
        "inference": "AI推断",
        "range_issue": "范围异常"
    }.get(
        review_type,
        "信息缺失"
    )


def build_attention_rows(review_rows):

    rows = []

    for row in review_rows:

        review_type = row.get(
            "检查类型"
        )

        if review_type == "dynamic_notice":

            continue

        rows.append(
            {
                "类型": get_attention_label(
                    review_type
                ),
                "车型": row.get(
                    "车型",
                    ""
                ),
                "问题": row.get(
                    "事项",
                    ""
                ),
                "建议": row.get(
                    "处理动作",
                    ""
                ) or row.get(
                    "说明",
                    ""
                )
            }
        )

    return rows


def build_update_notice_rows(review_rows):

    rows = []

    for row in review_rows:

        if row.get(
            "检查类型"
        ) != "dynamic_notice":

            continue

        rows.append(
            {
                "车型": row.get(
                    "车型",
                    ""
                ),
                "问题": row.get(
                    "事项",
                    ""
                ),
                "说明": row.get(
                    "说明",
                    ""
                ),
                "建议": row.get(
                    "处理动作",
                    ""
                )
            }
        )

    return rows


def render_metric_card(title, value, caption=""):

    with st.container(border=True):

        st.metric(title, value)

        if caption:

            st.caption(caption)


def display_risk_level(value):

    if value == "warning":

        return "优化建议"

    if value == "error":

        return "需处理"

    return value or ""


def apply_filters(rows, model_label, category_label=None, trim_label=None, key_prefix=""):

    if not rows:

        return rows

    df = pd.DataFrame(
        rows
    )

    filtered = df

    if "车型" in df.columns:

        model_options = [
            "全部"
        ] + sorted(
            value
            for value in df[
                "车型"
            ].dropna().unique()
            if value
        )

        selected_model = st.selectbox(
            model_label,
            model_options,
            key=f"{key_prefix}_model_filter"
        )

        if selected_model != "全部":

            filtered = filtered[
                filtered[
                    "车型"
                ] == selected_model
            ]

    if category_label and "分类" in df.columns:

        category_options = [
            "全部"
        ] + sorted(
            value
            for value in df[
                "分类"
            ].dropna().unique()
            if value
        )

        selected_category = st.selectbox(
            category_label,
            category_options,
            key=f"{key_prefix}_category_filter"
        )

        if selected_category != "全部":

            filtered = filtered[
                filtered[
                    "分类"
                ] == selected_category
            ]

    if trim_label and "版本" in df.columns:

        trim_options = [
            "全部"
        ] + sorted(
            value
            for value in df[
                "版本"
            ].dropna().unique()
            if value
        )

        selected_trim = st.selectbox(
            trim_label,
            trim_options,
            key=f"{key_prefix}_trim_filter"
        )

        if selected_trim != "全部":

            filtered = filtered[
                filtered[
                    "版本"
                ] == selected_trim
            ]

    return filtered


def show_table(rows, empty_text, key=None):

    if isinstance(
        rows,
        pd.DataFrame
    ):

        has_rows = not rows.empty

    else:

        has_rows = bool(
            rows
        )

    if has_rows:

        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
            key=key
        )

    else:

        st.info(
            empty_text
        )


SUPPORTED_UPLOAD_TYPES = [
    "xlsx",
    "xls",
    "docx",
    "pdf",
    "txt",
    "png",
    "jpg",
    "jpeg",
    "webp"
]


MAX_UPLOAD_FILE_COUNT = 100


IMAGE_PREVIEW_CHARS = 1200


def get_uploaded_file_extension(file):

    return os.path.splitext(
        file.name
    )[1].lower()


def is_image_upload(file):

    return get_uploaded_file_extension(
        file
    ) in IMAGE_EXTENSIONS


def build_material_block(file_name, content):

    return "\n".join(
        [
            f"===== 文件：{file_name} =====",
            content.strip()
        ]
    )


def render_parse_preview(records):

    st.subheader(
        "资料解析预览"
    )

    rows = [
        {
            "文件名": record["file_name"],
            "文件类型": record["file_type"],
            "解析状态": record["status"]
        }
        for record in records
    ]

    show_table(
        rows,
        "暂无解析结果"
    )

    for record in records:

        title = (
            f"{record['file_name']} - {record['status']}"
        )

        with st.expander(
            title,
            expanded=False
        ):

            if record.get(
                "is_image"
            ) and record.get(
                "image_bytes"
            ):

                st.image(
                    record[
                        "image_bytes"
                    ],
                    caption=record[
                        "file_name"
                    ],
                    use_container_width=True
                )

            if record[
                "status"
            ] == "解析成功":

                preview = record.get(
                    "preview",
                    ""
                )

                if len(
                    preview
                ) > IMAGE_PREVIEW_CHARS:

                    st.text(
                        preview[:IMAGE_PREVIEW_CHARS]
                        + "\n...（内容已截断，完整内容已进入Material）"
                    )

                else:

                    st.text(
                        preview
                    )

            else:

                st.error(
                    record.get(
                        "error",
                        "解析失败"
                    )
                )

def render_generate_page() -> None:
    render_page_header(
        "新建知识库 Generate",
        "上传原始资料，自动提取事实、生成 RAG 知识并完成质量检查。",
        eyebrow="Generate 可用"
    )

    render_step_navigation(
        [
            "1 上传资料",
            "2 解析资料",
            "3 提取 Facts",
            "4 生成 RAG",
            "5 质量检查",
            "6 导出",
        ]
    )


    uploaded_files = st.file_uploader(
        "上传汽车资料（支持 Excel、Word、PDF、TXT 及图片资料）",
        type=SUPPORTED_UPLOAD_TYPES,
        accept_multiple_files=True
    )

    st.caption(
        "图片可用于识别活动海报、价格截图、配置截图、PPT页面截图、朋友圈营销长图和产品卖点图片。"
    )

    st.caption(
        f"单次最多 {MAX_UPLOAD_FILE_COUNT} 个文件；单张图片最大 10MB。"
    )


    if uploaded_files:

        if len(
            uploaded_files
        ) > MAX_UPLOAD_FILE_COUNT:

            st.error(
                f"MVP阶段每次最多上传 {MAX_UPLOAD_FILE_COUNT} 个文件，请减少文件数量后重试。"
            )

            st.stop()

        st.success(
            f"已上传 {len(uploaded_files)} 个文件"
        )

        st.caption(
            f"当前已选择：{len(uploaded_files)}/{MAX_UPLOAD_FILE_COUNT}"
        )

        with st.expander(
            "查看上传文件"
        ):

            for file in uploaded_files:

                file_size = getattr(
                    file,
                    "size",
                    None
                )

                if file_size is None and hasattr(
                    file,
                    "getvalue"
                ):

                    file_size = len(
                        file.getvalue()
                    )

                render_file_card(
                    file.name,
                    get_uploaded_file_extension(
                        file
                    ).lstrip(
                        "."
                    ) or "未知类型",
                    file_size,
                    "已上传"
                )

        if st.button(
            "🚀 开始生成RAG知识库"
        ):

            st.divider()

            st.subheader(
                "生成过程"
            )

            parse_box = st.empty()

            materials = []

            parse_records = []

            for file in uploaded_files:

                file_type = get_uploaded_file_extension(
                    file
                ).lstrip(
                    "."
                )

                is_image = is_image_upload(
                    file
                )

                try:

                    parse_box.info(
                        f"正在解析：{file.name}"
                    )

                    content = parse_file(
                        file
                    ).strip()

                    if not content:

                        raise ValueError(
                            "解析结果为空"
                        )

                    materials.append(
                        build_material_block(
                            file.name,
                            content
                        )
                    )

                    parse_records.append(
                        {
                            "file_name": file.name,
                            "file_type": file_type,
                            "status": "解析成功",
                            "preview": content,
                            "is_image": is_image,
                            "image_bytes": (
                                file.getvalue()
                                if is_image and hasattr(file, "getvalue")
                                else
                                None
                            )
                        }
                    )

                except Exception as e:

                    st.error(
                        f"{file.name}解析失败：{e}"
                    )

                    parse_records.append(
                        {
                            "file_name": file.name,
                            "file_type": file_type,
                            "status": "解析失败",
                            "error": str(
                                e
                            ),
                            "is_image": is_image,
                            "image_bytes": (
                                file.getvalue()
                                if is_image and hasattr(file, "getvalue")
                                else
                                None
                            )
                        }
                    )

            material = "\n\n".join(
                materials
            )

            render_parse_preview(
                parse_records
            )

            if not material.strip():

                st.error(
                    "没有可进入生成链路的有效资料，请检查上传文件或图片解析配置。"
                )

                st.stop()

            image_records = [
                record
                for record in parse_records
                if record.get(
                    "is_image"
                )
            ]

            image_parse_stats = {
                "image_file_count": len(
                    image_records
                ),
                "image_parse_success": sum(
                    1
                    for record in image_records
                    if record.get(
                        "status"
                    ) == "解析成功"
                ),
                "image_parse_failed": sum(
                    1
                    for record in image_records
                    if record.get(
                        "status"
                    ) != "解析成功"
                ),
                "vision_model": get_vision_model_name()
            }

            parse_box.success(
                f"解析完成，成功 {len(materials)} 个，失败 {len(uploaded_files) - len(materials)} 个"
            )

            status_box = st.empty()

            logs = []

            def update_progress(step, data):

                if step == "Step1":

                    logs.append(
                        f"Step1 Facts事实抽取完成：{len(data.get('facts', []))} 条"
                    )

                elif step == "Step2":

                    logs.append(
                        f"Step2 RAG知识生成完成：{len(data.get('rag_knowledge', []))} 条"
                    )

                elif step == "Step3":

                    logs.append(
                        "Step3 QC质量检测完成"
                    )

                status_box.markdown(
                    "\n\n".join(
                        logs
                    )
                )

            with st.spinner(
                "AI正在生成知识库..."
            ):

                result = run_pipeline(
                    material,
                    progress_callback=update_progress,
                    source_files=[
                        file.name
                        for file in uploaded_files
                    ],
                    image_parse_stats=image_parse_stats
                )

            st.success(
                "RAG生成完成"
            )

            st.caption(
                f"本次任务编号：{result['run_id']}"
            )

            facts = result[
                "facts"
            ]

            rag = result[
                "rag"
            ]

            qc = result[
                "qc"
            ]

            project_info = get_project_info(
                facts,
                rag
            )

            static_rows = build_knowledge_rows(
                rag,
                "static"
            )

            dynamic_rows = build_knowledge_rows(
                rag,
                "dynamic"
            )

            review_rows = build_review_center_rows(
                facts,
                rag
            )

            qc_issues = qc.get(
                "issues",
                []
            )

            tabs = st.tabs(
                [
                    "生成概览",
                    "车型配置知识",
                    "价格政策知识",
                    "知识检查中心",
                    "QC报告",
                    "下载"
                ]
            )

            with tabs[0]:

                st.subheader(
                    f"{project_info['brand']} {project_info['model']}"
                )

                col_files,col_facts,col_rag,col_qc = st.columns(4)

                with col_files:

                    render_metric_card(
                        "文件数量",
                        len(uploaded_files)
                    )

                with col_facts:

                    render_metric_card(
                        "Facts",
                        len(facts.get("facts", []))
                    )

                with col_rag:

                    render_metric_card(
                        "RAG",
                        len(rag.get("rag_knowledge", []))
                    )

                with col_qc:

                    render_metric_card(
                        "QC状态",
                        qc.get(
                            "overall_result",
                            "未知"
                        )
                    )

                st.subheader(
                    "知识统计"
                )

                col_static,col_dynamic,col_total = st.columns(3)

                with col_static:

                    render_metric_card(
                        "车型配置知识",
                        len(
                            static_rows
                        )
                    )

                with col_dynamic:

                    render_metric_card(
                        "价格政策知识",
                        len(
                            dynamic_rows
                        )
                    )

                with col_total:

                    render_metric_card(
                        "RAG总数",
                        len(
                            rag.get(
                                "rag_knowledge",
                                []
                            )
                        )
                    )

                st.subheader(
                    "知识检查"
                )

                col_missing,col_conflict,col_inference,col_notice,col_issue = st.columns(5)

                with col_missing:

                    render_metric_card(
                        "信息缺失",
                        count_review_rows(
                            review_rows,
                            "missing"
                        )
                    )

                with col_conflict:

                    render_metric_card(
                        "信息冲突",
                        count_review_rows(
                            review_rows,
                            "conflict"
                        )
                    )

                with col_inference:

                    render_metric_card(
                        "AI推断",
                        count_review_rows(
                            review_rows,
                            "inference"
                        )
                    )

                with col_notice:

                    render_metric_card(
                        "动态知识",
                        count_review_rows(
                            review_rows,
                            "dynamic_notice"
                        )
                    )

                with col_issue:

                    render_metric_card(
                        "QC问题",
                        len(
                            qc_issues
                        )
                    )

            with tabs[1]:

                st.subheader(
                    "车型配置知识"
                )

                st.caption(
                    "包含车型长期稳定信息：车型定位、空间、动力、续航、补能、智驾、安全、舒适配置等。该类知识通常无需频繁更新。"
                )

                static_table = apply_filters(
                    static_rows,
                    "车型筛选",
                    category_label="分类筛选",
                    key_prefix="static"
                )

                show_table(
                    static_table,
                    "暂无车型配置知识",
                    key="static_knowledge_table"
                )

            with tabs[2]:

                st.subheader(
                    "价格政策知识"
                )

                st.caption(
                    "包含市场变化信息：官方价格、金融政策、购车权益、优惠活动、门店政策等。该类知识需要根据市场变化持续维护更新。"
                )

                dynamic_table = apply_filters(
                    dynamic_rows,
                    "车型筛选 ",
                    category_label="分类筛选 ",
                    trim_label="版本筛选",
                    key_prefix="dynamic"
                )

                show_table(
                    dynamic_table,
                    "暂无价格政策知识",
                    key="dynamic_knowledge_table"
                )

            with tabs[3]:

                st.subheader(
                    "知识检查中心"
                )

                st.caption(
                    "用于区分需要人工处理的问题，以及未来可能需要维护更新的动态知识。"
                )

                attention_rows = build_attention_rows(
                    review_rows
                )

                update_notice_rows = build_update_notice_rows(
                    review_rows
                )

                with st.container(
                    border=True
                ):

                    st.subheader(
                        f"需要人工关注（{len(attention_rows)}）"
                    )

                    attention_stats = get_attention_stats(
                        [
                            row
                            for row in review_rows
                            if row.get("检查类型") != "dynamic_notice"
                        ]
                    )

                    stat_cols = st.columns(4)

                    for stat_col, (name, value) in zip(
                        stat_cols,
                        attention_stats.items()
                    ):

                        with stat_col:

                            render_metric_card(
                                name,
                                value
                            )

                    with st.expander(
                        "展开需要人工关注的内容",
                        expanded=bool(
                            attention_rows
                        )
                    ):

                        show_table(
                            attention_rows,
                            "暂无需要人工关注的问题",
                            key="attention_review_table"
                        )

                with st.container(
                    border=True
                ):

                    st.subheader(
                        f"需要关注更新（{len(update_notice_rows)}）"
                    )

                    st.caption(
                        "价格政策、金融政策、购车权益和活动政策不是错误，只是未来可能随市场变化需要维护。"
                    )

                    stats = get_dynamic_notice_stats(
                        [
                            row
                            for row in review_rows
                            if row.get("检查类型") == "dynamic_notice"
                        ]
                    )

                    stat_cols = st.columns(4)

                    for stat_col, (name, value) in zip(
                        stat_cols,
                        stats.items()
                    ):

                        with stat_col:

                            render_metric_card(
                                name,
                                value
                            )

                    with st.expander(
                        "展开需要关注更新的内容"
                    ):

                        show_table(
                            update_notice_rows,
                            "暂无需要关注更新的动态知识",
                            key="update_notice_table"
                        )

            with tabs[4]:

                st.subheader(
                    "QC报告"
                )

                summary = qc.get(
                    "summary",
                    {}
                )

                col_result,col_total,col_warning,col_error = st.columns(4)

                with col_result:

                    st.metric(
                        "总体结果",
                        qc.get(
                            "overall_result",
                            "未知"
                        )
                    )

                with col_total:

                    st.metric(
                        "RAG总数",
                        summary.get(
                            "total_rag",
                            len(
                                rag.get(
                                    "rag_knowledge",
                                    []
                                )
                            )
                        )
                    )

                with col_warning:

                    st.metric(
                        "优化建议",
                        summary.get(
                            "warning",
                            0
                        )
                    )

                with col_error:

                    st.metric(
                        "错误",
                        summary.get(
                            "error",
                            0
                        )
                    )

                issue_rows = [
                    {
                        "问题类型": item.get(
                            "issue_type",
                            ""
                        ),
                        "严重等级": item.get(
                            "display_level",
                            display_risk_level(
                                item.get(
                                    "risk_level",
                                    ""
                                )
                            )
                        ),
                        "描述": item.get(
                            "description",
                            ""
                        ),
                        "建议": item.get(
                            "suggestion",
                            ""
                        )
                    }
                    for item in qc_issues
                    if isinstance(
                        item,
                        dict
                    )
                ]

                show_table(
                    issue_rows,
                    "暂无QC问题",
                    key="qc_issue_table"
                )

            with tabs[5]:

                st.subheader(
                    "Excel下载"
                )

                excel_paths = result.get(
                    "excel_paths",
                    {}
                )

                excluded_count = result.get(
                    "rag",
                    {}
                ).get(
                    "export_excluded_count",
                    0
                )

                if excluded_count:

                    st.info(
                        f"已自动排除 {excluded_count} 条不适合导出的待确认知识，可在知识检查中心查看。"
                    )

                col_static_download,col_dynamic_download = st.columns(2)

                static_path = excel_paths.get(
                    "static"
                )

                dynamic_path = excel_paths.get(
                    "dynamic"
                )

                with col_static_download:

                    if static_path:

                        with open(
                            static_path,
                            "rb"
                        ) as f:

                            st.download_button(
                                label="下载车型配置知识库Excel",
                                data=f,
                                file_name=os.path.basename(
                                    static_path
                                )
                            )

                with col_dynamic_download:

                    if dynamic_path:

                        with open(
                            dynamic_path,
                            "rb"
                        ) as f:

                            st.download_button(
                                label="下载价格政策知识库Excel",
                                data=f,
                                file_name=os.path.basename(
                                    dynamic_path
                                )
                            )

