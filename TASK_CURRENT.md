# AutoRAG-Studio Current Task

Version: V0.7.2

Status: Completed

Milestone: V0.7.2 Stable

## Completed In V0.6

- TASK-001: Run ID and isolated output directory
- TASK-002: Engineering hygiene fixes
- V0.6.1: Static/dynamic knowledge classification and dual Excel export
- V0.6.2: Brand/model/trim vehicle hierarchy
- V0.6.3: Model-level knowledge aggregation and version-difference generation
- V0.6.4: Streamlit review console and productized Excel naming
- V0.6.5: Knowledge review center and price overview optimization
- V0.6.6: Review console polish, price knowledge optimization, and QC static/dynamic false-positive fix

## Current Stable State

V0.7.2 is the current stable Generate baseline.

The system can:

- Parse common automotive material files
- Extract facts
- Generate AI outbound-call RAG knowledge
- Split static vehicle configuration knowledge and dynamic price policy knowledge
- Export two productized Excel files
- Display generated results in the review console
- Surface information gaps, conflicts, AI inference, dynamic reminders, and QC suggestions
- Block missing, unconfirmed, invalid, and contradictory no-information RAG from formal Excel export
- Keep blocked knowledge visible in the Knowledge Review Center
- Normalize common TTS-sensitive prices, units, percentages, and driving-assistance abbreviations

## Current Task

V0.7.2: RC bugfix and Generate quality gate stabilization.

Completed:

- Missing and need-confirm RAG items are excluded from formal Excel export.
- Contradictory missing-answer RAG is blocked when valid same-model same-topic knowledge exists.
- Excel export repeats the export quality gate as a safeguard.
- Fixed static/dynamic QC false positives for fixed benefits such as warranty, roadside assistance, fixed traffic packages, and standard driving-assistance capability.
- Knowledge Review Center normalizes string and object review data into model, item, reason, and suggestion fields.
- Added TTS cleanup for RMB prices, percentages, traffic package wording, voltage, and common driving-assistance abbreviations.
- Added `model_normalized` for future V0.8 matching while preserving Excel display names.

## Next Task

Start V0.8 knowledge update mode design.

## Future Tasks

1. Old knowledge base plus new policy material automatic update.
2. Image material parsing enhancement.
3. QC-assisted fixing with user accept/ignore choices.
