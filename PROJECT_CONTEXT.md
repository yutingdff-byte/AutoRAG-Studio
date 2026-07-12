# AutoRAG-Studio PROJECT CONTEXT

Version: V0.5.7

Last Update: 2026-07-12

Status:

核心链路已跑通

进入工程稳定化与真实生产测试阶段


---

# 1. 项目定位


## 项目名称

AutoRAG-Studio


## 项目目标

AutoRAG-Studio 是一个面向企业 Agent 场景的知识库生成平台。

当前重点应用：

- 汽车 AI 外呼
- 销售 Agent
- FAQ 知识库


输入：

- Word
- Excel
- PDF
- TXT
- 图片（规划）


输出：

可用于 AI 系统导入的结构化 RAG 知识库。


---

## 长期目标

AutoRAG-Studio 不只是 Excel 生成工具。

未来目标：

知识库生成

+

知识库检查

+

知识库更新

+

知识库运营

平台。


---

# 2. 当前技术架构


整体流程：

资料上传

↓

Parser Layer

↓

Step1 Fact Agent

↓

Step2 RAG Agent

↓

Step3 QC Agent

↓

Excel Generator

↓

Streamlit 展示


---

# 3. 当前目录结构

AutoRAG-Studio

├── agents

│ ├── fact_agent.py

│ ├── rag_agent.py

│ ├── qc_agent.py

│ └── llm_client.py

├── parser

│ ├── parser_factory.py

│ ├── docx_parser.py

│ ├── excel_parser.py

│ ├── pdf_parser.py

│ ├── txt_parser.py

│ └── image_parser.py

├── generator

│ └── excel_generator.py

├── prompts

│ ├── step1_prompt.txt

│ ├── step2_prompt.txt

│ └── step3_prompt.txt

├── schemas

│ └── excel_schema.json

├── utils

│ └── json_parser.py

├── tests

├── app.py

├── main.py

└── requirements.txt



---

# 4. 当前支持能力


## Parser


### TXT

状态：

✅ 支持


当前实现：

parser_factory.py 内部处理。


后续：

可独立拆分 txt_parser.py。


---

### DOCX

状态：

✅ 支持


---

### XLSX

状态：

✅ 支持


---

### PDF

状态：

✅ 支持


---

### Image

状态：

⏳ 未接入


当前：

保留 image_parser.py 文件。

尚未进入 parser_factory。


---

### PPT

状态：

⏳ 未支持


---

# 5. Agent架构


## Step1 Fact Agent


目标：

原始资料

↓

事实抽取


原则：

- 只抽取资料已有信息
- 禁止补充
- 保留来源


输出：

facts

info_gaps


---

## Step2 RAG Agent


目标：

facts

↓

RAG知识


原则：

- 基于facts生成
- 禁止幻觉
- 禁止越界销售表达
- 支持电话场景口语化


输出：

rag_knowledge

confirm_items

info_gaps


---

## Step3 QC Agent


目标：

检查生成质量。


检查：

- 信息完整性
- 风险
- 幻觉
- 覆盖率


状态：

可运行。

规则仍需优化。


---

# 6. 当前Excel设计


当前输出：

4 Sheet


## Sheet1

RAG知识库


## Sheet2

信息缺口


## Sheet3

人工确认事项


## Sheet4

QC报告


未来：

Sheet2-4迁移至网页检查台。

Excel主要用于系统导入。


---

# 7. 已确定设计原则


## 原则1

内部Schema和导出Excel分离。


内部：

保留完整字段：

- fact_refs
- confidence
- guardrails
- need_confirm


用于：

追踪

检查

更新。


导出：

根据业务需求精简。


---

## 原则2

知识生命周期分类


未来支持：


产品固定知识：

- 配置
- 尺寸
- 空间
- 智驾


营销政策知识：

- 金融
- 权益
- 补贴


---

## 原则3

更新模式设计


第一阶段：

用户指定更新范围。


第二阶段：

AI自动识别变化。


---

# 8. 当前版本状态


## 已完成


Parser：

✅


Fact Agent：

✅


RAG Agent：

✅


Excel Export：

✅


Streamlit：

✅


Git：

✅


---

## 未完成


Run ID：

⏳


独立输出目录：

⏳


网页检查台：

⏳


图片解析：

⏳


知识库更新：

⏳


---

# 9. 当前已知风险


P0：

运行结果固定写入output。

存在覆盖风险。


---

P1：

LLM返回异常时部分链路需要增强。


---

P1：

requirements.txt 与实际依赖需要同步。


---

P2：

Excel schema 与实际generator结构存在差异。


---

P2：

tests目前主要为开发验证脚本。

未形成稳定自动化测试。


---

# 10. 当前开发优先级


## V0.5.7

工程稳定化。


目标：

多人测试

结果追踪

版本可靠


包含：

- Run ID
- 独立输出目录
- run_info.json
- Streamlit结果隔离


---

# 11. Codex协作规范


开始任务前：

阅读：

PROJECT_CONTEXT.md

ROADMAP.md

TASK_CURRENT.md


---

修改前：

先说明方案。


---

修改后：

必须反馈：

1. 修改文件

2. 修改内容

3. 测试方式

4. 测试结果

5. 风险


---

禁止：

未经确认大规模重构。

禁止：

破坏稳定Pipeline。

禁止：

修改Prompt业务规则。