"""
TiMEM SDK 快速开始示例

演示如何使用 TiMEM SDK 进行经验学习、规则召回、记忆管理等操作
"""

import asyncio
from timem import TiMEMClient, AsyncTiMEMClient


def sync_example():
    """同步客户端示例"""
    print("=" * 60)
    print("同步客户端示例")
    print("=" * 60)
    
    # 初始化客户端
    client = TiMEMClient(
        api_key="your-api-key",
        base_url="http://localhost:8001"
    )
    
    try:
        # 1. 健康检查
        print("\n1. 健康检查")
        health = client.health_check()
        print(f"   状态: {health.get('status', 'unknown')}")
        
        # 2. 学习：从反馈生成规则（同时收集反馈）
        print("\n2. 从反馈学习生成经验规则（包含新反馈）")
        learn_result = client.learn(
            domain="aicv",
            feedback_cases=[  # 可选：提供新反馈案例
                {
                    "case_id": "case_001",
                    "user_id": 12345,
                    "domain": "aicv",
                    "suggestion_type": "项目经验优化",
                    "original_content": "负责公司项目开发",
                    "suggestion_text": "建议补充项目规模、技术栈和个人贡献",
                    "feedback_action": "adopt",
                    "feedback_score": 5.0
                }
            ],
            min_case_count=2,
            min_adoption_rate=0.5,
            strategy="adaptive"
        )
        print(f"   任务状态: {learn_result.get('data', {}).get('status', 'unknown')}")
        
        # 3. 召回：根据上下文召回规则
        print("\n3. 召回相关经验规则")
        recall_result = client.recall(
            context={
                "job_title": "Python开发工程师",
                "issue_type": "项目经验",
                "section": "工作经历"
            },
            domain="aicv",
            top_k=5
        )
        rules = recall_result.get('data', {}).get('rules', [])
        print(f"   召回规则数: {len(rules)}")
        for i, rule in enumerate(rules[:3], 1):
            print(f"   规则{i}: {rule.get('title', 'N/A')[:40]}")
        
        # 4. 添加记忆
        print("\n4. 添加记忆")
        memory_result = client.add_memory(
            user_id=12345,
            domain="aicv",
            content={
                "action": "resume_analysis",
                "job_title": "Python开发",
                "sections_viewed": ["项目经验", "技能清单"]
            },
            layer_type="L1",
            tags=["resume", "analysis", "python"]
        )
        print(f"   添加成功: {memory_result.get('code') == 200}")
        
        # 5. 搜索记忆
        print("\n5. 搜索记忆")
        search_result = client.search_memory(
            user_id=12345,
            domain="aicv",
            tags=["resume"],
            limit=5
        )
        print(f"   搜索结果: {search_result.get('data', {}).get('total', 0)} 条")
        
    except Exception as e:
        print(f"\n错误: {e}")
    finally:
        client.close()
        print("\n客户端已关闭")


async def async_example():
    """异步客户端示例"""
    print("\n\n" + "=" * 60)
    print("异步客户端示例")
    print("=" * 60)
    
    # 使用上下文管理器
    async with AsyncTiMEMClient(
        api_key="your-api-key",
        base_url="http://localhost:8001",
        max_retries=3
    ) as client:
        
        try:
            # 1. 异步健康检查
            print("\n1. 异步健康检查")
            health = await client.health_check()
            print(f"   状态: {health.get('status', 'unknown')}")
            
            # 2. 异步学习
            print("\n2. 异步学习")
            learn_result = await client.learn(
                domain="aicv",
                strategy="adaptive"
            )
            print(f"   任务ID: {learn_result.get('data', {}).get('task_id', 'N/A')[:40]}")
            
            # 3. 异步召回
            print("\n3. 异步召回")
            recall_result = await client.recall(
                context={"job_title": "数据科学家"},
                domain="aicv"
            )
            print(f"   召回规则数: {recall_result.get('data', {}).get('count', 0)}")
            
            # 4. 批量学习（多个领域并发）
            print("\n4. 批量学习（并发）")
            batch_results = await client.batch_learn(
                domains=["aicv", "education", "consulting"],
                strategy="adaptive"
            )
            success_count = sum(1 for r in batch_results if r.get('success'))
            print(f"   成功: {success_count}/{len(batch_results)} 个领域")
            
            # 5. 批量添加记忆（并发）
            print("\n5. 批量添加记忆（并发）")
            memories = [
                {
                    "user_id": 12345,
                    "domain": "aicv",
                    "content": {"action": "view_job", "job_id": i},
                    "layer_type": "L1",
                    "tags": ["job", "view"]
                }
                for i in range(1, 6)
            ]
            batch_add_results = await client.batch_add_memories(memories)
            success_count = sum(1 for r in batch_add_results if r.get('success'))
            print(f"   成功: {success_count}/{len(batch_add_results)} 条记忆")
            
            # 6. 计算用户画像
            print("\n6. 计算用户画像")
            profile_result = await client.compute_profile(
                user_id=12345,
                domain="aicv"
            )
            print(f"   计算状态: {profile_result.get('data', {}).get('status', 'unknown')}")
            
        except Exception as e:
            print(f"\n错误: {e}")
    
    print("\n异步客户端已自动关闭")


async def convenience_functions():
    """便捷函数示例"""
    print("\n\n" + "=" * 60)
    print("便捷函数示例")
    print("=" * 60)
    
    from timem import learn_async, recall_async
    
    try:
        # 1. 快速异步学习
        print("\n1. 快速学习")
        result = await learn_async(
            api_key="your-api-key",
            domain="aicv",
            strategy="adaptive",
            base_url="http://localhost:8001"
        )
        print(f"   结果: {result.get('message', 'N/A')}")
        
        # 2. 快速异步召回
        print("\n2. 快速召回")
        result = await recall_async(
            api_key="your-api-key",
            context={"job_title": "产品经理"},
            domain="aicv",
            base_url="http://localhost:8001"
        )
        print(f"   召回规则数: {result.get('data', {}).get('count', 0)}")
        
    except Exception as e:
        print(f"\n错误: {e}")


def main():
    """主函数"""
    print("TiMEM SDK 快速开始示例")
    print("请确保 TiMEM Engine 正在运行在 http://localhost:8001")
    print()
    
    # 运行同步示例
    sync_example()
    
    # 运行异步示例
    asyncio.run(async_example())
    
    # 运行便捷函数示例
    asyncio.run(convenience_functions())
    
    print("\n\n示例运行完成！")


if __name__ == "__main__":
    main()

