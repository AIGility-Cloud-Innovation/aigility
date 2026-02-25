# AIGility 依赖优化说明

## 优化目标

用户反馈 `pip install aigility` 安装时间过长，依赖包太大。本次优化将核心依赖与可选依赖分离，让用户可以按需安装。

## 优化内容

### 1. 核心依赖（最小化）

**安装命令**: `pip install aigility`

**包含功能**:
- HTTP 客户端 (httpx)
- 数据验证 (pydantic)
- LangChain 核心 (langchain-core)
- LangGraph 工作流引擎
- OpenAI LLM 支持
- YAML 配置解析

**核心依赖列表**:
```
httpx>=0.24.0
httpx-sse>=0.4.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
typing-extensions>=4.0.0
langchain-core>=0.1.0
langgraph>=0.0.20
langchain-openai>=0.0.5
pyyaml>=6.0
```

**预计安装大小**: 约 50-100MB（不包括子依赖）

### 2. 可选依赖（按需安装）

#### LLM 提供商
- `anthropic`: Anthropic Claude 支持

#### RAG 功能
- `rag`: RAG 核心依赖（最小）
- `embedding-huggingface`: HuggingFace Embedding（**重！含 torch**）
- `embedding-dashscope`: DashScope Embedding
- `vectorstore-chroma`: Chroma 向量库
- `vectorstore-faiss`: FAISS 向量库
- `vectorstore-milvus`: Milvus 向量库
- `vectorstore-qdrant`: Qdrant 向量库

#### 文档处理
- `doc-pdf`: PDF 处理（pdfplumber）
- `doc-word`: Word 处理（python-docx）
- `doc-excel`: Excel 处理（pandas + openpyxl）

#### NLP 处理
- `nlp`: 中文分词和 TF-IDF（jieba + scikit-learn）

#### 第三方服务
- `timem`: 太忆 RAG 服务
- `timem-rag`: 太忆 RAG 完整功能（含文档处理和 NLP）
- `zai`: 在智 embedding 服务

#### 功能组合
- `rag-local`: 本地 RAG（HuggingFace + Chroma + 文档处理 + NLP）
- `rag-qdrant`: Qdrant RAG（Qdrant + 文档处理 + NLP）
- `all`: 全功能

### 3. 从核心依赖移除的包

以下包从核心依赖移到可选依赖，**显著减少了安装大小**：

| 包名 | 原因 | 大小估算 |
|------|------|----------|
| `sentence-transformers` | 依赖 torch（>2GB） | ~500MB-2GB |
| `torch` | ML 框架，非常重 | >2GB |
| `transformers` | HuggingFace 模型库 | ~500MB |
| `chromadb` | 可选向量库 | ~50MB |
| `qdrant-client` | 可选向量库 | ~10MB |
| `pandas` | 仅用于 Excel 处理 | ~100MB |
| `pdfplumber` | 仅用于 PDF 处理 | ~10MB |
| `python-docx` | 仅用于 Word 处理 | ~5MB |
| `jieba` | 仅用于中文分词 | ~5MB |
| `scikit-learn` | 仅用于 TF-IDF | ~100MB |
| `langchain-community` | 仅用于向量库集成 | ~50MB |
| `langchain-huggingface` | 仅用于 HuggingFace embedding | ~10MB |
| `langchain-chroma` | 仅用于 Chroma 集成 | ~5MB |
| `openpyxl` | 仅用于 Excel 读写 | ~5MB |

### 4. 安装时间对比

| 安装方式 | 预计时间 | 下载大小 |
|----------|----------|----------|
| 核心安装 `pip install aigility` | **< 1 分钟** | ~50MB |
| 完整安装 `pip install aigility[all]` | **5-15 分钟** | ~3-4GB |

## 使用建议

### 开发环境

如果需要完整功能：

```bash
pip install "aigility[all]"
```

### 生产环境

根据实际使用的功能选择：

```bash
# 只用聊天和对话流
pip install aigility

# 使用太忆 RAG 服务（推荐）
pip install "aigility[timem-rag]"

# 使用本地 RAG（会下载模型，较慢）
pip install "aigility[rag-local]"

# 使用 Qdrant RAG
pip install "aigility[rag-qdrant]"
```

## 迁移指南

### 对现有用户的影响

如果用户已经安装了旧版本的 aigility，升级时会保留已安装的可选依赖。但如果需要重新安装：

**旧版本（包含所有依赖）**:
```bash
pip install aigility==0.0.1
```

**新版本（核心依赖）**:
```bash
pip install aigility==0.0.2
# 如果需要 RAG 功能
pip install "aigility[rag-local]"
```

### 代码兼容性

**完全兼容**！本次优化只改变了依赖的安装方式，不影响任何 API 和功能。

如果使用了某个模块但未安装对应的依赖，会收到友好的错误提示：

```python
# 示例：未安装 chromadb 时使用 Chroma
rag_service = RAGService(config=...)
# 错误提示：
# ImportError: 使用 Chroma 向量库需要安装: pip install chromadb langchain-chroma
```

## 测试建议

发布后建议进行以下测试：

1. **核心安装测试**
```bash
pip install aigility
python -c "import aigility; print('核心安装成功')"
```

2. **可选安装测试**
```bash
pip install "aigility[timem-rag]"
python -c "import aigility; print('timem-rag 安装成功')"
```

3. **功能测试**
- 聊天功能（核心）
- 对话流（核心）
- RAG 功能（可选）
- 文档处理（可选）

## 版本发布建议

建议发布 **0.0.3** 版本，包含这些优化：

```toml
version = "0.0.3"
```

并在 CHANGELOG 中注明：

```markdown
## [0.0.3] - 2025-XX-XX

### 优化
- 重构依赖结构，将核心依赖与可选依赖分离
- 大幅减少核心安装包大小（从 ~3GB 降至 ~50MB）
- 显著缩短安装时间（从 5-15 分钟降至 < 1 分钟）

### 新增
- 新增可选依赖组：anthropic, timem, timem-rag, zai 等
- 新增功能组合：rag-local, rag-qdrant, all

### 兼容性
- 完全向后兼容，不影响现有代码
```
