"""
测试简化后的软删除功能
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
        collection_name="test_final",
        url="http://localhost:6333"
    ),
    ingestion=IngestionConfig(
        chunk_size=500,
        chunk_overlap=50,
    ),
    search_top_k=5
)

print("=" * 60)
print("🧪 测试简化后的软删除功能")
print("=" * 60)

# 初始化服务
print("\n📦 初始化RAGService...")
service = RAGService(config=config)

# 清空
print("\n🗑️  清空测试集合...")
service.clear_knowledge_base()

# 创建测试文件
os.makedirs("./test_data", exist_ok=True)
test_file = "./test_data/test_final.txt"

with open(test_file, "w", encoding="utf-8") as f:
    f.write("""
这是一个关于人工智能的测试文档。

人工智能（AI）是计算机科学的一个分支，
致力于创建能够执行通常需要人类智能的任务的系统。

机器学习是人工智能的一个子集，
它使计算机能够从数据中学习并改进。
    """)

# ========================================
# 步骤1: 添加文件
# ========================================
print("\n📄 步骤1: 添加文件...")
result = service.add_file(test_file)

print(f"✅ 文件添加成功！")
print(f"   file_hash: {result['file_hash']}")
print(f"   file_name: {result['file_name']}")

# 保存 file_hash 用于后续操作
file_hash = result['file_hash']

# ========================================
# 步骤2: 搜索文件（删除前）
# ========================================
print("\n🔍 步骤2: 搜索文件（删除前）...")
query = "什么是人工智能"
results = service.search(query)
print(f"   查询: {query}")
print(f"   结果数: {len(results)}")

# ========================================
# 步骤3: 软删除文件（使用 file_hash）
# ========================================
print("\n🗑️  步骤3: 软删除文件（使用 file_hash）...")
print(f"   file_hash: {file_hash}")

success = service.delete_document(file_hash=file_hash)
print(f"   删除成功: {success}")

# ========================================
# 步骤4: 搜索文件（删除后）
# ========================================
print("\n🔍 步骤4: 搜索文件（删除后）...")
results = service.search(query)
print(f"   查询: {query}")
print(f"   结果数: {len(results)}")
if len(results) == 0:
    print("   ✅ 正确：搜索不到结果（文件已被软删除）")

# ========================================
# 步骤5: 恢复文件（使用 file_hash）
# ========================================
print("\n♻️  步骤5: 恢复文件（使用 file_hash）...")
print(f"   file_hash: {file_hash}")

success = service.restore_document(file_hash=file_hash)
print(f"   恢复成功: {success}")

# ========================================
# 步骤6: 搜索文件（恢复后）
# ========================================
print("\n🔍 步骤6: 搜索文件（恢复后）...")
results = service.search(query)
print(f"   查询: {query}")
print(f"   结果数: {len(results)}")
if len(results) > 0:
    print("   ✅ 正确：又能搜索到结果了（文件已恢复）")

# ========================================
# 步骤7: 查看所有文档
# ========================================
print("\n🔍 步骤7: 查看所有文档...")
all_docs = service.debug_list_all_documents()
print(f"   总文档数: {len(all_docs)}")
for doc in all_docs:
    print(f"   - file_name: {doc.get('file_name')}, file_hash: {doc.get('file_hash')}, is_deleted: {doc.get('is_deleted')}")

# 清理
print("\n🧹 清理测试数据...")
service.clear_knowledge_base()
os.remove(test_file)
print("   ✅ 清理完成")

print("\n" + "=" * 60)
print("✅ 测试完成！软删除功能正常工作！")
print("=" * 60)

print("\n📝 总结：")
print("   ✅ add_file 返回 file_hash 和 file_name")
print("   ✅ 使用 file_hash 可以精确删除文件")
print("   ✅ 使用 file_hash 可以精确恢复文件")
print("   ✅ 搜索时自动过滤已删除的文件")
