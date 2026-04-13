#!/usr/bin/env python3
"""
简单测试：只测试 "销售市场 销售区域 官方联系方式" 的检索效果
"""

import os
import sys
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig

# 只显示关键信息
logging.basicConfig(level=logging.ERROR)

print("=" * 80)
print("🔍 RAG 检索测试")
print("=" * 80)

# 配置
config = RAGConfig(
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
    search_top_k=5
)

# 初始化
print("\n1️⃣ 初始化服务...")
service = RAGService(config=config)
print("   ✅ 服务已启动")

# 清空知识库（确保从头开始）
print("\n🧹 清空知识库...")
service.clear_knowledge_base()

# 添加测试文档
test_file = "docs/怀鸽起重-外贸批发大客户售前知识库.docx"
if os.path.exists(test_file):
    print(f"\n📄 添加测试文档: {test_file}")
    service.add_file(test_file)
    print("   ✅ 文档已添加")

# 构建BM25索引
print("\n2️⃣ 构建 BM25 索引...")
service.build_bm25_index()
print(f"   ✅ BM25 索引已构建 ({len(service._bm25_corpus)} 个文档)")

# 测试检索
query = "联系 方式"

print(f"\n3️⃣ 测试查询: {query}")
print("-" * 80)

# 方法1: 纯语义检索
print("\n【方法1: 纯语义检索】")
result1 = service.search(query, expand_context=False, enable_keyword_boost=False)
if result1:
    if "官方联系方式" in result1:
        print("   ✅ 检索到 '官方联系方式'")
        print(f"   内容: {result1[:300]}...")
    else:
        print("   ❌ 未检索到 '官方联系方式'")
        print(f"   内容: {result1[:300]}...")
else:
    print("   ❌ 无结果")

# 方法2: BM25混合检索
print("\n【方法2: BM25混合检索】")
result2 = service.search_bm25_hybrid(query, expand_context=False)
if result2:
    if "官方联系方式" in result2:
        print("   ✅ 检索到 '官方联系方式'")
        print(f"   内容: {result2[:300]}...")
    else:
        print("   ❌ 未检索到 '官方联系方式'")
        print(f"   内容: {result2[:300]}...")
else:
    print("   ❌ 无结果")

# 总结
print("\n" + "=" * 80)
print("✅ 测试完成")
print("=" * 80)
