# AutoRAG-Studio Project Context

Version: V0.8.0-dev

Status: V0.8 Milestone 1 - Architecture and UI Foundation

Last Update: 2026-07-26

## 1. Project Goal

AutoRAG-Studio is a knowledge generation and review platform for enterprise Agent scenarios.

Current primary scenario:

- Automotive AI outbound calls
- Lead qualification
- Store visit invitation
- Handoff to human sales

The product is not designed for online transaction closing. Final landing price, financing approval, discount stacking, and store-specific commitments are handled by human sales.

## 2. Current Architecture

Pipeline:

```text
File Upload
-> Parser
-> Step1 Fact Agent
-> Step2 RAG Agent
-> Step3 QC Agent
-> Excel Generator
-> Streamlit Review Console
```

Main modules:

- `parser/`: docx, xlsx, pdf, txt, image parsing
- `agents/fact_agent.py`: fact extraction and information gaps
- `agents/rag_agent.py`: RAG knowledge generation
- `agents/qc_agent.py`: quality checks
- `generator/excel_generator.py`: static/dynamic Excel export
- `app.py`: Streamlit app setup, navigation, and page routing
- `pages/`: Home, Generate, and Update page renderers
- `ui/`: shared Streamlit styles and reusable UI components
- `knowledge/`: initial Knowledge Object definitions for future update mode
- `diff/`, `review/`, `merge/`, `exporter/`: V0.8 workflow placeholders
- `prompts/`: Step1, Step2, Step3 prompt rules
- `schemas/`: export schema reference

V0.8 Milestone 1 keeps the Generate business pipeline frozen and adds the platform foundation for two work modes:

- Generate: create a new knowledge base from source materials. This remains the stable production workflow.
- Update: future workflow for comparing old knowledge with new materials. In this milestone it is only a page skeleton and does not run Diff, Review, Merge, or Update Export.

## 3. Current Data Design

Vehicle hierarchy:

```json
{
  "brand": "",
  "model": "",
  "trim": ""
}
```

Knowledge lifecycle:

```text
static  -> vehicle configuration knowledge
dynamic -> price and policy knowledge
```

Final Excel output:

- `{brand}{model}_车型配置知识库.xlsx`
- `{brand}{model}_价格政策知识库.xlsx`

Excel columns:

- 车型
- 版本
- 问题
- 回答
- 分类

Internal JSON keeps richer fields for review and future update features:

- intent
- fact_refs
- confidence
- guardrails
- need_confirm
- review_type
- knowledge_type
- exportable
- export_block_reason
- model_normalized
- model_display_name

Formal Excel export is protected by a quality gate. Items are not exported when they are:

- `answer_type == "need_confirm"`
- `need_confirm == "是"`
- `review_type` in `missing`, `conflict`, or `inference`
- `knowledge_status` in `missing`, `unconfirmed`, or `invalid`
- empty answers or explicit missing-answer placeholders

## 4. V0.6 Completed Scope

V0.6 is complete and frozen as V0.6.6 Stable.

Completed:

- Static/dynamic knowledge classification
- Brand/model/trim vehicle hierarchy
- Model-level knowledge aggregation
- Version-difference knowledge generation
- Duplicate knowledge reduction
- AI outbound-call answer style optimization
- Dual Excel export
- Streamlit review console
- Knowledge review center
- QC checks for duplicate, range, answer length, intent granularity, price overview, and compliance risks
- QC static/dynamic false-positive fix for warranty, roadside assistance, traffic package, and vehicle capability knowledge

## 5. Current Review Console

Pages:

- 生成概览
- 车型配置知识
- 价格政策知识
- 知识检查中心
- QC报告
- 下载

Knowledge Review Center sections:

- 信息缺失
- 信息冲突
- AI推断
- 动态知识提醒

## 6. V0.7.0 Image Parser MVP

V0.7.0 adds image material recognition through Qwen-VL-Plus.

Supported image formats:

- PNG
- JPG
- JPEG
- WEBP

Model responsibilities:

- DeepSeek-V4-Flash: Fact extraction, RAG generation, QC
- Qwen-VL-Plus: image to Material text only

Image parsing flow:

```text
Image file
-> Qwen-VL-Plus
-> plain text Material
-> existing DeepSeek Fact/RAG/QC pipeline
```

Qwen configuration is read from `.env`:

- `QWEN_API_KEY`
- `QWEN_BASE_URL`
- `VISION_MODEL`

The parser uses local image bytes encoded as a Base64 Data URL. API keys and Base64 content are not written to run logs.

## 7. V0.7.1 Stable Optimization

V0.7.1 focuses on business usability for AI outbound-call knowledge bases.

Completed:

- Simplified the knowledge review center into:
  - 需要人工关注
  - 需要关注更新
- Improved multi-model Excel naming:
  - single model: model name
  - same brand with multiple models: brand name
  - multiple brands: 多品牌
- Fixed QC static/dynamic false positives caused by numeric formats such as `15.6`, `7.1.4`, and `30%-80%`.
- Added policy-period conflict detection for the same model and category.
- Added basic policy period fields to Fact output:
  - `policy_period`
  - `effective_date`
  - `expire_date`
- Added `source_file` guidance for source traceability.
- Added TTS-oriented RAG answer normalization for units and common driving-assistance abbreviations.
- Added upload guidance for file count and image size.

## 8. V0.7.2 Generate Stable Quality Gate

V0.7.2 fixes the release-candidate issues found in real Avita regression.

Completed:

- Missing or unconfirmed RAG items no longer enter formal Excel exports.
- Contradictory missing-answer RAG items are blocked when the same model and topic already has valid knowledge.
- Excel export repeats the quality gate as a final safeguard.
- Blocked knowledge remains visible in the Knowledge Review Center.
- Knowledge Review Center normalizes old string gaps and structured review objects into consistent fields:
  - review_type
  - model
  - item
  - reason
  - suggestion
- QC static/dynamic mismatch now avoids fixed-benefit false positives.
- Strong dynamic signals are still detected for limited-time orders, subsidies, deductions, finance rates, and policy periods.
- RAG answers receive additional TTS normalization for RMB prices, percentages, voltage, traffic packages, and driving-assistance abbreviations.
- `model_normalized` is added for future V0.8 matching while Excel continues to display `model`.

## 9. V0.7.3 Cloud Ready

V0.7.3 prepares AutoRAG-Studio for Streamlit Community Cloud without changing Generate business behavior.

Completed:

- Added Streamlit Cloud deployment guide.
- Added README quick start and safety notes.
- Added project cleanup report.
- Added `runtime.txt` with `python-3.11`.
- Added minimal `.streamlit/config.toml`.
- Added `.streamlit/secrets.toml.example`.
- Added unified config lookup:
  1. Streamlit Secrets
  2. Environment variables
  3. Local `.env`
- Kept `.env`, `.streamlit/secrets.toml`, `.venv`, `output`, generated Excel, caches, logs, and temp files out of Git.
- Removed only low-risk local Python cache directories.

V0.7.3 does not change:

- Fact extraction rules
- RAG generation strategy
- QC policy rules
- Export quality gate logic
- Excel naming
- Excel fields
- Static/dynamic split

## 10. Known Constraints

- Image parsing is available as a V0.7.0 MVP through Qwen-VL-Plus.
- PPT parsing is not implemented.
- No database, user permission system, project management, or version management yet.
- QC is advisory and can still require manual business review.
- Tests are mainly regression and smoke checks, not a complete automated test suite.
- V0.7.0 image parsing does not include OCR coordinates, image cropping, image correction, PPT parsing, or multimodal model routing.
- A single image is limited to 10MB in the MVP.
- Policy-period detection only reports mixed periods; it does not automatically delete or expire historical policy knowledge.
- V0.7.2 blocks unsafe export rows, but it does not automatically rewrite or repair them.
- V0.7.3 has not been deployed from this local environment because Streamlit Community Cloud access requires the user's account.

## 11. Next Phase

After V0.7.3 Cloud Ready stabilization, the next phase will focus on knowledge update mode:

1. Upload old knowledge base plus new policy material.
2. Automatically detect added, changed, and expired policy knowledge.
3. Update the price policy knowledge base without regenerating all static knowledge.

Future roadmap:

1. Old knowledge base plus new policy material automatic update.
2. Image material parsing enhancement.
3. QC-assisted fixing where users choose to accept or ignore suggestions.
