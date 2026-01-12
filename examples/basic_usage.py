#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TiMEM Python SDK - 基础使用示例

演示 TiMEM SDK 的基本功能：
1. 同步客户端使用
2. 经验学习（Learn）
3. 规则召回（Recall）
4. 记忆管理（Memory）
5. 用户画像（User Profile）
"""

from timem import TiMEMClient
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 配置
API_KEY = "string"  # 替换为您的 API Key
BASE_URL = "http://192.168.31.56:8000/"  # 替换为 TiMEM Engine 地址


def demo_learn_and_recall():
    """演示学习和召回功能"""
    print("\n" + "="*70)
    print("  示例 1: 经验学习与规则召回")
    print("="*70)
    
    # 创建客户端
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        # 1. 收集反馈并学习
        print("\n[步骤 1] 从反馈案例中学习...")
        feedback_cases = [
            {
                "case_id": "case_001",
                "user_id": 12345,
                "domain": "aicv",
                "context": {
                    "job_title": "Python开发工程师",
                    "issue_type": "项目经验",
                    "section": "工作经历"
                },
                "suggestion": "建议添加具体的项目成果和技术栈",
                "suggestion_type": "项目经验优化",
                "feedback_action": "adopt",  # 用户采纳
                "feedback_score": 5.0
            },
            {
                "case_id": "case_002",
                "user_id": 12346,
                "domain": "aicv",
                "context": {
                    "job_title": "Python开发工程师",
                    "issue_type": "技能描述",
                    "section": "技能特长"
                },
                "suggestion": "建议增加具体的框架和工具使用经验",
                "suggestion_type": "技能描述优化",
                "feedback_action": "adopt",
                "feedback_score": 4.5
            },
            {
                "case_id": "case_003",
                "user_id": 12347,
                "domain": "aicv",
                "context": {
                    "job_title": "Python开发工程师",
                    "issue_type": "项目经验",
                    "section": "工作经历"
                },
                "suggestion": "建议量化项目成果，如性能提升百分比",
                "suggestion_type": "项目经验优化",
                "feedback_action": "adopt",
                "feedback_score": 5.0
            }
        ]
        
        result = client.learn(
            domain="aicv",
            feedback_cases=feedback_cases,
            min_case_count=2,
            min_adoption_rate=0.6,
            strategy="adaptive"
        )
        
        print(f"✓ 学习完成")
        print(f"  - 生成规则数: {result.get('data', {}).get('generated_rule_count', 0)}")
        
        # 2. 召回相关规则
        print("\n[步骤 2] 根据上下文召回规则...")
        context = {
            "job_title": "Python开发工程师",
            "issue_type": "项目经验",
            "section": "工作经历"
        }
        
        rules = client.recall(
            context=context,
            domain="aicv",
            top_k=3,
            min_confidence=0.5
        )
        
        print(f"✓ 召回完成")
        print(f"  - 召回规则数: {len(rules.get('data', {}).get('rules', []))}")
        
        for i, rule in enumerate(rules.get('data', {}).get('rules', [])[:3], 1):
            print(f"\n  规则 {i}:")
            print(f"    - 标题: {rule.get('rule_title', 'N/A')}")
            print(f"    - 置信度: {rule.get('confidence_score', 0):.2f}")
            print(f"    - 相关性: {rule.get('relevance_score', 0):.2f}")


def demo_memory_management():
    """演示记忆管理功能"""
    print("\n" + "="*70)
    print("  示例 2: 记忆管理")
    print("="*70)
    
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        # 1. 添加记忆
        print("\n[步骤 1] 添加记忆...")
        memory = client.add_memory(
            user_id=99999,
            domain="aicv",
            content={
                "type": "resume_analysis",
                "action": "view_suggestion",
                "context": {
                    "job_title": "数据分析师",
                    "suggestion_type": "技能优化"
                },
                "timestamp": "2025-10-23T10:00:00Z"
            },
            layer_type="L1",
            tags=["resume", "suggestion", "view"],
            keywords=["数据分析", "技能"]
        )
        
        memory_id = memory.get('data', {}).get('id')
        print(f"✓ 记忆已添加")
        print(f"  - 记忆ID: {memory_id}")
        
        # 2. 搜索记忆
        print("\n[步骤 2] 搜索记忆...")
        results = client.search_memory(
            user_id=99999,
            domain="aicv",
            tags=["resume"],
            limit=10
        )
        
        print(f"✓ 搜索完成")
        print(f"  - 找到记忆数: {results.get('data', {}).get('total', 0)}")
        
        # 3. 更新记忆（如果有ID）
        if memory_id:
            print("\n[步骤 3] 更新记忆...")
            updated = client.update_memory(
                memory_id=memory_id,
                tags=["resume", "suggestion", "view", "updated"]
            )
            print(f"✓ 记忆已更新")


def demo_user_profile():
    """演示用户画像功能"""
    print("\n" + "="*70)
    print("  示例 3: 用户画像计算")
    print("="*70)
    
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        # 1. 计算用户画像
        print("\n[步骤 1] 计算用户画像...")
        try:
            profile = client.compute_profile(
                user_id=99999,
                domain="aicv"
            )
            
            print(f"✓ 画像计算完成")
            print(f"  - 画像ID: {profile.get('data', {}).get('id', 'N/A')}")
            
        except Exception as e:
            print(f"⚠ 画像计算失败: {e}")
            print("  (可能需要先添加L5级别的记忆)")
        
        # 2. 获取用户画像
        print("\n[步骤 2] 获取用户画像...")
        try:
            profile = client.get_profile(
                user_id=99999,
                domain="aicv"
            )
            
            print(f"✓ 画像获取完成")
            
        except Exception as e:
                print(f"⚠ 画像获取失败: {e}")


def demo_batch_operations():
    """演示批量操作"""
    print("\n" + "="*70)
    print("  示例 4: 批量操作")
    print("="*70)
    
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        # 批量学习多个领域
        print("\n[步骤 1] 批量学习多个领域...")
        try:
            results = client.batch_learn(
                domains=["aicv", "education"],
                min_case_count=2,
                strategy="adaptive"
            )
            
            print(f"✓ 批量学习完成")
            for result in results:
                domain = result.get('domain', 'unknown')
                success = result.get('success', False)
                print(f"  - {domain}: {'成功' if success else '失败'}")
            
        except Exception as e:
                print(f"⚠ 批量学习失败: {e}")


def demo_health_check():
    """演示健康检查"""
    print("\n" + "="*70)
    print("  示例 5: 健康检查")
    print("="*70)
    
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        # 1. 基础健康检查
        print("\n[步骤 1] 基础健康检查...")
        health = client.health_check()
        print(f"✓ 健康状态: {health.get('status', 'unknown')}")
        
        # 2. 增强健康状态
        print("\n[步骤 2] 增强健康状态...")
        enhanced_health = client.get_health_status()
        print(f"✓ 系统状态: {enhanced_health.get('status', 'unknown')}")
        
        # 3. 客户端统计
        print("\n[步骤 3] 客户端统计...")
        stats = client.get_client_stats()
        
        client_stats = stats.get('client_stats', {})
        print(f"✓ 客户端统计:")
        print(f"  - 总请求数: {client_stats.get('total_requests', 0)}")
        print(f"  - 成功请求: {client_stats.get('successful_requests', 0)}")
        print(f"  - 失败请求: {client_stats.get('failed_requests', 0)}")


def main():
    """主函数"""
    print("\n")
    print("*" * 70)
    print("  TiMEM Python SDK - 基础使用示例")
    print("*" * 70)
    
    try:
        # 演示各个功能
        demo_learn_and_recall()
        demo_memory_management()
        demo_user_profile()
        demo_batch_operations()
        demo_health_check()
        
        print("\n" + "="*70)
        print("  ✅ 所有示例执行完成！")
        print("="*70 + "\n")
    
    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
