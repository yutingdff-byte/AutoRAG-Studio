# AutoRAG-Studio Project Context

Version: V0.8.0-rc1

Status: Release Candidate 1 Stable Checkpoint

Last Update: 2026-08-12

## Current Stable Candidate

`v0.8.0-rc1` is the current V0.8 stable candidate.

This checkpoint preserves the completed Generate baseline, the V0.8 Update closed loop, and the first-stage performance baseline before TASK9 Facts Performance Experiment begins.

## Product Goal

AutoRAG-Studio is a knowledge generation, review, and update platform for enterprise Agent scenarios, especially automotive AI outbound-call knowledge bases.

Product principle:

```text
网页负责分析，Excel负责生产；系统负责判断，用户负责确认。
```

## Generate Status

Generate is stable and remains business-frozen.

Current Generate chain:

```text
Document
-> Parser
-> Facts
-> RAG
-> QC
-> Check Center
-> Dual Excel Export
```

Do not change Generate prompts, Fact rules, RAG rules, QC prompt, parser behavior, Excel schema, static/dynamic split, or export quality gate unless a separately confirmed bug requires it.

## Update RC1 Status

Update has a complete V0.8 RC1 closed loop:

```text
Historical Knowledge
+
New Documents
-> Restore
-> Unified Knowledge
-> Diff V0.2
-> Complex Relation Grouping
-> Exception Review
-> Merge
-> Exact Duplicate Cleanup
-> Export Quality Gate
-> Dual Excel Export
```

The normal Update page flow is:

```text
上传资料
-> 处理完成
-> 本轮资料范围
-> 本轮变化
-> 处理异常（仅必要时）
-> 生成新版知识库
-> 下载 Excel
```

Normal successful flows no longer show restore logs, parser logs, Facts/RAG logs, API transport logs, full restore previews, new knowledge previews, expanded Diff tables, or normal ADDED/UPDATED review cards.

## Historical Restore

Supported historical inputs:

- Standard AutoRAG Excel exports
- Word knowledge files

System-standard Word restore is deterministic and fast. Supported historical structures include:

- Schema A: `车系 / 问题 / 答案`
- Schema B: `意图名称1 / 意图描述1 / 参考内容1`

Users do not select Fast Restore or Deep Restore. The system detects the format and routes automatically.

## Image-Dominant Word

`IMAGE_DOMINANT_WORD` is supported for new source materials.

When a Word file contains little body text and the main business content is embedded as images:

```text
Extract embedded business images
-> Existing Vision parsing
-> Material text
-> Facts
-> RAG
```

Historical Restore remains separate from this new-material parser path.

## Diff V0.2

User-facing Diff states remain:

- ADDED
- UPDATED
- UNCHANGED
- REVIEW_REQUIRED

Diff V0.2 includes:

- Intent normalization
- Model normalization
- Candidate recall
- Numeric normalization
- GENERAL/DETAIL complex relation detection
- 1:N and N:1 safe handling
- Guardrails against obvious model mismatches such as H6 vs H6L

## Review, Merge, and Export

Default Update decisions:

```text
ADDED -> automatically accept new knowledge
UPDATED -> automatically use new knowledge to replace old knowledge
UNCHANGED -> retain old knowledge
Complex or uncertain relation -> Exception Review
```

Dynamic knowledge, including price, finance, benefits, promotions, and marketing policies, is automatically updated when Diff clearly identifies a safe 1:1 UPDATED relation.

Complex relations support:

- GENERAL_TO_DETAIL
- DETAIL_TO_GENERAL
- ONE_TO_MANY
- MANY_TO_ONE
- AMBIGUOUS_RELATION

Complex relation default:

```text
Add new knowledge
+
Keep old knowledge
```

Old knowledge is removed only when the user explicitly chooses replacement.

Single Review is restricted to:

```text
1 Old
+
1 New
+
related but not safe to automatically replace
```

Cases with New only are treated as ADDED and do not enter Single Review.

## Exact Duplicate Cleanup

Final Update production flow:

```text
Merge
-> Final Knowledge
-> Exact Duplicate Cleanup
-> Export
```

Only exact duplicates are cleaned automatically after safe normalization of:

```text
model
version
question
answer
category
```

The cleanup does not remove:

- same question with different answers
- different versions
- different models
- similar questions
- semantic duplicates

## Export Quality Gate

Formal Excel export still uses the existing `is_exportable_rag()` gate.

The following cannot enter production Excel:

- `need_confirm == 是`
- `answer_type == need_confirm`
- `review_type` in `missing`, `conflict`, `inference`
- `knowledge_status` in `missing`, `unconfirmed`, `invalid`
- empty answers or explicit missing-answer placeholders

Two counts must remain distinct:

```text
Final Clean Knowledge
= Update internal Merge + Exact Dedup complete set

Exportable Knowledge
= Knowledge that passes the final export quality gate and enters Excel
```

## Performance Baseline

RC1 default:

```text
RAG_MAX_CONCURRENCY=2
```

Rollback:

```text
RAG_MAX_CONCURRENCY=1
```

TASK7 benchmark:

- Input Facts: 101
- Batch Count: 4
- Requests: 4 -> 4
- Concurrency 1: 426.05s
- Concurrency 2: 177.89s
- Wall-time reduction: 58.25%
- Speedup: about 2.40x
- Fact coverage: 101/101 -> 101/101
- Missing Facts: 0 -> 0
- High-value dynamic missing: 0 -> 0

## QC Status

RC1 production default:

```text
QC_MODE=full
```

Experimental mode:

```text
QC_MODE=rule_first
```

Rule First QC framework exists, but it remains experimental. On the saved marketing-policy sample:

- Total Knowledge: 82
- LLM Routed: 78
- Route Ratio: 95.12%
- Estimated Requests: 1 -> 1

Therefore Full QC remains the RC1 default.

## Next Stage

Do not expand V0.8 Update business features before V0.8 final.

Next task:

```text
TASK9 Facts Performance Experiment V0.1
```

TASK9 should explore Facts chunking and controlled concurrency without reducing Fact coverage or accuracy.
