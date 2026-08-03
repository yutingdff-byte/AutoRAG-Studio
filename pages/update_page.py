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


def _restore_stage_label(stage: str) -> str:
    stage = str(stage or "")
    if stage in {"Format Detector"}:
        return "识别历史知识格式"
    if stage in {"Standard Restore", "直接恢复Knowledge", "识别现成问答"}:
        return "恢复历史知识"
    if stage in {"Parser", "读取文档", "KnowledgeItem", "合并去重", "完成"}:
        return "整理恢复结果"
    if stage in {"深度提取Facts", "生成RAG", "Restore"}:
        return "AI 智能恢复"
    return stage or "恢复历史知识"


def _restore_message_text(stage: str, status: str, message: str) -> str:
    stage_label = _restore_stage_label(stage)
    text = str(message or "")

    replacements = {
        "已识别为系统标准历史知识格式": "已识别系统标准知识格式",
        "正在快速恢复，无需模型处理": "正在恢复历史知识",
        "调用现有Fact Agent恢复事实": "正在使用 AI 智能恢复复杂文档",
        "调用现有RAG Agent生成知识": "正在使用 AI 整理历史知识",
        "Fact Agent": "AI 智能恢复",
        "RAG Agent": "AI 智能恢复",
        "Fact/RAG": "AI 智能恢复",
        "Parser": "文件解析",
        "Standard Restore": "历史知识恢复",
        "Fast Restore": "历史知识恢复",
        "Deep Restore": "AI 智能恢复",
        "LLM调用 0": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    if "qa_v1" in text or "intent_v1" in text or "严格解析" in text:
        return "已完成结构校验"
    if "LLM调用" in text:
        text = text.split("，LLM调用", 1)[0].strip()
    text = text.replace("候选记录", "识别记录")

    if "候选记录" in text and "成功" in text:
        return text
    if status == "缓存命中":
        return "同一批历史文件已恢复，直接复用结果"
    if stage_label == "识别历史知识格式" and status == "成功":
        return "已识别系统标准知识格式"
    if stage_label == "AI 智能恢复" and status in {"开始", "日志"}:
        return text or "正在使用 AI 智能恢复复杂文档"
    return text or status


def _friendly_restore_log_entry(entry: str) -> str:
    parts = str(entry or "").split("｜")
    if len(parts) >= 4:
        stage = parts[1]
        status = parts[2]
        message = "｜".join(parts[3:])
        return f"{_restore_stage_label(stage)}｜{status}｜{_restore_message_text(stage, status, message)}"
    if len(parts) >= 3:
        stage = parts[0]
        status = parts[1]
        message = "｜".join(parts[2:])
        return f"{_restore_stage_label(stage)}｜{status}｜{_restore_message_text(stage, status, message)}"
    return str(entry or "")


def _should_offer_ai_restore(result: RestoreResult) -> bool:
    for file_result in result.files:
        if not file_result.success:
            continue
        for entry in file_result.logs:
            if "暂缓" in entry and ("深度" in entry or "剩余" in entry):
                return True
    return False


def _restore_history_files(files, deep_restore: bool = False) -> RestoreResult:
    if not files:
        st.session_state.update_restore_result = None
        st.session_state.update_restore_logs = []
        st.session_state.update_restore_cache_key = ""
        st.session_state.update_restore_running = False
        st.session_state.update_restore_ai_mode = False
        return RestoreResult()

    cache_key = _history_files_cache_key(files, deep_restore=deep_restore)
    restore_cache = st.session_state.setdefault("update_restore_cache", {})
    cached_result = restore_cache.get(cache_key)
    if cached_result is not None:
        logs = [f"恢复历史知识｜缓存命中｜同一批历史文件已恢复，直接复用结果｜0.00s"]
        st.session_state.update_restore_result = cached_result
        st.session_state.update_restore_logs = logs
        st.session_state.update_restore_cache_key = cache_key
        st.info("同一批历史文件已恢复，直接复用结果。")
        return cached_result

    log_box = st.empty()
    logs: list[str] = []

    def update_progress(file_name: str, stage: str, status: str, message: str) -> None:
        logs.append(f"{file_name}｜{stage}｜{status}｜{message}")
        st.session_state.update_restore_logs = logs
        friendly_logs = [_friendly_restore_log_entry(entry) for entry in logs[-5:]]
        log_box.info("\n".join(friendly_logs))

    st.session_state.update_restore_running = True
    st.session_state.update_restore_cache_key = cache_key

    try:
        with st.spinner("正在识别历史知识格式..."):
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
            failed_count = report.get("failed_count", 0) + report.get("skipped_count", 0)
            message = "✓ 已识别系统标准知识格式，系统已自动完成恢复。"
            if failed_count:
                message += f" 有 {failed_count} 条记录需要进一步查看。"
            st.info(message)

        if file_result.success:
            st.success(
                f"{file_result.file_name}：历史知识恢复完成，恢复 {len(file_result.items)} 条，耗时 {file_result.elapsed_seconds:.2f}s"
            )
        else:
            st.error(
                f"{file_result.file_name}：{file_result.error or '知识恢复失败，请检查文件格式。'}"
            )

        if file_result.logs:
            with st.expander("查看恢复日志", expanded=False):
                for entry in file_result.logs:
                    st.caption(_friendly_restore_log_entry(entry))

        failures = report.get("failures") or []
        if failures:
            with st.expander("查看未恢复记录", expanded=False):
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
            "支持导入已有 Excel 或 Word 知识资料。系统会自动识别知识格式，并恢复为统一知识对象。"
        )
        old_files = st.file_uploader(
            "上传历史知识文件",
            type=HISTORY_TYPES,
            accept_multiple_files=True,
            key="update_old_files",
        )
        _render_uploaded_files(old_files, "尚未上传历史知识文件。")

        restore_result = st.session_state.get("update_restore_result") or RestoreResult()
        deep_restore_history = bool(st.session_state.get("update_restore_ai_mode", False))

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
                st.session_state.update_restore_ai_mode = False
                restore_result = _restore_history_files(old_files, deep_restore=False)
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
        if _should_offer_ai_restore(restore_result):
            st.warning(
                "检测到复杂文档\n\n"
                "当前文档不是系统标准知识格式，仍有部分内容可能需要智能分析。"
                "是否使用 AI 智能恢复继续补充？预计需要几分钟。"
            )
            ai_col, cancel_col = st.columns([1, 1])
            with ai_col:
                if st.button("开始 AI 恢复", use_container_width=True):
                    try:
                        st.session_state.update_restore_ai_mode = True
                        restore_result = _restore_history_files(old_files, deep_restore=True)
                        st.rerun()
                    except Exception as exc:
                        st.session_state.update_restore_result = RestoreResult()
                        st.session_state.update_restore_logs = [
                            f"AI 智能恢复｜失败｜{exc}"
                        ]
                        st.error(f"AI 智能恢复失败：{exc}")
            with cancel_col:
                if st.button("暂时仅使用已恢复知识", use_container_width=True):
                    st.info("已保留当前恢复结果，可继续上传新增资料。")

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
