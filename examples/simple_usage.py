"""
简单使用示例：改进后的工作流程
"""

from aigility.rag.service import RAGService
from aigility.rag.config import RAGConfig, EmbeddingConfig, VectorStoreConfig

# 初始化服务
config = RAGConfig(
    embedding=EmbeddingConfig(
        provider="zhipuai",
        model_name="embedding-3",
        api_key="your_api_key"
    ),
    vector_store=VectorStoreConfig(
        provider="qdrant",
        collection_name="my_knowledge_base",
        url="http://localhost:6333"
    )
)

service = RAGService(config=config)

# ========================================
# 步骤1: 添加文件
# ========================================
print("步骤1: 添加文件")
print("-" * 60)

result = service.add_file("/path/to/document.pdf")

print(f"✅ 文件添加成功！")
print(f"   file_id: {result['file_id']}")      # 保存这个ID！
print(f"   file_hash: {result['file_hash']}")
print(f"   file_name: {result['file_name']}")
print(f"   chunk_count: {result['chunk_count']}")

# 保存 file_id 到你的数据库或内存
file_id = result['file_id']

# ========================================
# 步骤2: 搜索文件
# ========================================
print("\n步骤2: 搜索文件")
print("-" * 60)

results = service.search("查询内容")
print(f"✅ 搜索结果: {len(results)} 字符")

# ========================================
# 步骤3: 软删除文件
# ========================================
print("\n步骤3: 软删除文件")
print("-" * 60)

success = service.delete_document(file_id=file_id)
print(f"✅ 文件已删除: {success}")

# 验证：搜索不到结果了
results = service.search("查询内容")
print(f"   搜索结果: {len(results)} 字符（应该为0）")

# ========================================
# 步骤4: 恢复文件
# ========================================
print("\n步骤4: 恢复文件")
print("-" * 60)

success = service.restore_document(file_id=file_id)
print(f"✅ 文件已恢复: {success}")

# 验证：又能搜索到了
results = service.search("查询内容")
print(f"   搜索结果: {len(results)} 字符（应该有内容）")

print("\n" + "=" * 60)
print("✅ 完成！这就是完整的软删除工作流程")
print("=" * 60)
