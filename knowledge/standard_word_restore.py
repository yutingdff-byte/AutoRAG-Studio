"""Deterministic restore for system-exported paragraph-split JSON Word files."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any

from docx import Document

from knowledge.adapter import build_knowledge_id, normalize_internal_knowledge_type
from knowledge.models import KnowledgeItem, normalize_question


FORMAT_ID = "SYSTEM_STANDARD_WORD_V1"
PARSER_VERSION = "v1"

QA_KEYS = {"车系", "问题", "答案"}
INTENT_KEYS = {"意图名称1", "意图描述1", "参考内容1"}
SAFE_REPAIR_KEYS = {"车系", "车型", "问题", "答案", "回答", "意图名称1", "意图描述1", "参考内容1"}


@dataclass(slots=True)
class ParsedRecord:
    data: dict[str, Any]
    source_record_index: int
    source_paragraph_start: int
    source_paragraph_end: int
    strict: bool
    repaired: bool = False


@dataclass(slots=True)
class FailedRecord:
    source_record_index: int
    source_paragraph_start: int
    source_paragraph_end: int
    reason: str
    raw_text: str


@dataclass(slots=True)
class FormatDetectionResult:
    format_id: str
    parser_version: str = PARSER_VERSION
    candidate_records: int = 0
    parse_success_count: int = 0
    supported_schema_count: int = 0
    parse_success_rate: float = 0.0
    supported_schema_rate: float = 0.0
    apache_poi: bool = False


@dataclass(slots=True)
class StandardWordRestoreReport:
    format_id: str = FORMAT_ID
    parser_version: str = PARSER_VERSION
    candidate_records: int = 0
    success_count: int = 0
    strict_success_count: int = 0
    repaired_success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    duplicate_exact_count: int = 0
    duplicate_possible_count: int = 0
    qa_v1_count: int = 0
    intent_v1_count: int = 0
    elapsed_seconds: float = 0.0
    llm_calls: int = 0
    failures: list[FailedRecord] = field(default_factory=list)


@dataclass(slots=True)
class StandardWordRestoreResult:
    items: list[KnowledgeItem]
    report: StandardWordRestoreReport


def clean_text(value: Any) -> str:
    text = str(value or "").replace("\u200b", "").replace("\ufeff", "")
    return re.sub(r"\s+", " ", text.strip())


def get_source_name(file: Any) -> str:
    name = getattr(file, "name", None)
    if name:
        return Path(str(name)).name
    if isinstance(file, (str, Path)):
        return Path(file).name
    return "历史知识.docx"


def load_document(file: Any) -> Document:
    if hasattr(file, "seek"):
        file.seek(0)
    return Document(file)


def paragraph_lines(file: Any) -> list[tuple[int, str]]:
    doc = load_document(file)
    return [
        (index, clean_text(paragraph.text))
        for index, paragraph in enumerate(doc.paragraphs)
        if clean_text(paragraph.text)
    ]


def collect_record_blocks(lines: list[tuple[int, str]]) -> tuple[list[tuple[int, int, str]], list[FailedRecord]]:
    blocks: list[tuple[int, int, str]] = []
    failures: list[FailedRecord] = []
    current: list[str] = []
    start: int | None = None
    depth = 0
    record_index = 0

    for paragraph_index, line in lines:
        opens = line.count("{")
        closes = line.count("}")

        if depth == 0 and opens:
            current = []
            start = paragraph_index

        if depth > 0 or opens:
            current.append(line)
            depth += opens - closes

            if depth == 0 and current and start is not None:
                record_index += 1
                blocks.append((start, paragraph_index, "\n".join(current)))
                current = []
                start = None

    if current and start is not None:
        failures.append(
            FailedRecord(
                source_record_index=record_index + 1,
                source_paragraph_start=start,
                source_paragraph_end=lines[-1][0] if lines else start,
                reason="JSON记录未闭合",
                raw_text="\n".join(current),
            )
        )

    return blocks, failures


def safe_repair_json(raw_text: str) -> str | None:
    """Repair only the confirmed missing opening quote pattern."""

    repaired_lines: list[str] = []
    changed = False
    pattern = re.compile(r'^(\s*"(?P<key>[^"]+)"\s*:\s*)(?P<value>[^"].*")(?P<suffix>\s*,?\s*)$')

    for line in raw_text.splitlines():
        match = pattern.match(line)
        if not match:
            repaired_lines.append(line)
            continue

        key = match.group("key")
        value = match.group("value").strip()
        if key not in SAFE_REPAIR_KEYS:
            repaired_lines.append(line)
            continue
        if not value.endswith('"'):
            repaired_lines.append(line)
            continue

        escaped_value = value[:-1].replace("\\", "\\\\").replace('"', '\\"')
        repaired_lines.append(f'{match.group(1)}"{escaped_value}"{match.group("suffix")}')
        changed = True

    if not changed:
        return None

    candidate = "\n".join(repaired_lines)
    try:
        json.loads(candidate)
    except Exception:
        return None
    return candidate


def parse_record(raw_text: str) -> tuple[dict[str, Any] | None, bool, str]:
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict):
            return data, False, ""
        return None, False, "JSON不是对象"
    except Exception as exc:
        strict_error = str(exc)

    repaired = safe_repair_json(raw_text)
    if repaired:
        data = json.loads(repaired)
        if isinstance(data, dict):
            return data, True, ""

    return None, False, strict_error


def schema_type(data: dict[str, Any]) -> str | None:
    keys = set(data.keys())
    if QA_KEYS.issubset(keys):
        return "qa_v1"
    if INTENT_KEYS.issubset(keys):
        return "intent_v1"
    return None


def detect_system_standard_word_v1(file: Any) -> FormatDetectionResult:
    try:
        lines = paragraph_lines(file)
    except Exception:
        return FormatDetectionResult(format_id="UNKNOWN_WORD_FORMAT")

    blocks, _ = collect_record_blocks(lines)
    candidate_count = len(blocks)
    if candidate_count < 3:
        return FormatDetectionResult(format_id="UNKNOWN_WORD_FORMAT", candidate_records=candidate_count)

    parse_success = 0
    supported = 0
    for _, _, raw_text in blocks:
        data, _, _ = parse_record(raw_text)
        if not data:
            continue
        parse_success += 1
        if schema_type(data):
            supported += 1

    parse_rate = parse_success / candidate_count if candidate_count else 0.0
    supported_rate = supported / parse_success if parse_success else 0.0
    format_id = FORMAT_ID if parse_rate >= 0.8 and supported_rate >= 0.8 else "UNKNOWN_WORD_FORMAT"

    return FormatDetectionResult(
        format_id=format_id,
        candidate_records=candidate_count,
        parse_success_count=parse_success,
        supported_schema_count=supported,
        parse_success_rate=parse_rate,
        supported_schema_rate=supported_rate,
        apache_poi=False,
    )


def valid_item_fields(question: str, answer: str, model: str | None = None) -> tuple[bool, str]:
    question = clean_text(question)
    answer = clean_text(answer)
    if not question:
        return False, "question为空"
    if not answer:
        return False, "answer为空"
    if any(mark in question for mark in ["{", "}", '"答案"', '"回答"']):
        return False, "question包含JSON字段或对象"
    if any(mark in answer for mark in ["{", "}", '"问题"']):
        return False, "answer包含未解析JSON"
    if "答案" in question and "是什么" in question:
        return False, "question疑似由答案机械生成"
    if model and any(mark in model for mark in ["{", "}", '"问题"', '"答案"']):
        return False, "model包含JSON字段"
    return True, ""


def item_from_record(
    data: dict[str, Any],
    source_file: str,
    record: ParsedRecord,
    schema: str,
) -> tuple[KnowledgeItem | None, str]:
    if schema == "qa_v1":
        question = clean_text(data.get("问题"))
        answer = clean_text(data.get("答案"))
        model = clean_text(data.get("车系"))
        category = clean_text(data.get("分类"))
        metadata_extra: dict[str, Any] = {}
    elif schema == "intent_v1":
        question = clean_text(data.get("意图描述1"))
        answer = clean_text(data.get("参考内容1"))
        model = ""
        category = ""
        metadata_extra = {"intent_name": clean_text(data.get("意图名称1"))}
    else:
        return None, "不支持的Schema"

    ok, reason = valid_item_fields(question, answer, model)
    if not ok:
        return None, reason

    metadata = {
        "source": "standard_word_restore",
        "parser_method": "system_standard_word_v1",
        "schema_type": schema,
        "format_version": FORMAT_ID,
        "parser_version": PARSER_VERSION,
        "source_record_index": record.source_record_index,
        "source_paragraph_start": record.source_paragraph_start,
        "source_paragraph_end": record.source_paragraph_end,
        "json_parse_mode": "repaired" if record.repaired else "strict",
        **metadata_extra,
    }

    return (
        KnowledgeItem(
            knowledge_id=build_knowledge_id(
                "STD-DOCX",
                source_file,
                record.source_record_index,
                question,
                answer,
                model,
            ),
            question=question,
            normalized_question=normalize_question(question),
            answer=answer,
            category=category,
            module=None,
            brand=None,
            model=model or None,
            trim=None,
            knowledge_type=normalize_internal_knowledge_type(None, category, None),
            answer_type="restored",
            need_confirm=False,
            fact_refs=[],
            source_files=[source_file],
            metadata=metadata,
        ),
        "",
    )


def restore_system_standard_word_v1(file: Any) -> StandardWordRestoreResult:
    started_at = perf_counter()
    source_file = get_source_name(file)
    lines = paragraph_lines(file)
    blocks, boundary_failures = collect_record_blocks(lines)
    report = StandardWordRestoreReport(candidate_records=len(blocks) + len(boundary_failures))
    report.failures.extend(boundary_failures)
    items: list[KnowledgeItem] = []
    exact_counter: Counter[tuple[str, str, str]] = Counter()
    question_counter: Counter[tuple[str, str]] = Counter()

    for record_index, (start, end, raw_text) in enumerate(blocks, start=1):
        data, repaired, error = parse_record(raw_text)
        if not data:
            report.failed_count += 1
            report.failures.append(
                FailedRecord(record_index, start, end, f"JSON解析失败：{error}", raw_text)
            )
            continue

        record = ParsedRecord(data, record_index, start, end, strict=not repaired, repaired=repaired)
        schema = schema_type(data)
        if not schema:
            report.skipped_count += 1
            report.failures.append(
                FailedRecord(record_index, start, end, "不支持的记录Schema", raw_text)
            )
            continue

        item, reason = item_from_record(data, source_file, record, schema)
        if not item:
            report.failed_count += 1
            report.failures.append(FailedRecord(record_index, start, end, reason, raw_text))
            continue

        if schema == "qa_v1":
            report.qa_v1_count += 1
        elif schema == "intent_v1":
            report.intent_v1_count += 1

        if repaired:
            report.repaired_success_count += 1
        else:
            report.strict_success_count += 1

        exact_counter[(item.model or "", item.question, item.answer)] += 1
        question_counter[(item.model or "", item.normalized_question)] += 1
        items.append(item)

    report.success_count = len(items)
    report.failed_count += len(boundary_failures)
    report.duplicate_exact_count = sum(count - 1 for count in exact_counter.values() if count > 1)
    report.duplicate_possible_count = sum(count - 1 for count in question_counter.values() if count > 1)
    report.elapsed_seconds = perf_counter() - started_at
    report.llm_calls = 0
    return StandardWordRestoreResult(items=items, report=report)


def restore_report_to_logs(report: StandardWordRestoreReport) -> list[str]:
    return [
        f"识别格式｜成功｜{report.format_id}",
        f"标准恢复｜完成｜候选记录 {report.candidate_records}，成功 {report.success_count}，失败 {report.failed_count}，跳过 {report.skipped_count}",
        f"标准恢复｜统计｜严格解析 {report.strict_success_count}，安全修复 {report.repaired_success_count}，qa_v1 {report.qa_v1_count}，intent_v1 {report.intent_v1_count}",
        f"标准恢复｜质量｜精确重复 {report.duplicate_exact_count}，疑似重复 {report.duplicate_possible_count}",
        f"标准恢复｜性能｜耗时 {report.elapsed_seconds:.2f}s，LLM调用 {report.llm_calls}",
    ]
