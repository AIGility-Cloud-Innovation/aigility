# RAG 软删除功能使用指南

## 功能概述

RAG服务实现了完整的文档软删除功能，包括：
- ✅ 软删除文档（不物理删除，仅标记）
- ✅ 恢复已删除的文档
- ✅ 检索时自动过滤已删除的文档
- ✅ 查看已删除文档列表
- ✅ **`add_file` 返回文件信息**（新增）

## 重要改进 ⭐

### add_file 现在返回文件信息

```python
result = service.add_file("/path/to/document.pdf")

# 返回值包含：
{
    "file_id": "de27311c-6eb1-4737-ba92-d745f24b1cc0",  # 唯一标识符
    "file_hash": "abc123def456...",                      # 文件内容的MD5
    "file_name": "document.pdf",                         # 文件名
    "chunk_count": 5,                                    # 切片数量
    "status": "success"                                  # 状态
}
```

**关键改进：**
- 如果不提供 `file_id`，系统**自动生成UUID**
- 返回的 `file_id` 可用于后续的删除和恢复操作
- 不需要提前知道 `file_id`，从返回值中获取即可

## 使用方式

### 方式1: 系统自动生成 file_id（推荐）✨

```python
# 添加文件，不提供 file_id
result = service.add_file("/path/to/document.pdf")

# 获取系统自动生成的 file_id
file_id = result['file_id']
file_hash = result['file_hash']

# 保存 file_id 到你的数据库
# db.save_file_id(file_id, document_id)

# 后续使用 file_id 进行操作
service.delete_document(file_id=file_id)
service.restore_document(file_id=file_id)
```

**优点：**
- ✅ 不需要提前生成 ID
- ✅ 系统保证唯一性
- ✅ 适用于大多数场景

### 方式2: 外部系统提供 file_id

```python
# 外部系统已有一个 file_id
external_id = "user_123_file_456"

# 添加文件时传入 file_id
result = service.add_file(
    "/path/to/document.pdf",
    file_id=external_id
)

# 返回的 file_id 就是你传入的值
assert result['file_id'] == external_id

# 后续使用外部系统的 file_id 进行操作
service.delete_document(file_id=external_id)
```

**适用场景：**
- 外部系统已有文件 ID
- 需要关联外部系统的数据
- 多系统之间的数据同步

### 方式3: 使用 file_hash 操作

```python
# 添加文件
result = service.add_file("/path/to/document.pdf")
file_hash = result['file_hash']

# 使用 file_hash 删除
# 注意：相同内容的文件都会有相同的 hash
service.delete_document(file_hash=file_hash)
```

**特点：**
- 基于文件内容，内容相同则 hash 相同
- 适合内容去重场景
- 会删除所有相同内容的文件

## 完整工作流程

### 推荐的完整流程

```python
from aigility.rag.service import RAGService

service = RAGService(config)

# 1. 用户上传文件到你的系统
file_path = "/uploads/document.pdf"
user_id = 123

# 2. 添加到 RAG（不提供 file_id，让系统自动生成）
result = service.add_file(file_path)

# 3. 保存文件信息到你的数据库
file_id = result['file_id']
file_hash = result['file_hash']

db.execute("""
    INSERT INTO files (id, user_id, file_hash, file_name, status)
    VALUES (?, ?, ?, ?, 'active')
""", (file_id, user_id, file_hash, result['file_name']))

# 4. 返回给前端
return jsonify({
    "file_id": file_id,
    "status": "success"
})

# 5. 后续删除操作
def delete_file(file_id):
    # 从数据库删除
    db.execute("UPDATE files SET status='deleted' WHERE id=?", (file_id,))

    # 从 RAG 软删除
    service.delete_document(file_id=file_id)
```

## API 参考

### add_file()

```python
def add_file(self, file_path: str, file_id: Optional[str] = None) -> Dict[str, Any]
```

**参数：**
- `file_path`: 文件路径（必填）
- `file_id`: 外部系统的文件ID（可选）

**返回值：**
```python
{
    "file_id": str,      # 唯一标识符（自动生成或外部提供）
    "file_hash": str,    # 文件内容的MD5哈希
    "file_name": str,    # 文件名
    "chunk_count": int,  # 切片数量
    "status": str        # 状态: success/already_exists/no_chunks
}
```

### delete_document()

```python
def delete_document(
    file_id: Optional[str] = None,
    file_hash: Optional[str] = None,
    file_name: Optional[str] = None
) -> bool
```

**参数：**
- `file_id`: 文件ID（推荐，从 add_file 返回值获取）
- `file_hash`: 文件内容的MD5哈希
- `file_name`: 文件名（会删除所有同名文件）

**返回：**
- `bool`: 是否删除成功

### restore_document()

```python
def restore_document(
    file_id: Optional[str] = None,
    file_hash: Optional[str] = None,
    file_name: Optional[str] = None
) -> bool
```

**参数：**
- `file_id`: 文件ID（推荐）
- `file_hash`: 文件内容的MD5哈希
- `file_name`: 文件名（会恢复所有同名文件）

**返回：**
- `bool`: 是否恢复成功

## 数据库设计建议

### 表结构示例

```sql
CREATE TABLE files (
    id VARCHAR(36) PRIMARY KEY,          -- file_id (自动生成UUID)
    user_id INT NOT NULL,
    file_hash VARCHAR(32),               -- 文件内容hash
    file_name VARCHAR(255),              -- 文件名
    chunk_count INT,                     -- chunk数量
    status ENUM('active', 'deleted') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,

    INDEX idx_user_id (user_id),
    INDEX idx_file_hash (file_hash),
    INDEX idx_status (status)
);
```

### 使用示例

```python
# 添加文件
result = service.add_file(file_path)
file_id = result['file_id']

# 保存到数据库
db.insert('files', {
    'id': file_id,
    'user_id': user_id,
    'file_hash': result['file_hash'],
    'file_name': result['file_name'],
    'chunk_count': result['chunk_count']
})

# 删除文件
file = db.select('files', where={'id': file_id})
service.delete_document(file_id=file['id'])
db.update('files', {'status': 'deleted'}, where={'id': file_id})

# 恢复文件
service.restore_document(file_id=file_id)
db.update('files', {'status': 'active'}, where={'id': file_id})
```

## 常见问题

### Q: 不提供 file_id 时，系统如何保证唯一性？

A: 系统使用 UUID4 算法自动生成唯一标识符，冲突概率极低（约 1/2^122）。

### Q: file_hash 会冲突吗？

A: MD5哈希冲突概率极低（约 1/2^128），在实际应用中可以认为是唯一的。

### Q: 应该使用 file_id 还是 file_hash？

A:
- **使用 file_id**（推荐）：更精确，适合大多数场景
- **使用 file_hash**：需要内容去重时使用

### Q: 可以修改 file_id 吗？

A: 不建议。如果需要更改 file_id，应该删除后重新添加文件。

### Q: 如何获取已添加文件的 file_id？

A:
1. **添加时保存**：从 `add_file` 的返回值中获取并保存到数据库
2. **查询已有文件**：使用 `debug_list_all_documents()` 查看（仅用于调试）

## 测试

```bash
# 测试返回值功能
python examples/test_return_value.py

# 测试软删除功能
python examples/test_soft_delete.py

# 测试 file_id 功能
python examples/test_file_id.py
```
