# AutoRAG-Studio Roadmap

Current Stable: `v0.8.2`

Current Branch: `main`

Date: 2026-08-15

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

## V0.8 Final Completed Scope

Status: Completed

Tag: `v0.8.0`

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
- `RAG_MAX_CONCURRENCY=2` is the V0.8 production default
- Benchmark: 426.05s -> 177.89s, down 58.25%, about 2.40x speedup
- End-to-end Generate validation improved the old baseline from about 807.78s to 465.41s, down 42.38%

### QC Experiment

- QC Rule First framework completed
- `QC_MODE=full` remains V0.8 production default
- `QC_MODE=rule_first` remains experimental because the marketing-policy sample routed 78/82 items to LLM QC

### Facts Experiment

- Experimental chunked Facts extraction completed
- Oversized block safe splitting completed
- `FACTS_MODE=single` remains the V0.8 production default
- `FACTS_MODE=chunked` remains experimental because Fact granularity and scope stability need further hardening

### Release Validation

- TASK10 End-to-End Release Validation completed
- TASK10.1 Facts Coverage Release Gate completed with PASS WITH MINOR BACKLOG
- V0.8 has no known P0/P1 release blocker

## V0.8.1 Internal Trial Release

Status: Completed

Tag: `v0.8.1`

### Complex Excel Parser

- Added Column-oriented Vehicle Matrix Parser.
- Supports `COLUMN_ORIENTED_VEHICLE_MATRIX`.
- Converts attribute-row / vehicle-version-column Excel files into deterministic Vehicle Record blocks.
- Real validation:
  - Material chars: 49,861
  - Vehicle Records: 41
  - Series: 13
  - Facts: 123
  - RAG: 207

### RAG Reliability

- Added Empty Response Retry Once for RAG batch execution.
- Retry success continues normal merge.
- Retry failure remains fail-fast and does not output a partial knowledge base.

### Evaluation Framework

- Added RAG Coverage Evaluator V2.
- Release hard gate now uses Answerability Coverage.
- Independent FAQ Coverage is retained as a soft optimization metric.
- Fixed evaluator false negatives such as old `Price 5/41` and dynamic `0/41` reports.

### Release Gate

- TASK12.8 V0.8.1 Final Release Gate completed.
- Result: RELEASE READY WITH BACKLOG.
- Full regression: `213 passed, 2 skipped`.
- No known P0/P1 release blocker.

## V0.8.2 Complex Facts Reliability Patch

Status: Completed

Tag: `v0.8.2`

### Production Facts Routing

- Added production `FACTS_MODE=auto`.
- Normal Word and normal row-oriented Excel inputs continue using Single Facts mode.
- `COLUMN_ORIENTED_VEHICLE_MATRIX` inputs automatically use record-aware Facts generation.
- Record-aware production candidate:
  - `FACTS_RECORD_BATCH_SIZE=3`
  - `FACTS_RECORD_BATCH_MAX_CHARS=12000`
  - `FACTS_MAX_CONCURRENCY=2`

### Complex Matrix Reliability

- Added Vehicle Record-aware Facts batching.
- Preserves complete vehicle/version record boundaries during Facts extraction.
- Uses internal stable `VRxxx` trace IDs for evaluation and debug.
- Scopes exact dedup by vehicle record to avoid removing same-content Facts from different vehicles or versions.

### Validation

- Complex Excel production E2E completed:
  - Vehicle Records: 41
  - Series: 13
  - Facts: 763
  - RAG: 421
  - QC warnings: 21
  - QC errors: 0
  - Exportable: 391
  - Vehicle configuration Excel: 210 rows
  - Price/policy Excel: 181 rows
- TASK12.14 accepted validation debt for:
  - Normal Word Generate owner smoke
  - Small Update owner smoke

### Known Backlog

- Complex matrix performance remains around 40 minutes in the 41-vehicle benchmark.
- Dynamic FAQ granularity optimization.
- Color/exterior color Facts coverage.
- Retry policy expansion for 429, timeout, and connection errors.

## Next Planned Work

### Internal Trial and Owner Smoke

Status: Next

Goal:

Complete owner smoke for the deployed V0.8.2 Cloud build, then move to internal trial if normal Word Generate and small Update both pass.

Focus areas:

- Owner normal Word Generate smoke
- Owner small Update smoke
- Internal trial readiness

### V0.9 Feedback Loop

Status: Future

Goal:

Collect real user feedback from V0.8.2 internal trial usage, classify badcases, and turn them into evaluation-backed optimization tasks.

Focus areas:

- Input format badcases
- Knowledge coverage and granularity badcases
- Agent answerability and scope badcases
- Dynamic FAQ optimization
- Color/exterior extraction
- Reliability hardening beyond empty-response retry

### End-to-End Performance Benchmark

Status: Future

Continue measuring production workloads after cloud deployment or additional local acceptance.

### Post-release Planning

Status: Future

Goal:

Plan V0.9 based on real user acceptance and production badcases.

## Deferred Work

- Facts non-determinism and granularity stability
- Chunked Facts quality improvement
- Adaptive Facts routing
- QC Rule First routing optimization
- Targeted Semantic Judge for low-confidence or complex cases if needed
- Embedding or vector search
- QC concurrency
- Facts prompt changes
- Batch size experiments
- Version History
- Incremental Update history
- Dynamic policy lifecycle
- UI detail polish
- Official website/source-material entry
- Account system
- Database persistence
- Task history center
