import os

import pandas as pd
import streamlit as st

from main import run_pipeline
from parser.parser_factory import parse_file


st.set_page_config(
    page_title="AutoRAG-Studio",
    page_icon="🚗",
    layout="wide"
)


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


def is_gap_resolved(item, coverage_text):

    text = get_review_text(item)

    if not text:

        return False

    for keywords in REVIEW_TOPIC_KEYWORDS.values():

        if any(keyword in text for keyword in keywords):

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

    gaps = []
    gaps.extend(facts_data.get("info_gaps", []))
    gaps.extend(rag_data.get("info_gaps", []))

    for item in gaps:

        if is_gap_resolved(item, coverage_text):

            continue

        review_type = classify_review_item(item)

        if isinstance(item, dict):

            rows.append(
                {
                    "检查类型": review_type,
                    "车型": item.get("model", "") or item.get("vehicle", ""),
                    "事项": item.get("missing_content", "") or item.get("item", ""),
                    "说明": item.get("description", "") or item.get("reason", ""),
                    "处理动作": "补充资料"
                }
            )

        else:

            rows.append(
                {
                    "检查类型": "missing",
                    "车型": "",
                    "事项": str(item),
                    "说明": "",
                    "处理动作": "补充资料"
                }
            )

    for item in rag_data.get("confirm_items", []):

        review_type = classify_review_item(item)

        if isinstance(item, dict):

            rows.append(
                {
                    "检查类型": review_type,
                    "车型": item.get("model", ""),
                    "事项": item.get("item", "") or item.get("question", ""),
                    "说明": item.get("reason", ""),
                    "处理动作": (
                        "人工确认"
                        if review_type == "conflict"
                        else
                        "人工核查"
                    )
                }
            )

        else:

            rows.append(
                {
                    "检查类型": review_type,
                    "车型": "",
                    "事项": str(item),
                    "说明": "",
                    "处理动作": (
                        "人工确认"
                        if review_type == "conflict"
                        else
                        "人工核查"
                    )
                }
            )

    for item in rag_data.get("rag_knowledge", []):

        if item.get("knowledge_type") == "dynamic":

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


def apply_filters(rows, model_label, category_label=None, trim_label=None):

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
            model_options
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
            category_options
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
            trim_options
        )

        if selected_trim != "全部":

            filtered = filtered[
                filtered[
                    "版本"
                ] == selected_trim
            ]

    return filtered


def show_table(rows, empty_text):

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
            hide_index=True
        )

    else:

        st.info(
            empty_text
        )


st.title(
    "🚗 AutoRAG-Studio"
)

st.caption(
    "汽车行业 RAG知识生成与检查平台"
)


uploaded_files = st.file_uploader(
    "上传汽车资料（支持 txt / Word / Excel / PDF）",
    type=[
        "txt",
        "docx",
        "xlsx",
        "pdf"
    ],
    accept_multiple_files=True
)


if uploaded_files:

    st.success(
        f"已上传 {len(uploaded_files)} 个文件"
    )

    with st.expander(
        "查看上传文件"
    ):

        for file in uploaded_files:

            st.write(
                f"📄 {file.name}"
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

        for file in uploaded_files:

            try:

                parse_box.info(
                    f"正在解析：{file.name}"
                )

                materials.append(
                    parse_file(
                        file
                    )
                )

            except Exception as e:

                st.error(
                    f"{file.name}解析失败：{e}"
                )

        material = "\n\n".join(
            materials
        )

        parse_box.success(
            f"全部解析完成，共{len(uploaded_files)}个文件"
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
                ]
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
                category_label="分类筛选"
            )

            show_table(
                static_table,
                "暂无车型配置知识"
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
                trim_label="版本筛选"
            )

            show_table(
                dynamic_table,
                "暂无价格政策知识"
            )

        with tabs[3]:

            st.subheader(
                "知识检查中心"
            )

            st.caption(
                "用于区分资料缺失、信息冲突、AI推断和动态知识提醒。动态知识提醒不是问题，只表示未来可能需要随市场政策更新。"
            )

            review_tabs = st.tabs(
                [
                    "信息缺失",
                    "信息冲突",
                    "AI推断",
                    "动态知识提醒"
                ]
            )

            review_labels = [
                ("missing", "暂无信息缺失"),
                ("conflict", "暂无信息冲突"),
                ("inference", "暂无AI推断"),
                ("dynamic_notice", "暂无动态知识提醒")
            ]

            for tab, (review_type, empty_text) in zip(
                review_tabs,
                review_labels
            ):

                with tab:

                    filtered_rows = [
                        row
                        for row in review_rows
                        if row.get(
                            "检查类型"
                        ) == review_type
                    ]

                    if review_type == "dynamic_notice":

                        stats = get_dynamic_notice_stats(
                            filtered_rows
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

                        with st.expander("展开详情"):

                            show_table(
                                filtered_rows,
                                empty_text
                            )

                    else:

                        show_table(
                            filtered_rows,
                            empty_text
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
                "暂无QC问题"
            )

        with tabs[5]:

            st.subheader(
                "Excel下载"
            )

            excel_paths = result.get(
                "excel_paths",
                {}
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
