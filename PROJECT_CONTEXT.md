# AutoRAG-Studio Project Context

Version: V0.8.2

Status: Ready for Internal Trial

Last Update: 2026-08-23

## Current Stable

`v0.8.2` is the current stable internal trial release.

This release preserves the completed Generate baseline, the V0.8 Update closed loop, the RAG performance improvement, complex Excel matrix parsing, RAG empty-response retry, and RAG Coverage Evaluator V2.

V0.8.2 adds production `FACTS_MODE=auto` with record-aware routing for complex vehicle matrix Excel files. Normal Word Generate, complex Matrix Excel Generate, and small Update smoke are validated.

Cloud URL:

```text
https://autorag-studio.streamlit.app/
```

Current phase:

```text
TASK14 Excel Persistence and Recovery MVP
```

## Excel Persistence and Recovery Status

TASK14 introduces a minimal recovery layer for completed Excel outputs.

Implemented locally:

- Generate and Update final Excel persistence through a shared task store.
- Same-browser auto-recovery using a minimal browser-side recovery token.
- Cross-browser recovery by manually entering the recovery code.
- Download recovery without rerunning Parser, Facts, RAG, QC, Diff, Merge, or Export.

Current default backend:

```text
TASK_STORE_LOCAL_DIR=output/task_store
TASK_STORE_RETENTION_DAYS=7
```

Security boundary:

- Recovery tokens are random and unguessable.
- Manifests store token hashes, not plaintext tokens.
- The MVP stores only final Excel files and minimal task metadata.
- Uploaded source materials and model intermediate JSON are not persisted for recovery.

Cloud limitation:

```text
Local filesystem storage is not a durable Streamlit Cloud backend.
Cloud restart-safe recovery requires a private object-store backend and configured Secrets.
```

## ZIP Image Import MVP Status

TASK13 adds small ZIP image资料 ingestion for automotive source images.

Validated local sample:

```text
Sample: output/task13_3_zip_gate_c/gate_c_two_groups.zip
Groups: 2
Images: 3
Latest source Run ID: 20260919_145648
```

Supported in the MVP scope:

- Outer ZIP image extraction.
- One-level inner ZIP image extraction.
- Folder/group isolation for vehicle material groups.
- Large image preprocessing path.
- Existing Generate chain reuse:

```text
ZIP images
-> Vision Material
-> Facts
-> RAG
-> QC
-> Dual Excel Export
```

Release-gate policy:

```text
Correct facts may be omitted in the MVP.
Unsupported deterministic facts must not enter formal Excel.
```

Latest safety-filtered small-ZIP export:

```text
Vehicle configuration Excel: 14 rows
Price/policy Excel: 7 rows
Total: 21 rows
Confirmed high-risk formal-export issues: 0
```

Known ZIP MVP limits:

- Full customer ZIP around 195 MB is not validated.
- Cloud small-ZIP E2E is pending deployment validation.
- Trunk/cargo capacity `560L-1485L` remains a coverage gap.
- ICCOA Carlink remains a coverage gap.
- Subjective expression cleanup and key-fact coverage evaluation remain backlog.

Do not claim full customer ZIP production readiness until scale, resource, cost, and knowledge-quality validation are complete.

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

## Update V0.8 Status

Update has a complete V0.8 closed loop:

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

## Production Defaults

```text
FACTS_MODE=auto
FACTS_RECORD_BATCH_SIZE=3
FACTS_RECORD_BATCH_MAX_CHARS=12000
FACTS_MAX_CONCURRENCY=2

RAG_MAX_CONCURRENCY=2
RAG_BATCH_RETRY=1

QC_MODE=full

MODEL=deepseek-v4-flash
temperature=0.2
```

Facts routing:

```text
Normal Word / normal row-oriented Excel
-> single

COLUMN_ORIENTED_VEHICLE_MATRIX
-> record_aware
```

## V0.8.2 Additions

V0.8.2 adds:

- Production `FACTS_MODE=auto`.
- Record-aware Facts Routing for complex vehicle matrix Excel files.
- Vehicle Record-aware batching with stable internal `VRxxx` trace IDs.
- Scoped exact dedup for record-aware multi-vehicle Facts.

Complex Excel production E2E baseline:

```text
Orientation: COLUMN_ORIENTED_VEHICLE_MATRIX
Vehicle Records: 41
Series: 13
Facts: 763
RAG: 421
QC warnings: 21
QC errors: 0
Exportable: 391
Vehicle configuration Excel: 210 rows
Price/policy Excel: 181 rows
```

V0.8.2 release status:

```text
READY FOR INTERNAL TRIAL
```

Owner smoke validation:

- Normal Word Generate: PASS
- Complex Matrix Excel Generate: PASS
- Small Update: PASS

Normal Word smoke:

```text
Sample: tests/data/test.docx
FACTS_MODE=auto -> single
Material chars: 104
Facts: 5
RAG: 5
QC issues: 1
Exportable: 5
Static rows: 4
Dynamic rows: 1
Total: 92.098s
```

Small Update smoke:

```text
History: 3-row standard historical Excel
New material: tests/data/test.docx
Restore: 3/3
ADDED: 2
UPDATED: 3
UNCHANGED: 0
REVIEW_REQUIRED: 0
Final Clean: 5
Dedup Removed: 0
Static rows: 4
Dynamic rows: 1
```

Engineering story:

```text
Complex multi-vehicle Matrix Excel
-> Parser recovers 41 Vehicle Records
-> FACTS_MODE=single may produce finish_reason=length
-> JSON truncation
-> Facts=None
-> Generate fail-fast
```

V0.8.2 solution:

```text
Parser orientation detection
-> auto Facts routing
-> Vehicle Record-aware batching
-> Scoped exact dedup
-> RAG
-> QC
-> Dual Excel Export
```

Record-aware is not character chunking. A Vehicle Record is the minimum indivisible business boundary. Normal documents continue using Single mode.

Internal trial rule:

Do not proactively optimize prompts, concurrency, batch size, semantic dedup, color extraction, or retry scope unless real user feedback proves a priority issue.

Known P2 backlog:

- Dynamic FAQ granularity for Cash, Trade-in, and Finance.
- Color/exterior Facts coverage.
- Retry expansion for 429, timeout, and connection error.
- Complex matrix performance, currently around 2468s / 41 minutes in the 41-vehicle benchmark.
- Development environment cleanup: local `.venv` points to a missing Python 3.14 runtime; TASK12.16 smoke used the bundled runtime plus project requirements.

## V0.8.1 Additions

V0.8.1 adds:

- Excel Column-oriented Vehicle Matrix Parser for files where attributes are rows and vehicle versions are columns.
- Deterministic conversion from complex Excel matrices into complete Vehicle Record blocks.
- RAG Empty Response Retry Once with fail-fast behavior preserved after retry failure.
- RAG Coverage Evaluator V2, separating:
  - Answerability Coverage for release hard gates
  - Independent FAQ Coverage for optimization/backlog tracking

Complex Excel validation baseline:

```text
Orientation: COLUMN_ORIENTED_VEHICLE_MATRIX
Material chars: 49,861
Vehicle Records: 41
Series: 13
Facts: 123
RAG: 207
```

Evaluator V2 Answerability Coverage:

```text
Price: 41/41
Cash: 41/41
Trade-in: 35/41
Finance: 36/41
Benefit: 39/41
Activity: 40/41
```

## Production Defaults

V0.8.1 production defaults:

```text
FACTS_MODE=single
RAG_MAX_CONCURRENCY=2
RAG_BATCH_RETRY=1
QC_MODE=full
MODEL=deepseek-v4-flash
temperature=0.2
```

`FACTS_MODE=chunked` and `QC_MODE=rule_first` remain experimental and are not production defaults.

## Performance Baseline

V0.8 default:

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

## Final Release Validation

TASK10 Generate E2E:

```text
Parser: 0.81s
Facts: 230.85s
RAG: 122.25s
QC: 111.32s
Excel: 0.16s
Total: 465.41s
Facts: 49
RAG: 68
Exportable: 68
```

TASK10 Update E2E:

```text
Old Knowledge: 1136
New Knowledge: 68

ADDED: 39
UPDATED: 10
UNCHANGED: 1126
REVIEW_REQUIRED: 19

Complex Groups: 7
Single Reviews: 0

Final Clean: 1193
Exportable: 1193
```

TASK10.1 Facts Coverage Release Gate:

```text
Result: PASS WITH MINOR BACKLOG
Input: 12081 chars
FACTS_MODE: single
Model: deepseek-v4-flash
temperature: 0.2

TASK9 Single: 102 Facts
TASK10 Final Generate: 49 Facts

Canonical model coverage: 11/11
Price coverage: 6/6
Finance coverage: 13/13
Source numeric signal missing: 0
```

The `102 -> 49` Facts difference is mainly from merged and differently split Facts. It is not a V0.8 release blocker.

## QC Status

Production default:

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

Therefore Full QC remains the V0.8 production default.

## V0.8.1 Known Backlog

- Dynamic FAQ granularity optimization, especially independent Cash, Trade-in, and Finance FAQs.
- Color and exterior appearance extraction improvements in Step1 Facts.
- Retry policy expansion for 429, timeout, and connection errors.
- Facts non-determinism and granularity stability.
- Chunked Facts quality improvement before production rollout.
- Rule First QC routing optimization.
- Targeted Semantic Judge for future low-confidence or complex cases if needed.
- UI detail polish.

## Next Stage

Do not expand V0.8 Update business features in the V0.8.1 release line. Next work should be real user feedback collection and V0.9 planning based on observed badcases.
