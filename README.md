# Embedding Cache Inspector

Embedding Cache Inspector 是一个面向 RAG/AI 应用开发者的本地嵌入缓存审计 CLI。它可以读取 JSONL 和 SQLite 缓存，检查文档 id、chunk 文本、embedding 维度、重复内容、空向量、NaN/Infinity、模型混用、元数据缺失，并输出 JSON 或 Markdown 报告与修复建议。

项目目标是做一个轻量、可审计、容易放进 CI 的工具。运行时只使用 Python 标准库，没有第三方依赖。

## 功能

- `inspect jsonl`：逐行读取 JSONL 嵌入缓存。
- `inspect sqlite`：读取 SQLite 表中的嵌入缓存。
- `schema options`：查看 JSONL 字段和 SQLite 表/列配置。
- 维度统计：最小值、最大值、均值和维度分布。
- 维度校验：通过 `--expected-dimension` 检出异常向量。
- 重复检测：chunk hash、embedding hash、document id。
- 空向量和非有限值检测：空数组、缺失 embedding、NaN、Infinity。
- 模型分布：发现模型混用或模型缺失。
- 元数据必填项：通过 `--required-metadata source,language` 检查。
- 报告输出：Markdown 或 JSON，可写入文件。
- 标准库测试：loader、audit rules、reporter、CLI。

## 安装

本地开发安装：

```bash
python -m pip install -e .
```

也可以不安装，直接设置 `PYTHONPATH=src` 后运行模块：

```bash
PYTHONPATH=src python -m embedding_cache_inspector.cli inspect jsonl examples/sample.jsonl
```

Windows PowerShell：

```powershell
$env:PYTHONPATH = "src"
python -m embedding_cache_inspector.cli inspect jsonl examples/sample.jsonl
```

## 快速开始

检查 JSONL：

```bash
embedding-cache-inspector inspect jsonl examples/sample.jsonl \
  --expected-dimension 3 \
  --required-metadata source,language \
  --format markdown
```

生成 JSON 报告：

```bash
embedding-cache-inspector inspect jsonl examples/sample.jsonl \
  --expected-dimension 3 \
  --required-metadata source \
  --format json \
  --report report.json
```

检查 SQLite：

```bash
embedding-cache-inspector inspect sqlite cache.sqlite \
  --table embeddings \
  --id-column id \
  --chunk-column chunk \
  --embedding-column embedding \
  --model-column model \
  --metadata-column metadata \
  --expected-dimension 1536
```

查看 schema 配置项：

```bash
embedding-cache-inspector schema options
```

## JSONL 格式

默认字段：

```json
{"id":"doc-1","chunk":"hello world","embedding":[0.1,0.2,0.3],"model":"text-embedding-3-small","metadata":{"source":"demo.md","language":"zh"}}
```

字段名可以配置：

```bash
embedding-cache-inspector inspect jsonl cache.jsonl \
  --id-field document_id \
  --chunk-field text \
  --embedding-field vector \
  --model-field embedding_model \
  --metadata-field meta
```

## SQLite 格式

默认表名是 `embeddings`，默认列是：

| 列 | 含义 |
| --- | --- |
| `id` | 文档或 chunk id |
| `chunk` | 被嵌入的文本 |
| `embedding` | JSON 数组或逗号分隔数字 |
| `model` | 嵌入模型名称 |
| `metadata` | JSON object |

SQLite 的 embedding 可以是：

- JSON 数组字符串：`[0.1, 0.2, 0.3]`
- 逗号分隔字符串：`0.1,0.2,0.3`

## 退出码

默认 `--fail-on error`：

- 没有 error：退出码 0。
- 存在 error：退出码 1。
- `--fail-on warning`：warning 或 error 都返回 1。
- `--fail-on never`：总是返回 0，适合只生成报告。

## 报告字段

JSON 报告包含：

- `summary`：记录数、错误数、警告数。
- `dimension_stats`：维度统计和分布。
- `model_distribution`：模型名称计数。
- `duplicate_summary`：重复 chunk、重复 embedding、重复 id 的数量。
- `findings`：每条问题的 severity、code、message、source、position、suggestion 和 details。

## 开发与测试

```bash
python -m unittest discover -s tests
```

本项目不需要真实 API key，不读取 GitHub token，不连接外部服务。示例数据全部是合成数据。

## English

Embedding Cache Inspector is a local embedding cache audit CLI for RAG and AI application developers. It reads JSONL and SQLite caches, validates document ids, chunk text, embedding dimensions, duplicate hashes, empty vectors, NaN/Infinity values, mixed models, and required metadata, then emits JSON or Markdown reports with repair suggestions.

Runtime dependencies: zero. The tool uses only the Python standard library.

### Features

- `inspect jsonl` for JSONL embedding caches.
- `inspect sqlite` for SQLite embedding cache tables.
- Configurable schema field and column names.
- Dimension statistics and expected dimension validation.
- Duplicate detection for chunk hashes, embedding hashes, and document ids.
- Empty embedding and non-finite value detection.
- Model distribution and mixed model warnings.
- Required metadata checks.
- JSON and Markdown reporters.
- Standard-library test suite for loaders, audit rules, reporter, and CLI.

### Usage

```bash
embedding-cache-inspector inspect jsonl examples/sample.jsonl \
  --expected-dimension 3 \
  --required-metadata source,language \
  --format markdown
```

```bash
embedding-cache-inspector inspect sqlite cache.sqlite \
  --table embeddings \
  --expected-dimension 1536 \
  --format json
```

### Development

```bash
python -m unittest discover -s tests
```

Use synthetic fixtures only. Do not commit secrets, private documents, generated reports, local databases, virtual environments, or build artifacts.
