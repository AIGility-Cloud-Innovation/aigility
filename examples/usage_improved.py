"""
改进后的使用方式示例

展示如何使用 add_file 返回值进行后续操作
"""

import os
from aigility.rag.service import RAGService
from aigility.rag.config import RAGConfig, EmbeddingConfig, VectorStoreConfig

# 初始化服务
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

print("=" * 60)
print("💡 改进后的使用方式")
print("=" * 60)

# ========================================
# 场景1: 外部系统有 file_id
# ========================================
print("\n✅ 场景1: 外部系统已有 file_id")
print("-" * 60)

# 假设从外部系统获得的 file_id
external_file_id = "user_123_file_456"

# 添加文件时传入 file_id
file_path = "/path/to/document.pdf"
result = service.add_file(file_path, file_id=external_file_id)

print(f"添加文件成功:")
print(f"  file_id: {result['file_id']}")
print(f"  file_hash: {result['file_hash']}")
print(f"  file_name: {result['file_name']}")
print(f"  chunk_count: {result['chunk_count']}")

# 后续操作使用返回的 file_id
service.delete_document(file_id=result['file_id'])
print(f"\n使用返回的 file_id 删除文件: {result['file_id']}")

# ========================================
# 场景2: 外部系统没有 file_id
# ========================================
print("\n✅ 场景2: 外部系统没有 file_id")
print("-" * 60)

# 不提供 file_id，系统自动生成
result = service.add_file(file_path)

auto_file_id = result['file_id']
print(f"系统自动生成的 file_id: {auto_file_id}")
print(f"file_hash: {result['file_hash']}")

# 保存这个 file_id 到数据库
# db.save_file_mapping(auto_file_id, file_path)

# 后续操作使用这个 file_id
service.delete_document(file_id=auto_file_id)
print(f"\n使用自动生成的 file_id 删除文件: {auto_file_id}")

# ========================================
# 场景3: 使用 file_hash 进行操作
# ========================================
print("\n✅ 场景3: 使用 file_hash 进行操作")
print("-" * 60)

result = service.add_file(file_path)
file_hash = result['file_hash']

print(f"file_hash: {file_hash}")
print(f"注意: 相同内容的文件会有相同的 hash")

# 可以使用 file_hash 删除（相同内容的文件都会被删除）
service.delete_document(file_hash=file_hash)
print(f"\n使用 file_hash 删除文件")

# ========================================
# 场景4: 建议的数据库表结构
# ========================================
print("\n✅ 场景4: 建议的数据库表结构")
print("-" * 60)

print("""
CREATE TABLE files (
    id VARCHAR(36) PRIMARY KEY,        -- 外部系统的 file_id
    file_hash VARCHAR(32),             -- RAG 返回的 file_hash
    file_name VARCHAR(255),            -- RAG 返回的 file_name
    chunk_count INT,                   -- RAG 返回的 chunk_count
    uploaded_at TIMESTAMP,             -- 上传时间
    user_id INT,                       -- 上传用户
    status ENUM('active', 'deleted'),  -- 状态
    INDEX idx_file_hash (file_hash),
    INDEX idx_user_id (user_id)
);

# 使用流程
# 1. 用户上传文件，你的系统生成一个 file_id
# 2. 调用 RAG add_file(file_path, file_id)
# 3. 保存返回结果到数据库
# 4. 后续删除/恢复时，使用数据库中的 file_id 或 file_hash
""")

print("=" * 60)
