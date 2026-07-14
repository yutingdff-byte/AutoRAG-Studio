# AutoRAG-Studio Changelog

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
