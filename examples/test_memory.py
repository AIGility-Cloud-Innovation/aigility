#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TiMEM Python SDK - 记忆管理测试示例

主要测试记忆管理功能
"""

from timem import TiMEMClient
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 配置 - 修改为实际值
API_KEY = "string"  # 替换为您的 API Key
BASE_URL = "http://192.168.31.56:8000/"  # 替换为 TiMEM Engine 地址


def test_memory_basic():
    """测试基础记忆操作"""
    print("\n" + "="*70)
    print("  测试 1: 基础记忆操作")
    print("="*70)
    
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        # 1. 添加记忆
        print("\n[步骤 1] 添加记忆...")
        try:
            memory = client.add_memory(
                user_id=99999,
                domain="general",
                content={
                    "type": "test_memory",
                    "action": "create",
                    "message": "这是一个测试记忆",
                    "timestamp": "2025-10-23"
                },
                layer_type="L1",
                tags=["test", "demo", "v0.1.3"],
                keywords=["测试", "记忆管理"]
            )
            
            memory_data = memory.get('data', {})
            memory_id = memory_data.get('id')
            print(f"✓ 记忆添加成功")
            print(f"  - 记忆ID: {memory_id}")
            print(f"  - 用户ID: {memory_data.get('user_id')}")
            print(f"  - 领域: {memory_data.get('domain')}")
            print(f"  - 层级: {memory_data.get('layer_type')}")
            
            return memory_id
            
        except Exception as e:
            print(f"✗ 添加记忆失败: {e}")
            import traceback
            traceback.print_exc()
            return None


def test_memory_search():
    """测试记忆搜索"""
    print("\n" + "="*70)
    print("  测试 2: 记忆搜索")
    print("="*70)
    
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        # 搜索记忆
        print("\n[步骤 1] 搜索记忆...")
        try:
            results = client.search_memory(
                user_id=99999,
                domain="general",
                tags=["test"],
                limit=10
            )
            
            total = results.get('total', 0)
            memories = results.get('memories', [])
            
            print(f"✓ 搜索完成")
            print(f"  - 找到记忆数: {total}")
            
            if memories:
                print(f"\n前3条记忆:")
                for i, mem in enumerate(memories[:3], 1):
                    print(f"\n  记忆 {i}:")
                    print(f"    - ID: {mem.get('id')}")
                    print(f"    - 领域: {mem.get('domain')}")
                    print(f"    - 层级: {mem.get('layer') or mem.get('layer_type')}")
                    print(f"    - 标签: {mem.get('tags', [])}")
                    print(f"    - 内容: {mem.get('content', {})}")
                    print(f"    - 标签: {mem.get('tags', [])}")
            else:
                print("  ⚠ 没有找到记忆")
            
            return memories[0] if memories else None
            
        except Exception as e:
            print(f"✗ 搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return None


def test_memory_update(memory_id):
    """测试记忆更新"""
    if not memory_id:
        print("\n⚠ 跳过更新测试（没有记忆ID）")
        return
    
    print("\n" + "="*70)
    print("  测试 3: 记忆更新")
    print("="*70)
    
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        print(f"\n[步骤 1] 更新记忆 {memory_id}...")
        try:
            result = client.update_memory(
                memory_id=memory_id,
                tags=["test", "demo", "v0.1.3", "updated"],
                keywords=["测试", "记忆管理", "已更新"]
            )
            
            print(f"✓ 记忆更新成功")
            print(f"  - 结果: {result.get('message')}")
            
        except Exception as e:
            print(f"✗ 更新失败: {e}")
            import traceback
            traceback.print_exc()


def test_memory_get(memory_id):
    """测试获取单个记忆"""
    if not memory_id:
        print("\n⚠ 跳过获取测试（没有记忆ID）")
        return
    
    print("\n" + "="*70)
    print("  测试 4: 获取单个记忆")
    print("="*70)
    
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        print(f"\n[步骤 1] 获取记忆 {memory_id}...")
        try:
            result = client.get_memory(memory_id)
            
            memory = result.get('data', {})
            print(f"✓ 获取成功")
            print(f"  - ID: {memory.get('id')}")
            print(f"  - 用户ID: {memory.get('user_id')}")
            print(f"  - 领域: {memory.get('domain')}")
            print(f"  - 层级: {memory.get('layer_type')}")
            print(f"  - 标签: {memory.get('tags')}")
            print(f"  - 内容: {memory.get('content')}")
            
        except Exception as e:
            print(f"✗ 获取失败: {e}")
            import traceback
            traceback.print_exc()


def test_memory_batch():
    """测试批量添加记忆"""
    print("\n" + "="*70)
    print("  测试 5: 批量添加记忆")
    print("="*70)
    
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        print("\n[步骤 1] 批量添加5条记忆...")
        try:
            memories = [
                {
                    "user_id": 99999,
                    "domain": "test",
                    "content": {
                        "type": "batch_test",
                        "index": i,
                        "message": f"批量测试记忆 {i}"
                    },
                    "layer_type": "L1",
                    "tags": ["batch", "test"]
                }
                for i in range(5)
            ]
            
            results = client.batch_add_memories(memories)
            
            success_count = sum(1 for r in results if r.get('success', False))
            print(f"✓ 批量添加完成")
            print(f"  - 成功: {success_count}/5")
            
            for i, result in enumerate(results):
                if result.get('success'):
                    mem_id = result.get('result', {}).get('data', {}).get('id')
                    print(f"  - 记忆 {i}: {mem_id}")
                else:
                    print(f"  - 记忆 {i}: 失败 - {result.get('error')}")
            
        except Exception as e:
            print(f"✗ 批量添加失败: {e}")
            import traceback
            traceback.print_exc()


def test_health_check():
    """测试健康检查"""
    print("\n" + "="*70)
    print("  测试 6: 健康检查（已跳过 SDK 端 /api/v1/health 调用）")
    print("="*70)
    
    with TiMEMClient(api_key=API_KEY, base_url=BASE_URL) as client:
        
        print("\n[步骤 1] 跳过健康检查调用（服务端未提供 /api/v1/health）")
        
        print("\n[步骤 2] 客户端统计...")
        try:
            stats = client.get_client_stats()
            client_stats = stats.get('client_stats', {})
            
            print(f"✓ 客户端统计:")
            print(f"  - 总请求数: {client_stats.get('total_requests', 0)}")
            print(f"  - 成功请求: {client_stats.get('successful_requests', 0)}")
            print(f"  - 失败请求: {client_stats.get('failed_requests', 0)}")
            
        except Exception as e:
            print(f"✗ 统计获取失败: {e}")


def main():
    """主函数"""
    print("\n")
    print("*" * 70)
    print("  TiMEM Python SDK v0.1.3 - 记忆管理测试")
    print("*" * 70)
    
    try:
        # 测试序列
        print("\n配置信息:")
        print(f"  - API Key: {API_KEY[:20]}...")
        print(f"  - Base URL: {BASE_URL}")
        
        # 1. 基础操作
        memory_id = test_memory_basic()
        
        # 2. 搜索
        found_memory = test_memory_search()
        
        # 3. 更新（使用刚创建的ID或搜索到的ID）
        test_id = memory_id or (found_memory.get('id') if found_memory else None)
        test_memory_update(test_id)
        
        # 4. 获取
        test_memory_get(test_id)
        
        # 5. 批量操作
        test_memory_batch()
        
        # 6. 健康检查
        test_health_check()
        
        print("\n" + "="*70)
        print("  ✅ 所有测试完成！")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

