"""
最简单的调用示例 - 外部如何使用
"""

from aigility.rag.service import RAGService
from aigility.rag.config import RAGConfig, EmbeddingConfig, VectorStoreConfig
import os

# ========================================
# 1. 初始化（只需一次）
# ========================================
config = RAGConfig(
    embedding=EmbeddingConfig(
        provider="zhipuai",
        model_name="embedding-3",
        api_key=os.getenv("ZHIPUAI_API_KEY", "")
    ),
    vector_store=VectorStoreConfig(
        provider="qdrant",
        collection_name="my_knowledge_base",
        url="http://localhost:6333"
    )
)

service = RAGService(config=config)

# ========================================
# 2. 添加文件
# ========================================
file_path = "/path/to/document.pdf"

# 添加文件，返回 file_hash 和 file_name
result = service.add_file(file_path)

print("✅ 文件添加成功")
print(f"file_hash: {result['file_hash']}")   # 重要！保存这个
print(f"file_name: {result['file_name']}")

# 保存到数据库
file_hash = result['file_hash']
file_name = result['file_name']

# ========================================
# 3. 搜索文件
# ========================================
results = service.search("查询内容")
print(f"搜索到 {len(results)} 字符")

# ========================================
# 4. 删除文件
# ========================================
# 方式1: 使用 file_hash（推荐）
service.delete_document(file_hash=file_hash)
print("✅ 文件已删除（使用 file_hash）")

# 方式2: 使用 file_name（谨慎）
# service.delete_document(file_name=file_name)

# ========================================
# 5. 恢复文件
# ========================================
# 方式1: 使用 file_hash（推荐）
service.restore_document(file_hash=file_hash)
print("✅ 文件已恢复（使用 file_hash）")

# 方式2: 使用 file_name（谨慎）
# service.restore_document(file_name=file_name)

# ========================================
# 💡 实际应用示例
# ========================================

print("\n" + "="*50)
print("实际应用示例")
print("="*50)

# 假设你有一个数据库表
# CREATE TABLE files (
#     id INT PRIMARY KEY,
#     file_hash VARCHAR(32),
#     file_name VARCHAR(255),
#     user_id INT,
#     created_at TIMESTAMP
# );

# 上传文件的处理流程
print("\n# 上传文件的处理流程:")
print("-"*50)

code = '''
def upload_file(file_path, user_id):
    """上传文件并保存到RAG"""

    # 1. 添加到 RAG
    result = service.add_file(file_path)
    file_hash = result['file_hash']
    file_name = result['file_name']

    # 2. 保存到数据库
    db.execute("""
        INSERT INTO files (file_hash, file_name, user_id, created_at)
        VALUES (?, ?, ?, NOW())
    """, (file_hash, file_name, user_id))

    # 3. 返回给前端
    return {
        "file_hash": file_hash,
        "file_name": file_name
    }

# 删除文件的处理流程
def delete_file(file_hash):
    """删除文件（软删除）"""

    # 1. 从数据库删除
    db.execute("DELETE FROM files WHERE file_hash=?", (file_hash,))

    # 2. 从 RAG 删除
    service.delete_document(file_hash=file_hash)

    return {"success": True}

# 恢复文件的处理流程
def restore_file(file_hash):
    """恢复文件"""

    # 1. 从数据库恢复
    db.execute("""
        INSERT INTO files (file_hash, file_name, user_id, created_at)
        VALUES (?, ?, ?, NOW())
    """, (file_hash, file_name, user_id))

    # 2. 从 RAG 恢复
    service.restore_document(file_hash=file_hash)

    return {"success": True}
'''

print(code)

print("\n" + "="*50)
print("✅ 完成！就是这么简单！")
print("="*50)
