# AutoRAG-Studio Current Task

Version: V0.8.2

Status: Cloud Deployment / Owner Smoke

Last Update: 2026-08-15

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
TASK12.15:
DEPLOYED - OWNER SMOKE PENDING
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

## Known P2 Backlog

- Dynamic FAQ granularity optimization, especially independent Cash, Trade-in, and Finance FAQs.
- Color and exterior appearance extraction improvements in Step1 Facts.
- Retry policy expansion for 429, timeout, and connection errors.
- Chunked Facts quality improvement before production rollout.
- Rule First QC routing optimization.
- Complex matrix generation performance remains around 40 minutes in the 41-vehicle benchmark.

## Next

```text
Owner Smoke Validation
```

Deployment owner checklist:

1. Normal Word Generate smoke
2. Small Update smoke
3. If both pass, mark V0.8.2 ready for internal trial
4. If either fails, create a focused V0.8.2 hotfix branch

After owner smoke, collect production-trial badcases from real users and classify them into:

- Input/parser issues
- Facts coverage issues
- RAG answerability or FAQ granularity issues
- Scope or cross-vehicle issues
- Reliability issues

## Do Not Start Automatically

Do not begin V0.9 optimization, Prompt changes, Step1/Step2 changes, or new feature development without explicit user instruction.
