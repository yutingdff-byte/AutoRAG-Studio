# AutoRAG-Studio Roadmap

Current Stable Version: V0.6.6

Date: 2026-07-14

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

## V0.7 - Knowledge Update Mode

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

## V0.8 - Multimodal Material Parsing

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
