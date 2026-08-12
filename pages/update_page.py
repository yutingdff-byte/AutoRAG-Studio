"""Update mode skeleton for future V0.8 milestones."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import streamlit as st

from knowledge.adapter import knowledge_to_preview_rows
from knowledge.restore_manager import RestoreResult, get_restore_cache_key, restore
from knowledge.adapter import rag_to_knowledge
from knowledge.models import KnowledgeItem
from diff.engine import compare
from diff.models import ChangeType, DiffResult, DiffRunResult, DetectedUpdateScope
from diff.reasons import change_type_label, review_reason_label
from generator.excel_generator import generate_excel
from knowledge.deduplicator import DuplicateCleanupResult, cleanup_exact_duplicates
from merge.engine import MergeResult, merge_knowledge
from review.decisions import build_default_decisions, decision_from_label
from review.models import ReviewDecision, ReviewDecisionType
from review.relation_decisions import (
    apply_relation_decisions,
    build_default_relation_decisions,
    default_relation_decision,
)
from review.relation_grouper import group_review_required
from review.relation_models import RelationDecision, RelationDecisionType, RelationGroup, RelationGroupingResult, RelationType
from ui.components import (
    render_file_card,
    render_metric_cards,
    render_page_header,
    render_section_title,
    render_step_navigation,
)


HISTORY_TYPES = ["xlsx", "xls", "docx"]
NEW_MATERIAL_TYPES = ["xlsx", "xls", "docx", "pdf", "txt", "png", "jpg", "jpeg", "webp"]


def _reset_update_review_state() -> None:
    st.session_state.update_review_decisions = {}
    st.session_state.update_relation_groups = None
    st.session_state.update_relation_decisions = {}
    st.session_state.update_review_completed = False
    st.session_state.update_merge_result = None
    st.session_state.update_dedup_result = None
    st.session_state.update_export_files = {}


def _reset_update_diff_state() -> None:
    st.session_state.update_diff_result = None
    _reset_update_review_state()


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
        _reset_update_diff_state()
        return RestoreResult()

    cache_key = _history_files_cache_key(files, deep_restore=deep_restore)
    restore_cache = st.session_state.setdefault("update_restore_cache", {})
    cached_result = restore_cache.get(cache_key)
    if cached_result is not None:
        logs = [f"恢复历史知识｜缓存命中｜同一批历史文件已恢复，直接复用结果｜0.00s"]
        st.session_state.update_restore_result = cached_result
        st.session_state.update_restore_logs = logs
        st.session_state.update_restore_cache_key = cache_key
        st.session_state.update_stage = "restored"
        st.info("同一批历史文件已恢复，直接复用结果。")
        return cached_result

    log_box = st.empty()
    logs: list[str] = []

    def update_progress(file_name: str, stage: str, status: str, message: str) -> None:
        logs.append(f"{file_name}｜{stage}｜{status}｜{message}")
        st.session_state.update_restore_logs = logs
        friendly_logs = [_friendly_restore_log_entry(entry) for entry in logs[-5:]]
        log_box.code("\n".join(friendly_logs), language="text")

    st.session_state.update_stage = "restoring"
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
        st.session_state.update_stage = "restore_error"
        logs.append(f"Restore｜失败｜{exc}")
        st.session_state.update_restore_result = RestoreResult()
        st.session_state.update_restore_logs = logs
        raise
    finally:
        st.session_state.update_restore_running = False

    restore_cache[cache_key] = result
    st.session_state.update_restore_result = result
    st.session_state.update_restore_logs = logs
    st.session_state.update_stage = "restored"
    log_box.empty()
    return result


def _render_restore_result(result: RestoreResult) -> None:
    render_section_title("历史知识恢复完成")

    render_metric_cards(
        [
            ("恢复知识", result.restored_count, "从历史知识文件恢复出的统一知识对象数量"),
            ("涉及车型", result.model_count, "根据历史知识中的车型字段统计"),
            ("文件数量", len(result.files), "已处理的历史知识文件数量"),
            ("待确认", result.need_confirm_count, "历史知识中标记为需要确认的条目"),
        ]
    )

    failed_files = [file_result for file_result in result.files if not file_result.success]
    if failed_files:
        st.warning(f"有 {len(failed_files)} 个历史知识文件处理失败。")
    else:
        st.success("历史知识已恢复完成。")

    with st.expander("查看文件处理结果", expanded=False):
        st.dataframe(
            [
                {
                    "文件": file_result.file_name,
                    "结果": "成功" if file_result.success else "失败",
                    "知识数量": len(file_result.items),
                }
                for file_result in result.files
            ],
            use_container_width=True,
            hide_index=True,
        )

    if failed_files:
        with st.expander("查看错误详情", expanded=False):
            for file_result in failed_files:
                st.error(f"{file_result.file_name}：{file_result.error or '知识恢复失败，请检查文件格式。'}")
                if file_result.logs:
                    st.code(
                        "\n".join(_friendly_restore_log_entry(entry) for entry in file_result.logs),
                        language="text",
                    )

    failures = []
    for file_result in result.files:
        report = file_result.report or {}
        for failure in report.get("failures") or []:
            failures.append(
                {
                    "文件": file_result.file_name,
                    "记录": failure.get("source_record_index"),
                    "原因": failure.get("reason"),
                }
            )
    if failures:
        with st.expander("查看未恢复记录", expanded=False):
            st.dataframe(
                failures,
                use_container_width=True,
                hide_index=True,
            )


def _build_material_block(file_name: str, content: str) -> str:
    return f"===== 文件：{file_name} =====\n{content}"


def _capture_stage_output(func, *args):
    buffer = StringIO()
    with redirect_stdout(buffer):
        result = func(*args)
    return result, buffer.getvalue()


def _summarize_stage_output(output: str) -> str:
    lines = [
        line.strip()
        for line in str(output or "").splitlines()
        if line.strip()
    ]
    diagnostic_prefixes = (
        "调用DeepSeek失败",
        "exception_class:",
        "exception_message:",
        "cause_class:",
        "cause_message:",
        "http_status:",
        "request_endpoint:",
        "model:",
        "timeout:",
        "max_retries:",
    )
    selected = [
        line
        for line in lines
        if line.startswith(diagnostic_prefixes)
    ]
    selected.extend(lines[-8:])
    selected = list(dict.fromkeys(selected))
    return "\n".join(selected)[:3000]


def _fact_count(facts) -> int:
    if isinstance(facts, dict):
        values = facts.get("facts", [])
        return len(values) if isinstance(values, list) else 0
    if isinstance(facts, list):
        return len(facts)
    return 0


def _rag_count(rag) -> int:
    if isinstance(rag, dict):
        values = rag.get("rag_knowledge", [])
        return len(values) if isinstance(values, list) else 0
    return 0


def _append_new_log(logs: list[str], stage: str, status: str, message: str) -> None:
    logs.append(f"{stage}｜{status}｜{message}")
    st.session_state.update_new_logs = logs


def _new_knowledge_user_error(error: str) -> str:
    text = str(error or "")
    if "ReadTimeout" in text or "响应超时" in text:
        return "AI 服务响应超时，请稍后重试或减少单次资料量。"
    if "解析结果为空" in text or "未能生成有效 Facts" in text and "解析" in text:
        return "未从新增资料中提取到有效内容，请检查文件后重试。"
    if (
        "Connection error" in text
        or "APIConnectionError" in text
        or "ConnectError" in text
        or "模型调用" in text
        or "未能生成有效 Facts" in text
    ):
        return "AI 服务暂时无法连接，请稍后重试。"
    if "未能生成有效 RAG" in text:
        return "新增资料生成失败，请稍后重试。"
    return text or "新增资料生成失败，请稍后重试。"


def _friendly_new_log_entry(entry: str) -> str:
    parts = str(entry or "").split("｜")
    if len(parts) < 3:
        return str(entry or "")

    stage, status = parts[0], parts[1]
    message = "｜".join(parts[2:])
    stage_label = {
        "Parser": "解析资料",
        "Facts": "提取事实",
        "RAG": "生成知识",
        "KnowledgeItem": "整理结果",
    }.get(stage, stage)
    message = message.replace("Facts", "事实")
    message = message.replace("RAG", "知识")
    message = message.replace("DeepSeek", "AI 服务")
    return f"{stage_label}｜{status}｜{message}"


def _generate_new_knowledge(files):
    if not files:
        st.session_state.update_new_knowledge = []
        st.session_state.update_new_errors = []
        st.session_state.update_new_logs = []
        _reset_update_diff_state()
        return []

    st.session_state.update_new_knowledge = []
    st.session_state.update_new_errors = []
    st.session_state.update_new_logs = []
    st.session_state.update_stage = "generating_new"
    _reset_update_diff_state()

    materials = []
    source_files = []
    errors = []
    logs: list[str] = []

    with st.spinner("正在解析新增资料并生成新知识..."):
        from parser.parser_factory import parse_file
        from agents.fact_agent import extract_facts
        from agents.rag_agent import generate_rag

        for file in files:
            try:
                _append_new_log(logs, "Parser", "开始", f"解析 {file.name}")
                content = parse_file(file).strip()
                if not content:
                    raise ValueError("解析结果为空")
                materials.append(_build_material_block(file.name, content))
                source_files.append(file.name)
                _append_new_log(logs, "Parser", "成功", f"{file.name} 解析出 {len(content)} 个字符")
            except Exception as exc:
                error = f"{file.name}：{exc}"
                errors.append(error)
                _append_new_log(logs, "Parser", "失败", error)

        if not materials:
            st.session_state.update_new_knowledge = []
            st.session_state.update_new_errors = errors
            st.session_state.update_new_logs = logs
            st.session_state.update_stage = "new_error"
            return []

        material = "\n\n".join(materials)

        try:
            _append_new_log(logs, "Facts", "开始", "从新增资料中提取事实")
            facts, facts_stdout = _capture_stage_output(extract_facts, material)
            facts_output = _summarize_stage_output(facts_stdout)
            if facts_output:
                _append_new_log(logs, "Facts", "日志", facts_output)
        except Exception as exc:
            facts = None
            _append_new_log(logs, "Facts", "异常", str(exc))

        fact_count = _fact_count(facts)
        if not facts or fact_count == 0:
            message = "新增资料未能生成有效 Facts，请检查文件内容或模型调用后重试。"
            technical_error = "\n".join(
                part
                for part in [message, facts_output]
                if part
            )
            errors.append(technical_error)
            _append_new_log(logs, "Facts", "失败", message)
            st.session_state.update_new_knowledge = []
            st.session_state.update_new_errors = errors
            st.session_state.update_new_logs = logs
            st.session_state.update_stage = "new_error"
            return []

        _append_new_log(logs, "Facts", "成功", f"提取 {fact_count} 条事实")

        try:
            _append_new_log(logs, "RAG", "开始", "根据事实生成新增知识")
            rag, rag_stdout = _capture_stage_output(generate_rag, facts)
            rag_output = _summarize_stage_output(rag_stdout)
            if rag_output:
                _append_new_log(logs, "RAG", "日志", rag_output)
        except Exception as exc:
            message = f"新增资料 RAG 生成失败：{exc}"
            errors.append(message)
            _append_new_log(logs, "RAG", "异常", message)
            st.session_state.update_new_knowledge = []
            st.session_state.update_new_errors = errors
            st.session_state.update_new_logs = logs
            st.session_state.update_stage = "new_error"
            return []

        rag_count = _rag_count(rag)
        if not rag or rag_count == 0:
            message = "新增资料未能生成有效 RAG 知识，请检查文件内容或模型调用后重试。"
            technical_error = "\n".join(
                part
                for part in [message, rag_output]
                if part
            )
            errors.append(technical_error)
            _append_new_log(logs, "RAG", "失败", message)
            st.session_state.update_new_knowledge = []
            st.session_state.update_new_errors = errors
            st.session_state.update_new_logs = logs
            st.session_state.update_stage = "new_error"
            return []

        _append_new_log(logs, "RAG", "成功", f"生成 {rag_count} 条知识")
        items = rag_to_knowledge(rag, source_file="、".join(source_files))
        _append_new_log(logs, "KnowledgeItem", "成功", f"转换 {len(items)} 条统一知识")

    st.session_state.update_new_knowledge = items
    st.session_state.update_new_errors = errors
    st.session_state.update_new_logs = logs
    st.session_state.update_stage = "new_generated"
    return items


def _render_new_knowledge_result(items, errors) -> None:
    render_section_title("新增资料处理完成" if items else "新增资料处理结果")

    if errors:
        user_errors = []
        for error in errors:
            user_error = _new_knowledge_user_error(error)
            if user_error not in user_errors:
                user_errors.append(user_error)
        for error in user_errors:
            st.error(f"新增资料生成失败：{error}")

    logs = st.session_state.get("update_new_logs", [])
    if errors and logs:
        with st.expander("查看错误详情", expanded=False):
            for entry in logs:
                st.code(_friendly_new_log_entry(entry), language="text")

    if not items:
        st.warning("本轮新增资料未生成有效知识。")
        return

    models = sorted({item.model for item in items if item.model})
    source_files = sorted({source for item in items for source in item.source_files if source})
    need_confirm_count = sum(1 for item in items if item.need_confirm)
    st.success("新增资料已处理完成。")
    render_metric_cards(
        [
            ("生成知识", len(items), "由本轮新增资料生成的统一知识对象数量"),
            ("涉及车型", len(models), "根据新增知识中的车型字段统计"),
            ("文件数量", len(source_files), "本轮新增资料来源文件数量"),
            ("待确认", need_confirm_count, "新增知识中标记为需要确认的条目"),
        ]
    )


def _render_scope(scope: DetectedUpdateScope) -> None:
    render_section_title("系统识别本轮资料范围")

    def preview_values(values: list[str], limit: int = 3) -> str:
        values = [str(value) for value in values if value]
        if not values:
            return "—"
        preview = " / ".join(values[:limit])
        if len(values) > limit:
            preview += f" +{len(values) - limit}"
        return preview

    def knowledge_type_label(value: str) -> str:
        return {
            "product": "车型配置",
            "price": "价格",
            "policy": "营销政策",
            "store": "门店政策",
            "marketing": "活动政策",
            "finance": "金融政策",
            "general": "通用知识",
            "static": "车型配置",
            "dynamic": "价格政策",
        }.get(str(value or "").lower(), str(value or ""))

    type_values = [knowledge_type_label(value) for value in scope.knowledge_types]
    render_metric_cards(
        [
            ("涉及品牌", len(scope.brands), preview_values(scope.brands)),
            ("涉及车型", len(scope.models), preview_values(scope.models)),
            ("主要分类", len(scope.categories), preview_values(scope.categories)),
            ("知识类型", len(type_values), preview_values(type_values)),
        ]
    )
    with st.expander("展开查看全部范围", expanded=False):
        st.dataframe(
            [
                {"范围": "涉及品牌", "内容": "、".join(scope.brands) or "—"},
                {"范围": "涉及车型", "内容": "、".join(scope.models) or "—"},
                {"范围": "主要分类", "内容": "、".join(scope.categories) or "—"},
                {"范围": "知识类型", "内容": "、".join(type_values) or "—"},
                {"范围": "来源文件", "内容": "、".join(scope.source_files) or "—"},
            ],
            use_container_width=True,
            hide_index=True,
        )
    not_obvious = scope.metadata.get("not_obvious_categories", [])
    if not_obvious:
        st.caption("未明显涉及：" + "、".join(not_obvious))


def _result_model(result: DiffResult) -> str:
    item = result.new_item or result.old_item
    return item.model if item and item.model else "未指定"


def _review_reason_text(result: DiffResult) -> str:
    reason = review_reason_label(result.review_reason)
    if result.review_reason:
        return reason
    return result.change_summary or result.reason_text or "需要人工确认后再处理。"


def _diff_rows(results, change_type: ChangeType) -> list[dict]:
    rows = []
    for result in results:
        if result.change_type != change_type:
            continue
        old_item = result.old_item
        new_item = result.new_item
        question = new_item.question if new_item else old_item.question if old_item else ""
        category = (new_item.category if new_item else old_item.category if old_item else "") or ""

        if change_type == ChangeType.ADDED:
            rows.append(
                {
                    "车型": _result_model(result),
                    "问题": question,
                    "新增答案": new_item.answer if new_item else "",
                    "分类": category,
                }
            )
        elif change_type == ChangeType.UPDATED:
            rows.append(
                {
                    "车型": _result_model(result),
                    "问题": question,
                    "原答案": old_item.answer if old_item else "",
                    "新答案": new_item.answer if new_item else "",
                    "分类": category,
                }
            )
        elif change_type == ChangeType.UNCHANGED:
            rows.append(
                {
                    "车型": _result_model(result),
                    "问题": question,
                    "当前答案": old_item.answer if old_item else new_item.answer if new_item else "",
                    "分类": category,
                }
            )
        else:
            rows.append(
                {
                    "车型": _result_model(result),
                    "问题": question,
                    "原答案": old_item.answer if old_item else "",
                    "候选新答案": new_item.answer if new_item else "",
                    "需要确认的原因": _review_reason_text(result),
                }
            )
    return rows


def _diff_column_config(change_type: ChangeType) -> dict:
    if change_type == ChangeType.ADDED:
        return {
            "车型": st.column_config.TextColumn("车型", width="small"),
            "问题": st.column_config.TextColumn("问题", width="large"),
            "新增答案": st.column_config.TextColumn("新增答案", width="large"),
            "分类": st.column_config.TextColumn("分类", width="small"),
        }
    if change_type == ChangeType.UPDATED:
        return {
            "车型": st.column_config.TextColumn("车型", width="small"),
            "问题": st.column_config.TextColumn("问题", width="medium"),
            "原答案": st.column_config.TextColumn("原答案", width="large"),
            "新答案": st.column_config.TextColumn("新答案", width="large"),
            "分类": st.column_config.TextColumn("分类", width="small"),
        }
    if change_type == ChangeType.UNCHANGED:
        return {
            "车型": st.column_config.TextColumn("车型", width="small"),
            "问题": st.column_config.TextColumn("问题", width="large"),
            "当前答案": st.column_config.TextColumn("当前答案", width="large"),
            "分类": st.column_config.TextColumn("分类", width="small"),
        }
    return {
        "车型": st.column_config.TextColumn("车型", width="small"),
        "问题": st.column_config.TextColumn("问题", width="medium"),
        "原答案": st.column_config.TextColumn("原答案", width="large"),
        "候选新答案": st.column_config.TextColumn("候选新答案", width="large"),
        "需要确认的原因": st.column_config.TextColumn("需要确认的原因", width="large"),
    }


def _render_diff_result(result: DiffRunResult) -> None:
    _render_scope(result.detected_scope)
    grouping = _ensure_relation_grouping(result)
    single_count = len(grouping.single_items)
    auto_added_count = len(_auto_added_review_results(result, grouping))

    render_section_title("本轮变化")
    render_metric_cards(
        [
            ("新增", result.added_count + auto_added_count, "将自动加入新版知识库"),
            ("更新", result.updated_count, "将自动采用新答案替换旧答案"),
            ("未变化", result.unchanged_count, "继续保留历史知识"),
            ("复杂变化", len(grouping.groups), "按关系组处理"),
            ("单条待确认", single_count, "默认保留原知识"),
        ]
    )

    with st.expander("查看全部变化详情", expanded=False):
        tabs = st.tabs(["新增", "更新", "待确认", "未变化"])
        tab_specs = [
            (tabs[0], ChangeType.ADDED),
            (tabs[1], ChangeType.UPDATED),
            (tabs[2], ChangeType.REVIEW_REQUIRED),
            (tabs[3], ChangeType.UNCHANGED),
        ]
        for tab, change_type in tab_specs:
            with tab:
                rows = _diff_rows(result.results, change_type)
                if rows:
                    st.dataframe(
                        rows,
                        use_container_width=True,
                        hide_index=True,
                        column_config=_diff_column_config(change_type),
                    )
                else:
                    st.caption("暂无数据。")


def _reviewable_results(result: DiffRunResult, change_type: ChangeType | None = None) -> list[DiffResult]:
    reviewable = [
        item
        for item in result.results
        if item.change_type in {ChangeType.ADDED, ChangeType.UPDATED, ChangeType.REVIEW_REQUIRED}
    ]
    if change_type:
        reviewable = [item for item in reviewable if item.change_type == change_type]
    return reviewable


def _auto_added_review_results(result: DiffRunResult, grouping: RelationGroupingResult) -> list[DiffResult]:
    grouped_ids = {diff_id for group in grouping.groups for diff_id in group.diff_ids}
    grouped_ids.update(grouping.single_items)
    return [
        item
        for item in result.results
        if item.change_type == ChangeType.REVIEW_REQUIRED
        and item.diff_id not in grouped_ids
        and item.old_item is None
        and item.new_item is not None
    ]


def _ensure_review_decisions(result: DiffRunResult) -> dict[str, ReviewDecision]:
    decisions = st.session_state.setdefault("update_review_decisions", {})
    defaults = build_default_decisions(result.results)
    for diff_id, decision in defaults.items():
        decisions.setdefault(diff_id, decision)
    for diff_id in list(decisions):
        if diff_id not in defaults:
            decisions.pop(diff_id, None)
    st.session_state.update_review_decisions = decisions
    return decisions


def _ensure_relation_grouping(result: DiffRunResult) -> RelationGroupingResult:
    grouping = st.session_state.get("update_relation_groups")
    source_key = "|".join(item.diff_id for item in result.results)
    if not grouping or st.session_state.get("update_relation_groups_source") != source_key:
        grouping = group_review_required(result)
        st.session_state.update_relation_groups = grouping
        st.session_state.update_relation_groups_source = source_key
        st.session_state.update_relation_decisions = {}
    return grouping


def _ensure_relation_decisions(groups: list[RelationGroup]) -> dict[str, RelationDecision]:
    decisions = st.session_state.setdefault("update_relation_decisions", {})
    defaults = build_default_relation_decisions(groups)
    for group_id, decision in defaults.items():
        decisions.setdefault(group_id, decision)
    for group_id in list(decisions):
        if group_id not in defaults:
            decisions.pop(group_id, None)
    st.session_state.update_relation_decisions = decisions
    return decisions


def _decision_label(result: DiffResult, decision: ReviewDecision) -> str:
    if result.change_type == ChangeType.ADDED:
        return "不加入" if decision.decision == ReviewDecisionType.SKIP else "加入新版知识库"
    if result.change_type == ChangeType.UPDATED:
        return "保留原答案" if decision.decision == ReviewDecisionType.KEEP_OLD else "使用新答案"
    if decision.decision == ReviewDecisionType.REMOVE:
        return "确认删除"
    if decision.decision == ReviewDecisionType.ACCEPT_NEW:
        return "使用新知识"
    return "保留原知识"


def _review_options(result: DiffResult) -> list[str]:
    if result.change_type == ChangeType.ADDED:
        return ["加入新版知识库", "不加入"]
    if result.change_type == ChangeType.UPDATED:
        return ["使用新答案", "保留原答案"]
    return ["保留原知识", "使用新知识", "确认删除"]


def _render_review_item(result: DiffResult, decisions: dict[str, ReviewDecision], key_scope: str) -> None:
    old_item = result.old_item
    new_item = result.new_item
    item = new_item or old_item
    title = item.question if item else result.diff_id
    with st.expander(f"{change_type_label(result.change_type)}｜{_result_model(result)}｜{title}", expanded=False):
        st.caption(result.change_summary or result.reason_text or review_reason_label(result.review_reason))
        st.markdown(f"**问题**：{title or '未指定'}")
        if old_item:
            st.markdown("**原答案**")
            st.write(old_item.answer)
        if new_item:
            st.markdown("**新答案**")
            st.write(new_item.answer)

        options = _review_options(result)
        current = decisions.get(result.diff_id)
        current_label = _decision_label(result, current) if current else options[0]
        index = options.index(current_label) if current_label in options else 0
        selected = st.selectbox(
            "处理方式",
            options,
            index=index,
            key=f"review_decision_{key_scope}_{result.diff_id}",
        )

        delete_confirmed = False
        if selected == "确认删除":
            delete_confirmed = st.checkbox(
                "确认从新版知识库中删除此知识",
                key=f"review_delete_confirm_{key_scope}_{result.diff_id}",
            )
            if not delete_confirmed:
                st.warning("删除需要二次确认；未确认前系统仍会保留原知识。")

        if selected == "确认删除" and not delete_confirmed:
            decisions[result.diff_id] = decision_from_label(result, "保留原知识")
        else:
            decisions[result.diff_id] = decision_from_label(
                result,
                selected,
                delete_confirmed=delete_confirmed,
            )
        st.session_state.update_review_decisions = decisions


def _relation_type_label(relation_type: RelationType) -> str:
    if relation_type == RelationType.GENERAL_TO_DETAIL:
        return "综合知识被拆分"
    if relation_type == RelationType.DETAIL_TO_GENERAL:
        return "细分知识被合并"
    if relation_type == RelationType.ONE_TO_MANY:
        return "一条历史知识对应多条新知识"
    if relation_type == RelationType.MANY_TO_ONE:
        return "多条历史知识对应一条新知识"
    return "复杂知识关系"


def _relation_decision_label(decision: RelationDecision) -> str:
    if decision.decision == RelationDecisionType.REPLACE_OLD_WITH_NEW:
        return "用新知识替换原知识"
    if decision.decision == RelationDecisionType.KEEP_OLD_ONLY:
        return "保留原知识"
    if decision.decision == RelationDecisionType.CUSTOM:
        return "高级调整"
    return "采用推荐方案"


def _relation_decision_type_from_label(label: str) -> RelationDecisionType:
    if label == "用新知识替换原知识":
        return RelationDecisionType.REPLACE_OLD_WITH_NEW
    if label == "保留原知识":
        return RelationDecisionType.KEEP_OLD_ONLY
    if label == "高级调整":
        return RelationDecisionType.CUSTOM
    return RelationDecisionType.ADD_NEW_KEEP_OLD


def _item_label(item: KnowledgeItem) -> str:
    return f"{item.knowledge_id}｜{item.question}"


def _render_relation_group(group: RelationGroup, decisions: dict[str, RelationDecision]) -> None:
    title = f"{group.model or '未指定车型'}｜{_relation_type_label(group.relation_type)}"
    with st.expander(title, expanded=False):
        st.caption(group.review_reason or "系统发现新旧知识存在复杂对应关系。")

        if group.old_items:
            st.markdown("**原知识**")
            for item in group.old_items:
                st.markdown(f"- {item.question}")
                st.caption(item.answer)

        if group.new_items:
            st.markdown("**新知识**")
            for item in group.new_items:
                st.markdown(f"- {item.question}")
                st.caption(item.answer)

        st.info("推荐处理：采用新的知识，同时暂时保留历史知识。这样不会误删旧知识，后续可人工精修。")

        current = decisions.get(group.group_id) or default_relation_decision(group)
        options = ["采用推荐方案", "用新知识替换原知识", "保留原知识", "高级调整"]
        current_label = _relation_decision_label(current)
        selected = st.selectbox(
            "处理方式",
            options,
            index=options.index(current_label) if current_label in options else 0,
            key=f"relation_decision_{group.group_id}",
        )
        decision_type = _relation_decision_type_from_label(selected)

        metadata = {}
        selected_old_ids = [item.knowledge_id for item in group.old_items]
        selected_new_ids = [item.knowledge_id for item in group.new_items]

        if decision_type == RelationDecisionType.REPLACE_OLD_WITH_NEW:
            delete_confirmed = st.checkbox(
                f"确认从新版知识库中移除 {len(group.old_items)} 条历史知识",
                key=f"relation_delete_confirm_{group.group_id}",
            )
            metadata["delete_confirmed"] = bool(delete_confirmed)
            if not delete_confirmed:
                st.warning("替换原知识需要二次确认；未确认前系统仍会采用推荐方案。")
                decision_type = RelationDecisionType.ADD_NEW_KEEP_OLD

        if decision_type == RelationDecisionType.CUSTOM:
            new_options = {_item_label(item): item.knowledge_id for item in group.new_items}
            old_options = {_item_label(item): item.knowledge_id for item in group.old_items}
            selected_new_labels = st.multiselect(
                "选择要加入的新知识",
                list(new_options),
                default=list(new_options),
                key=f"relation_custom_new_{group.group_id}",
            )
            selected_old_labels = st.multiselect(
                "选择要保留的原知识",
                list(old_options),
                default=list(old_options),
                key=f"relation_custom_old_{group.group_id}",
            )
            selected_new_ids = [new_options[label] for label in selected_new_labels]
            selected_old_ids = [old_options[label] for label in selected_old_labels]
            if len(selected_old_ids) < len(group.old_items):
                delete_confirmed = st.checkbox(
                    "确认移除未勾选的历史知识",
                    key=f"relation_custom_delete_confirm_{group.group_id}",
                )
                metadata["delete_confirmed"] = bool(delete_confirmed)
                if not delete_confirmed:
                    st.warning("未确认删除前，系统会继续保留所有历史知识。")
                    selected_old_ids = [item.knowledge_id for item in group.old_items]

        decisions[group.group_id] = RelationDecision(
            group_id=group.group_id,
            decision=decision_type,
            reviewed=True,
            selected_old_ids=selected_old_ids,
            selected_new_ids=selected_new_ids,
            metadata=metadata,
        )
        st.session_state.update_relation_decisions = decisions


def _merge_decisions_with_relations(
    result: DiffRunResult,
    grouping: RelationGroupingResult,
    base_decisions: dict[str, ReviewDecision],
    relation_decisions: dict[str, RelationDecision],
) -> dict[str, ReviewDecision]:
    return apply_relation_decisions(result, grouping.groups, relation_decisions, base_decisions)


def _render_review_center(result: DiffRunResult) -> None:
    decisions = _ensure_review_decisions(result)
    grouping = _ensure_relation_grouping(result)
    relation_decisions = _ensure_relation_decisions(grouping.groups)
    added = _reviewable_results(result, ChangeType.ADDED)
    updated = _reviewable_results(result, ChangeType.UPDATED)
    result_by_id = {item.diff_id: item for item in result.results}
    single_required = [result_by_id[diff_id] for diff_id in grouping.single_items if diff_id in result_by_id]
    grouped_review_count = sum(len(group.diff_ids) for group in grouping.groups)
    auto_added = _auto_added_review_results(result, grouping)
    auto_added_count = len(added) + len(auto_added)

    if grouping.groups or single_required:
        render_section_title("处理异常")
        if grouping.groups:
            st.info(
                f"发现 {len(grouping.groups)} 组复杂知识变化，涉及 {grouped_review_count} 条知识。"
                "系统已准备安全默认方案：加入新知识，同时保留历史知识。"
            )
            with st.expander("检查复杂变化", expanded=False):
                for group in grouping.groups:
                    _render_relation_group(group, relation_decisions)

        if single_required:
            st.warning(
                f"还有 {len(single_required)} 条单条知识需要确认；未处理时本次会继续保留原知识。"
            )
            with st.expander("处理单条待确认知识", expanded=True):
                for item in single_required:
                    _render_review_item(item, decisions, "required_main")
    else:
        st.success("本轮没有需要人工处理的异常变化。")

    render_section_title("生成新版知识库")
    st.info(
        "系统将自动：\n\n"
        f"- 加入 {auto_added_count} 条新增知识\n"
        f"- 替换 {len(updated)} 条已更新知识\n"
        f"- 保留 {result.unchanged_count} 条未变化知识\n\n"
        "复杂变化和单条待确认知识将按当前选择处理；未处理时采用安全默认方案。"
    )

    if st.button("生成新版知识库", use_container_width=True):
        final_decisions = _merge_decisions_with_relations(
            result,
            grouping,
            decisions,
            relation_decisions,
        )
        st.session_state.update_review_decisions = final_decisions
        merge_result = merge_knowledge(result, final_decisions)
        st.session_state.update_merge_result = merge_result
        dedup_result = cleanup_exact_duplicates(merge_result.final_items)
        st.session_state.update_dedup_result = dedup_result
        st.session_state.update_review_completed = True
        st.session_state.update_stage = "merged"
        if not dedup_result.final_items:
            st.session_state.update_export_files = {}
            st.error("最终知识为空，已停止导出。")
        else:
            st.session_state.update_export_files = _build_update_export_files(dedup_result.final_items)


def _knowledge_items_to_rag_data(items: list[KnowledgeItem]) -> dict:
    rag_items = []
    for index, item in enumerate(items, start=1):
        source_type = str(item.knowledge_type or "").lower()
        excel_type = "dynamic" if source_type in {"price", "policy", "store", "marketing", "finance", "dynamic"} else "static"
        rag_items.append(
            {
                "rag_id": item.knowledge_id or f"UPDATE-{index:03d}",
                "brand": item.brand or "",
                "model": item.model or "",
                "trim": item.trim or "",
                "question": item.question,
                "answer": item.answer,
                "category": item.category,
                "module": item.module or "",
                "knowledge_type": excel_type,
                "answer_type": item.answer_type or "updated",
                "need_confirm": "是" if item.need_confirm else "否",
                "fact_refs": item.fact_refs,
                "source_files": item.source_files,
            }
        )
    return {"rag_knowledge": rag_items}


def _facts_data_for_export(items: list[KnowledgeItem]) -> dict:
    return {
        "facts": [
            {
                "brand": item.brand or "",
                "model": item.model or "",
                "trim": item.trim or "",
                "category": item.category,
                "knowledge_type": item.knowledge_type,
            }
            for item in items
        ]
    }


def _build_update_export_files(items: list[KnowledgeItem]) -> dict:
    with TemporaryDirectory() as temp_dir:
        output_path = str(Path(temp_dir) / "update.xlsx")
        output_paths = generate_excel(
            _facts_data_for_export(items),
            _knowledge_items_to_rag_data(items),
            {"overall_result": "PASS", "issues": []},
            output_path,
        )
        export_files = {}
        for key, path in output_paths.items():
            file_path = Path(path)
            export_files[key] = {
                "file_name": file_path.name,
                "data": file_path.read_bytes(),
            }
        return export_files


def _render_update_export(merge_result: MergeResult | None) -> None:
    if merge_result is None:
        return

    dedup_result = st.session_state.get("update_dedup_result")
    if not isinstance(dedup_result, DuplicateCleanupResult):
        dedup_result = DuplicateCleanupResult(final_items=merge_result.final_items)

    diff_result = st.session_state.get("update_diff_result")
    grouping = st.session_state.get("update_relation_grouping")
    auto_added_count = 0
    complex_group_count = 0
    if isinstance(diff_result, DiffRunResult) and isinstance(grouping, RelationGroupingResult):
        auto_added_count = len(_auto_added_review_results(diff_result, grouping))
        complex_group_count = len(grouping.groups)

    render_section_title("新版知识库生成完成")
    final_count = len(dedup_result.final_items)
    st.success("新版知识库已生成完成，可以下载 Excel。")
    render_metric_cards(
        [
            ("最终知识", final_count, "新版知识库最终条数"),
            ("新增采用", merge_result.added_accepted + auto_added_count, "已加入新版知识库的新增知识"),
            ("自动更新", merge_result.updated_accepted, "已自动替换为新答案的知识"),
            ("保留旧知识", merge_result.kept_old, "未变化或选择保留的历史知识"),
            ("复杂变化处理", complex_group_count, "已按当前选择处理的复杂变化组"),
            ("重复清理", dedup_result.removed_count, "已自动清理的完全重复知识"),
            ("删除", merge_result.removed, "已二次确认删除的知识"),
        ]
    )

    if dedup_result.removed_count:
        st.caption(f"已自动清理完全重复知识：{dedup_result.removed_count} 条。")

    removed_ids = {item.knowledge_id for item in dedup_result.removed_items}
    visible_duplicate_warnings = [
        warning
        for warning in merge_result.duplicate_warnings
        if not (warning.warning_type == "duplicate_exact" and removed_ids.intersection(warning.knowledge_ids))
    ]
    if visible_duplicate_warnings:
        with st.expander("重复知识提示", expanded=False):
            st.dataframe(
                [
                    {
                        "类型": warning.warning_type,
                        "知识ID": "、".join(warning.knowledge_ids),
                        "说明": warning.message,
                    }
                    for warning in visible_duplicate_warnings
                ],
                use_container_width=True,
                hide_index=True,
            )

    if not final_count:
        st.error("最终知识为空，不能导出。")
        return

    export_files = st.session_state.get("update_export_files", {})
    if not export_files:
        st.warning("下载文件尚未生成，请重新点击“生成新版知识库”。")
        return

    static_file = export_files.get("static")
    dynamic_file = export_files.get("dynamic")
    render_section_title("下载新版知识库")
    download_col_1, download_col_2 = st.columns(2)
    with download_col_1:
        if static_file:
            st.download_button(
                "下载车型配置知识库",
                data=static_file["data"],
                file_name=static_file["file_name"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    with download_col_2:
        if dynamic_file:
            st.download_button(
                "下载价格政策知识库",
                data=dynamic_file["data"],
                file_name=dynamic_file["file_name"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )


def _update_steps() -> list[str]:
    stage = st.session_state.get("update_stage", "idle")
    restore_done = bool((st.session_state.get("update_restore_result") or RestoreResult()).items)
    new_done = bool(st.session_state.get("update_new_knowledge"))
    diff_result = st.session_state.get("update_diff_result")
    exceptions_ready = False
    if diff_result:
        grouping = st.session_state.get("update_relation_groups") or group_review_required(diff_result)
        exceptions_ready = bool(grouping.groups or grouping.single_items)
    completed = {
        "1 上传资料": bool(st.session_state.get("update_old_file_names") or st.session_state.get("update_new_file_names")),
        "2 恢复与生成": bool(restore_done and (new_done or st.session_state.get("update_review_completed"))),
        "3 差异分析": bool(diff_result),
        "4 处理异常": bool(diff_result and not exceptions_ready) or bool(st.session_state.get("update_review_completed")),
        "5 生成新版": bool(st.session_state.get("update_review_completed")),
        "6 下载": bool(st.session_state.get("update_export_files")),
    }
    labels = []
    for step, done in completed.items():
        if done:
            labels.append(f"{step} ✓")
        elif stage in {"restoring", "generating_new", "diff_completed", "merged"} and not labels:
            labels.append(f"{step} 当前")
        else:
            labels.append(step)
    return labels


def render_update_page() -> None:
    render_page_header(
        "更新已有知识库 Update",
        "上传历史知识和新增资料，系统自动识别变化并生成新版知识库。",
    )

    render_step_navigation(_update_steps())

    old_col, new_col = st.columns(2)

    with old_col:
        render_section_title("历史知识")
        st.caption("支持导入已有 Excel 或 Word 知识资料。")
        with st.container(height=360, border=False):
            old_files = st.file_uploader(
                "上传历史知识文件",
                type=HISTORY_TYPES,
                accept_multiple_files=True,
                key="update_old_files",
            )
            if old_files:
                st.session_state.update_old_file_names = [file.name for file in old_files]
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
            _reset_update_diff_state()

        if st.button(
            "恢复历史知识",
            use_container_width=True,
            disabled=not bool(old_files),
        ):
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
        st.caption("上传本次新增或更新的产品资料。")
        with st.container(height=360, border=False):
            new_files = st.file_uploader(
                "上传新增资料",
                type=NEW_MATERIAL_TYPES,
                accept_multiple_files=True,
                key="update_new_files",
            )
            if new_files:
                st.session_state.update_new_file_names = [file.name for file in new_files]
            _render_uploaded_files(new_files, "尚未上传新增资料。")

        if st.button(
            "生成新增知识",
            use_container_width=True,
            disabled=not bool(new_files),
        ):
            _generate_new_knowledge(new_files)

    if restore_result.files:
        _render_restore_result(restore_result)
        if old_files and _should_offer_ai_restore(restore_result):
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

    new_items = st.session_state.get("update_new_knowledge", [])
    new_errors = st.session_state.get("update_new_errors", [])
    new_logs = st.session_state.get("update_new_logs", [])
    if new_items or new_errors or new_logs:
        _render_new_knowledge_result(
            new_items,
            new_errors,
        )

    old_items = restore_result.items
    can_diff = bool(old_items and new_items)
    can_keep_old = bool(old_items and not new_items)

    st.divider()
    status_text = f"历史知识 {'✓' if old_items else '○'}　新增知识 {'✓' if new_items else '○'}"
    st.caption(status_text)

    if st.button("开始差异分析", use_container_width=True, disabled=not can_diff):
        st.session_state.update_diff_result = compare(old_items, new_items)
        _ensure_review_decisions(st.session_state.update_diff_result)
        st.session_state.update_merge_result = None
        st.session_state.update_dedup_result = None
        st.session_state.update_export_files = {}
        st.session_state.update_stage = "diff_completed"

    if can_keep_old:
        st.info("当前没有新增知识，可以直接生成新版知识库，结果将保留历史知识。")
        if st.button("直接生成新版知识库", use_container_width=True):
            merge_result = MergeResult(final_items=list(old_items), kept_old=len(old_items))
            st.session_state.update_merge_result = merge_result
            dedup_result = cleanup_exact_duplicates(merge_result.final_items)
            st.session_state.update_dedup_result = dedup_result
            st.session_state.update_review_completed = True
            st.session_state.update_export_files = _build_update_export_files(dedup_result.final_items)
            st.session_state.update_stage = "merged"
    elif not can_diff:
        st.caption("恢复历史知识并生成新增知识后，可以开始差异分析。")

    diff_result = st.session_state.get("update_diff_result")
    if diff_result:
        _render_diff_result(diff_result)
        _render_review_center(diff_result)

    _render_update_export(st.session_state.get("update_merge_result"))
