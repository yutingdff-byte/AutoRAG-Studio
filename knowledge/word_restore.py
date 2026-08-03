"""Restore Word knowledge material through the existing Generate Agent chain."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from time import perf_counter
from typing import Any

from knowledge.adapter import rag_to_knowledge
from knowledge.excel_restore import KnowledgeRestoreError
from knowledge.models import KnowledgeItem
from knowledge.word_fast_restore import (
    DEEP_RESTORE_REMAINDER_THRESHOLD,
    MIN_FAST_RESTORE_CONFIDENCE,
    restore_word_fast,
)


def get_source_name(file: Any) -> str:
    name = getattr(file, "name", None)
    if name:
        return Path(str(name)).name
    if isinstance(file, (str, Path)):
        return Path(file).name
    return "历史知识.docx"


def parse_document(file: Any) -> str:
    from parser.parser_factory import parse_file

    return parse_file(file)


def extract_material_facts(material: str):
    from agents.fact_agent import extract_facts

    return extract_facts(material)


def generate_material_rag(facts, progress_callback: StageLogger | None = None):
    from agents import rag_agent
    from utils import rag_quality

    def log(status: str, message: str) -> None:
        if progress_callback:
            progress_callback("生成RAG", status, message)

    system_prompt = rag_agent.load_prompt()
    fact_list = rag_agent.normalize_facts(facts)
    for fact in fact_list:
        if isinstance(fact, dict):
            rag_agent.normalize_vehicle_fields(fact)

    fact_index = rag_agent.build_fact_index(fact_list)
    groups = rag_agent.group_facts(fact_list)
    batches = rag_agent.merge_small_groups(groups, max_size=30)
    results = []
    failed_batches = []

    log("日志", f"Facts数量: {len(fact_list)}")
    log("日志", f"RAG Batch数量: {len(batches)}")

    for index, batch in enumerate(batches, start=1):
        log("批次开始", f"Batch {index}/{len(batches)}，Facts数量 {len(batch)}")
        batch_started = perf_counter()
        result = rag_agent.generate_batch(batch, system_prompt)
        if result:
            normalized = rag_agent.normalize_rag_metadata(result, fact_index)
            results.append(normalized)
            batch_count = len(normalized.get("rag_knowledge", []))
            log("批次成功", f"Batch {index}/{len(batches)} 生成 {batch_count} 条，耗时 {perf_counter() - batch_started:.2f}s")
        else:
            failed_batches.append(index)
            log("批次失败", f"Batch {index}/{len(batches)} 未返回有效结果，已保留其他成功批次")

    final_result = rag_agent.normalize_rag_metadata(
        rag_agent.merge_results(results),
        fact_index,
    )
    final_result["rag_knowledge"] = rag_agent.dedupe_rag_items(
        final_result.get("rag_knowledge", [])
    )
    final_result = rag_agent.ensure_model_price_overview(final_result, fact_list)
    final_result = rag_quality.apply_export_quality_gate(final_result)
    final_result["restore_failed_batches"] = failed_batches
    return final_result


def count_facts(facts) -> int:
    if isinstance(facts, dict):
        facts = facts.get("facts", [])
    return len(facts) if isinstance(facts, list) else 0


def estimate_rag_model_calls(facts) -> int:
    try:
        from agents.rag_agent import group_facts, merge_small_groups, normalize_facts

        fact_list = normalize_facts(deepcopy(facts))
        groups = group_facts(fact_list)
        batches = merge_small_groups(groups, max_size=30)
        return len(batches)
    except Exception:
        return 0


def summarize_agent_stdout(output: str) -> str:
    lines = [
        line.strip()
        for line in output.splitlines()
        if line.strip()
    ]
    if not lines:
        return ""
    return "；".join(lines[-8:])[:1000]


class ProgressStdout:
    def __init__(self, log_func):
        self.log_func = log_func
        self.lines: list[str] = []
        self._buffer = ""

    def write(self, value: str) -> int:
        self._buffer += value
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._emit(line)
        return len(value)

    def flush(self) -> None:
        if self._buffer.strip():
            self._emit(self._buffer)
            self._buffer = ""

    def _emit(self, line: str) -> None:
        line = line.strip()
        if not line:
            return
        self.lines.append(line)
        self.log_func("日志", line)

    def summary(self) -> str:
        return summarize_agent_stdout("\n".join(self.lines))


def run_agent_with_progress(stage: str, agent_func, log_func, *args):
    import sys

    stdout = ProgressStdout(lambda status, message: log_func(stage, status, message))
    previous_stdout = sys.stdout
    try:
        sys.stdout = stdout
        result = agent_func(*args)
    finally:
        stdout.flush()
        sys.stdout = previous_stdout
    return result, stdout.summary()


StageLogger = Callable[[str, str, str], None]


def merge_restored_items(direct_items: list[KnowledgeItem], deep_items: list[KnowledgeItem]) -> list[KnowledgeItem]:
    merged = list(direct_items)
    seen = {
        (
            item.model or "",
            item.trim or "",
            item.category or "",
            item.normalized_question,
        ): item
        for item in direct_items
    }

    for item in deep_items:
        key = (
            item.model or "",
            item.trim or "",
            item.category or "",
            item.normalized_question,
        )
        existing = seen.get(key)
        if not existing:
            seen[key] = item
            merged.append(item)
            continue

        if existing.answer.strip() == item.answer.strip():
            continue

        item.need_confirm = True
        item.metadata["duplicate_conflict_with"] = existing.knowledge_id
        item.metadata["restore_merge_status"] = "duplicate_needs_review"
        merged.append(item)

    return merged


def restore_word(
    file: Any,
    progress_callback: StageLogger | None = None,
    deep_restore: bool = False,
) -> list[KnowledgeItem]:
    """Restore Word material by reusing Parser -> Fact Agent -> RAG Agent."""

    source_name = get_source_name(file)

    def log(stage: str, status: str, message: str) -> None:
        if progress_callback:
            progress_callback(stage, status, message)

    def timed_log(stage: str, status: str, message: str, started_at: float) -> None:
        log(stage, status, f"{message}，耗时 {perf_counter() - started_at:.2f}s")

    direct_items: list[KnowledgeItem] = []
    material = ""
    full_document_text = ""

    try:
        log("读取文档", "开始", "读取Word文档结构")
        stage_started = perf_counter()
        fast_result = restore_word_fast(file)
        full_document_text = fast_result.document_text
        material = fast_result.remaining_text if fast_result.items else fast_result.document_text
        direct_items = fast_result.items
        timed_log(
            "识别现成问答",
            "成功",
            (
                f"直接识别 {len(direct_items)} 条知识"
                f"（JSON {fast_result.json_items}，表格 {fast_result.table_items}，"
                f"问答 {fast_result.qa_items}，标题正文 {fast_result.heading_items}，"
                f"失败 {fast_result.failed_items}，可信度 {fast_result.confidence:.0%}）"
            ),
            stage_started,
        )
        log(
            "直接恢复Knowledge",
            "成功",
            (
                f"文档 {fast_result.total_chars} 字，剩余 {fast_result.remaining_chars} 字，"
                f"剩余比例 {fast_result.remaining_ratio:.0%}"
            ),
        )
    except Exception as exc:
        log("识别现成问答", "跳过", f"未识别到可直接恢复结构：{exc}")
        try:
            log("读取文档", "开始", "使用通用Parser解析Word资料")
            stage_started = perf_counter()
            material = parse_document(file).strip()
            timed_log("读取文档", "成功", f"解析出 {len(material)} 个字符", stage_started)
        except Exception as parse_exc:
            log("读取文档", "失败", str(parse_exc))
            raise KnowledgeRestoreError(
                f"知识恢复失败：{source_name}。请检查文件格式。"
            ) from parse_exc

    if not material:
        if direct_items:
            log("完成", "成功", "剩余文本为空，仅使用直接恢复知识")
            return direct_items
        log("读取文档", "失败", "解析结果为空")
        raise KnowledgeRestoreError(f"知识恢复失败：{source_name}。文件解析结果为空。")

    if direct_items and not deep_restore:
        if fast_result.confidence < MIN_FAST_RESTORE_CONFIDENCE:
            log(
                "质量门禁",
                "回退",
                (
                    f"直接恢复可信度 {fast_result.confidence:.0%} 低于阈值 "
                    f"{MIN_FAST_RESTORE_CONFIDENCE:.0%}，自动回退深度恢复"
                ),
            )
            direct_items = []
            material = full_document_text or material
        else:
            if len(material) > DEEP_RESTORE_REMAINDER_THRESHOLD:
                log(
                    "深度提取Facts",
                    "暂缓",
                    (
                        f"已先完成快速恢复；剩余非结构化文本 {len(material)} 字。"
                        "如需补充未识别内容，请勾选深度恢复后重试。"
                    ),
                )
            log("完成", "成功", f"快速恢复 {len(direct_items)} 条知识")
            return direct_items

    try:
        log("深度提取Facts", "开始", "调用现有Fact Agent恢复事实，预计模型调用 1 次")
        stage_started = perf_counter()
        facts, facts_stdout = run_agent_with_progress("深度提取Facts", extract_material_facts, log, material)
        if not facts:
            raise ValueError(
                "Fact Agent未返回有效结果。"
                + (facts_stdout or "未捕获到模型调用日志")
            )
        fact_count = count_facts(facts)
        timed_log("深度提取Facts", "成功", f"恢复 {fact_count} 条事实，实际模型调用 1 次", stage_started)

        estimated_rag_calls = estimate_rag_model_calls(facts)
        rag_call_text = (
            f"预计模型调用 {estimated_rag_calls} 次"
            if estimated_rag_calls
            else "模型调用次数待RAG分批后确认"
        )
        log("生成RAG", "开始", f"调用现有RAG Agent生成知识，{rag_call_text}")
        stage_started = perf_counter()
        rag, rag_stdout = run_agent_with_progress("生成RAG", generate_material_rag, log, facts, log)
        if not rag:
            raise ValueError(
                "RAG Agent未返回有效结果。"
                + (rag_stdout or "未捕获到模型调用日志")
            )
        rag_count = len(rag.get("rag_knowledge", [])) if isinstance(rag, dict) else 0
        timed_log("生成RAG", "成功", f"生成 {rag_count} 条RAG知识，预计模型调用 {estimated_rag_calls or '未知'} 次", stage_started)

        log("合并去重", "开始", "转换并合并KnowledgeItem")
        stage_started = perf_counter()
        deep_items = rag_to_knowledge(rag, source_file=source_name)
        items = merge_restored_items(direct_items, deep_items)
        timed_log("完成", "成功", f"合并后 {len(items)} 条知识", stage_started)
        return items

    except KnowledgeRestoreError:
        raise
    except Exception as exc:
        if direct_items:
            log("完成", "部分成功", f"深度恢复失败，保留快速恢复 {len(direct_items)} 条知识：{exc}")
            return direct_items
        log("Restore", "失败", str(exc))
        raise KnowledgeRestoreError(
            f"知识恢复失败：{source_name}。请检查文件内容或模型配置。"
        ) from exc
