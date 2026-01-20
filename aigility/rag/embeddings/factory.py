# [核心] 嵌入模型工厂
"""
嵌入模型工厂 - 根据配置动态加载对应的嵌入模型

支持的 provider:
- huggingface: 本地 HuggingFace 模型
- dashscope: 阿里云 DashScope 服务
- openai: OpenAI API
- zhipuai: 智谱 AI 嵌入模型
"""

from typing import TYPE_CHECKING
from ..config import EmbeddingConfig

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings


class EmbeddingFactory:
    """嵌入模型工厂（核心：根据 provider 创建对应实例）"""

    @staticmethod
    def get_embedding_model(config: EmbeddingConfig) -> "Embeddings":
        """
        工厂核心方法：根据配置的 provider 返回对应嵌入模型实例
        
        Args:
            config: 嵌入模型配置
            
        Returns:
            标准化的 LangChain Embeddings 实例
        """
        provider = config.provider
        
        if provider == "huggingface":
            from .huggingface import HuggingFaceEmbeddingAdapter
            embedding_model = HuggingFaceEmbeddingAdapter.load(config)
            
        elif provider == "dashscope":
            from .dashscope import DashScopeEmbeddingAdapter
            embedding_model = DashScopeEmbeddingAdapter.load(config)
            
        elif provider == "openai":
            # OpenAI 使用 LangChain 官方适配器
            try:
                from langchain_openai import OpenAIEmbeddings
            except ImportError:
                raise ImportError(
                    "使用 OpenAI 嵌入模型需要安装 langchain-openai: "
                    "pip install langchain-openai"
                )
            embedding_model = OpenAIEmbeddings(
                model=config.model_name,
                openai_api_key=config.get_api_key(),
                openai_api_base=config.get_base_url(),
            )

        elif provider == "zhipuai":
            from .zai import ZhipuAiEmbeddingAdapter
            embedding_model = ZhipuAiEmbeddingAdapter.load(config)

        else:
            raise ValueError(
                f"不支持的嵌入模型：{provider} | "
                f"支持的类型：['huggingface', 'dashscope', 'openai', 'zhipuai']"
            )
        
        # 校验接口
        if not hasattr(embedding_model, "embed_query") or not hasattr(embedding_model, "embed_documents"):
            raise RuntimeError(f"{provider} 适配器未实现 LangChain Embeddings 核心接口")
        
        return embedding_model


__all__ = ["EmbeddingFactory"]

# ====================== 测试代码 ======================
if __name__ == "__main__":
    import os
    import sys
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _package_dir = os.path.dirname(os.path.dirname(_current_dir))
    if _package_dir not in sys.path:
        sys.path.insert(0, _package_dir)
    
    from aigility.rag.config import EmbeddingConfig

    print("=" * 60)
    print("嵌入模型工厂测试")
    print("=" * 60)

    # 测试文本
    test_query = "人工智能技术正在快速发展，为各行各业带来了巨大的变革。"
    test_documents = [
        "机器学习是人工智能的一个重要分支。",
        "深度学习基于神经网络，能够处理复杂的模式识别任务。",
        "自然语言处理让计算机能够理解和生成人类语言。"
    ]

    # ========== 测试智谱 AI (Zhipu AI) Embedding ==========
    print("\n【测试 1】智谱 AI Embedding 模型")
    print("-" * 60)

    try:
        # 配置智谱 AI
        zhipuai_config = EmbeddingConfig(
            provider="zhipuai",
            model_name="embedding-3",
            api_key=os.getenv("ZHIPUAI_API_KEY", "")  # 从环境变量读取
        )

        # 检查是否配置了 API Key
        if not zhipuai_config.api_key:
            print("⚠️  跳过智谱 AI 测试：未设置 ZHIPUAI_API_KEY 环境变量")
            print("   提示：export ZHIPUAI_API_KEY='your-api-key'")
        else:
            print(f"✓ 配置: provider={zhipuai_config.provider}")
            print(f"✓ 模型: {zhipuai_config.model_name}")

            # 获取嵌入模型实例
            zhipuai_model = EmbeddingFactory.get_embedding_model(zhipuai_config)
            print(f"✓ 模型类型: {type(zhipuai_model).__name__}")

            # 测试单文本嵌入
            print(f"\n📝 测试单文本嵌入:")
            print(f"   文本: {test_query[:30]}...")
            query_embedding = zhipuai_model.embed_query(test_query)
            print(f"✓ 嵌入维度: {len(query_embedding)}")
            print(f"✓ 前500个值: {query_embedding[:500]}")

            # 测试批量文本嵌入
            print(f"\n📚 测试批量文本嵌入:")
            print(f"   文档数量: {len(test_documents)}")
            doc_embeddings = zhipuai_model.embed_documents(test_documents)
            print(f"✓ 嵌入数量: {len(doc_embeddings)}")
            print(f"✓ 每个嵌入维度: {[len(emb) for emb in doc_embeddings]}")
            for i, emb in enumerate(doc_embeddings):
                print(f"   文档 {i+1} 前500个值: {emb[:500]}")

            print("\n✅ 智谱 AI 测试通过！")

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("   请安装: pip install zhipuai-sdk")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)