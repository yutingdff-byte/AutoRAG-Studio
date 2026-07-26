"""Update mode skeleton for future V0.8 milestones."""

from __future__ import annotations

import streamlit as st

from knowledge.adapter import knowledge_to_preview_rows
from knowledge.restore_manager import RestoreResult, restore
from ui.components import (
    render_file_card,
    render_metric_cards,
    render_page_header,
    render_section_title,
    render_step_navigation,
)


HISTORY_TYPES = ["xlsx", "xls", "docx"]
NEW_MATERIAL_TYPES = ["xlsx", "xls", "docx", "pdf", "txt", "png", "jpg", "jpeg", "webp"]


def _file_type(file) -> str:
    name = getattr(file, "name", "")
    if "." not in name:
        return "未知类型"
    return name.rsplit(".", 1)[-1].lower()


def _render_uploaded_files(files, empty_text: str) -> None:
    if not files:
        st.caption(empty_text)
        return

    for file in files:
        size = getattr(file, "size", None)
        if size is None and hasattr(file, "getvalue"):
            size = len(file.getvalue())
        render_file_card(file.name, _file_type(file), size, "文件已接收")


def _restore_history_files(files) -> RestoreResult:
    if not files:
        st.session_state.update_restore_result = None
        return RestoreResult()

    with st.spinner("正在恢复历史知识..."):
        result = restore(files)

    st.session_state.update_restore_result = result
    return result


def _render_restore_result(result: RestoreResult) -> None:
    render_section_title("恢复结果")

    render_metric_cards(
        [
            ("恢复知识", result.restored_count, "从历史知识文件恢复出的统一知识对象数量"),
            ("涉及车型", result.model_count, "根据历史知识中的车型字段统计"),
            ("待确认", result.need_confirm_count, "历史知识中标记为需要确认的条目"),
        ]
    )

    for file_result in result.files:
        if file_result.success:
            st.success(
                f"{file_result.file_name}：恢复 {len(file_result.items)} 条知识"
            )
        else:
            st.error(
                f"{file_result.file_name}：{file_result.error or '知识恢复失败，请检查文件格式。'}"
            )

    if result.items:
        with st.expander("恢复结果预览", expanded=True):
            st.dataframe(
                knowledge_to_preview_rows(result.items),
                use_container_width=True,
                hide_index=True,
            )


def render_update_page() -> None:
    render_page_header(
        "更新已有知识库 Update",
        "从历史知识中恢复知识，与新增资料对比，确认变化后生成新版知识库。",
        eyebrow="V0.8 框架页面",
    )

    render_step_navigation(
        [
            "1 上传历史知识",
            "2 上传新增资料",
            "3 恢复统一知识",
            "4 差异分析",
            "5 人工确认",
            "6 导出",
        ]
    )

    old_col, new_col = st.columns(2)

    with old_col:
        render_section_title("历史知识")
        st.caption(
            "支持导入已有 Excel 或 Word 知识资料。Excel 将按标准字段读取；Word 将通过现有 Parser → Facts → RAG 流程恢复为统一知识对象。"
        )
        old_files = st.file_uploader(
            "上传历史知识文件",
            type=HISTORY_TYPES,
            accept_multiple_files=True,
            key="update_old_files",
        )
        _render_uploaded_files(old_files, "尚未上传历史知识文件。")

        restore_result = _restore_history_files(old_files)

    with new_col:
        render_section_title("新增资料")
        st.caption("上传本次新增或更新的产品资料、价格政策、车型配置及其他业务资料。")
        new_files = st.file_uploader(
            "上传新增资料",
            type=NEW_MATERIAL_TYPES,
            accept_multiple_files=True,
            key="update_new_files",
        )
        _render_uploaded_files(new_files, "尚未上传新增资料。")

    if old_files:
        _render_restore_result(restore_result)

    if new_files:
        st.info("新增资料文件已接收。Diff Engine 将在下一开发阶段接入。")

    render_section_title("预计分析结果")
    render_metric_cards(
        [
            ("新增", "—", "下一阶段由 Diff Engine 生成"),
            ("修改", "—", "下一阶段由 Diff Engine 生成"),
            ("保留", "—", "下一阶段由 Diff Engine 生成"),
            ("候选删除", "—", "下一阶段由 Diff Engine 生成"),
            ("待确认", "—", "下一阶段由 Review 流程生成"),
        ]
    )

    render_section_title("人工确认预览")
    st.caption("界面预览，不进入真实 session 数据，也不会参与导出。")
    with st.container(border=True):
        st.write("问题：某车型的官方指导价是多少？")
        st.write("原回答：249,800元")
        st.write("新回答：239,800元")
        st.write("状态：修改")

    if st.button("开始差异分析", use_container_width=True, disabled=True):
        st.info("Knowledge Parser 与 Diff Engine 将在下一阶段接入。")
