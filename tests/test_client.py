"""
TiMEM SDK 客户端测试

基础单元测试示例
"""

import pytest
from timem import TiMEMClient, AsyncTiMEMClient
from timem.exceptions import ValidationError, AuthenticationError


class TestTiMEMClient:
    """同步客户端测试"""
    
    def test_client_initialization(self):
        """测试客户端初始化"""
        client = TiMEMClient(
            api_key="test-key",
            base_url="http://localhost:8001"
        )
        assert client.api_key == "test-key"
        assert client.base_url == "http://localhost:8001"
        client.close()
    
    def test_client_requires_api_key(self):
        """测试客户端需要 API Key"""
        with pytest.raises(ValidationError):
            TiMEMClient(api_key="")
    
    def test_client_context_manager(self):
        """测试上下文管理器"""
        with TiMEMClient(api_key="test-key") as client:
            assert client is not None
    
    def test_learn_requires_domain(self):
        """测试 learn 需要 domain"""
        client = TiMEMClient(api_key="test-key")
        with pytest.raises(ValidationError):
            client.learn(domain="")
        client.close()
    
    def test_recall_requires_context(self):
        """测试 recall 需要 context"""
        client = TiMEMClient(api_key="test-key")
        with pytest.raises(ValidationError):
            client.recall(context={})
        client.close()
    
    def test_add_memory_requires_content(self):
        """测试 add_memory 需要 content"""
        client = TiMEMClient(api_key="test-key")
        with pytest.raises(ValidationError):
            client.add_memory(
                user_id=123,
                domain="test",
                content=None
            )
        client.close()


class TestAsyncTiMEMClient:
    """异步客户端测试"""
    
    def test_async_client_initialization(self):
        """测试异步客户端初始化"""
        client = AsyncTiMEMClient(
            api_key="test-key",
            base_url="http://localhost:8001"
        )
        assert client.api_key == "test-key"
        assert client.base_url == "http://localhost:8001"
    
    def test_async_client_requires_api_key(self):
        """测试异步客户端需要 API Key"""
        with pytest.raises(ValidationError):
            AsyncTiMEMClient(api_key="")
    
    @pytest.mark.asyncio
    async def test_async_client_context_manager(self):
        """测试异步上下文管理器"""
        async with AsyncTiMEMClient(api_key="test-key") as client:
            assert client is not None
    
    @pytest.mark.asyncio
    async def test_async_learn_requires_domain(self):
        """测试异步 learn 需要 domain"""
        async with AsyncTiMEMClient(api_key="test-key") as client:
            with pytest.raises(ValidationError):
                await client.learn(domain="")
    
    @pytest.mark.asyncio
    async def test_async_recall_requires_context(self):
        """测试异步 recall 需要 context"""
        async with AsyncTiMEMClient(api_key="test-key") as client:
            with pytest.raises(ValidationError):
                await client.recall(context={})
    
    @pytest.mark.asyncio
    async def test_async_batch_learn(self):
        """测试批量学习"""
        async with AsyncTiMEMClient(api_key="test-key") as client:
            # 测试空列表
            results = await client.batch_learn(domains=[])
            assert results == []
    
    @pytest.mark.asyncio
    async def test_async_batch_add_memories(self):
        """测试批量添加记忆"""
        async with AsyncTiMEMClient(api_key="test-key") as client:
            # 测试空列表
            results = await client.batch_add_memories(memories=[])
            assert results == []


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    @pytest.mark.asyncio
    async def test_learn_async(self):
        """测试便捷学习函数"""
        from timem import learn_async
        
        # 测试需要 API key
        with pytest.raises(ValidationError):
            await learn_async(api_key="", domain="test")
    
    @pytest.mark.asyncio
    async def test_recall_async(self):
        """测试便捷召回函数"""
        from timem import recall_async
        
        # 测试需要 API key
        with pytest.raises(ValidationError):
            await recall_async(api_key="", context={"test": "test"})


# 集成测试标记
@pytest.mark.integration
class TestIntegration:
    """集成测试（需要运行的 TiMEM Engine）"""
    
    def test_health_check(self):
        """测试健康检查"""
        # 跳过，因为需要实际的服务
        pytest.skip("Requires running TiMEM Engine")
    
    @pytest.mark.asyncio
    async def test_async_health_check(self):
        """测试异步健康检查"""
        # 跳过，因为需要实际的服务
        pytest.skip("Requires running TiMEM Engine")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

