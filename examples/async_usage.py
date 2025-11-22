#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TiMEM Python SDK - 异步客户端使用示例

演示 TiMEM SDK 的异步功能：
1. 异步客户端基础使用
2. 并发批量操作
3. 高性能异步调用
"""

import asyncio
import logging
from timem import AsyncTiMEMClient, learn_async, recall_async

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 配置
API_KEY = "timem_your_api_key_here"  # 替换为实际的API Key
BASE_URL = "http://localhost:8001"  # 替换为实际的服务地址


async def demo_basic_async():
    """演示基础异步操作"""
    print("\n" + "="*70)
    print("  示例 1: 异步客户端基础使用")
    print("="*70)
    
    # 使用异步上下文管理器
    async with AsyncTiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        # 1. 异步学习
        print("\n[步骤 1] 异步学习...")
        result = await client.learn(
            domain="aicv",
            min_case_count=2,
            strategy="adaptive"
        )
        
        print(f"✓ 学习完成")
        print(f"  - 生成规则数: {result.get('data', {}).get('generated_rule_count', 0)}")
        
        # 2. 异步召回
        print("\n[步骤 2] 异步召回...")
        rules = await client.recall(
            context={"job_title": "Python工程师"},
            domain="aicv",
            top_k=5
        )
        
        print(f"✓ 召回完成")
        print(f"  - 召回规则数: {len(rules.get('data', {}).get('rules', []))}")


async def demo_concurrent_operations():
    """演示并发操作"""
    print("\n" + "="*70)
    print("  示例 2: 并发操作")
    print("="*70)
    
    async with AsyncTiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        # 并发添加多个记忆
        print("\n[步骤 1] 并发添加记忆...")
        
        # 创建多个记忆任务
        tasks = []
        for i in range(5):
            task = client.add_memory(
                user_id=99999 + i,
                domain="test",
                content={
                    "type": f"concurrent_test_{i}",
                    "index": i
                },
                layer_type="L1",
                tags=["concurrent", "test"]
            )
            tasks.append(task)
        
        # 并发执行
        import time
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        print(f"✓ 并发添加完成")
        print(f"  - 成功: {success_count}/5")
        print(f"  - 耗时: {duration:.2f}s")
        
        # 并发搜索
        print("\n[步骤 2] 并发搜索...")
        search_tasks = [
            client.search_memory(domain="test", tags=["concurrent"]),
            client.search_memory(domain="aicv", limit=10),
            client.search_memory(user_id=99999, limit=5)
        ]
        
        start_time = time.time()
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        duration = time.time() - start_time
        
        print(f"✓ 并发搜索完成")
        print(f"  - 搜索任务数: {len(search_tasks)}")
        print(f"  - 耗时: {duration:.2f}s")


async def demo_batch_operations():
    """演示批量操作"""
    print("\n" + "="*70)
    print("  示例 3: 批量操作")
    print("="*70)
    
    async with AsyncTiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        # 批量学习
        print("\n[步骤 1] 批量学习多个领域...")
        domains = ["aicv", "education", "general"]
        
        import time
        start_time = time.time()
        results = await client.batch_learn(
            domains=domains,
            min_case_count=2,
            strategy="adaptive"
        )
        duration = time.time() - start_time
        
        print(f"✓ 批量学习完成")
        print(f"  - 领域数: {len(domains)}")
        print(f"  - 耗时: {duration:.2f}s")
        
        for result in results:
            domain = result.get('domain', 'unknown')
            success = result.get('success', False)
            print(f"  - {domain}: {'✓' if success else '✗'}")
        
        # 批量添加记忆
        print("\n[步骤 2] 批量添加记忆...")
        memories = [
            {
                "user_id": 99999,
                "domain": "test",
                "content": {"type": "batch_test", "index": i},
                "layer_type": "L1"
            }
            for i in range(10)
        ]
        
        start_time = time.time()
        results = await client.batch_add_memories(memories)
        duration = time.time() - start_time
        
        success_count = sum(1 for r in results if r.get('success', False))
        print(f"✓ 批量添加完成")
        print(f"  - 成功: {success_count}/{len(memories)}")
        print(f"  - 耗时: {duration:.2f}s")


async def demo_convenience_functions():
    """演示便捷函数"""
    print("\n" + "="*70)
    print("  示例 4: 便捷函数")
    print("="*70)
    
    # 使用便捷函数进行学习
    print("\n[步骤 1] 使用便捷函数学习...")
    result = await learn_async(
        api_key=API_KEY,
        base_url=BASE_URL,
        domain="aicv",
        strategy="adaptive"
    )
    
    print(f"✓ 学习完成")
    print(f"  - 生成规则数: {result.get('data', {}).get('generated_rule_count', 0)}")
    
    # 使用便捷函数召回
    print("\n[步骤 2] 使用便捷函数召回...")
    rules = await recall_async(
        api_key=API_KEY,
        base_url=BASE_URL,
        context={"job_title": "数据科学家"},
        domain="aicv"
    )
    
    print(f"✓ 召回完成")
    print(f"  - 召回规则数: {len(rules.get('data', {}).get('rules', []))}")


async def demo_enhanced_features():
    """演示增强功能"""
    print("\n" + "="*70)
    print("  示例 5: 增强功能（连接池、熔断器、监控）")
    print("="*70)
    
    # 启用所有增强功能
    async with AsyncTiMEMClient(
        api_key=API_KEY,
        base_url=BASE_URL,
        enable_connection_pool=True,
        enable_circuit_breaker=True,
        enable_monitoring=True
    ) as client:
        
        # 执行一些操作
        print("\n[步骤 1] 执行操作...")
        for i in range(5):
            try:
                await client.health_check()
            except Exception as e:
                print(f"  请求 {i+1} 失败: {e}")
        
        # 查看客户端统计
        print("\n[步骤 2] 查看增强功能统计...")
        stats = client.get_client_stats()
        
        print(f"✓ 客户端统计:")
        client_stats = stats.get('client_stats', {})
        print(f"  - 总请求数: {client_stats.get('total_requests', 0)}")
        print(f"  - 成功请求: {client_stats.get('successful_requests', 0)}")
        print(f"  - 失败请求: {client_stats.get('failed_requests', 0)}")
        
        # 连接池状态
        pool_stats = stats.get('connection_pool')
        if pool_stats:
            print(f"\n✓ 连接池状态:")
            print(f"  - 健康状态: {'健康' if pool_stats.get('is_healthy') else '不健康'}")
            print(f"  - 成功请求: {pool_stats.get('successful_requests', 0)}")
            print(f"  - 失败请求: {pool_stats.get('failed_requests', 0)}")
            print(f"  - 成功率: {pool_stats.get('success_rate', 0):.2%}")
        
        # 熔断器状态
        breaker_state = stats.get('circuit_breaker')
        if breaker_state:
            print(f"\n✓ 熔断器状态:")
            print(f"  - 状态: {breaker_state.get('state', 'unknown')}")
            print(f"  - 失败次数: {breaker_state.get('failure_count', 0)}")
            print(f"  - 错误率: {breaker_state.get('error_rate', 0):.2%}")


async def main():
    """主函数"""
    print("\n")
    print("*" * 70)
    print("  TiMEM Python SDK - 异步客户端使用示例")
    print("*" * 70)
    
    try:
        # 演示各个功能
        await demo_basic_async()
        await demo_concurrent_operations()
        await demo_batch_operations()
        await demo_convenience_functions()
        await demo_enhanced_features()
        
        print("\n" + "="*70)
        print("  ✅ 所有示例执行完成！")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())

