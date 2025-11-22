"""
TiMEM简化使用示例

展示如何使用简化的API，无需了解enhanced等复杂概念。
"""

import asyncio
import logging
from timem import create_client, AsyncTiMEMClient


async def simple_usage_example():
    """简化使用示例 - 用户无需了解增强功能"""
    print("=== TiMEM简化使用示例 ===")
    
    # 方式1：使用便利函数（推荐）
    async with create_client(
        api_key="your_timem_api_key",
        base_url="http://localhost:8001",
        enable_enhanced_features=True  # 默认启用增强功能
    ) as client:
        
        # 1. 添加记忆
        print("1. 添加记忆...")
        memory_result = await client.add_memory(
            user_id=12345,
            domain="aicv",
            content={
                "message": "用户询问简历优化建议",
                "context": {"job_title": "软件工程师"}
            },
            layer_type="L1",
            tags=["简历", "优化", "建议"],
            keywords=["简历", "优化", "软件工程师"]
        )
        print(f"记忆添加结果: {memory_result}")
        
        # 2. 学习生成规则
        print("2. 学习生成规则...")
        learn_result = await client.learn(
            domain="aicv",
            min_case_count=3,
            min_adoption_rate=0.6,
            min_confidence_score=0.5,
            strategy="adaptive",
            user_id="12345"
        )
        print(f"学习结果: {learn_result}")
        
        # 3. 召回规则
        print("3. 召回规则...")
        recall_result = await client.recall(
            context={
                "job_title": "软件工程师",
                "issue_type": "技能描述",
                "section": "工作经验"
            },
            domain="aicv",
            top_k=5,
            min_confidence=0.5,
            user_id="12345"
        )
        print(f"召回结果: {recall_result}")
        
        # 4. 获取健康状态（增强功能）
        print("4. 获取健康状态...")
        health = await client.get_health_status()
        print(f"健康状态: {health['status']}")
        
        # 5. 获取客户端统计（增强功能）
        print("5. 获取客户端统计...")
        stats = client.get_client_stats()
        print(f"总请求数: {stats['client_stats']['total_requests']}")
        print(f"成功率: {stats['client_stats']['successful_requests'] / max(stats['client_stats']['total_requests'], 1):.2%}")


async def advanced_usage_example():
    """高级使用示例 - 需要更多控制时"""
    print("\n=== 高级使用示例 ===")
    
    # 方式2：直接使用AsyncTiMEMClient（更多控制）
    async with AsyncTiMEMClient(
        api_key="your_timem_api_key",
        base_url="http://localhost:8001",
        # 可以精确控制增强功能
        enable_connection_pool=True,
        enable_circuit_breaker=True,
        enable_monitoring=True,
        # 可以自定义配置
        connection_config=None,  # 使用默认配置
        circuit_breaker_config=None,  # 使用默认配置
    ) as client:
        
        # 执行一些操作
        for i in range(3):
            try:
                await client.search_memory(
                    user_id=12345,
                    domain="aicv",
                    limit=10
                )
                print(f"请求 {i+1} 完成")
                
            except Exception as e:
                print(f"请求 {i+1} 失败: {str(e)}")
        
        # 获取详细统计
        stats = client.get_client_stats()
        print(f"连接池状态: {stats['connection_pool']['is_healthy'] if stats['connection_pool'] else 'N/A'}")
        print(f"熔断器状态: {stats['circuit_breaker']['state'] if stats['circuit_breaker'] else 'N/A'}")
        
        # 重置连接（如果需要）
        await client.reset_connections()
        client.reset_circuit_breaker()


async def basic_usage_example():
    """基础使用示例 - 不使用增强功能"""
    print("\n=== 基础使用示例（无增强功能）===")
    
    # 禁用增强功能，使用传统方式
    async with create_client(
        api_key="your_timem_api_key",
        base_url="http://localhost:8001",
        enable_enhanced_features=False  # 禁用增强功能
    ) as client:
        
        # 基础操作
        result = await client.learn(domain="aicv")
        print(f"学习结果: {result}")
        
        # 注意：基础模式下没有增强功能
        # client.get_health_status()  # 仍然可用，但信息较少
        # client.get_client_stats()   # 仍然可用，但信息较少


async def error_handling_example():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")
    
    try:
        async with create_client(
            api_key="invalid_api_key",  # 错误的API密钥
            base_url="http://localhost:8001"
        ) as client:
            
            # 尝试操作
            await client.learn(domain="test")
            
    except Exception as e:
        print(f"预期的错误: {type(e).__name__}: {str(e)}")
        
        # 即使出错，也可以获取统计信息
        if hasattr(client, 'get_client_stats'):
            stats = client.get_client_stats()
            print(f"错误处理统计: {stats}")


async def monitoring_example():
    """监控示例"""
    print("\n=== 监控示例 ===")
    
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    async with create_client(
        api_key="your_timem_api_key",
        base_url="http://localhost:8001"
    ) as client:
        
        # 执行一些操作
        for i in range(5):
            try:
                await client.search_memory(domain="aicv", limit=5)
                print(f"请求 {i+1} 完成")
                
            except Exception as e:
                print(f"请求 {i+1} 失败: {str(e)}")
        
        # 获取监控信息
        health = await client.get_health_status()
        stats = client.get_client_stats()
        
        print(f"健康状态: {health.get('status', 'unknown')}")
        print(f"总请求数: {stats['client_stats']['total_requests']}")
        print(f"成功请求数: {stats['client_stats']['successful_requests']}")
        print(f"失败请求数: {stats['client_stats']['failed_requests']}")
        
        if stats['connection_pool']:
            print(f"连接池健康: {stats['connection_pool']['is_healthy']}")
            print(f"连接池成功率: {stats['connection_pool']['success_rate']:.2%}")
        
        if stats['circuit_breaker']:
            print(f"熔断器状态: {stats['circuit_breaker']['state']}")
            print(f"熔断器失败次数: {stats['circuit_breaker']['failure_count']}")


async def main():
    """主函数"""
    print("TiMEM简化使用示例")
    print("=" * 50)
    
    try:
        # 简化使用示例
        await simple_usage_example()
        
        # 高级使用示例
        await advanced_usage_example()
        
        # 基础使用示例
        await basic_usage_example()
        
        # 错误处理示例
        await error_handling_example()
        
        # 监控示例
        await monitoring_example()
        
    except Exception as e:
        print(f"示例执行失败: {str(e)}")
    
    print("\n示例执行完成！")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
