# AutoRAG-Studio Current Task

Version: V0.8.1

Status: Released for Internal Trial

Last Update: 2026-08-14

## Current Stable Release

```text
v0.8.1
```

V0.8.1 includes:

- V0.8 Generate stable production chain
- V0.8 Update closed loop
- Excel Column-oriented Vehicle Matrix Parser
- Complex Excel Vehicle Record parsing
- RAG Empty Response Retry Once
- RAG Coverage Evaluator V2
- Export regression coverage

## Current Production Defaults

```text
FACTS_MODE=single
RAG_MAX_CONCURRENCY=2
RAG_BATCH_RETRY=1
QC_MODE=full
MODEL=deepseek-v4-flash
temperature=0.2
```

`FACTS_MODE=chunked` and `QC_MODE=rule_first` remain experimental capabilities and are not production defaults.

## Release Gate

```text
TASK12.8:
RELEASE READY WITH BACKLOG
```

Hard Gate uses Answerability Coverage:

```text
Price: 41/41
Cash: 41/41
Trade-in: 35/41
Finance: 36/41
Benefit: 39/41
Activity: 40/41
```

Full regression:

```text
213 passed, 2 skipped
```

## Known P2 Backlog

- Dynamic FAQ granularity optimization, especially independent Cash, Trade-in, and Finance FAQs.
- Color and exterior appearance extraction improvements in Step1 Facts.
- Retry policy expansion for 429, timeout, and connection errors.
- Chunked Facts quality improvement before production rollout.
- Rule First QC routing optimization.

## Next

```text
Real User Feedback Collection
```

Collect production-trial badcases from real users, then classify them into:

- Input/parser issues
- Facts coverage issues
- RAG answerability or FAQ granularity issues
- Scope or cross-vehicle issues
- Reliability issues

## Do Not Start Automatically

Do not begin V0.9 optimization, Prompt changes, Step1/Step2 changes, or new feature development without explicit user instruction.
