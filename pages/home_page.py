"""Home page for the V0.8 dual-mode entry."""

from __future__ import annotations

import streamlit as st

from ui.components import render_feature_card, render_page_header, render_section_title


def render_home_page() -> None:
    render_page_header(
        "AutoRAG-Studio",
        "AI 知识库生成、检查与持续更新平台。",
    )

    render_section_title("选择工作模式")

    generate_col, update_col = st.columns(2)

    with generate_col:
        render_feature_card(
            "新建知识库 Generate",
            "上传原始资料，自动提取事实、生成知识并完成质量检查，最终导出车型配置知识库和价格政策知识库。",
            ["多格式解析", "图片识别", "Facts", "RAG", "QC"],
            "可用",
            "ready",
        )
        if st.button("进入新建知识库", use_container_width=True, key="home_go_generate"):
            st.session_state.current_mode = "generate"
            st.session_state.navigation_mode = "generate"
            st.rerun()

    with update_col:
        render_feature_card(
            "更新知识库 Update",
            "导入历史知识与新增资料，后续将识别变化、支持人工确认并生成新版知识库。",
            ["历史知识恢复", "Diff", "人工确认", "合并导出"],
            "V0.8 建设中",
            "building",
        )
        if st.button("进入更新知识库", use_container_width=True, key="home_go_update"):
            st.session_state.current_mode = "update"
            st.session_state.navigation_mode = "update"
            st.rerun()
