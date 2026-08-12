# AutoRAG-Studio Streamlit Cloud Deployment

Version: V0.7.3 Cloud Ready

This guide deploys AutoRAG-Studio to Streamlit Community Cloud without changing the V0.7.2 Generate business baseline.

## 1. Deployment Prerequisites

- A GitHub repository containing this project.
- A Streamlit Community Cloud account.
- Python version: `python-3.11`, pinned in `runtime.txt`.
- Main entry file: `app.py`.
- Required API keys:
  - DeepSeek text model API key for Fact/RAG/QC.
  - Qwen Vision API key and OpenAI-compatible base URL for image parsing.

## 2. Deploy Steps

1. Push the code to GitHub.
2. Log in to Streamlit Community Cloud.
3. Create a new app.
4. Select the repository and deployment branch.
5. Set the main file path to `app.py`.
6. Open Advanced settings.
7. Confirm the Python version is compatible with `runtime.txt`.
8. Add Secrets using the template below.
9. Click Deploy.
10. Check the deployment log.
11. Upload a small TXT or Excel sample first.
12. Then test one image file after Qwen Vision Secrets are configured.

## 3. Secrets Template

Do not commit real secrets. Configure these in Streamlit Cloud Secrets.

```toml
DEEPSEEK_API_KEY = "your-deepseek-api-key"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

QWEN_API_KEY = "your-qwen-api-key"
QWEN_BASE_URL = "your-qwen-openai-compatible-base-url"
VISION_MODEL = "qwen-vl-plus"
```

Local development can use `.env` with the same names. `.env` is ignored by Git.

## 4. Update Deployment

- Push new commits to the deployed branch to trigger a redeploy.
- To isolate cloud releases from future development, deploy from a release branch such as `release/v0.7.3-cloud`.
- To roll back, switch the deployed branch or commit in Streamlit Cloud, or restore from tag `v0.7.3` or `v0.7.2`.
- Keep V0.8 feature work on a separate branch such as `feature/v0.8-update`.

## 5. Validation Checklist

After deployment, verify:

- App opens without a blank page.
- Secrets are detected during model calls.
- TXT, DOCX, XLSX, PDF, PNG, and JPG/JPEG uploads parse correctly.
- Image parsing preview works for Qwen Vision.
- Facts, RAG, QC, and the Knowledge Review Center render.
- Two Excel files are generated:
  - `车型配置知识库`
  - `价格政策知识库`
- Excel columns remain:
  - `车型`
  - `版本`
  - `问题`
  - `回答`
  - `分类`
- Missing or unconfirmed RAG items are not exported.

## 6. Common Issues

| Issue | Likely Cause | Action |
| -- | -- | -- |
| `ModuleNotFoundError` | Missing package in `requirements.txt` | Add the package, redeploy, and check logs |
| Missing DeepSeek key | `DEEPSEEK_API_KEY` not configured | Add it in Streamlit Secrets |
| Missing Qwen key | `QWEN_API_KEY` or `QWEN_BASE_URL` not configured | Add Qwen Vision Secrets |
| Linux path error | Windows-only hardcoded path | Replace with relative paths or `pathlib.Path` |
| File upload failed | File too large or unsupported type | Check `.streamlit/config.toml` and supported formats |
| Memory limit | Too many large images/PDFs | Use fewer files or smaller images |
| Model timeout | Network or provider latency | Retry or reduce material size |
| Chinese font issue | Browser/system font rendering | Verify in browser; Excel content remains text data |
| Excel download failed | Output file not generated | Check generation step and server logs |
| PDF parse failed | Damaged PDF or unsupported content | Try another PDF or convert to text |
| Image recognition failed | Invalid image, missing Qwen config, or provider failure | Check image size, format, and Secrets |

## 7. Security Notes

AutoRAG-Studio may process product materials, pricing policies, financial policies, operational knowledge, and unpublished vehicle information.

Do not upload customer-sensitive, unpublished, confidential, or personal data to an unauthorized public cloud environment.
