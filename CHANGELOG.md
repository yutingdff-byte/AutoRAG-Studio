# AutoRAG-Studio Changelog

---

## V0.5.6

发布日期：

2026-07

状态：

已完成

---

### 新增

Streamlit Web Demo

Parser Factory

TXT Parser

DOCX Parser

XLSX Parser

PDF Parser

Image Parser（预留）

---

### 新增Agent

Step1 Fact Agent

Step2 RAG Agent

Step3 QC Agent

---

### 新增功能

多文件上传

JSON结果展示

Excel自动生成

4 Sheet导出

---

### 修复

BUG-001

Step2返回None导致崩溃

修复：

增加异常兜底。

---

BUG-002

大资料JSON截断

修复：

增加max_tokens。

增加finish_reason日志。

---

BUG-003

RAG数量严重不足

问题：

41 Facts

↓

10 RAG

修复：

增加覆盖率规则。

按vehicle/category分批生成。

结果：

76 Facts

↓

66 RAG

---

BUG-004

品牌/车型/年款为空

修复：

新增：

brand

vehicle

year

字段。

---

BUG-005

Excel兼容问题

问题：

str has no attribute get

修复：

增加dict兼容判断。

---

BUG-006

PDF依赖缺失

修复：

安装pypdf。

---

BUG-007

excel_parser误覆盖

修复：

恢复parse_excel。

---

### 内容质量优化

新增：

年款规则

金融规则

销售转译边界

权益规则

---

### 测试结果

Parser

TXT

DOCX

XLSX

PDF

全部通过。

---

Step1

76 Facts

---

Step2

66 RAG

覆盖率约92%

---

Step3

可运行

规则待优化

---

### 版本评价

Parser

9/10

Fact Agent

8.5/10

RAG Agent

8.5/10

Excel

9/10

Streamlit

8/10

QC

6/10

---

整体：

8.3 / 10

---

## V0.5.7

状态：

开发中

---

目标

工程稳定化

---

计划内容

Run ID机制

独立输出目录

运行日志

多用户隔离

Git规范化

---

预计完成后

支持：

多人同时测试

结果追溯

版本回滚

持续迭代开发