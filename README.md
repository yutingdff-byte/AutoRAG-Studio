# AutoRAG-Studio

Current version: V0.8.0

AutoRAG-Studio generates and updates reviewable AI outbound-call knowledge bases from automotive business materials.

V0.8.0 keeps the Generate workflow stable and adds the Update workflow for restoring historical knowledge, detecting changes, merging decisions, and exporting a new production-ready knowledge base.

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
FACTS_MODE=single
RAG_MAX_CONCURRENCY=2
QC_MODE=full
```

`FACTS_MODE=chunked` and `QC_MODE=rule_first` are experimental and are not the V0.8.0 production defaults.

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

Not included in V0.8.0:

- QC auto-fix Agent Loop
- PPT parsing
- Database
- User permission system
- Project management
- Cloud deployment for the final V0.8.0 release
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
