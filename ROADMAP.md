# AutoRAG-Studio Roadmap

Current Stable Version: V0.7.3 Cloud Ready

Current Development Version: V0.8.0-dev

Date: 2026-07-26

## Product Direction

AutoRAG-Studio is evolving from an Excel generation tool into an AI knowledge generation, review, and update platform.

Core scenario:

```text
AI outbound call
-> lead qualification
-> store visit invitation
-> human sales handoff
```

## V0.6 Stable - Completed

Status: Completed and frozen

Stable tag: `v0.6.6`

Completed capabilities:

- Static and dynamic knowledge split
- Brand/model/trim vehicle hierarchy
- Model-level knowledge aggregation
- Version-difference knowledge generation
- Static and dynamic dual Excel export
- Streamlit review console
- Knowledge review center
- Dynamic knowledge reminders
- QC report display
- Price overview knowledge generation
- QC false-positive reduction for fixed services and vehicle capabilities

V0.6 output:

- 车型配置知识库
- 价格政策知识库
- Review console for gaps, conflicts, AI inference, dynamic reminders, and QC suggestions

## V0.7.0 - Image Material Recognition MVP

Status: In development

Goal:

Support automotive image materials as input without changing the existing Fact/RAG/QC agents.

Supported formats:

- PNG
- JPG
- JPEG
- WEBP

Model responsibilities:

- Qwen-VL-Plus: image to structured plain text Material
- DeepSeek-V4-Flash: Fact extraction, RAG generation, QC

Out of scope:

- OCR coordinates
- Image editing or generation
- Image cropping and correction
- PPT file parsing
- Model router
- Knowledge update mode

## V0.7.1 - Stable Business Optimization

Status: Completed

Goal:

Make generated knowledge more suitable for real AI outbound-call delivery.

Completed:

- Simplified knowledge review center.
- Fixed multi-model Excel naming.
- Added policy-period conflict QC.
- Reduced QC date false positives.
- Improved structural coverage checks for information gaps.
- Added source file and policy period guidance.
- Improved unit and abbreviation pronunciation for TTS.
- Added upload guidance for file count and image size.

## V0.7.2 - Generate Stable Quality Gate

Status: Completed

Goal:

Freeze the Generate module by preventing unsafe or contradictory knowledge from entering formal outbound-call Excel files.

Completed:

- Missing, unconfirmed, invalid, and conflict/inference review RAG items are blocked from Excel export.
- RAG post-processing and Excel export share the same exportability rules.
- Contradictory missing-answer RAG is blocked when the same model and topic already has effective knowledge.
- Blocked knowledge is moved into the Knowledge Review Center for human attention.
- Fixed static/dynamic QC false positives for fixed benefits and vehicle capabilities.
- Kept real limited-time policy signals detectable.
- Normalized Knowledge Review Center rows so model, item, reason, and suggestion are not blank.
- Added TTS cleanup for RMB prices, percentages, voltage, traffic package wording, and common abbreviations.
- Added lightweight model normalization for future matching.

## V0.7.3 - Cloud Ready

Status: Completed

Goal:

Prepare the frozen Generate module for Streamlit Community Cloud deployment without changing business output behavior.

## V0.8.0 Milestone 1 - Architecture and UI Foundation

Status: Completed

Goal:

Turn AutoRAG-Studio into a two-mode platform foundation without changing the frozen Generate business output.

Scope:

- Add a Home page with Generate and Update mode entries.
- Refactor Streamlit app structure into page modules and shared UI components.
- Keep Generate workflow, prompts, Agents, parser logic, Excel output, and export quality gate unchanged.
- Add an Update page skeleton for future Knowledge Parser, Diff, Review, Merge, and Update Export.
- Add initial Knowledge Object definitions for later adapters.

Out of scope:

- Real historical knowledge parsing.
- Knowledge Diff.
- Review decision persistence.
- Merge.
- Update-mode Excel export.
- Embeddings, vector database, account system, or task history.

## V0.8.0 Milestone 2 - Knowledge Restore and Parser Foundation

Status: Completed

Goal:

Give Update mode a unified historical knowledge restore layer so the future Diff Engine receives `KnowledgeItem[]` only.

Scope:

- Standard AutoRAG Excel export -> KnowledgeItem.
- Word history knowledge -> existing Parser -> existing Fact Agent -> existing RAG Agent -> KnowledgeItem.
- RAG JSON -> KnowledgeItem adapter.
- Restore Manager for file-type dispatch.
- Update page restore statistics and preview.

Out of scope:

- Diff Engine.
- Embedding or similarity matching.
- Review decisions.
- Merge.
- Update-mode Excel export.

## V0.8.0 Milestone 3A - Rule-based Knowledge Change Detection

Status: In development

Goal:

Compare old and new `KnowledgeItem[]` with conservative rule-based matching and change detection.

Scope:

- Automatic update scope detection.
- Candidate building without full Old x New comparison.
- Normalized-question and structured rule matching.
- Change detection for format-only unchanged answers, price changes, number changes, answer changes, and explicit possible deprecation evidence.
- Four page statuses: added, updated, unchanged, and review required.
- Update page Diff statistics and preview tabs.

Out of scope:

- LLM Semantic Judge.
- Embedding and vector database.
- Review actions.
- Merge Engine.
- Update-mode Excel export.
- Automatic deletion or overwrite of old knowledge.

Completed:

- Streamlit Cloud deployment documentation.
- Python runtime pin.
- Production dependency version ranges.
- Streamlit Secrets support.
- Local `.env` compatibility for development.
- Minimal Streamlit config.
- Project cleanup classification.
- Low-risk local cache cleanup.
- README and data safety notes.

## V0.8 - Knowledge Update Mode

Status: Next

Goal:

Support partial updates for dynamic policy knowledge without regenerating the full knowledge base.

Planned workflow:

```text
Upload old knowledge base
+ Upload new policy material
-> Detect changes
-> Generate update suggestions
-> Export updated price policy knowledge base
```

Planned capabilities:

- Identify added policies
- Identify changed policies
- Identify expired policies
- Preserve unchanged static knowledge
- Generate update diff report
- Export updated dynamic knowledge

## V0.8.x - Multimodal Material Parsing Enhancement

Status: Planned

Planned capabilities:

- Image material parsing
- Campaign poster parsing
- Rights and benefits image extraction
- PPT parsing after image support is stable

## V0.9 - QC-Assisted Fixing

Status: Planned

Goal:

Allow users to review QC suggestions and choose whether to accept or ignore AI-assisted fixes.

Planned capabilities:

- Suggested rewrite for overlong answers
- Suggested split for mixed-intent FAQ
- Suggested category correction
- User accept/ignore workflow
- Review history

## V1.0 - Knowledge Operations Platform

Status: Long-term

Planned capabilities:

- Project management
- Knowledge base version management
- Update history
- Multi-user collaboration
- Knowledge lifecycle operations
