# AutoRAG-Studio Current Task

Version: V0.8.0-rc1

Status: Stable Checkpoint

Last Update: 2026-08-12

## Current Stable Checkpoint

```text
v0.8.0-rc1
```

The RC1 checkpoint preserves:

- Generate stable production chain
- Update closed loop
- Historical Restore
- Diff V0.2
- Complex Relation Grouping
- Exception Review
- Merge
- Exact Duplicate Cleanup
- Dual Excel Export
- RAG concurrency performance baseline
- Experimental Rule First QC framework

## Current Production Defaults

```text
RAG_MAX_CONCURRENCY=2
QC_MODE=full
```

`QC_MODE=rule_first` exists only as an experimental capability in RC1.

## Completed V0.8 Work

- Architecture and UI foundation
- Update historical knowledge restore
- System-standard Word restore
- Image-dominant Word parsing for new source materials
- New material generation in Update through existing Parser -> Facts -> RAG
- Diff V0.2 rule matching
- Complex relation grouping
- Exception Review
- Deterministic Merge
- Exact Duplicate Cleanup
- Update dual Excel export
- Streamlit session state stability
- Update UX simplification
- RAG batch concurrency performance optimization
- QC Rule First experiment framework

## Next Task

```text
TASK9 Facts Performance Experiment V0.1
```

TASK9 goal:

Explore Facts chunking and controlled concurrency in order to reduce Facts wall time without lowering Fact coverage or accuracy.

## TASK9 Guardrails

- Do not change Generate business rules.
- Do not change Fact prompt without explicit approval.
- Do not change RAG prompt or RAG batch size.
- Do not change Diff, Review, Merge, Dedup, or Excel schema.
- Compare output against the `v0.8.0-rc1` baseline.

## Do Not Start Yet

This checkpoint task only saves and pushes RC1.

Do not begin TASK9 implementation in the RC1 checkpoint task.
