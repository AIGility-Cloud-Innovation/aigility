#!/usr/bin/env python3
"""
清理知识库并重新测试高阳纺织PDF
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

print(f"DEBUG: DASHSCOPE_API_KEY = {os.environ.get('DASHSCOPE_API_KEY', 'NOT SET')[:10]}...")

from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig,IngestionConfig,RerankConfig

print("=" * 80)
print("🧹 清理知识库并重新测试")
print("=" * 80)

# 初始化RAG服务
rag_config = RAGConfig(
    embedding=EmbeddingConfig(
        provider="zhipuai",
        model_name="embedding-3",
        api_key=os.getenv("ZHIPUAI_API_KEY", "")
    ),
    vector_store=VectorStoreConfig(
        provider="qdrant",
        collection_name="adp_knowledge_base",
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

# 0. 验证 Payload Index
print("\n0️⃣ 验证 Payload Index")
print("-" * 80)
try:
    client = rag_service.vector_store.client
    collection = client.get_collection("adp_knowledge_base")
    schema = collection.payload_schema
    if schema:
        print(f"✅ Payload Index 已建立，共 {len(schema)} 个字段：")
        for field, info in schema.items():
            print(f"   - {field}: {info.type}")
    else:
        print("⚠️ Payload Schema 为空，索引可能未建立")
except Exception as e:
    print(f"⚠️ 查询索引状态失败: {e}")

# 1. 清空知识库
print("\n1️⃣ 清空知识库")
print("-" * 80)
rag_service.clear_knowledge_base()
print("✅ 知识库已清空")

# 2. 添加知识库文件
print("\n2️⃣ 添加知识库文件")
print("-" * 80)
pdf_path = "docs/test.docx"
result = rag_service.add_file(pdf_path, auto_build_bm25=True)
print(f"✅ 已添加: {result['file_name']}")
print(f"   文件哈希: {result['file_hash'][:16]}...")

# 3. 测试查询
print("\n3️⃣ 测试查询")
print("-" * 80)

queries = [
    "K-1电动绞盘 产品差异"
]

for query in queries:
    print(f"\n查询: 「{query}」")
    print("-" * 40)
    result = rag_service.search(query)
    if result:
        print(result)
    else:
        print("❌ 无结果")

print("\n" + "=" * 80)
