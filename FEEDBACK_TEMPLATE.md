# AutoRAG-Studio Feedback / Badcase Template

Use this lightweight template during the V0.8.2 internal trial. One issue per entry.

```text
BC-ID:
Date:
User:

Mode:
Generate / Update

Input Type:
Word / Excel / PDF / Image / Other

Input Summary:

Problem:

Expected:

Actual:

Layer:
Parser / Facts / RAG / QC / Update / Export / UX / Performance / Unknown

Priority:
P0 / P1 / P2 / P3

Reproducible:
Yes / No / Unknown

Business Impact:

Status:
Open / Investigating / Fixed / Won't Fix

Evidence:
File name, screenshot, output path, row number, question, answer, or logs if available.

Notes:
```

## Priority Guide

- `P0`: Blocks generation/export or creates clearly unusable production output.
- `P1`: Serious quality or scope issue that could mislead users or customers.
- `P2`: Important improvement or recurring quality gap, but not a release blocker.
- `P3`: Minor UX, wording, documentation, or polish item.

## Internal Trial Rule

Do not open prompt tuning, concurrency changes, semantic dedup, color optimization, or retry expansion from a single anecdote. Accumulate evidence, group similar badcases, then define a focused fix task or V0.9 scope.
