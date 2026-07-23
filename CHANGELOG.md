# AutoRAG-Studio Changelog

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
