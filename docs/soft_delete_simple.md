# RAG 软删除功能 - 简化版使用指南

## 📋 功能概述

RAG服务实现了完整的文档软删除功能，包括：
- ✅ 软删除文档（不物理删除，仅标记）
- ✅ 恢复已删除的文档
- ✅ 检索时自动过滤已删除的文档
- ✅ 查看已删除文档列表

## 🎯 核心改进

**简化设计：只使用 `file_hash` 和 `file_name`**

- `add_file` 返回 `file_hash` 和 `file_name`
- 删除和恢复只支持 `file_hash` 或 `file_name`
- 移除了 `file_id` 相关的所有逻辑

## 📝 API 说明

### 1. add_file()

添加文件到向量库，返回文件信息。

```python
def add_file(self, file_path: str) -> Dict[str, str]
```

**参数：**
- `file_path`: 文件路径

**返回值：**
```python
{
    "file_hash": str,  # 基于文件内容的MD5哈希（用于后续操作）
    "file_name": str   # 文件名
}
```

### 2. delete_document()

软删除文档（标记为已删除）。

```python
def delete_document(
    file_name: Optional[str] = None,
    file_hash: Optional[str] = None
) -> bool
```

**参数：**
- `file_hash`: 文件哈希值（推荐，基于内容）
- `file_name`: 文件名（会删除所有同名文件）

**返回：**
- `bool`: 是否删除成功

### 3. restore_document()

恢复已删除的文档。

```python
def restore_document(
    file_name: Optional[str] = None,
    file_hash: Optional[str] = None
) -> bool
```

**参数：**
- `file_hash`: 文件哈希值（推荐）
- `file_name`: 文件名（会恢复所有同名文件）

**返回：**
- `bool`: 是否恢复成功

## 🔄 智能文件处理逻辑

### 重新上传已删除文件

当用户删除文件后又重新上传相同内容的文件时，RAG 服务会：

1. **检测到相同的 `file_hash`**
2. **如果文件已删除**：自动恢复文件（`is_deleted=False`）
3. **更新文件名**：将文件名更新为新上传的文件名
4. **不添加新 chunks**：复用现有的向量数据

**示例场景**：
```python
# 1. 上传文件 document.pdf
result = service.add_file("/path/to/document.pdf")
# 返回: {"file_hash": "abc123", "file_name": "document.pdf"}

# 2. 删除文件
service.delete_document(file_hash="abc123")

# 3. 重新上传相同内容但不同名的文件
result = service.add_file("/path/to/renamed.pdf")
# 返回: {"file_hash": "abc123", "file_name": "renamed.pdf"}
# ✅ 旧文件已自动恢复
# ✅ 文件名已更新为 "renamed.pdf"
# ✅ 没有产生重复的 chunks
```

**优势**：
- 🚀 更高效：不需要重新 embedding
- 🧹 更整洁：不产生重复的向量数据
- 💾 更省空间：复用现有 chunks
- ✨ 更智能：自动处理，用户无感知

## 💡 完整使用流程

```python
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
file_path = "/path/to/document.pdf"
result = service.add_file(file_path)

# 返回值
file_hash = result['file_hash']  # 保存这个！
file_name = result['file_name']

print(f"文件已添加: {file_name}")
print(f"文件哈希: {file_hash}")

# 保存 file_hash 到数据库
# db.insert("files", {"file_hash": file_hash, "file_name": file_name})

# ========================================
# 步骤2: 搜索文件
# ========================================
results = service.search("查询内容")
print(f"搜索结果: {len(results)} 字符")

# ========================================
# 步骤3: 软删除文件
# ========================================
# 使用 file_hash 删除（推荐）
success = service.delete_document(file_hash=file_hash)
print(f"删除成功: {success}")

# 验证：搜索不到结果了
results = service.search("查询内容")
print(f"搜索结果: {len(results)} 字符（应该为0）")

# ========================================
# 步骤4: 恢复文件
# ========================================
# 使用 file_hash 恢复
success = service.restore_document(file_hash=file_hash)
print(f"恢复成功: {success}")

# 验证：又能搜索到了
results = service.search("查询内容")
print(f"搜索结果: {len(results)} 字符（应该有内容）")
```

## 💻 实际应用示例

### Flask API 示例

```python
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
    db.insert("files", {
        "file_hash": result["file_hash"],
        "file_name": result["file_name"],
        "user_id": current_user.id
    })

    return jsonify({
        "file_hash": result["file_hash"],
        "file_name": result["file_name"]
    })

# 2. 删除文件
@app.route("/files/<file_hash>", methods=["DELETE"])
def delete_file(file_hash):
    # 从数据库删除
    db.delete("files", where={"file_hash": file_hash})

    # 从 RAG 软删除
    success = service.delete_document(file_hash=file_hash)

    return jsonify({"success": success})

# 3. 恢复文件
@app.route("/files/<file_hash>/restore", methods=["POST"])
def restore_file(file_hash):
    # 从数据库恢复
    db.update("files", {"status": "active"}, where={"file_hash": file_hash})

    # 从 RAG 恢复
    success = service.restore_document(file_hash=file_hash)

    return jsonify({"success": success})
```

## 🗄️ 数据库设计建议

### 表结构

```sql
CREATE TABLE files (
    id INT PRIMARY KEY AUTO_INCREMENT,
    file_hash VARCHAR(32) NOT NULL UNIQUE,  -- 文件内容的MD5
    file_name VARCHAR(255) NOT NULL,
    user_id INT NOT NULL,
    status ENUM('active', 'deleted') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_file_hash (file_hash),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
);
```

## ⚠️ 注意事项

### file_hash vs file_name

| 方式 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **file_hash** | 基于内容，唯一性强 | 相同内容会有相同hash | ⭐ **强烈推荐** |
| **file_name** | 简单直接 | 同名文件会全部被删除/恢复 | ⚠️ 谨慎使用 |

### file_hash 的特性

- ✅ 相同内容的文件有相同的 `file_hash`
- ✅ 基于 MD5，冲突概率极低（约 1/2^128）
- ✅ **智能处理相同文件**：
   - 如果文件已存在且未删除：更新文件名为新的文件名
   - 如果文件已删除：自动恢复文件（`is_deleted=False`）并更新文件名
   - 不会重复添加 chunks，保持向量库整洁
- ✅ **删除后重新上传**：上传相同内容的文件会自动恢复，无需手动调用 `restore_document`

### 使用建议

1. **推荐使用 `file_hash`**
   ```python
   result = service.add_file(file_path)
   file_hash = result['file_hash']

   # 后续使用 file_hash 操作
   service.delete_document(file_hash=file_hash)
   service.restore_document(file_hash=file_hash)
   ```

2. **谨慎使用 `file_name`**
   ```python
   # 只有确定没有同名文件时才使用
   service.delete_document(file_name="document.pdf")
   ```

## 🧪 测试

运行测试文件查看完整示例：

```bash
python examples/usage_simple.py
```

## 📚 相关文件

- **使用示例**: [examples/usage_simple.py](examples/usage_simple.py)
- **完整测试**: [examples/test_soft_delete.py](examples/test_soft_delete.py)
- **搜索测试**: [examples/test_simple_search.py](examples/test_simple_search.py)
