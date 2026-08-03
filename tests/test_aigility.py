"""
AIGility 模块单元测试

测试基础功能和模块导入
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAIGilityImport:
    """测试 AIGility 模块导入"""

    def test_import_aigility(self):
        """测试导入 aigility 主模块"""
        import aigility
        assert aigility is not None

    def test_import_version(self):
        """测试版本号"""
        import aigility
        assert hasattr(aigility, '__version__')
        assert aigility.__version__ == '0.1.3'

    def test_import_rag_module(self):
        """测试导入 RAG 模块"""
        from aigility import rag
        assert rag is not None

    def test_import_rag_service(self):
        """测试导入 RAGService"""
        from aigility.rag import RAGService
        assert RAGService is not None

    def test_import_rag_config(self):
        """测试导入 RAGConfig"""
        from aigility.rag import RAGConfig
        assert RAGConfig is not None


class TestRAGConfig:
    """测试 RAG 配置"""

    def test_rag_config_creation(self):
        """测试创建 RAGConfig"""
        from aigility.rag import RAGConfig, EmbeddingConfig

        config = RAGConfig(
            embedding=EmbeddingConfig(
                provider="openai",
                model_name="text-embedding-ada-002"
            )
        )
        assert config.embedding.provider == "openai"
        assert config.embedding.model_name == "text-embedding-ada-002"

    def test_embedding_config_defaults(self):
        """测试 EmbeddingConfig 默认值"""
        from aigility.rag import EmbeddingConfig

        config = EmbeddingConfig(provider="openai")
        assert config.provider == "openai"
        assert config.model_name is not None


class TestUsageStats:
    """测试使用量统计"""

    def test_usage_stats_creation(self):
        """测试创建 UsageStats"""
        try:
            from aigility.rag import UsageStats
            stats = UsageStats()
            assert stats is not None
        except ImportError:
            pytest.skip("UsageStats not available")

    def test_usage_stats_properties(self):
        """测试 UsageStats 属性"""
        try:
            from aigility.rag import UsageStats
            stats = UsageStats()
            assert hasattr(stats, 'total_tokens')
            assert hasattr(stats, 'embedding')
            assert hasattr(stats, 'rerank')
        except ImportError:
            pytest.skip("UsageStats not available")

    def test_usage_stats_total_tokens(self):
        """测试 total_tokens 计算"""
        try:
            from aigility.rag import UsageStats, TokenUsage
            stats = UsageStats(
                embedding=TokenUsage(input_tokens=100, total_tokens=150),
                rerank=TokenUsage(input_tokens=50, total_tokens=80)
            )
            assert stats.total_tokens == 230  # 150 + 80
        except ImportError:
            pytest.skip("TokenUsage not available")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])