"""
简单搜索测试 - 不使用过滤
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aigility.rag.service import RAGService
from aigility.rag.config import RAGConfig, EmbeddingConfig, VectorStoreConfig, IngestionConfig

logging.basicConfig(level=logging.INFO, format='%(message)s')

# 配置RAG服务
config = RAGConfig(
    embedding=EmbeddingConfig(
        provider="zhipuai",
        model_name="embedding-3",
        api_key=os.getenv("ZHIPUAI_API_KEY", "")
    ),
    vector_store=VectorStoreConfig(
        provider="qdrant",
        collection_name="test_simple_search",
        url="http://localhost:6333"
    ),
    ingestion=IngestionConfig(
        chunk_size=500,
        chunk_overlap=50,
    ),
    search_top_k=5
)

print("初始化RAGService...")
service = RAGService(config=config)

# 清空
print("\n清空测试集合...")
service.clear_knowledge_base()

# 添加文档
print("\n添加测试文档...")
test_file = "./test_data/test_simple.txt"

os.makedirs("./test_data", exist_ok=True)
with open(test_file, "w", encoding="utf-8") as f:
    f.write("这是一个关于人工智能的测试文档。")

service.add_file(test_file)
print("✅ 文档添加成功！")

# 测试1: 不带过滤的搜索
print("\n测试1: 不带过滤的搜索...")
try:
    # 直接调用 vector_store 的 similarity_search，不带 filter
    docs = service.vector_store.similarity_search("人工智能", k=5)
    print(f"找到 {len(docs)} 个结果")
    for i, doc in enumerate(docs):
        print(f"结果 {i+1}:")
        print(f"  内容: {doc.page_content[:100]}")
        print(f"  Metadata: {doc.metadata}")
except Exception as e:
    print(f"❌ 搜索失败: {e}")
    import traceback
    traceback.print_exc()

# 测试2: 带 filter 的搜索（字典格式）
print("\n测试2: 带 filter 的搜索（字典格式 is_deleted=False）...")
try:
    docs = service.vector_store.similarity_search(
        "人工智能",
        k=5,
        filter={"is_deleted": False}
    )
    print(f"找到 {len(docs)} 个结果")
    for i, doc in enumerate(docs):
        print(f"结果 {i+1}:")
        print(f"  内容: {doc.page_content[:100]}")
        print(f"  Metadata: {doc.metadata}")
except Exception as e:
    print(f"❌ 搜索失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 带 filter 的搜索（is_deleted=True）
print("\n测试3: 带 filter 的搜索（字典格式 is_deleted=True）...")
try:
    docs = service.vector_store.similarity_search(
        "人工智能",
        k=5,
        filter={"is_deleted": True}
    )
    print(f"找到 {len(docs)} 个结果")
    if docs:
        for i, doc in enumerate(docs):
            print(f"结果 {i+1}:")
            print(f"  内容: {doc.page_content[:100]}")
            print(f"  Metadata: {doc.metadata}")
    else:
        print("✅ 正确：没有找到 is_deleted=True 的文档")
except Exception as e:
    print(f"❌ 搜索失败: {e}")
    import traceback
    traceback.print_exc()

# 清理
print("\n清理...")
service.clear_knowledge_base()
os.remove(test_file)
print("✅ 完成")
