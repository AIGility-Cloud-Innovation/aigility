"""
测试：删除后重新添加相同文件的场景（新逻辑：恢复旧文件）
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
        collection_name="test_reupload",
        url="http://localhost:6333"
    ),
    ingestion=IngestionConfig(
        chunk_size=500,
        chunk_overlap=50,
    ),
    search_top_k=5
)

print("=" * 60)
print("🧪 测试：删除后重新添加相同文件（恢复旧文件）")
print("=" * 60)

# 初始化服务
print("\n📦 初始化RAGService...")
service = RAGService(config=config)

# 清空
print("\n🗑️  清空测试集合...")
service.clear_knowledge_base()

# 创建测试文件
os.makedirs("./test_data", exist_ok=True)

# ========================================
# 步骤1: 第一次添加文件
# ========================================
print("\n📄 步骤1: 第一次添加文件...")
test_file1 = "./test_data/original.txt"
content1 = "这是原始文档的内容，包含一些重要信息。"

with open(test_file1, "w", encoding="utf-8") as f:
    f.write(content1)

result1 = service.add_file(test_file1)
print(f"✅ 文件添加成功！")
print(f"   file_hash: {result1['file_hash']}")
print(f"   file_name: {result1['file_name']}")

file_hash = result1['file_hash']

# ========================================
# 步骤2: 搜索文件（应该能找到）
# ========================================
print("\n🔍 步骤2: 搜索文件...")
results = service.search("测试文档")
print(f"   搜索结果: {len(results)} 字符")
if len(results) > 0:
    print("   ✅ 能搜索到文件")

# ========================================
# 步骤3: 删除文件
# ========================================
print("\n🗑️  步骤3: 删除文件...")
success = service.delete_document(file_hash=file_hash)
print(f"   删除成功: {success}")

# 验证：搜索不到
results = service.search("测试文档")
print(f"   搜索结果: {len(results)} 字符")
if len(results) == 0:
    print("   ✅ 正确：搜索不到（已删除）")

# ========================================
# 步骤4: 查看向量库状态
# ========================================
print("\n🔍 步骤4: 查看向量库状态...")
all_docs = service.debug_list_all_documents()
print(f"   总文档数: {len(all_docs)}")
for doc in all_docs:
    print(f"   - file_name: {doc.get('file_name')}, is_deleted: {doc.get('is_deleted')}, file_hash: {doc.get('file_hash')}")

# ========================================
# 步骤5: 重新添加相同内容但不同文件名的文件
# ========================================
print("\n📄 步骤5: 重新添加相同内容但不同文件名的文件...")
print("   （新逻辑：应该恢复旧文件并更新文件名）")

test_file2 = "./test_data/renamed.txt"
with open(test_file2, "w", encoding="utf-8") as f:
    f.write(content1)  # 相同内容

result2 = service.add_file(test_file2)
print(f"✅ 文件添加成功！")
print(f"   file_hash: {result2['file_hash']}")
print(f"   file_name: {result2['file_name']}")

# 验证：file_hash 应该相同
if result1['file_hash'] == result2['file_hash']:
    print("   ✅ file_hash 相同（内容相同，符合预期）")

# 验证：文件名应该更新
if result2['file_name'] == "renamed.txt":
    print("   ✅ 文件名已更新为新文件名")

# ========================================
# 步骤6: 搜索文件（应该能找到！）
# ========================================
print("\n🔍 步骤6: 搜索文件...")
results = service.search("测试文档")
print(f"   搜索结果: {len(results)} 字符")
if len(results) > 0:
    print("   ✅ 成功！能搜索到文件（旧文件已恢复）")

# ========================================
# 步骤7: 查看向量库状态（应该只有1个文件记录）
# ========================================
print("\n🔍 步骤7: 查看向量库状态...")
all_docs = service.debug_list_all_documents()
print(f"   总文档数: {len(all_docs)}")
for doc in all_docs:
    print(f"   - file_name: {doc.get('file_name')}, is_deleted: {doc.get('is_deleted')}, file_hash: {doc.get('file_hash')}")

# 统计
active_count = sum(1 for doc in all_docs if doc.get('is_deleted') == False)
deleted_count = sum(1 for doc in all_docs if doc.get('is_deleted') == True)
print(f"\n   统计:")
print(f"   - 未删除的文件: {active_count}")
print(f"   - 已删除的文件: {deleted_count}")

# ========================================
# 步骤8: 验证结果
# ========================================
print("\n" + "=" * 60)
print("✅ 测试结果分析")
print("=" * 60)

if active_count == 1 and deleted_count == 0 and result2['file_name'] == "renamed.txt":
    print("✅ 完美！")
    print("   - 有1个未删除的文件（旧文件已恢复）")
    print("   - 有0个已删除的文件（没有重复记录）")
    print("   - 文件名已更新为新文件名")
    print("   - 用户可以正常搜索到文件")
    print("   - 新逻辑：恢复旧文件 + 更新元数据，而不是添加新 chunks")
else:
    print("❌ 失败！")
    print(f"   - 未删除: {active_count}")
    print(f"   - 已删除: {deleted_count}")
    print(f"   - 文件名: {result2['file_name']}")

# 清理
print("\n🧹 清理测试数据...")
service.clear_knowledge_base()
os.remove(test_file1)
os.remove(test_file2)
print("   ✅ 清理完成")

print("\n" + "=" * 60)
print("📝 总结")
print("=" * 60)
print("""
新方案：
1. 检测到相同 file_hash 时，不添加新 chunks
2. 如果文件已删除：恢复文件（is_deleted=False）
3. 更新文件名为新上传的文件名

优势：
- ✅ 不产生重复的 chunks
- ✅ 删除后重新上传可以正常使用
- ✅ 文件名保持最新
- ✅ 更高效（不需要重新 embedding）
- ✅ 保持向量库整洁
""")
