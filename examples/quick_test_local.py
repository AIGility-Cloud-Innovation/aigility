#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TiMem 快速测试脚本 - 云端测试
最简单的测试示例，快速验证服务是否可用

运行方式:
    python examples/quick_test_local.py
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from timem import Memory

# ==================== 配置 ====================
# 修改为您的实际配置
API_KEY = os.getenv("TIMEM_API_KEY", "sk-82a47b83d6b4e2305cb4f3828466c0982bea8ffa64c3f615")
BASE_URL = os.getenv("TIMEM_BASE_URL", "http://apitest.timem.cloud")
CHARACTER_ID = "chat_assistant"


def main():
    """快速测试"""
    print("=" * 60)
    print("TiMem 快速测试 - 云端连接")
    print("=" * 60)

    # 初始化客户端
    print(f"\n1. 初始化客户端...")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Character ID: {CHARACTER_ID}")

    try:
        memory = Memory(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        print("   ✓ 客户端初始化成功")
    except Exception as e:
        print(f"   ✗ 初始化失败: {e}")
        return
    
    # 测试添加记忆
    print(f"\n2. 测试添加记忆...")
    messages = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "您好！有什么可以帮您的吗？"}
    ]
    
    try:
        result = memory.add(
            messages=messages,
            user_id="test_user",
            character_id=CHARACTER_ID,
            session_id="test_session"
        )
        
        if result.get("success"):
            print(f"   ✓ 记忆添加成功")
            print(f"   - 生成记忆数: {result.get('total', 0)}")
            if result.get("memory_id"):
                print(f"   - 记忆ID: {result.get('memory_id')}")
        else:
            print(f"   ✗ 添加失败: {result.get('message', '未知错误')}")
    except Exception as e:
        print(f"   ✗ 添加失败: {e}")
        return
    
    # 测试搜索记忆
    print(f"\n3. 测试搜索记忆...")
    try:
        result = memory.search(
            query="你好",
            user_id="test_user",
            character_id=CHARACTER_ID,
            limit=3
        )
        
        total = result.get("total", 0)
        print(f"   ✓ 搜索完成")
        print(f"   - 找到 {total} 条相关记忆")
        
        if result.get("results"):
            print(f"\n   前3条结果:")
            for i, mem in enumerate(result["results"][:3], 1):
                score = mem.get("score", 0.0)
                content = mem.get("memory", "")[:50]
                print(f"   {i}. [相似度: {score:.2f}] {content}...")
    except Exception as e:
        print(f"   ✗ 搜索失败: {e}")
        return
    
    print(f"\n" + "=" * 60)
    print("✅ 快速测试完成！")
    print("=" * 60)
    
    # 清理资源
    try:
        memory.close()
    except Exception:
        pass


if __name__ == "__main__":
    main()

