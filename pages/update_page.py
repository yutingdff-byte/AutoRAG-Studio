"""Update mode skeleton for future V0.8 milestones."""

from __future__ import annotations

import streamlit as st

from knowledge.adapter import knowledge_to_preview_rows
from knowledge.restore_manager import RestoreResult, get_restore_cache_key, restore
from knowledge.adapter import rag_to_knowledge
from diff.engine import compare
from diff.models import ChangeType, DiffRunResult, DetectedUpdateScope
from diff.reasons import change_type_label, review_reason_label
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


def _history_files_cache_key(files, deep_restore: bool = False) -> str:
    if not files:
        return ""
    return "|".join(get_restore_cache_key(file, deep_restore=deep_restore) for file in files)


def _restore_history_files(files, deep_restore: bool = False) -> RestoreResult:
    if not files:
        st.session_state.update_restore_result = None
        st.session_state.update_restore_logs = []
        st.session_state.update_restore_cache_key = ""
        st.session_state.update_restore_running = False
        return RestoreResult()

    cache_key = _history_files_cache_key(files, deep_restore=deep_restore)
    restore_cache = st.session_state.setdefault("update_restore_cache", {})
    cached_result = restore_cache.get(cache_key)
    if cached_result is not None:
        logs = [f"Restore｜缓存命中｜同一批历史文件已恢复，直接复用结果｜0.00s"]
        st.session_state.update_restore_result = cached_result
        st.session_state.update_restore_logs = logs
        st.session_state.update_restore_cache_key = cache_key
        st.info(logs[0])
        return cached_result

    log_box = st.empty()
    logs: list[str] = []

    def update_progress(file_name: str, stage: str, status: str, message: str) -> None:
        logs.append(f"{file_name}｜{stage}｜{status}｜{message}")
        st.session_state.update_restore_logs = logs
        log_box.info("\n".join(logs[-8:]))

    st.session_state.update_restore_running = True
    st.session_state.update_restore_cache_key = cache_key

    try:
        with st.spinner("正在恢复历史知识..."):
            result = restore(
                files,
                progress_callback=update_progress,
                deep_restore=deep_restore,
            )
    except Exception as exc:
        logs.append(f"Restore｜失败｜{exc}")
        st.session_state.update_restore_result = RestoreResult()
        st.session_state.update_restore_logs = logs
        raise
    finally:
        st.session_state.update_restore_running = False

    restore_cache[cache_key] = result
    st.session_state.update_restore_result = result
    st.session_state.update_restore_logs = logs
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
        report = file_result.report or {}
        if report.get("format_id") == "SYSTEM_STANDARD_WORD_V1":
            st.info(
                "已识别为系统标准历史知识格式，已快速恢复，无需模型处理。"
                f"候选记录 {report.get('candidate_records', 0)} 条，"
                f"成功 {report.get('success_count', 0)} 条，"
                f"失败 {report.get('failed_count', 0)} 条，"
                f"LLM 调用 {report.get('llm_calls', 0)} 次。"
            )

        if file_result.success:
            st.success(
                f"{file_result.file_name}：恢复 {len(file_result.items)} 条知识，耗时 {file_result.elapsed_seconds:.2f}s"
            )
        else:
            st.error(
                f"{file_result.file_name}：{file_result.error or '知识恢复失败，请检查文件格式。'}"
            )

        if file_result.logs:
            with st.expander(f"{file_result.file_name} 恢复日志", expanded=not file_result.success):
                for entry in file_result.logs:
                    st.caption(entry)

        failures = report.get("failures") or []
        if failures:
            with st.expander(f"{file_result.file_name} 标准恢复失败记录", expanded=False):
                st.dataframe(
                    [
                        {
                            "记录": failure.get("source_record_index"),
                            "段落开始": failure.get("source_paragraph_start"),
                            "段落结束": failure.get("source_paragraph_end"),
                            "原因": failure.get("reason"),
                        }
                        for failure in failures
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

    if result.items:
        with st.expander("恢复结果预览", expanded=True):
            st.dataframe(
                knowledge_to_preview_rows(result.items),
                use_container_width=True,
                hide_index=True,
            )


def _build_material_block(file_name: str, content: str) -> str:
    return f"===== 文件：{file_name} =====\n{content}"


def _generate_new_knowledge(files):
    if not files:
        st.session_state.update_new_knowledge = []
        return []

    materials = []
    source_files = []
    errors = []

    with st.spinner("正在解析新增资料并生成新知识..."):
        from parser.parser_factory import parse_file
        from agents.fact_agent import extract_facts
        from agents.rag_agent import generate_rag

        for file in files:
            try:
                content = parse_file(file).strip()
                if not content:
                    raise ValueError("解析结果为空")
                materials.append(_build_material_block(file.name, content))
                source_files.append(file.name)
            except Exception as exc:
                errors.append(f"{file.name}：{exc}")

        if not materials:
            st.session_state.update_new_knowledge = []
            st.session_state.update_new_errors = errors
            return []

        material = "\n\n".join(materials)
        facts = extract_facts(material)
        rag = generate_rag(facts)
        items = rag_to_knowledge(rag, source_file="、".join(source_files))

    st.session_state.update_new_knowledge = items
    st.session_state.update_new_errors = errors
    return items


def _render_new_knowledge_result(items, errors) -> None:
    render_section_title("新增资料知识")

    if errors:
        for error in errors:
            st.error(f"新增资料处理失败：{error}")

    if not items:
        st.warning("本轮新增资料未生成有效知识。")
        return

    models = sorted({item.model for item in items if item.model})
    need_confirm_count = sum(1 for item in items if item.need_confirm)
    render_metric_cards(
        [
            ("新增知识", len(items), "由本轮新增资料生成的统一知识对象数量"),
            ("涉及车型", len(models), "根据新增知识中的车型字段统计"),
            ("待确认", need_confirm_count, "新增知识中标记为需要确认的条目"),
        ]
    )

    with st.expander("新增知识预览", expanded=False):
        st.dataframe(
            knowledge_to_preview_rows(items),
            use_container_width=True,
            hide_index=True,
        )


def _render_scope(scope: DetectedUpdateScope) -> None:
    render_section_title("系统识别本轮资料范围")
    st.info(scope.summary or "未识别到明确更新范围。")
    render_metric_cards(
        [
            ("涉及品牌", "、".join(scope.brands) or "—", ""),
            ("涉及车型", "、".join(scope.models) or "—", ""),
            ("主要分类", "、".join(scope.categories) or "—", ""),
            ("知识类型", "、".join(scope.knowledge_types) or "—", ""),
        ]
    )
    not_obvious = scope.metadata.get("not_obvious_categories", [])
    if not_obvious:
        st.caption("未明显涉及：" + "、".join(not_obvious))


def _diff_rows(results, change_type: ChangeType | None = None) -> list[dict]:
    rows = []
    for result in results:
        if change_type and result.change_type != change_type:
            continue
        old_item = result.old_item
        new_item = result.new_item
        rows.append(
            {
                "问题": (new_item.question if new_item else old_item.question if old_item else ""),
                "原回答": old_item.answer if old_item else "",
                "新回答": new_item.answer if new_item else "",
                "状态": change_type_label(result.change_type),
                "变化说明": result.change_summary,
                "匹配方式": result.match_method.value,
                "置信度": result.overall_confidence,
                "待确认原因": review_reason_label(result.review_reason),
                "来源文件": "、".join((new_item or old_item).source_files) if (new_item or old_item) else "",
            }
        )
    return rows


def _render_diff_result(result: DiffRunResult) -> None:
    _render_scope(result.detected_scope)

    render_section_title("差异分析结果")
    render_metric_cards(
        [
            ("总知识数", result.total_count, "Diff 结果总条数"),
            ("新增", result.added_count, "新增资料中出现、历史知识中未可靠匹配的知识"),
            ("更新", result.updated_count, "已匹配且回答发生明确变化的知识"),
            ("未变化", result.unchanged_count, "未变化或本轮未明显涉及、默认保留的旧知识"),
            ("待确认", result.review_required_count, "无法可靠自动处理，需要人工判断的知识"),
        ]
    )

    tabs = st.tabs(["全部", "新增", "更新", "未变化", "待确认"])
    tab_specs = [
        (tabs[0], None),
        (tabs[1], ChangeType.ADDED),
        (tabs[2], ChangeType.UPDATED),
        (tabs[3], ChangeType.UNCHANGED),
        (tabs[4], ChangeType.REVIEW_REQUIRED),
    ]
    for tab, change_type in tab_specs:
        with tab:
            rows = _diff_rows(result.results, change_type)
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.caption("暂无数据。")


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

        restore_result = st.session_state.get("update_restore_result") or RestoreResult()
        deep_restore_history = False
        if old_files:
            has_word_file = any(str(getattr(file, "name", "")).lower().endswith(".docx") for file in old_files)
            if has_word_file:
                deep_restore_history = st.checkbox(
                    "深度恢复未识别内容（会调用Fact/RAG，耗时较长）",
                    value=False,
                    help="默认优先识别Word中的表格、问答和标题正文。只有勾选后，才会对未识别剩余文本继续调用现有Fact/RAG。",
                    key="update_deep_restore_history",
                )
                st.caption("建议先使用快速恢复；如果恢复结果明显缺少内容，再开启深度恢复。")

        current_cache_key = _history_files_cache_key(old_files, deep_restore=deep_restore_history)
        if (
            current_cache_key
            and st.session_state.get("update_restore_cache_key")
            and st.session_state.get("update_restore_cache_key") != current_cache_key
        ):
            restore_result = RestoreResult()
            st.session_state.update_restore_result = None
            st.session_state.update_restore_logs = []

        if old_files and st.button("开始恢复历史知识", use_container_width=True):
            try:
                restore_result = _restore_history_files(old_files, deep_restore=deep_restore_history)
            except Exception as exc:
                st.session_state.update_restore_result = RestoreResult()
                st.session_state.update_restore_logs = [
                    f"Restore｜失败｜{exc}"
                ]
                st.error(f"知识恢复失败：{exc}")

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

    if old_files and restore_result.files:
        _render_restore_result(restore_result)

    if new_files:
        if st.button("生成新增知识", use_container_width=True):
            _generate_new_knowledge(new_files)

        _render_new_knowledge_result(
            st.session_state.get("update_new_knowledge", []),
            st.session_state.get("update_new_errors", []),
        )

    old_items = restore_result.items if old_files else []
    new_items = st.session_state.get("update_new_knowledge", [])
    can_diff = bool(old_items and new_items)

    if st.button("开始差异分析", use_container_width=True, disabled=not can_diff):
        st.session_state.update_diff_result = compare(old_items, new_items)

    if not can_diff:
        st.caption("恢复历史知识并生成新增知识后，可以开始差异分析。")

    diff_result = st.session_state.get("update_diff_result")
    if diff_result:
        _render_diff_result(diff_result)
