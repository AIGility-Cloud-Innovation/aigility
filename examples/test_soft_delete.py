"""
软删除功能测试示例

演示如何使用RAGService的软删除功能：
1. 添加文档
2. 搜索文档
3. 软删除文档
4. 验证删除后的搜索结果
5. 恢复文档
6. 验证恢复后的搜索结果
"""

import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 设置为DEBUG级别以获取更多信息
    format='%(levelname)s: %(message)s'
)

def test_soft_delete():
    """测试软删除功能"""

    # 导入必要的模块
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from aigility.rag.service import RAGService
    from aigility.rag.config import RAGConfig, EmbeddingConfig, VectorStoreConfig, IngestionConfig

    print("=" * 60)
    print("🧪 软删除功能测试")
    print("=" * 60)

    # 配置RAG服务
    config = RAGConfig(
        embedding=EmbeddingConfig(
            provider="zhipuai",
            model_name="embedding-3",
            api_key=os.getenv("ZHIPUAI_API_KEY", "")
        ),
        vector_store=VectorStoreConfig(
            provider="qdrant",
            collection_name="test_soft_delete",
            url="http://localhost:6333"
        ),
        ingestion=IngestionConfig(
            chunk_size=500,
            chunk_overlap=50,
        ),
        search_top_k=5
    )

    # 初始化服务
    print("\n📦 初始化RAGService...")
    try:
        service = RAGService(config=config)
        print("   ✅ 初始化成功！")
    except Exception as e:
        print(f"   ❌ 初始化失败: {e}")
        return

    # 步骤1: 清空测试集合
    print("\n🗑️  清空测试集合...")
    service.clear_knowledge_base()

    # 步骤2: 添加测试文档
    print("\n📄 添加测试文档...")
    test_file = "./test_data/sample.txt"

    # 创建测试文件（如果不存在）
    os.makedirs("./test_data", exist_ok=True)
    if not os.path.exists(test_file):
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("""
这是一个关于人工智能的测试文档。

人工智能（AI）是计算机科学的一个分支，
致力于创建能够执行通常需要人类智能的任务的系统。

机器学习是人工智能的一个子集，
它使计算机能够从数据中学习并改进。

深度学习是机器学习的一种方法，
使用多层神经网络来处理复杂的数据。
            """)
        print(f"   ✅ 创建测试文件: {test_file}")

    try:
        service.add_file(test_file)
        print("   ✅ 文档添加成功！")
    except Exception as e:
        print(f"   ❌ 文档添加失败: {e}")
        return

    # 步骤3: 调试 - 列出所有文档
    print("\n🔍 调试：列出向量库中的所有文档...")
    all_docs = service.debug_list_all_documents()
    print(f"   总文档数: {len(all_docs)}")
    for doc in all_docs[:5]:  # 只显示前5个
        print(f"   - file_name: {doc.get('file_name')}, is_deleted: {doc.get('is_deleted')}, file_hash: {doc.get('file_hash')}")

    # 步骤4: 搜索文档（删除前）
    print("\n🔍 搜索测试（删除前）...")
    query = "什么是人工智能"
    results = service.search(query)
    print(f"   查询: {query}")
    print(f"   结果数: {len(results)}")
    if results:
        print(f"   结果预览: {results[:200]}...")
    else:
        print("   ⚠️ 未找到结果")

    # 步骤5: 软删除文档
    print("\n🗑️  软删除文档...")
    file_name = os.path.basename(test_file)
    print(f"   目标文件名: {file_name}")

    # 再次列出所有文档确认文件名
    print("\n🔍 调试：再次列出所有文档（删除前）...")
    all_docs_before = service.debug_list_all_documents()
    for doc in all_docs_before:
        print(f"   - {doc}")

    success = service.delete_document(file_name=file_name)
    if success:
        print(f"   ✅ 文档 '{file_name}' 已标记为删除")
    else:
        print(f"   ❌ 文档删除失败")

    # 列出删除后的文档状态
    print("\n🔍 调试：列出所有文档（删除后）...")
    all_docs_after = service.debug_list_all_documents()
    for doc in all_docs_after:
        print(f"   - {doc}")

    if not success:
        print("\n⚠️ 删除失败，但继续测试以观察搜索结果...")

    # 步骤6: 搜索文档（删除后）
    print("\n🔍 搜索测试（删除后）...")
    results_after_delete = service.search(query)
    print(f"   查询: {query}")
    print(f"   结果数: {len(results_after_delete)}")
    if not results_after_delete:
        print("   ✅ 没有找到结果（文档已被软删除）")

    # 步骤7: 查看已删除文档列表
    print("\n📋 已删除文档列表...")
    deleted_docs = service.get_deleted_documents()
    print(f"   已删除文档: {deleted_docs}")

    # 步骤8: 恢复文档
    print("\n♻️  恢复文档...")
    success = service.restore_document(file_name=file_name)
    if success:
        print(f"   ✅ 文档 '{file_name}' 已恢复")
    else:
        print(f"   ❌ 文档恢复失败")
        return

    # 步骤9: 搜索文档（恢复后）
    print("\n🔍 搜索测试（恢复后）...")
    results_after_restore = service.search(query)
    print(f"   查询: {query}")
    print(f"   结果数: {len(results_after_restore)}")
    if results_after_restore:
        print(f"   结果预览: {results_after_restore[:200]}...")
        print("   ✅ 找到结果（文档已恢复）")

    print("\n" + "=" * 60)
    print("✅ 软删除功能测试完成！")
    print("=" * 60)

    # 清理
    print("\n🧹 清理测试数据...")
    service.clear_knowledge_base()
    if os.path.exists(test_file):
        os.remove(test_file)
        print("   ✅ 测试文件已删除")


if __name__ == "__main__":
    test_soft_delete()
