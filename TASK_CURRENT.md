# AutoRAG-Studio Current Task

Version: V0.8.2

Status: Ready for Internal Trial

Last Update: 2026-09-19

## Current Active Task

```text
TASK14
Excel Persistence and Cross-session Recovery MVP
```

Current implementation status:

```text
Branch: main
Local task-store backend: output/task_store
Cloud durable backend: pending external object-store configuration
```

Current objective:

```text
Allow completed Generate and Update Excel files to be recovered without rerunning model pipelines.
```

Implemented locally:

```text
Same-browser recovery token bootstrap
Manual recovery-code download
Generate Excel persistence
Update Excel persistence after temporary export
```

Still pending:

```text
Private object-store backend selection and Secrets configuration
Streamlit Cloud restart/redeploy recovery validation
Cloud retention cleanup validation
```

Do not claim Cloud restart-safe recovery until external storage is configured and tested.

## Current Stable Release

```text
v0.8.2
```

V0.8.2 includes:

- V0.8 Generate stable production chain
- V0.8 Update closed loop
- Excel Column-oriented Vehicle Matrix Parser
- Complex Excel Vehicle Record parsing
- RAG Empty Response Retry Once
- RAG Coverage Evaluator V2
- Production `FACTS_MODE=auto`
- Record-aware Facts Routing for complex vehicle matrix Excel
- Scoped exact dedup for record-aware multi-vehicle Facts

## Current Production Defaults

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

Routing:

```text
Normal Word / normal row-oriented Excel
-> single

COLUMN_ORIENTED_VEHICLE_MATRIX
-> record_aware
```

`FACTS_MODE=chunked` and `QC_MODE=rule_first` remain experimental capabilities and are not production defaults.

## Release Gate

```text
TASK12.16:
OWNER SMOKE PASS
```

Complex Excel E2E validation:

```text
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

Latest full regression:

```text
236 passed, 2 skipped
```

Owner smoke validation:

```text
Normal Word Generate: PASS
Complex Matrix Generate: PASS
Small Update: PASS
```

Normal Word smoke:

```text
Sample: tests/data/test.docx
FACTS_MODE=auto -> single
Facts: 5
RAG: 5
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
Static rows: 4
Dynamic rows: 1
```

## Known P2 Backlog

- Dynamic FAQ granularity optimization, especially independent Cash, Trade-in, and Finance FAQs.
- Color and exterior appearance extraction improvements in Step1 Facts.
- Retry policy expansion for 429, timeout, and connection errors.
- Chunked Facts quality improvement before production rollout.
- Rule First QC routing optimization.
- Complex matrix generation performance remains around 40 minutes in the 41-vehicle benchmark.

## Next

```text
Real User Feedback & Badcase Collection
```

Current goal:

Collect real user feedback and production badcases. There is no active development task.

Recommended next actions:

1. Invite 3-5 internal users
2. Collect Generate / Update feedback
3. Record Badcases with `FEEDBACK_TEMPLATE.md`
4. Accumulate about 10-20 useful feedback items
5. Run Feedback Review
6. Define V0.9 scope

Classify badcases into:

- Input/parser issues
- Facts coverage issues
- RAG answerability or FAQ granularity issues
- Scope or cross-vehicle issues
- Reliability issues
 - QC issues
 - Export issues
 - UX/performance issues

## Do Not Start Automatically

Do not begin V0.9 optimization, Prompt changes, Step1/Step2 changes, concurrency changes, semantic dedup, retry expansion, or new feature development without explicit user instruction and real feedback evidence.
