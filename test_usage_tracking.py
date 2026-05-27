#!/usr/bin/env python3
"""
Usage Tracking 测试脚本

验证 token 用量追踪功能：
- add_file() 返回 AddFileResult，包含 usage 信息
- search() 返回 SearchResult，包含 usage 信息
- service.usage 累计总用量
- on_usage 回调触发
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from aigility.rag import (
    RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig,
    IngestionConfig, RerankConfig, UsageStats,
)

print("=" * 80)
print("📊 Usage Tracking 测试")
print("=" * 80)

# 初始化 RAG 服务
rag_config = RAGConfig(
    embedding=EmbeddingConfig(
        provider="zhipuai",
        model_name="embedding-3",
        api_key=os.getenv("ZHIPUAI_API_KEY", "")
    ),
    vector_store=VectorStoreConfig(
        provider="qdrant",
        collection_name="usage_test_collection",
        url="http://localhost:6333"
    ),
    rerank=RerankConfig(enabled=True),
    search_top_k=5,
    ingestion=IngestionConfig(
        chunk_size=300,
        chunk_overlap=100,
    )
)

rag_service = RAGService(config=rag_config)

# ============================================================
# 0. 注册 usage 回调
# ============================================================
print("\n0️⃣ 注册 usage 回调")
print("-" * 80)

callback_logs = []

def my_usage_callback(usage: UsageStats):
    callback_logs.append(usage)
    print(f"   📡 回调触发: embedding={usage.embedding.total_tokens}, rerank={usage.rerank.total_tokens}, total={usage.total_tokens}")

rag_service.on_usage(my_usage_callback)
print("✅ 回调已注册")

# ============================================================
# 1. 清空知识库
# ============================================================
print("\n1️⃣ 清空知识库")
print("-" * 80)
rag_service.clear_knowledge_base()
print("✅ 知识库已清空")

# ============================================================
# 2. 添加文件 - 验证 AddFileResult
# ============================================================
print("\n2️⃣ 添加文件 (验证 AddFileResult)")
print("-" * 80)

pdf_path = "docs/test.docx"
result = rag_service.add_file(pdf_path, auto_build_bm25=True)

# 2.1 验证 dict 风格访问（向后兼容）
print(f"✅ 文件名 (dict access): {result['file_name']}")
print(f"   文件哈希: {result['file_hash'][:16]}...")

# 2.2 验证属性访问
print(f"✅ 文件名 (attr access): {result.file_name}")
print(f"   文件哈希: {result.file_hash[:16]}...")

# 2.3 验证 usage 信息
print(f"\n📊 add_file() Usage:")
print(f"   Embedding tokens: {result.usage.embedding.total_tokens}")
print(f"   Embedding model:  {result.usage.embedding.model}")
print(f"   Total tokens:     {result.usage.total_tokens}")

# ============================================================
# 3. 搜索 - 验证 SearchResult
# ============================================================
print("\n3️⃣ 搜索 (验证 SearchResult)")
print("-" * 80)

query = "K-1电动绞盘 产品差异"
search_result = rag_service.search(query)

# 3.1 验证字符串兼容
print(f"✅ str(result) 输出 (前200字符):")
print(f"   {str(search_result)[:200]}...")

# 3.2 验证布尔兼容
print(f"\n✅ bool(result): {bool(search_result)}")

# 3.3 验证结构化数据
print(f"\n✅ 结构化数据:")
print(f"   documents 数量: {len(search_result.documents)}")
print(f"   metadata: {search_result.metadata}")

# 3.4 验证 usage 信息
print(f"\n📊 search() Usage:")
print(f"   Embedding tokens: {search_result.usage.embedding.total_tokens}")
print(f"   Rerank tokens:    {search_result.usage.rerank.total_tokens}")
print(f"   Total tokens:     {search_result.usage.total_tokens}")

# ============================================================
# 4. 验证累计用量
# ============================================================
print("\n4️⃣ 验证累计用量")
print("-" * 80)

total = rag_service.usage
print(f"✅ 累计 Usage:")
print(f"   Embedding tokens: {total.embedding.total_tokens}")
print(f"   Rerank tokens:    {total.rerank.total_tokens}")
print(f"   Total tokens:     {total.total_tokens}")

# ============================================================
# 5. 验证回调日志
# ============================================================
print("\n5️⃣ 验证回调日志")
print("-" * 80)
print(f"✅ 回调触发次数: {len(callback_logs)}")
for i, log in enumerate(callback_logs):
    print(f"   [{i+1}] embedding={log.embedding.total_tokens}, rerank={log.rerank.total_tokens}")

# ============================================================
# 6. 测试 reset_usage
# ============================================================
print("\n6️⃣ 测试 reset_usage")
print("-" * 80)
rag_service.reset_usage()
print(f"✅ reset 后累计: {rag_service.usage.total_tokens}")

# ============================================================
# 7. 再次搜索验证 reset 后重新累计
# ============================================================
print("\n7️⃣ Reset 后再次搜索")
print("-" * 80)
search_result2 = rag_service.search(query)
print(f"✅ 新搜索 Usage:")
print(f"   Embedding tokens: {search_result2.usage.embedding.total_tokens}")
print(f"   Rerank tokens:    {search_result2.usage.rerank.total_tokens}")
print(f"\n✅ 累计 Usage (reset 后):")
print(f"   Total tokens: {rag_service.usage.total_tokens}")

# ============================================================
# 完成
# ============================================================
print("\n" + "=" * 80)
print("🎉 Usage Tracking 测试完成!")
print("=" * 80)
