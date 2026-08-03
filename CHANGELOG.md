# 变更日志

本文件记录 AIGility 项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
本项目遵循 [语义化版本控制](https://semver.org/lang/zh-CN/)。

## [0.1.3] - 2026-05-27

### 新增
- **资源使用监控系统**：完整的 RAG 资源监控功能
  - 新增 `usage_tracking.py` 模块，用于跟踪 token 消耗和资源使用情况
  - 为嵌入模型（DashScope、HuggingFace、ZAI）添加监控能力
  - 为重排序操作添加监控
  - 新增 `wrapper.py` 嵌入包装器，支持使用量跟踪
  - 完整的测试套件 `test_usage_tracking.py`
  - 使用量跟踪指南文档 (`USAGE_TRACKING_GUIDE.md`)

- **RAG 模块增强**：
  - 集成重排序功能，支持 DashScope 重排序器
  - 新增 payload 和元数据优化
  - 实现 small2big 机制，提升检索效果
  - 新增 RAGAS 基线评估指标
  - 新增 markdown-AST 切分方式
  - 支持 payload 索引，提升搜索性能

- **开发和发布配置**：
  - 添加发布配置文件
  - 增强 `.gitignore` 设置
  - 添加 Claude 开发配置
  - 新增 AIGility 模块单元测试 (`tests/test_aigility.py`)

### 变更
- 更新 RAG 服务，增强 token 跟踪和监控功能
- 改进所有提供商（DashScope、HuggingFace、ZAI）的嵌入实现
- 增强重排序基类，添加使用量跟踪能力
- 更新工作流模块，集成监控功能

### 修复
- 修复文本处理中的列表切分问题
- 改进元数据处理和 payload 处理
- 修复 GitHub Actions CI 配置中的 Python 版本解析问题（3.10 被解析为 3.1）
- 修复 CI 配置中的目录名错误（`aicv` → `aigility`）
- 修复版本号不一致问题（`__init__.py` 与 `pyproject.toml`）
- 修复 Python 3.8/3.9 兼容性问题（PDF 库设为可选依赖）
- 简化测试文件，提高低版本 Python 兼容性

### 文档
- 添加全面的使用量跟踪指南
- 更新项目文档结构
- 添加中文变更日志

---

## [0.1.2] - 2026-05-20

### 新增
- **RAG 核心模块**：
  - 实现基础 RAG 模块
  - 支持多种嵌入模型（DashScope、HuggingFace、智谱）
  - 集成向量数据库支持（Qdrant）
  - 实现文档解析和切分功能
  - 支持 PDF、Markdown 等多种文档格式

- **核心功能**：
  - 基础聊天和工作流功能
  - 内存管理系统
  - 知识库集成

### 变更
- 重构知识模块，迁移到 RAG 模块
- 优化文档解析策略
- 解耦配置项，减少硬编码

### 修复
- 修复智谱导入错误
- 修复 service 中的 get 方法检查问题

---

## [0.1.1] - 2026-05-10

### 新增
- **Provider 系统**：
  - 新增 Provider 使用文档和配置示例
  - 将 TiEM Provider 服务集成到内存模块
  - 为向量数据库添加 Qdrant 库支持

- **嵌入模型支持**：
  - 为 RAG 嵌入新增智谱嵌入模型支持
  - 添加向量数据库对 Qdrant 的适配

### 变更
- 重构模块结构，更新项目配置
- 更新 API 密钥认证，添加调试日志

---

## [0.1.0] - 2026-05-01

### 新增
- **项目初始化**：
  - 首次发布 AIGility SDK
  - 实现通用 LangGraph ChatFlow
  - 支持思维链（CoT）、RAG 和网络搜索交互
  - 完善 RAG 模块，支持多嵌入模型、多向量数据库兼容

- **核心架构**：
  - 解耦标题和建议生成功能
  - 实现可配置的 LLM 集成
  - 完成 RAG 模块的 use_rag 开关配置项
  - 实现自定义 RAG 使用

### 文档
- 添加核心项目文档
- 添加 RAG 召回效果测试

---

## 版本历史总结

- **0.1.3**：资源监控、RAG 增强、重排序集成
- **0.1.2**：RAG 核心模块、多模型支持
- **0.1.1**：Provider 系统、向量数据库适配
- **0.1.0**：项目初始化、基础架构搭建