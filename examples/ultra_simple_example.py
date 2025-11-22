"""
TiMEM超简化使用示例

展示最简洁的API使用方式，用户无需关心同步/异步、增强功能等复杂概念。
"""

import asyncio
from timem import TiMEMClient, SyncTiMEMClient


async def async_example():
    """异步使用示例（推荐）"""
    print("=== 异步使用示例（推荐）===")
    
    # 超简单使用 - 无需了解任何复杂概念
    async with TiMEMClient(api_key="your_timem_api_key") as client:
        
        # 1. 添加记忆
        memory = await client.add_memory(
            user_id=12345,
            domain="aicv",
            content={"message": "用户询问简历优化建议"}
        )
        print(f"记忆添加: {memory}")
        
        # 2. 学习生成规则
        rules = await client.learn(domain="aicv")
        print(f"学习结果: {rules}")
        
        # 3. 召回规则
        recalled = await client.recall(
            context={"job_title": "软件工程师"},
            domain="aicv"
        )
        print(f"召回结果: {recalled}")
        
        # 4. 获取健康状态（自动包含增强功能）
        health = await client.get_health_status()
        print(f"服务状态: {health['status']}")


def sync_example():
    """同步使用示例（兼容层）"""
    print("\n=== 同步使用示例（兼容层）===")
    
    # 同步使用 - 内部使用异步实现
    with SyncTiMEMClient(api_key="your_timem_api_key") as client:
        
        # 1. 添加记忆
        memory = client.add_memory(
            user_id=12345,
            domain="aicv",
            content={"message": "用户询问简历优化建议"}
        )
        print(f"记忆添加: {memory}")
        
        # 2. 学习生成规则
        rules = client.learn(domain="aicv")
        print(f"学习结果: {rules}")
        
        # 3. 召回规则
        recalled = client.recall(
            context={"job_title": "软件工程师"},
            domain="aicv"
        )
        print(f"召回结果: {recalled}")
        
        # 4. 获取健康状态
        health = client.get_health_status()
        print(f"服务状态: {health['status']}")


async def batch_example():
    """批量操作示例"""
    print("\n=== 批量操作示例 ===")
    
    async with TiMEMClient(api_key="your_timem_api_key") as client:
        # 批量学习多个域
        domains = ["aicv", "education", "consulting"]
        results = await client.batch_learn(domains=domains)
        
        for result in results:
            if result['success']:
                print(f"{result['domain']}: 学习成功")
            else:
                print(f"{result['domain']}: 学习失败 - {result['error']}")


async def monitoring_example():
    """监控示例"""
    print("\n=== 监控示例 ===")
    
    async with TiMEMClient(api_key="your_timem_api_key") as client:
        # 执行一些操作
        for i in range(3):
            try:
                await client.search_memory(domain="aicv", limit=10)
                print(f"请求 {i+1} 完成")
            except Exception as e:
                print(f"请求 {i+1} 失败: {str(e)}")
        
        # 获取统计信息（自动包含增强功能）
        stats = client.get_client_stats()
        print(f"总请求数: {stats['client_stats']['total_requests']}")
        print(f"成功率: {stats['client_stats']['successful_requests'] / max(stats['client_stats']['total_requests'], 1):.2%}")


async def main():
    """主函数"""
    print("TiMEM超简化使用示例")
    print("=" * 50)
    
    try:
        # 异步使用（推荐）
        await async_example()
        
        # 同步使用（兼容层）
        sync_example()
        
        # 批量操作
        await batch_example()
        
        # 监控示例
        await monitoring_example()
        
    except Exception as e:
        print(f"示例执行失败: {str(e)}")
    
    print("\n示例执行完成！")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
