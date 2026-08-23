# AutoRAG-Studio

Current version: V0.8.2

Status: Ready for Internal Trial

AutoRAG-Studio generates and updates reviewable AI outbound-call knowledge bases from automotive business materials.

V0.8.2 keeps the Generate and Update workflows stable and adds production record-aware Facts routing for complex vehicle matrix Excel files.

## What It Does

Supported inputs:

- Excel: `.xlsx`, `.xls`
- Word: `.docx`
- PDF: `.pdf`
- TXT: `.txt`
- Images: `.png`, `.jpg`, `.jpeg`, `.webp`

Generate pipeline:

```text
Upload files
-> Parser
-> Fact Agent
-> RAG Agent
-> QC Agent
-> Knowledge Review Center
-> Dual Excel export
```

Facts routing:

```text
Normal Word / normal row-oriented Excel
-> single

COLUMN_ORIENTED_VEHICLE_MATRIX
-> record_aware
```

Update pipeline:

```text
Historical knowledge
+ new source materials
-> Restore
-> Facts/RAG
-> Diff V0.2
-> Exception Review
-> Merge
-> Exact Duplicate Cleanup
-> Dual Excel export
```

Outputs:

- `车型配置知识库.xlsx`
- `价格政策知识库.xlsx`

Excel columns stay fixed:

- `车型`
- `版本`
- `问题`
- `回答`
- `分类`

## Model Roles

- DeepSeek: Fact extraction, RAG generation, QC.
- Qwen-VL-Plus: image material recognition only.

## Production Defaults

```env
FACTS_MODE=auto
FACTS_RECORD_BATCH_SIZE=3
FACTS_RECORD_BATCH_MAX_CHARS=12000
FACTS_MAX_CONCURRENCY=2
RAG_MAX_CONCURRENCY=2
RAG_BATCH_RETRY=1
QC_MODE=full
```

`FACTS_MODE=chunked` and `QC_MODE=rule_first` are experimental and are not the V0.8.2 production defaults.

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

On macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Environment Variables

Local development can use `.env`:

```env
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

QWEN_API_KEY=
QWEN_BASE_URL=
VISION_MODEL=qwen-vl-plus
```

Streamlit Cloud should use Secrets. See `.streamlit/secrets.toml.example` and `DEPLOY.md`.

Config lookup order:

1. Streamlit Secrets
2. System environment variables
3. Local `.env`

## Streamlit Cloud

Cloud URL:

```text
https://autorag-studio.streamlit.app/
```

Main entry file:

```text
app.py
```

Python version:

```text
python-3.11
```

Deployment guide:

```text
DEPLOY.md
```

## Data Safety

Please do not upload customer-sensitive, unpublished, confidential, or personal data to an unauthorized public cloud environment.

## Current Boundaries

Not included in V0.8.2:

- QC auto-fix Agent Loop
- PPT parsing
- Database
- User permission system
- Project management
- Prompt optimization without real feedback evidence
- Semantic dedup
- Retry expansion beyond empty response
- Default rollout of chunked Facts extraction
- Default rollout of Rule First QC
- Semantic Judge / Embedding / Vector DB

## Next Phase

Next steps are user-decided:

```text
V0.8 Cloud Deployment
or
Post-release planning
```
