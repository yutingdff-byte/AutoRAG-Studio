# AutoRAG-Studio Current Task

Version: V0.8.0

Status: Completed

Last Update: 2026-08-12

## Current Stable Release

```text
v0.8.0
```

The V0.8 final release preserves:

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
- Experimental chunked Facts framework
- TASK10 End-to-End Release Validation
- TASK10.1 Facts Coverage Release Gate

## Current Production Defaults

```text
FACTS_MODE=single
RAG_MAX_CONCURRENCY=2
QC_MODE=full
```

`FACTS_MODE=chunked` and `QC_MODE=rule_first` exist only as experimental capabilities in V0.8.0.

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
- Facts chunking and controlled concurrency experiment framework
- Oversized Facts chunk safe splitting
- End-to-end release validation
- Facts coverage release gate

## Release Validation

```text
TASK10:
RELEASE READY WITH MINOR BACKLOG

TASK10.1:
PASS WITH MINOR BACKLOG
```

Known minor backlog:

- Facts non-determinism and granularity stability
- Chunked Facts quality improvement before production rollout
- Rule First QC routing optimization
- Targeted Semantic Judge only if future badcases require it
- Cloud Deployment
- UI detail polish

## Next

```text
V0.8 Cloud Deployment / Post-release Planning
```

Wait for user decision before starting the next task.

## Do Not Start Automatically

Do not begin V0.8.1, V0.9, Cloud Deployment, or new feature development without explicit user instruction.
