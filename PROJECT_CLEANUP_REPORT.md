# AutoRAG-Studio Project Cleanup Report

Version: V0.7.3 Cloud Ready

Date: 2026-07-23

Scope: scan, classify, and safely clean local-only generated artifacts without changing Generate business logic.

## 1. Git Baseline

| Item | Result |
| -- | -- |
| Current branch | `main` |
| Baseline commit | `4d75aa5` |
| Baseline tag | `v0.7.2` |
| Worktree before V0.7.3 work | Clean |
| `v0.7.2` target | `4d75aa55a302ba3e4e77f4530bc924eee28e6865` |

## 2. 可直接清理

These items are generated caches or local runtime artifacts. They are not required by Python source, prompts, tests, Streamlit Cloud deployment, or documentation.

| 路径 | 类型 | 删除原因 | 是否被引用 | 风险 |
| -- | -- | -- | -- | -- |
| `__pycache__/` | Python cache | Python bytecode cache generated during local runs | No code reference | Low |
| `agents/__pycache__/` | Python cache | Python bytecode cache generated during local runs | No code reference | Low |
| `generator/__pycache__/` | Python cache | Python bytecode cache generated during local runs | No code reference | Low |
| `parser/__pycache__/` | Python cache | Python bytecode cache generated during local runs | No code reference | Low |
| `tests/__pycache__/` | Python cache | Python bytecode cache generated during local test runs | No code reference | Low |
| `utils/__pycache__/` | Python cache | Python bytecode cache generated during local test runs | No code reference | Low |

## 3. 建议归档

These items are local generated outputs. They are useful for regression comparison, but they should not be committed or deployed.

| 路径 | 类型 | 建议 | 是否被引用 | 风险 |
| -- | -- | -- | -- | -- |
| `output/20260714_112516/` | Historical run output | Keep local or archive under external storage if needed | Ignored; not runtime dependency | Low |
| `output/20260714_165500/` | Historical run output | Keep local or archive under external storage if needed | Ignored; not runtime dependency | Low |
| `output/20260714_225814/` | Historical run output | Keep local or archive under external storage if needed | Ignored; not runtime dependency | Low |
| `output/20260715_224222/` | Historical run output | Keep local or archive under external storage if needed | Ignored; not runtime dependency | Low |
| `output/20260715_232245/` | Historical run output | Keep local or archive under external storage if needed | Used manually for historical Avita comparison | Medium |
| `output/20260717_170231/` | Historical run output | Keep local or archive under external storage if needed | Used manually for prior regression | Medium |
| `output/20260718_161941/` | V0.7.1 Avita RC output | Keep local as regression baseline; do not delete automatically | Used for V0.7.2/V0.7.3 regression | Medium |

## 4. 必须保留

| 路径 | 保留原因 |
| -- | -- |
| `app.py` | Streamlit main entry |
| `main.py` | Generate pipeline entry |
| `agents/` | Fact, RAG, QC, and LLM client modules |
| `parser/` | TXT, DOCX, Excel, PDF, and image parsers |
| `generator/excel_generator.py` | Formal dual Excel export |
| `utils/` | JSON parsing, quality gate, and config helpers |
| `prompts/` | Generate core prompt rules |
| `schemas/` | Export schema reference |
| `tests/` | Regression and rule checks |
| `tests/data/` | Local parser smoke-test fixtures |
| `requirements.txt` | Streamlit Cloud dependency installation |
| `runtime.txt` | Cloud Python version pin |
| `.streamlit/config.toml` | Streamlit runtime configuration |
| `.streamlit/secrets.toml.example` | Secrets template without real keys |
| `.env.example` | Local environment template without real keys |
| `.gitignore` | Prevents local secrets, output, venv, cache, and Excel exports from being committed |
| `CHANGELOG.md` | Version history |
| `PROJECT_CONTEXT.md` | Project handoff context |
| `ROADMAP.md` | Product roadmap |
| `TASK_CURRENT.md` | Current task state |
| `README.md` | User and developer quick start |
| `DEPLOY.md` | Streamlit Cloud deployment guide |

## 5. 无法判断

| 路径 | 原因 | 处理 |
| -- | -- | -- |
| `.agents/` | Codex/local agent metadata; not part of product runtime but may be useful locally | 保留 |
| `.codex/` | Codex/local workspace metadata | 保留 |
| `.env` | Local secret file; ignored and not inspected for full contents | 保留本地，不提交 |
| `.venv/` | Local virtual environment; ignored and not deployed | 保留本地，不提交 |

## 6. 清理执行规则

- Only low-risk Python caches are removed automatically.
- Historical outputs are not deleted automatically because they are useful regression evidence.
- Local secrets and virtual environments are not modified.
- No broad cleanup command such as `git clean -fd` is used.

## 7. 清理结果

Executed cleanup:

- Removed `__pycache__/`
- Removed `agents/__pycache__/`
- Removed `generator/__pycache__/`
- Removed `parser/__pycache__/`
- Removed `tests/__pycache__/`
- Removed `utils/__pycache__/`

Not removed:

- `output/`
- `.env`
- `.venv/`
- test fixtures
- prompts
- schemas
- documentation
