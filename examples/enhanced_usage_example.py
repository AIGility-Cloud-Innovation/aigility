"""
TiMEM增强功能使用示例

展示如何使用连接池、熔断器、监控等企业级特性。
"""

import asyncio
import logging
from timem import (
    create_enhanced_client,
    ConnectionConfig,
    CircuitBreakerConfig
)


async def basic_usage_example():
    """基础使用示例"""
    print("=== TiMEM增强功能基础使用示例 ===")
    
    # 配置连接池
    connection_config = ConnectionConfig(
        max_connections=10,
        max_keepalive_connections=5,
        keepalive_timeout=30.0,
        health_check_interval=60.0
    )
    
    # 配置熔断器
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30.0,
        success_threshold=2,
        timeout=60.0
    )
    
    # 创建增强客户端
    async with create_enhanced_client(
        api_key="your_timem_api_key",
        base_url="http://localhost:8001",
        connection_config=connection_config,
        circuit_breaker_config=circuit_breaker_config,
        enable_monitoring=True,
        verify_ssl=False
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
        
        # 4. 获取健康状态
        print("4. 获取健康状态...")
        health = await client.get_health_status()
        print(f"健康状态: {health}")
        
        # 5. 获取客户端统计
        print("5. 获取客户端统计...")
        stats = client.get_client_stats()
        print(f"客户端统计: {stats}")


async def batch_operations_example():
    """批量操作示例"""
    print("\n=== 批量操作示例 ===")
    
    async with create_enhanced_client(
        api_key="your_timem_api_key",
        base_url="http://localhost:8001",
        enable_monitoring=True
    ) as client:
        
        # 批量学习多个域
        domains = ["aicv", "education", "consulting"]
        batch_results = await client.batch_learn(
            domains=domains,
            min_case_count=3,
            min_adoption_rate=0.6,
            min_confidence_score=0.5,
            strategy="adaptive"
        )
        
        print("批量学习结果:")
        for result in batch_results:
            if result['success']:
                print(f"  {result['domain']}: 成功")
            else:
                print(f"  {result['domain']}: 失败 - {result['error']}")


async def error_handling_example():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")
    
    # 使用错误的API密钥测试错误处理
    try:
        async with create_enhanced_client(
            api_key="invalid_api_key",
            base_url="http://localhost:8001",
            enable_monitoring=True
        ) as client:
            
            # 尝试添加记忆
            await client.add_memory(
                user_id=12345,
                domain="test",
                content={"message": "测试记忆"}
            )
            
    except Exception as e:
        print(f"预期的错误: {type(e).__name__}: {str(e)}")
        
        # 获取客户端统计，查看错误处理情况
        if hasattr(client, 'get_client_stats'):
            stats = client.get_client_stats()
            print(f"错误处理统计: {stats}")


async def monitoring_example():
    """监控示例"""
    print("\n=== 监控示例 ===")
    
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    async with create_enhanced_client(
        api_key="your_timem_api_key",
        base_url="http://localhost:8001",
        enable_monitoring=True
    ) as client:
        
        # 执行一些操作
        for i in range(5):
            try:
                # 模拟一些请求
                await client.search_memory(
                    user_id=12345,
                    domain="aicv",
                    limit=10
                )
                print(f"请求 {i+1} 完成")
                
            except Exception as e:
                print(f"请求 {i+1} 失败: {str(e)}")
        
        # 获取监控信息
        health = await client.get_health_status()
        stats = client.get_client_stats()
        
        print(f"健康状态: {health['status']}")
        print(f"总请求数: {stats['client_stats']['total_requests']}")
        print(f"成功请求数: {stats['client_stats']['successful_requests']}")
        print(f"失败请求数: {stats['client_stats']['failed_requests']}")
        
        if stats['connection_pool']:
            print(f"连接池状态: {stats['connection_pool']['is_healthy']}")
            print(f"连接池成功率: {stats['connection_pool']['success_rate']:.2%}")
        
        if stats['circuit_breaker']:
            print(f"熔断器状态: {stats['circuit_breaker']['state']}")
            print(f"熔断器失败次数: {stats['circuit_breaker']['failure_count']}")


async def connection_management_example():
    """连接管理示例"""
    print("\n=== 连接管理示例 ===")
    
    async with create_enhanced_client(
        api_key="your_timem_api_key",
        base_url="http://localhost:8001",
        enable_monitoring=True
    ) as client:
        
        # 获取初始连接池状态
        initial_stats = client.get_client_stats()
        print(f"初始连接池状态: {initial_stats['connection_pool']}")
        
        # 执行一些操作
        await client.search_memory(domain="aicv", limit=5)
        
        # 重置连接池
        print("重置连接池...")
        await client.reset_connections()
        
        # 重置熔断器
        print("重置熔断器...")
        client.reset_circuit_breaker()
        
        # 获取重置后的状态
        final_stats = client.get_client_stats()
        print(f"重置后连接池状态: {final_stats['connection_pool']}")
        print(f"重置后熔断器状态: {final_stats['circuit_breaker']}")


async def main():
    """主函数"""
    print("TiMEM增强功能使用示例")
    print("=" * 50)
    
    try:
        # 基础使用示例
        await basic_usage_example()
        
        # 批量操作示例
        await batch_operations_example()
        
        # 错误处理示例
        await error_handling_example()
        
        # 监控示例
        await monitoring_example()
        
        # 连接管理示例
        await connection_management_example()
        
    except Exception as e:
        print(f"示例执行失败: {str(e)}")
    
    print("\n示例执行完成！")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
