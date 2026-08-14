# AutoRAG-Studio Changelog

## V0.8.1 - Complex Excel Matrix and Evaluation Reliability

Date: 2026-08-14

Status: Internal Trial Release

### Added

- Added Excel Column-oriented Vehicle Matrix Parser for files where attributes are rows and vehicle versions are columns.
- Added deterministic transposition from complex Excel matrix files into complete Vehicle Record blocks before Facts/RAG.
- Added RAG Empty Response Retry Once for failed batch reliability while preserving fail-fast behavior when retry also fails.
- Added RAG Coverage Evaluator V2 with separate Answerability Coverage and Independent FAQ Coverage metrics.

### Changed

- Release Gate now uses Answerability Coverage as the hard gate instead of independent FAQ count.
- Independent FAQ Coverage is retained as an optimization metric for Step2 FAQ granularity backlog.
- Complex Excel validation now distinguishes evaluator false negatives from true RAG answerability gaps.

### Fixed

- Fixed Excel matrix parsing where row attributes and column vehicle versions were previously misread as ordinary tables.
- Fixed transient empty RAG batch responses causing full pipeline failure without a controlled recovery attempt.
- Fixed RAG coverage evaluator false negatives such as `Price 5/41` and dynamic `0/41` when usable RAG answers existed.

### Validation

- Full regression: `213 passed, 2 skipped`.
- Complex Excel parser validation:
  - Orientation: `COLUMN_ORIENTED_VEHICLE_MATRIX`
  - Material chars: 49,861
  - Vehicle Records: 41
  - Series: 13
  - Price Records: 41
- Complex Excel Facts/RAG validation:
  - Facts: 123
  - RAG: 207
  - RAG batches: 5
  - Failed batches: 0
- Evaluator V2 Answerability Coverage:
  - Price: 41/41
  - Cash: 41/41
  - Trade-in: 35/41
  - Finance: 36/41
  - Benefit: 39/41
  - Activity: 40/41

### Known Backlog

- Dynamic FAQ granularity optimization, especially independent Cash, Trade-in, and Finance FAQs.
- Color and exterior appearance extraction improvements in Step1 Facts.
- Retry policy expansion for 429, timeout, and connection errors.

## V0.8.0 - Update Closed Loop Final Release

Date: 2026-08-12

Status: Final Release

### Added

- Released the complete Update mode production loop: Historical Knowledge + New Documents -> Restore -> Facts/RAG -> Diff V0.2 -> Complex Relation Grouping -> Exception Review -> Merge -> Exact Duplicate Cleanup -> Export Quality Gate -> Dual Excel Export.
- Added historical restore for standard AutoRAG Excel exports and system-standard Word knowledge files.
- Added deterministic system-standard Word restore for:
  - Schema A: `车型 / 问题 / 答案`
  - Schema B: `意图名称1 / 意图描述1 / 参考内容1`
- Added automatic restore routing, including AI fallback for non-standard Word files when deterministic restore is insufficient.
- Added IMAGE_DOMINANT_WORD handling for new source materials: embedded Word images are extracted, parsed with the existing Vision capability, then sent through the normal Facts/RAG pipeline.
- Added Diff V0.2 with intent normalization, model normalization, candidate matching, candidate recall, numeric normalization, and complex relation grouping.
- Added Exception Review, deterministic Merge, and Update dual Excel export using the existing Generate Excel schema.
- Added exact duplicate cleanup between Merge and Export.

### Changed

- Simplified Update into a production workflow: upload materials -> processing complete -> scope summary -> change summary -> exception handling if needed -> generate new knowledge base -> download Excel.
- ADDED knowledge is automatically included in the new knowledge base.
- Clear 1:1 UPDATED knowledge automatically replaces the matched old knowledge.
- UNCHANGED knowledge is automatically retained.
- Complex or uncertain relations keep the safe default of adding new knowledge while keeping old knowledge unless the user explicitly chooses replacement.
- Single Review is restricted to exactly one Old item plus one New item with a known relation that cannot be safely auto-replaced.
- Dynamic knowledge such as price, finance, benefits, promotions, and marketing policies is auto-updated when Diff determines a safe 1:1 update.

### Fixed

- Fixed Streamlit session state and rerun stability across Generate and Update.
- Fixed Generate internal navigation so section filters no longer cause multiple panels to render.
- Fixed raw HTML leakage on the Home page.
- Fixed lifecycle QC false positives where limited-time benefits involving warranty, service, traffic, and intelligent-driving content were incorrectly treated as static.
- Fixed Single Review cases where only New knowledge existed without an Old candidate.
- Fixed exact duplicate knowledge entering final production Excel.
- Fixed oversized Facts chunk splitting for experimental chunked Facts mode.

### Performance

- Production default keeps `FACTS_MODE=single`, `RAG_MAX_CONCURRENCY=2`, and `QC_MODE=full`.
- TASK7 RAG benchmark:
  - `RAG_MAX_CONCURRENCY=1`: 426.05s
  - `RAG_MAX_CONCURRENCY=2`: 177.89s
  - Wall-time reduction: 58.25%
  - Speedup: about 2.40x
  - Requests: 4 -> 4
- TASK10 final Generate validation:
  - Old baseline: about 807.78s
  - V0.8 final: 465.41s
  - Total wall-time reduction: 42.38%

### Validation

- Generate E2E release validation:
  - Parser: 0.81s
  - Facts: 230.85s
  - RAG: 122.25s
  - QC: 111.32s
  - Excel: 0.16s
  - Facts: 49
  - RAG: 68
  - Exportable: 68
- Update E2E release validation:
  - Old Knowledge: 1136
  - New Knowledge: 68
  - ADDED: 39
  - UPDATED: 10
  - UNCHANGED: 1126
  - REVIEW_REQUIRED: 19
  - Complex Groups: 7
  - Single Reviews: 0
  - Final Clean Knowledge: 1193
  - Exportable Knowledge: 1193
- Facts Coverage Release Gate:
  - Result: PASS WITH MINOR BACKLOG
  - Same 12081-character input, `FACTS_MODE=single`, `deepseek-v4-flash`, temperature 0.2
  - TASK9 Single: 102 Facts
  - TASK10: 49 Facts
  - Canonical model coverage: 11/11
  - Price coverage: 6/6
  - Finance coverage: 13/13
  - Source numeric signal missing: 0
  - Main difference: MERGED / SPLIT_DIFFERENTLY, not a release blocker.

### Experimental

- `FACTS_MODE=chunked` remains experimental and is not the production default. It showed about 27% wall-time improvement in one benchmark, but Fact granularity and scope stability are not yet sufficient for default rollout.
- `QC_MODE=rule_first` remains experimental and is not the production default. On the saved marketing-policy sample, 78/82 knowledge items were still routed to LLM QC, so the current performance value is limited.
- Targeted Semantic Judge is not included in V0.8.0.
- Cloud deployment is not part of this release task.

## V0.8.0-rc1 - Update Closed Loop and Performance Baseline

Date: 2026-08-12

Status: Release Candidate

### Added

- Added complete Update mode workflow: Historical Knowledge + New Documents -> Restore -> Unified Knowledge -> Diff -> Complex Relation Grouping -> Exception Review -> Merge -> Exact Duplicate Cleanup -> Export Quality Gate -> Dual Excel Export.
- Added historical knowledge restore for standard Excel and Word files.
- Added deterministic system-standard Word restore for:
  - Schema A: `车系 / 问题 / 答案`
  - Schema B: `意图名称1 / 意图描述1 / 参考内容1`
- Added automatic restore format detection so users do not choose Fast or Deep restore modes.
- Added IMAGE_DOMINANT_WORD support: embedded Word images are extracted, parsed through the existing Vision capability, then sent through the normal Facts/RAG flow.
- Added Diff V0.2 with intent normalization, model normalization, candidate recall, numeric normalization, GENERAL/DETAIL relation handling, and safer model matching.
- Added Complex Relation Grouping for `GENERAL_TO_DETAIL`, `DETAIL_TO_GENERAL`, `ONE_TO_MANY`, `MANY_TO_ONE`, and `AMBIGUOUS_RELATION`.
- Added Exception Review and deterministic Merge for Update mode.
- Added exact duplicate cleanup before Update export.
- Added controlled RAG batch concurrency with `RAG_MAX_CONCURRENCY=2`.
- Added experimental Rule First QC framework with `QC_MODE=full` and `QC_MODE=rule_first`.

### Changed

- Simplified Update UX into: upload materials -> processing result -> scope summary -> change summary -> exception handling when needed -> generate new knowledge base -> download Excel.
- ADDED knowledge is automatically accepted into the new knowledge base.
- UPDATED knowledge automatically replaces the matched old knowledge.
- UNCHANGED knowledge is retained.
- Complex or uncertain relations enter Exception Review; default handling adds new knowledge while keeping old knowledge.
- Dynamic lifecycle handling now distinguishes knowledge lifecycle from content topic.
- Diff detail tables and technical fields are hidden from the default user flow.

### Fixed

- Fixed Streamlit session state and rerun issues in Generate and Update.
- Fixed Generate internal section navigation so only the active section renders.
- Fixed raw HTML leakage on the Home page.
- Fixed lifecycle QC false positives for limited-time benefits involving warranty, service, traffic, and intelligent-driving content.
- Fixed Single Review cases where only New knowledge existed without an Old candidate.
- Fixed exact duplicate knowledge entering final production Excel.

### Performance

- RAG benchmark on saved 101 Facts / 4 batches:
  - `RAG_MAX_CONCURRENCY=1`: 426.05s
  - `RAG_MAX_CONCURRENCY=2`: 177.89s
  - Wall-time reduction: 58.25%
  - Speedup: about 2.40x
  - Requests: 4 -> 4
  - Fact coverage: 101/101 -> 101/101
  - Missing Facts: 0 -> 0
  - High-value dynamic missing: 0 -> 0

### Notes

- `RAG_MAX_CONCURRENCY=2` is the RC1 default, with `1` retained as a rollback setting.
- `QC_MODE=full` remains the RC1 production default.
- `QC_MODE=rule_first` is experimental. Current offline routing on a marketing-policy sample routed 78/82 knowledge items to LLM QC, so performance value is limited for that scenario.
- Generate business logic, prompts, Excel schema, and export quality gate remain unchanged.

## V0.8.0-dev - Rule-based Knowledge Change Detection

Date: 2026-07-29

Status: In development

### Added

- Added rule-based Diff data models, including `ChangeType`, `MatchMethod`, `ReviewReason`, `MatchResult`, `DiffResult`, and `DiffRunResult`.
- Added Knowledge normalizer for question, answer, number, topic, and signature normalization.
- Added automatic update scope detection from new `KnowledgeItem[]`.
- Added candidate builder with normalized-question, model, category, knowledge-type, and signature indexes.
- Added conservative rule matcher with normalized-question and structured matching.
- Added change detector for unchanged answers, price or number changes, answer changes, and possible deprecation evidence.
- Added unified Diff Engine entrypoint: `compare(old_items, new_items)`.
- Added Update page generation of new knowledge through the existing Parser -> Fact Agent -> RAG Agent -> Knowledge Adapter chain.
- Added Update page Diff statistics and result tabs for all, added, updated, unchanged, and review-required items.
- Added Diff unit tests for normalizer, scope detector, candidate builder, matcher, change detector, and engine scenarios.

### Notes

- First-level page statuses are limited to added, updated, unchanged, and review required.
- Possible deprecation is a review reason, not an automatic deletion state.
- Old knowledge is kept by default. New material not mentioning old knowledge does not mark it invalid.
- LLM Semantic Judge, Review actions, Merge, and Update Excel Export remain out of scope.
- Generate business logic remains frozen.

## V0.8.0-dev - Knowledge Restore and Parser Foundation

Date: 2026-07-26

Status: Completed

### Added

- Added `knowledge.adapter` to convert RAG JSON and restored Excel rows into `KnowledgeItem` objects.
- Added `knowledge.excel_restore` for restoring standard AutoRAG Excel exports into unified knowledge objects.
- Added `knowledge.word_restore` for restoring Word knowledge material through the existing Parser -> Fact Agent -> RAG Agent chain.
- Added `knowledge.restore_manager` as the Update mode restore entrypoint.
- Added Update page restore statistics and a restored knowledge preview table.
- Added restore unit tests covering Excel restore, Word restore via existing Agent interfaces, and restore manager mixed results.

### Changed

- Expanded `KnowledgeItem` with `normalized_question` and internal `knowledge_type` for future Diff inputs.
- Update mode now restores history knowledge files before the future Diff step.

### Notes

- Diff Engine, Review, Merge, and Update Export are still out of scope.
- Generate business logic remains frozen.
- No changes were made to prompts, parser behavior, Agent logic, Excel export logic, or export quality gate logic.

## V0.8.0-dev - Architecture and UI Foundation

Date: 2026-07-26

Status: Completed

### Added

- Added a dual-mode home page for Generate and Update workflows.
- Added `pages/` modules for home, Generate, and Update page rendering.
- Added shared `ui/` styles and components for headers, steps, feature cards, metrics, file cards, and footer.
- Added V0.8 placeholder packages for `knowledge/`, `diff/`, `review/`, `merge/`, and `exporter/`.
- Added an initial `KnowledgeItem` dataclass as the future unified knowledge object foundation.
- Added an Update page skeleton with history material upload, new material upload, Diff preview, and Review preview placeholders.

### Changed

- Refactored `app.py` into a lightweight Streamlit entrypoint for page setup, global styling, navigation, and routing.
- Wrapped the existing Generate UI in `pages/generate_page.py` while preserving the existing Generate pipeline calls.
- Lightly improved Generate page readability with a page header, step navigation, and uploaded file cards.
- Disabled Streamlit's automatic sidebar page navigation so the app-level navigation remains the single source of truth.

### Notes

- Generate business logic remains frozen.
- No changes were made to prompts, Agent rules, parser behavior, Excel fields, Excel naming, static/dynamic splitting, or export quality gate logic.
- Update mode is a UI and architecture foundation only. Knowledge Parser, Diff, Review, Merge, and Update Export are not implemented in this milestone.

## V0.7.3 - Cloud Ready

Date: 2026-07-23

Status: Completed

### Added

- Added Streamlit Community Cloud deployment documentation in `DEPLOY.md`.
- Added project quick-start documentation in `README.md`.
- Added `PROJECT_CLEANUP_REPORT.md` for project cleanup classification.
- Added `runtime.txt` with `python-3.11`.
- Added `.streamlit/config.toml` with upload size configuration.
- Added `.streamlit/secrets.toml.example` for cloud Secrets setup.
- Added unified configuration helper for Streamlit Secrets, environment variables, and local `.env`.

### Changed

- DeepSeek and Qwen configuration now read in this order:
  1. Streamlit Secrets
  2. System environment variables
  3. Local `.env`
- `requirements.txt` now uses conservative production version ranges.
- `.gitignore` now explicitly excludes local Streamlit secrets, Python bytecode, pytest cache, logs, temp files, and backup files.

### Fixed

- Avoids Streamlit startup failure when Secrets are not yet configured by creating the DeepSeek client lazily during model calls.
- Keeps Qwen Vision image parsing compatible with Streamlit Cloud Secrets.

### Cleanup

- Removed local Python cache directories only.
- Kept historical `output/` runs local and ignored for regression reference.

### Notes

- Generate business behavior remains based on V0.7.2 Stable.
- No changes were made to prompt rules, static/dynamic classification, Excel fields, Excel naming, or export quality gate logic.
- Streamlit Cloud code adaptation is complete, but actual cloud deployment must be performed from the user's Streamlit account.

## V0.7.2 - Generate Stable Quality Gate

Date: 2026-07-18

Status: Completed

### Fixed

- Added a unified export quality gate for RAG knowledge.
- `need_confirm`, `missing`, `conflict`, `inference`, invalid, empty-answer, and missing-answer RAG items no longer enter the formal Excel files.
- RAG post-processing marks blocked items with `exportable: false` and an `export_block_reason`.
- Excel export performs the same quality gate again before writing rows.
- Existing effective knowledge now wins over contradictory missing-answer RAG items for the same model and topic.
- Fixed QC static/dynamic false positives for fixed vehicle benefits such as warranty, roadside assistance, fixed traffic packages, and standard driving-assistance capability.
- Dynamic classification mismatch now requires stronger policy signals such as limited time, order condition, subsidy, deduction, finance rate, or policy period.
- Knowledge Review Center normalizes mixed string/object review data so model, item, reason, and suggestion are no longer blank.
- Added TTS normalization for RMB price symbols, yuan prices, percentages, 10G traffic wording, voltage, and common driving-assistance abbreviations.
- Added lightweight `model_normalized` support for future V0.8 matching while keeping Excel display names unchanged.

### Verified

- Offline regression on `output/20260718_161941` excludes `RAG-099` through `RAG-104`.
- Static Excel rows reduced from 84 to 78; dynamic Excel remains 54.
- `RAG-063` no longer triggers static/dynamic QC mismatch.
- Review item normalization produced no blank model/item/suggestion fields in the regression set.

### Notes

- This release does not implement knowledge update mode.
- This release does not implement QC auto-fix Agent Loop.
- PPT parsing remains out of scope.

## V0.7.1 - Stable Business Optimization

Date: 2026-07-16

Status: Completed

### Added

- Knowledge Review Center now separates:
  - 需要人工关注
  - 需要关注更新
- QC detects mixed policy periods for the same model and category.
- Fact prompt and post-processing support:
  - `source_file`
  - `policy_period`
  - `effective_date`
  - `expire_date`
- RAG post-processing normalizes TTS-sensitive units and abbreviations.
- Upload area shows max file count, image size guidance, and selected file count.
- Streamlit widgets and dataframes now use more stable keys.

### Fixed

- Multi-model Excel output no longer uses the first model name as the project name.
- Same-brand multi-model output uses the brand name.
- Avoids duplicated brand/model names such as `阿维塔阿维塔06T`.
- QC no longer treats numeric formats such as `15.6英寸`, `7.1.4声场`, or `30%-80%` as policy dates.
- Information gap display now uses structured model/category/module coverage checks before showing missing items.

### Notes

- This release does not implement knowledge update mode.
- This release does not implement QC auto-fix loops.
- PPT parsing remains out of scope.

## V0.7.0 - Image Parser MVP

Date: 2026-07-14

Status: In development

### Added

- Qwen-VL-Plus image parser MVP.
- Supported image formats: PNG, JPG, JPEG, WEBP.
- Image files are converted to Base64 Data URLs and sent through an OpenAI-compatible Qwen client.
- Image parsing returns plain text Material for the existing DeepSeek Fact/RAG/QC pipeline.
- Streamlit upload supports mixed files: Excel, Word, PDF, TXT, and images.
- Added parsing preview with file name, file type, status, and recognized text preview.
- Added image parsing statistics to `run_info.json`.
- Added `.env.example` entries for Qwen Vision configuration.

### Constraints

- No OCR coordinate display.
- No image cropping or correction.
- No PPT file parsing.
- No model router.
- No knowledge update mode in this release.

## V0.6.6 - V0.6 Stable

Date: 2026-07-14

Status: Completed

### Fixed

- Reduced QC false positives for static/dynamic classification.
- QC no longer treats fixed vehicle services or capabilities as dynamic only because answers contain words such as free, gifted, or lifetime.
- Warranty, three-electric warranty, roadside assistance, car networking traffic, entertainment traffic, ADS packages, intelligent driving functions, cockpit capabilities, and basic after-sales protection remain static when they are fixed services or vehicle capabilities.
- Static/dynamic QC now only reports a mismatch when static knowledge contains clear dynamic policy signals such as limited-time activity, order condition, subsidy, finance rate, discount, deduction, option waiver, validity period, or explicit activity dates.

### Verified

- Avita regression data no longer reports the specified static RAG items as static/dynamic classification errors.
- Synthetic dynamic-policy cases still trigger the static/dynamic mismatch check when they are incorrectly marked as static.
- `agents/qc_agent.py` passes syntax check.

### Stable Scope

V0.6 is now frozen as the stable baseline.

Completed scope:

- Static/dynamic knowledge split
- Brand/model/trim vehicle hierarchy
- Model-level aggregation
- Version-difference generation
- Dual Excel export
- Streamlit review console
- Knowledge review center
- QC report display and rule-based checks
- Price overview knowledge generation

## V0.6.5

### Added

- Knowledge Review Center with information missing, conflict, AI inference, and dynamic notice sections.
- Overview metrics for knowledge review and QC issues.
- Model-level price overview generation.
- QC check for missing model-level price overview.

## V0.6.4

### Added

- Streamlit review console.
- Static knowledge page.
- Dynamic knowledge page.
- Information gap, confirmation, QC, and download pages.
- Productized Excel names:
  - 车型配置知识库
  - 价格政策知识库

## V0.6.3

### Added

- Model-level knowledge priority.
- Version differences generated only when necessary.
- Duplicate and over-split knowledge checks.

## V0.6.2

### Added

- Brand/model/trim vehicle hierarchy.
- Excel columns changed to 车型, 版本, 问题, 回答, 分类.
- RAG answer quality optimization for AI outbound-call scenarios.

## V0.6.1

### Added

- Static/dynamic knowledge classification.
- Dual Excel output.
- Simplified import-oriented Excel fields.

## V0.5.7

### Added

- Run ID mechanism.
- Isolated output directory.
- Run metadata.
- Streamlit result isolation.

## V0.5.6

### Added

- Streamlit web demo.
- Parser factory.
- TXT, DOCX, XLSX, PDF parsing.
- Step1 Fact Agent.
- Step2 RAG Agent.
- Step3 QC Agent.
- Excel generation.
