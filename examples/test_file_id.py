"""
测试 file_id 功能

演示如何使用外部系统的 file_id 来唯一标识和管理文档
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aigility.rag.service import RAGService
from aigility.rag.config import RAGConfig, EmbeddingConfig, VectorStoreConfig, IngestionConfig

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_file_id():
    """测试使用 file_id 管理同名文件"""

    # 配置RAG服务
    config = RAGConfig(
        embedding=EmbeddingConfig(
            provider="zhipuai",
            model_name="embedding-3",
            api_key=os.getenv("ZHIPUAI_API_KEY", "")
        ),
        vector_store=VectorStoreConfig(
            provider="qdrant",
            collection_name="test_file_id",
            url="http://localhost:6333"
        ),
        ingestion=IngestionConfig(
            chunk_size=500,
            chunk_overlap=50,
        ),
        search_top_k=5
    )

    print("=" * 60)
    print("🧪 测试 file_id 功能")
    print("=" * 60)

    # 初始化服务
    print("\n📦 初始化RAGService...")
    service = RAGService(config=config)

    # 清空
    print("\n🗑️  清空测试集合...")
    service.clear_knowledge_base()

    # 创建测试目录
    os.makedirs("./test_data", exist_ok=True)

    # 场景：多个同名文件，但内容不同
    print("\n📄 场景：添加多个同名文件（内容不同）...")

    # 文件1: 来自用户A的 document.txt
    file1_path = "./test_data/userA_document.txt"
    with open(file1_path, "w", encoding="utf-8") as f:
        f.write("这是用户A的文档内容，包含重要信息。")

    # 文件2: 来自用户B的 document.txt（同名但内容不同）
    file2_path = "./test_data/userB_document.txt"
    with open(file2_path, "w", encoding="utf-8") as f:
        f.write("这是用户B的文档内容，完全不同的信息。")

    # 使用外部系统的 file_id 来区分
    file_id_1 = "user_a_123"  # 外部系统分配的ID
    file_id_2 = "user_b_456"  # 外部系统分配的ID

    print(f"   添加文件1: document.pdf (file_id={file_id_1})")
    service.add_file(file1_path, file_id=file_id_1)
    print("   ✅ 文件1添加成功！")

    print(f"   添加文件2: document.pdf (file_id={file_id_2})")
    service.add_file(file2_path, file_id=file_id_2)
    print("   ✅ 文件2添加成功！")

    # 列出所有文档
    print("\n🔍 列出所有文档...")
    all_docs = service.debug_list_all_documents()
    print(f"   总文档数: {len(all_docs)}")
    for doc in all_docs:
        print(f"   - file_name: {doc.get('file_name')}, file_id: {doc.get('file_id')}, is_deleted: {doc.get('is_deleted')}")

    # 测试1: 使用 file_id 删除特定文件
    print(f"\n🗑️  使用 file_id 删除用户A的文档...")
    success = service.delete_document(file_id=file_id_1)
    if success:
        print(f"   ✅ 成功删除 file_id={file_id_1} 的文档")

    # 列出删除后的文档
    print("\n🔍 删除后的文档列表...")
    all_docs = service.debug_list_all_documents()
    for doc in all_docs:
        print(f"   - file_name: {doc.get('file_name')}, file_id: {doc.get('file_id')}, is_deleted: {doc.get('is_deleted')}")

    # 测试2: 使用 file_id 恢复文档
    print(f"\n♻️  恢复 file_id={file_id_1} 的文档...")
    success = service.restore_document(file_id=file_id_1)
    if success:
        print(f"   ✅ 成功恢复文档")

    # 测试3: 使用 file_name 会删除所有同名文件
    print("\n⚠️  测试：使用 file_name 删除...")
    print("   注意：这会删除所有名为 'userA_document.txt' 或 'userB_document.txt' 的文件！")
    success = service.delete_document(file_name="userA_document.txt")
    if success:
        print("   ✅ 同名文件已删除")

    print("\n🔍 最终文档列表...")
    all_docs = service.debug_list_all_documents()
    print(f"   总文档数: {len(all_docs)}")
    for doc in all_docs:
        print(f"   - file_name: {doc.get('file_name')}, file_id: {doc.get('file_id')}, is_deleted: {doc.get('is_deleted')}")

    # 清理
    print("\n🧹 清理测试数据...")
    service.clear_knowledge_base()
    os.remove(file1_path)
    os.remove(file2_path)
    print("   ✅ 清理完成")

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)

    print("\n📝 总结：")
    print("   ✅ file_id 是最精确的标识符，推荐使用")
    print("   ✅ 可以处理多个同名文件的场景")
    print("   ⚠️  使用 file_name 会影响所有同名文件")
    print("   ℹ️  file_hash 基于内容，相同内容会有相同hash")


if __name__ == "__main__":
    test_file_id()
