# AutoRAG-Studio Current Task

Version: V0.8.0-dev

Status: In Progress

Milestone: V0.8.0 Milestone 2 - Knowledge Restore & Parser Foundation

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

V0.7.3 Cloud Ready is the current deployable Generate baseline.

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
- Read model configuration from Streamlit Secrets, environment variables, or local `.env`
- Run with Streamlit Community Cloud-oriented runtime and dependency files

## Current Task

V0.8.0 Milestone 2: Knowledge Restore and Parser Foundation.

Completed in Milestone 1:

- Create a dual-mode Home page for Generate and Update.
- Refactor `app.py` into a lightweight setup and router.
- Move Generate page rendering into a dedicated page module while preserving business behavior.
- Add an Update page skeleton without implementing Knowledge Parser, Diff, Review, Merge, or Update Export.
- Add shared UI styles and components.
- Add initial Knowledge Object definitions for future adapters.

In progress:

- Restore standard AutoRAG Excel exports into `KnowledgeItem[]`.
- Restore Word history knowledge by reusing existing Parser -> Fact Agent -> RAG Agent.
- Convert generated RAG JSON into `KnowledgeItem[]` through a Knowledge Adapter.
- Add Restore Manager as the Update mode entrypoint.
- Show restored knowledge statistics and preview on the Update page.

Generate freeze rules:

- Do not change Fact extraction rules.
- Do not change RAG generation rules.
- Do not change QC rules.
- Do not change parser behavior.
- Do not change Excel fields, naming, static/dynamic split, or export quality gate.

## Next Task

V0.8 Milestone 3: Diff Engine.

## Future Tasks

1. Standard Excel to Knowledge Object.
2. Word material to Facts/RAG/Knowledge Object.
3. Knowledge Diff with KEEP/ADD/MODIFY/REMOVE_CANDIDATE.
4. Review confirmation workflow.
5. Merge and Update-mode export.
6. QC-assisted fixing with user accept/ignore choices.
