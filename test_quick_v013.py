#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TiMEM SDK v0.1.3 快速验证脚本

用于验证 v0.1.3 版本是否正常工作
"""

import sys
from timem import TiMEMClient

# 配置 - 请修改为实际值
API_KEY = "timem_your_api_key_here"  # 替换为实际的API Key
BASE_URL = "http://localhost:8001"  # 替换为实际的服务地址


def print_header(title):
    """打印标题"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def test_version():
    """测试版本号"""
    import timem
    print(f"\n✓ SDK版本: {timem.__version__}")
    assert timem.__version__ == "0.1.3", f"版本号错误: {timem.__version__}"


def test_sync_client():
    """测试同步客户端"""
    print("\n[测试] 同步客户端初始化...")
    
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        # 测试健康检查
        result = client.health_check()
        print(f"✓ 健康检查通过: {result.get('status', 'unknown')}")
        
        return True


def test_learn_with_user_id():
    """测试学习功能（带 user_id）"""
    print("\n[测试] 学习功能（带 user_id 参数）...")
    
    try:
        with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = client.learn(
                domain="test",
                min_case_count=1,
                user_id="test_user_v013"  # v0.1.3 新增参数
            )
            print(f"✓ 学习功能正常（支持 user_id 参数）")
            return True
    except TypeError as e:
        if "user_id" in str(e):
            print(f"✗ 错误: 不支持 user_id 参数")
            print(f"  可能仍在使用旧版本")
            return False
        raise


def test_recall_with_user_id():
    """测试召回功能（带 user_id）"""
    print("\n[测试] 召回功能（带 user_id 参数）...")
    
    try:
        with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
            result = client.recall(
                context={"test": "context"},
                domain="test",
                user_id="test_user_v013"  # v0.1.3 新增参数
            )
            print(f"✓ 召回功能正常（支持 user_id 参数）")
            return True
    except TypeError as e:
        if "user_id" in str(e):
            print(f"✗ 错误: 不支持 user_id 参数")
            print(f"  可能仍在使用旧版本")
            return False
        raise


def test_memory_management():
    """测试记忆管理"""
    print("\n[测试] 记忆管理...")
    
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        # 添加记忆
        memory = client.add_memory(
            user_id=99999,
            domain="test_v013",
            content={
                "type": "v013_verification",
                "timestamp": "2025-10-23"
            },
            layer_type="L1",
            tags=["test", "v013"]
        )
        
        memory_id = memory.get('data', {}).get('id')
        print(f"✓ 记忆添加成功: {memory_id}")
        
        # 搜索记忆
        results = client.search_memory(
            domain="test_v013",
            tags=["test"],
            limit=10
        )
        
        count = results.get('data', {}).get('total', 0)
        print(f"✓ 记忆搜索成功: 找到 {count} 条记忆")
        
        return True


def test_client_stats():
    """测试客户端统计"""
    print("\n[测试] 客户端统计...")
    
    with TiMEMClient(
        api_key=API_KEY,
        base_url=BASE_URL,
        enable_connection_pool=True,
        enable_circuit_breaker=True,
        enable_monitoring=True
    ) as client:
        # 执行一些操作
        for i in range(3):
            try:
                client.health_check()
            except:
                pass
        
        # 获取统计信息
        stats = client.get_client_stats()
        
        client_stats = stats.get('client_stats', {})
        print(f"✓ 客户端统计:")
        print(f"  - 总请求数: {client_stats.get('total_requests', 0)}")
        print(f"  - 成功请求: {client_stats.get('successful_requests', 0)}")
        print(f"  - 失败请求: {client_stats.get('failed_requests', 0)}")
        
        return True


def test_resource_cleanup():
    """测试资源清理"""
    print("\n[测试] 资源清理...")
    
    # 使用上下文管理器
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        client.health_check()
    
    print(f"✓ 资源清理正常（上下文管理器自动清理）")
    return True


def main():
    """主函数"""
    print_header("TiMEM SDK v0.1.3 - 快速验证脚本")
    
    print("\n提示: 请确保已配置正确的 API_KEY 和 BASE_URL")
    print(f"  - API_KEY: {API_KEY[:20]}...")
    print(f"  - BASE_URL: {BASE_URL}")
    
    tests = [
        ("版本检查", test_version),
        ("同步客户端", test_sync_client),
        ("学习功能（user_id）", test_learn_with_user_id),
        ("召回功能（user_id）", test_recall_with_user_id),
        ("记忆管理", test_memory_management),
        ("客户端统计", test_client_stats),
        ("资源清理", test_resource_cleanup),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print_header(f"测试: {name}")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # 打印总结
    print_header("测试总结")
    print(f"\n总测试数: {len(tests)}")
    print(f"✓ 通过: {passed}")
    print(f"✗ 失败: {failed}")
    
    if failed == 0:
        print("\n" + "="*70)
        print("  ✅ v0.1.3 所有功能正常！")
        print("="*70 + "\n")
        return 0
    else:
        print("\n" + "="*70)
        print("  ❌ 部分测试失败，请检查配置或版本")
        print("="*70 + "\n")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

