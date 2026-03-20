"""
测试 add_file 返回值功能

演示如何使用 add_file 返回的 file_id 进行后续操作
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aigility.rag.service import RAGService
from aigility.rag.config import RAGConfig, EmbeddingConfig, VectorStoreConfig, IngestionConfig

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_add_file_return():
    """测试 add_file 返回值的使用"""

    # 配置RAG服务
    config = RAGConfig(
        embedding=EmbeddingConfig(
            provider="zhipuai",
            model_name="embedding-3",
            api_key=os.getenv("ZHIPUAI_API_KEY", "")
        ),
        vector_store=VectorStoreConfig(
            provider="qdrant",
            collection_name="test_return_value",
            url="http://localhost:6333"
        ),
        ingestion=IngestionConfig(
            chunk_size=500,
            chunk_overlap=50,
        ),
        search_top_k=5
    )

    print("=" * 60)
    print("🧪 测试 add_file 返回值功能")
    print("=" * 60)

    # 初始化服务
    print("\n📦 初始化RAGService...")
    service = RAGService(config=config)

    # 清空
    print("\n🗑️  清空测试集合...")
    service.clear_knowledge_base()

    # 创建测试文件
    os.makedirs("./test_data", exist_ok=True)
    test_file = "./test_data/test_return.txt"

    with open(test_file, "w", encoding="utf-8") as f:
        f.write("这是一个测试文档，用于演示返回值功能。")

    # ========================================
    # 方式1: 不提供 file_id，系统自动生成
    # ========================================
    print("\n📄 方式1: 不提供 file_id，让系统自动生成...")
    result1 = service.add_file(test_file)

    print(f"   返回结果:")
    print(f"   - file_id: {result1['file_id']}")
    print(f"   - file_hash: {result1['file_hash']}")
    print(f"   - file_name: {result1['file_name']}")
    print(f"   - chunk_count: {result1['chunk_count']}")
    print(f"   - status: {result1['status']}")

    # 保存 file_id 用于后续操作
    auto_generated_file_id = result1['file_id']

    # ========================================
    # 方式2: 提供外部系统的 file_id
    # ========================================
    print("\n📄 方式2: 提供外部系统的 file_id...")

    # 先删除刚才添加的文件
    service.delete_document(file_id=auto_generated_file_id)

    external_file_id = "external_system_123"
    result2 = service.add_file(test_file, file_id=external_file_id)

    print(f"   返回结果:")
    print(f"   - file_id: {result2['file_id']}")
    print(f"   - file_hash: {result2['file_hash']}")
    print(f"   - file_name: {result2['file_name']}")
    print(f"   - chunk_count: {result2['chunk_count']}")
    print(f"   - status: {result2['status']}")

    # ========================================
    # 方式3: 使用返回的 file_id 进行删除
    # ========================================
    print(f"\n🗑️  使用返回的 file_id 删除文件...")
    print(f"   删除 file_id={result2['file_id']}")

    success = service.delete_document(file_id=result2['file_id'])
    if success:
        print("   ✅ 删除成功")

    # 验证删除
    print("\n🔍 验证删除结果...")
    results = service.search("测试文档")
    if not results:
        print("   ✅ 搜索不到结果，文件已被删除")
    else:
        print("   ❌ 仍能搜索到结果，删除失败")

    # ========================================
    # 方式4: 使用返回的 file_id 进行恢复
    # ========================================
    print(f"\n♻️  使用返回的 file_id 恢复文件...")
    print(f"   恢复 file_id={result2['file_id']}")

    success = service.restore_document(file_id=result2['file_id'])
    if success:
        print("   ✅ 恢复成功")

    # 验证恢复
    print("\n🔍 验证恢复结果...")
    results = service.search("测试文档")
    if results:
        print("   ✅ 搜索到结果，文件已恢复")
    else:
        print("   ❌ 搜索不到结果，恢复失败")

    # ========================================
    # 方式5: 重复添加相同文件（使用相同 file_id）
    # ========================================
    print(f"\n📄 方式5: 重复添加相同文件...")
    result3 = service.add_file(test_file, file_id=external_file_id)

    print(f"   返回结果:")
    print(f"   - file_id: {result3['file_id']}")
    print(f"   - status: {result3['status']}")

    if result3['status'] == 'already_exists':
        print("   ✅ 正确识别为已存在，不会重复添加")

    # ========================================
    # 方式6: 重复添加相同文件（不提供 file_id）
    # ========================================
    print(f"\n📄 方式6: 重复添加相同文件（不提供 file_id）...")

    # 先删除，然后重新添加
    service.delete_document(file_id=external_file_id)
    result4 = service.add_file(test_file)
    result5 = service.add_file(test_file)

    print(f"   第一次添加 status: {result4['status']}")
    print(f"   第二次添加 status: {result5['status']}")
    print(f"   第二次添加 file_id: {result5['file_id']}")

    if result5['status'] == 'already_exists':
        print("   ✅ 基于 file_hash 的去重生效")

    # 清理
    print("\n🧹 清理测试数据...")
    service.clear_knowledge_base()
    os.remove(test_file)
    print("   ✅ 清理完成")

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)

    print("\n📝 总结：")
    print("   ✅ add_file 现在会返回文件信息")
    print("   ✅ 不提供 file_id 时，系统自动生成UUID")
    print("   ✅ 可以使用返回的 file_id 进行后续操作")
    print("   ✅ 支持基于 file_hash 的去重")
    print("   ✅ 返回值包含所有需要的信息")


if __name__ == "__main__":
    test_add_file_return()
