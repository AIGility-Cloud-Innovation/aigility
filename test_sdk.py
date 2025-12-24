"""
本地测试 aigility-python SDK
"""

print("=" * 60)
print("🧪 测试 aigility-python SDK")
print("=" * 60)

# 测试 1: 导入模块
print("\n📦 测试1: 导入模块...")
try:
    from aigility.rag import RAGService, RAGConfig, EmbeddingConfig, VectorStoreConfig
    print("   ✅ 导入成功！")
except ImportError as e:
    print(f"   ❌ 导入失败: {e}")
    exit(1)

# 测试 2: 创建配置
print("\n⚙️ 测试2: 创建配置...")
try:
    config = RAGConfig(
        embedding=EmbeddingConfig(
            provider="huggingface",
            model_name="BAAI/bge-small-zh-v1.5"
        ),
        vector_store=VectorStoreConfig(
            provider="chroma",
            persist_path="./test_chroma_db"
        )
    )
    print(f"   ✅ 配置创建成功！")
    print(f"   - Embedding: {config.embedding.provider} / {config.embedding.model_name}")
    print(f"   - VectorStore: {config.vector_store.provider}")
except Exception as e:
    print(f"   ❌ 配置创建失败: {e}")
    exit(1)

# 测试 3: 配置方法
print("\n🔧 测试3: 配置方法...")
try:
    api_key = config.embedding.get_api_key()
    base_url = config.embedding.get_base_url()
    persist_path = config.vector_store.get_persist_path()
    print(f"   ✅ get_api_key(): {api_key}")
    print(f"   ✅ get_base_url(): {base_url}")
    print(f"   ✅ get_persist_path(): {persist_path}")
except Exception as e:
    print(f"   ❌ 配置方法失败: {e}")

# 测试 4: 版本号
print("\n📋 测试4: 版本信息...")
try:
    import aigility
    print(f"   ✅ 版本: {aigility.__version__}")
except Exception as e:
    print(f"   ⚠️ 获取版本失败: {e}")

print("\n" + "=" * 60)
print("✅ SDK 基础测试完成！")
print("=" * 60)

# 可选：完整 RAG 测试（需要更多依赖）
print("\n💡 提示：如果要测试完整 RAG 功能，需要安装额外依赖：")
print("   pip3 install sentence-transformers chromadb langchain-huggingface langchain-chroma")

# 初始化服务
service = RAGService(config=config)

# 添加文件
service.add_file("test.pdf")

# 检索
result = service.search("你的问题")
print(result)
