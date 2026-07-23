# AutoRAG-Studio

Current version: V0.7.3 Cloud Ready

AutoRAG-Studio generates reviewable AI outbound-call knowledge bases from automotive business materials.

V0.7.3 only adds cloud deployment and engineering readiness. Generate business behavior remains based on the V0.7.2 stable baseline.

## What It Does

Supported inputs:

- Excel: `.xlsx`, `.xls`
- Word: `.docx`
- PDF: `.pdf`
- TXT: `.txt`
- Images: `.png`, `.jpg`, `.jpeg`, `.webp`

Pipeline:

```text
Upload files
-> Parser
-> Fact Agent
-> RAG Agent
-> QC Agent
-> Knowledge Review Center
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

Not included in V0.7.3:

- Knowledge base incremental update
- QC auto-fix Agent Loop
- PPT parsing
- Database
- User permission system
- Project management

## Next Phase

V0.8 will focus on knowledge update mode:

```text
Old knowledge base
+ new policy material
-> detect additions, changes, and expired policies
-> update price policy knowledge
```
