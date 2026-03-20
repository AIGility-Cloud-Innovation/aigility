"""
简单的使用示例：软删除功能
"""

from aigility.rag.service import RAGService
from aigility.rag.config import RAGConfig, EmbeddingConfig, VectorStoreConfig
import os

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
print("📚 软删除功能使用示例")
print("=" * 60)

# ========================================
# 步骤1: 添加文件
# ========================================
print("\n步骤1: 添加文件")
print("-" * 60)

file_path = "/path/to/document.pdf"
result = service.add_file(file_path)

print(f"✅ 文件添加成功！")
print(f"   file_hash: {result['file_hash']}")      # 保存这个！用于后续操作
print(f"   file_name: {result['file_name']}")

# 保存到你的数据库或内存
file_hash = result['file_hash']
file_name = result['file_name']

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

# 使用 file_hash 删除（推荐）
success = service.delete_document(file_hash=file_hash)
print(f"✅ 文件已删除: {success}")

# 验证：搜索不到结果了
results = service.search("查询内容")
print(f"   搜索结果: {len(results)} 字符（应该为0）")

# ========================================
# 步骤4: 恢复文件
# ========================================
print("\n步骤4: 恢复文件")
print("-" * 60)

# 使用 file_hash 恢复
success = service.restore_document(file_hash=file_hash)
print(f"✅ 文件已恢复: {success}")

# 验证：又能搜索到了
results = service.search("查询内容")
print(f"   搜索结果: {len(results)} 字符（应该有内容）")

print("\n" + "=" * 60)
print("✅ 完成！")
print("=" * 60)

print("\n💡 提示：")
print("   - 使用 file_hash 删除/恢复更精确")
print("   - 使用 file_name 会影响所有同名文件")
print("   - 返回的 file_hash 要保存到数据库")

# ========================================
# 实际应用示例（Flask）
# ========================================
print("\n" + "=" * 60)
print("💻 实际应用示例（Flask）")
print("=" * 60)

example_code = '''
# Flask API 示例
from flask import Flask, request, jsonify
from aigility.rag.service import RAGService

app = Flask(__name__)
service = RAGService(config)

# 1. 上传文件
@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files["file"]
    file_path = f"/tmp/{file.filename}"
    file.save(file_path)

    # 添加到 RAG
    result = service.add_file(file_path)

    # 保存到数据库
    # db.insert("files", {
    #     "file_hash": result["file_hash"],
    #     "file_name": result["file_name"],
    #     "user_id": current_user.id
    # })

    return jsonify({
        "file_hash": result["file_hash"],
        "file_name": result["file_name"]
    })

# 2. 删除文件
@app.route("/files/<file_hash>", methods=["DELETE"])
def delete_file(file_hash):
    # 从数据库删除
    # db.delete("files", where={"file_hash": file_hash})

    # 从 RAG 软删除
    success = service.delete_document(file_hash=file_hash)

    return jsonify({"success": success})

# 3. 恢复文件
@app.route("/files/<file_hash>/restore", methods=["POST"])
def restore_file(file_hash):
    # 从数据库恢复
    # db.update("files", {"status": "active"}, where={"file_hash": file_hash})

    # 从 RAG 恢复
    success = service.restore_document(file_hash=file_hash)

    return jsonify({"success": success})
'''

print(example_code)
