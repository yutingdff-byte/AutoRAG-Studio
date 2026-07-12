# AutoRAG-Studio Current Task


Version:

V0.5.7


Current Status:

工程稳定化阶段



---

# TASK-001

## Run ID与输出隔离


状态：

未开始


目标：

解决多人测试结果覆盖问题。



---

## 要求


每次运行生成：

output/{run_id}/


run_id格式：

YYYYMMDD_HHMMSS



---

目录：

output/

├──20260712_103501

│

├── facts.json

├── rag.json

├── qc_report.json

├── run_info.json

└── excel.xlsx



---

## 修改范围建议


允许：

main.py

app.py

generator


禁止：

修改：

Parser

Prompt

Agent核心逻辑



---

## 验收标准


连续运行两次：

生成两个不同目录。


结果：

互不覆盖。


Streamlit下载：

对应当前运行结果。



---

# 后续任务


TASK-002

统一requirements依赖。


TASK-003

修复QC展示字段。


TASK-004

测试体系整理。


TASK-005

Excel schema同步。

