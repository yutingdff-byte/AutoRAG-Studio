# AutoRAG-Studio Roadmap

Current Stable Candidate: `v0.8.0-rc1`

Current Branch: `feature/v0.8-architecture-ui`

Date: 2026-08-12

## Product Direction

AutoRAG-Studio is evolving from a one-time Excel generation tool into an AI knowledge generation, review, and continuous-update platform.

Core scenario:

```text
AI outbound call
-> lead qualification
-> store visit invitation
-> human sales handoff
```

## Completed Stable Baselines

### V0.6 Stable

Status: Completed and frozen

Stable tag: `v0.6.6`

Completed:

- Static/dynamic knowledge split
- Brand/model/trim hierarchy
- Model-level aggregation
- Version-difference generation
- Dual Excel export
- Streamlit review console
- Knowledge review center
- QC report display
- Price overview generation
- QC false-positive reduction for fixed services and vehicle capabilities

### V0.7.2 Generate Stable

Status: Completed and frozen

Stable tag: `v0.7.2`

Completed:

- Export quality gate
- Missing, unconfirmed, invalid, conflict, and inference knowledge blocked from Excel
- Knowledge Review Center normalization
- Static/dynamic lifecycle QC improvements
- TTS cleanup for prices, percentages, traffic packages, voltage, and abbreviations
- Generate output retained as the stable production baseline

### V0.7.3 Cloud Ready

Status: Completed

Completed:

- Streamlit Community Cloud compatibility
- Runtime and dependency pinning
- Streamlit Secrets support
- Local `.env` compatibility
- Deployment documentation
- Project cleanup classification

## V0.8 RC1 Completed Scope

Status: Release Candidate

Tag: `v0.8.0-rc1`

### Architecture

- V0.8 Architecture and UI Foundation
- Home page with Generate and Update entries
- Separate page modules and shared UI components
- Unified `KnowledgeItem` foundation

### Restore

- Standard Excel Restore
- System-standard Word Restore
- Automatic restore format detection
- Supported Word schemas:
  - `车系 / 问题 / 答案`
  - `意图名称1 / 意图描述1 / 参考内容1`

### New Material Parsing

- Existing text/Excel/PDF/TXT/image parsing retained
- IMAGE_DOMINANT_WORD support for embedded Word business images
- Existing Vision capability reused for embedded images

### Diff

- Diff V0.2
- Intent normalization
- Model normalization
- Candidate recall
- Numeric normalization
- GENERAL/DETAIL relation detection
- 1:N and N:1 safe handling
- Model mismatch guardrails

### Review, Merge, Export

- Exception Review
- Complex Relation Grouping
- Deterministic Merge
- ADDED auto-accept
- UPDATED auto-replace
- UNCHANGED keep old
- Complex/uncertain relations reviewed only when needed
- Exact Duplicate Cleanup before export
- Update dual Excel export using existing Generate schema and quality gate

### UX Simplification

- Update workflow simplified to result-first production flow
- Normal success path hides technical logs and large previews
- Diff detail tables moved behind optional audit details
- Ordinary ADDED/UPDATED review removed from the main flow

### Performance

- RAG Performance V0.1 completed
- `RAG_MAX_CONCURRENCY=2` is the RC1 default
- Benchmark: 426.05s -> 177.89s, down 58.25%, about 2.40x speedup

### QC Experiment

- QC Rule First framework completed
- `QC_MODE=full` remains RC1 default
- `QC_MODE=rule_first` remains experimental because the marketing-policy sample routed 78/82 items to LLM QC

## Next Planned Work

### TASK9 - Facts Performance Experiment V0.1

Status: Next

Goal:

Explore Facts chunking and controlled concurrency while preserving Fact coverage and accuracy.

Constraints:

- Do not change Fact prompt or extraction rules unless separately approved
- Do not reduce Fact coverage
- Compare quality against the RC1 baseline

### End-to-End Performance Benchmark

Status: Planned after TASK9

Goal:

Measure Generate and Update total wall time after RAG and Facts performance experiments.

### V0.8.0 Final

Status: Planned

Goal:

Freeze the V0.8 Update closed loop after TASK9 and end-to-end benchmark validation.

### Cloud Deployment

Status: Planned after V0.8.0 Final

Goal:

Deploy the final V0.8 branch after performance and quality validation.

## Deferred Work

- Semantic Judge for targeted low-confidence or complex cases
- Embedding or vector search
- QC concurrency
- QC Rule First default rollout
- Facts prompt changes
- Batch size experiments
- Account system
- Database persistence
- Task history center
