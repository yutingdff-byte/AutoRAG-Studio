# AutoRAG-Studio Roadmap

Current Stable: `v0.8.2`

Current Branch: `main`

Date: 2026-08-23

## Product Direction

AutoRAG-Studio is evolving from a one-time Excel generation tool into an AI knowledge generation, review, and continuous-update platform.

Core scenario:

```text
AI outbound call
-> lead qualification
-> store visit invitation
-> human sales handoff
```

## Active Reliability Track

### TASK14 Excel Persistence and Recovery MVP

Status: Local implementation completed; Cloud durable-storage validation pending

Completed locally:

- Persist completed Generate and Update Excel outputs through a shared task-store interface.
- Recover downloads by random recovery code.
- Attempt same-browser auto-recovery through a minimal browser-side token.
- Keep recovery separate from knowledge generation and quality gates.

Pending before claiming Cloud recovery:

- Choose and configure a private object-store backend such as Cloudflare R2, AWS S3, or OSS.
- Store task manifests and Excel files outside Streamlit Cloud local disk.
- Validate recovery after Streamlit Cloud redeploy/restart.
- Confirm retention cleanup through object-store lifecycle policy or an equivalent maintenance command.

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
- Owner smoke completed:
  - Normal Word Generate: PASS
  - Small Update: PASS
  - V0.8.2 status: READY FOR INTERNAL TRIAL

### Known Backlog

- Complex matrix performance remains around 40 minutes in the 41-vehicle benchmark.
- Dynamic FAQ granularity optimization.
- Color/exterior color Facts coverage.
- Retry policy expansion for 429, timeout, and connection errors.

## Next Planned Work

### ZIP Image Import MVP

Status: Release closeout

Scope validated locally:

- Small ZIP image import.
- One-level inner ZIP image extraction.
- Folder/group isolation for two vehicle资料 groups.
- Large image preprocessing path.
- Generate pipeline through Material, Facts, RAG, QC, and dual Excel export.
- Safety filtering for unsupported deterministic image-derived knowledge.

Release-gate output:

```text
Sample: gate_c_two_groups.zip
Latest source Run ID: 20260919_145648
Formal Excel after safety gate: 21 rows
Confirmed high-risk formal-export issues: 0
```

Not yet validated:

- Full original ZIP around 195 MB.
- 15 groups / 24 images / 9 inner ZIP files.
- Cloud upload size, runtime, memory, temp storage, cost, and full knowledge quality.
- Broad key-fact coverage across all customer images.

#### P1: Image Key Fact Coverage

- Improve extraction of clear source facts such as trunk/cargo capacity `560L-1485L`.
- Preserve current safety principle: omissions are acceptable during MVP, unsupported deterministic exports are not.

#### P1: Image Table and Parameter Binding

- Reduce numeric misreads.
- Reduce adjacent table parameter contamination.
- Reduce engine/transmission parameter binding errors.
- Reduce vehicle/version scope errors.
- Reduce incomplete full-series price ranges.

#### P1: Full ZIP Scale and Reliability

- Validate the original 195 MB customer ZIP separately.
- Measure upload limits, runtime, memory, temp storage, model calls, cost, cross-group isolation, and final knowledge quality.

#### P2: ICCOA Carlink Coverage

- Trace Image -> Material -> Facts -> RAG -> QC -> Excel.
- Determine whether the missing knowledge is a Material, Facts, RAG, or export issue.

#### P2: Deduplication and Expression Quality

- Reduce low-value repeated price questions.
- Reduce unsupported subjective driving, comfort, and marketing statements.

#### P2: Knowledge Coverage Evaluation

- Build a fixed image test set and key-fact checklist.
- Track wrong exports, correct knowledge retention, key fact omissions, and vehicle/version/parameter binding separately.

#### P2: Review and Traceability UX

- Improve source image lookup.
- Improve Material/Facts/RAG traceability.
- Show filtered knowledge and filter reasons.
- Improve manual confirmation workflow.

### Internal Trial

Status: Next

Goal:

Collect real user feedback from V0.8.2 internal trial usage and classify badcases before defining V0.9 scope.

Focus areas:

- Invite 3-5 internal users
- Collect Generate and Update feedback
- Record reproducible badcases
- Accumulate about 10-20 useful feedback items
- Run feedback review
- Define V0.9 scope from evidence

### V0.9 Discovery

Status: Future

Goal:

Turn internal trial evidence into prioritized V0.9 optimization tasks.

Focus areas:

- Input format badcases
- Knowledge coverage and granularity badcases
- Agent answerability and scope badcases
- Dynamic FAQ optimization
- Color/exterior extraction
- Reliability hardening beyond empty-response retry

Do not open prompt tuning, concurrency changes, batch-size changes, semantic dedup, color optimization, or retry expansion without real feedback evidence.

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
