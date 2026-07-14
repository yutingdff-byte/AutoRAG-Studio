# AutoRAG-Studio Project Context

Version: V0.6.6

Status: V0.6 Stable

Last Update: 2026-07-14

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

- `parser/`: docx, xlsx, pdf, txt parsing
- `agents/fact_agent.py`: fact extraction and information gaps
- `agents/rag_agent.py`: RAG knowledge generation
- `agents/qc_agent.py`: quality checks
- `generator/excel_generator.py`: static/dynamic Excel export
- `app.py`: Streamlit review console
- `prompts/`: Step1, Step2, Step3 prompt rules
- `schemas/`: export schema reference

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

## 6. Known Constraints

- Image parsing is reserved but not active in the production flow.
- PPT parsing is not implemented.
- No database, user permission system, project management, or version management yet.
- QC is advisory and can still require manual business review.
- Tests are mainly regression and smoke checks, not a complete automated test suite.

## 7. Next Phase

V0.7 will focus on knowledge update mode:

1. Upload old knowledge base plus new policy material.
2. Automatically detect added, changed, and expired policy knowledge.
3. Update the price policy knowledge base without regenerating all static knowledge.

Future roadmap:

1. Image material parsing.
2. QC-assisted fixing where users choose to accept or ignore suggestions.
