#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TiMem 记忆服务本地测试 Demo
测试局域网内本地8000端口的记忆服务

运行方式:
    python examples/demo_local_memory.py
"""

import os
import sys
from typing import Dict, Any, List

# 添加项目根目录到路径（如果直接运行此文件）
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from timem import Memory
from timem.exceptions import TiMEMError


# ==================== 配置 ====================
# 修改为您的实际配置
API_KEY = os.getenv("TIMEM_API_KEY", "sk-ce34d247d9ac3d5ad68152dcad872bb9ee261dfac060798e")
BASE_URL = os.getenv("TIMEM_BASE_URL", "http://localhost:8000")
CHARACTER_ID = "chat_assistant"  # 角色ID，可以根据实际情况修改


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_step(step_num: int, title: str):
    """打印步骤标题"""
    print(f"\n[步骤 {step_num}] {title}")
    print("-" * 80)


def print_memory_result(result: Dict[str, Any]):
    """打印记忆生成结果"""
    if isinstance(result, dict):
        if result.get("success"):
            memories = result.get("memories", [])
            total = result.get("total", 0)
            print(f"✓ 成功生成 {total} 条记忆")
            
            for i, mem in enumerate(memories, 1):
                mem_id = mem.get("id", "未知")
                event = mem.get("event", "未知")
                data = mem.get("data", {})
                memory_text = data.get("memory", "无内容")
                
                print(f"\n  记忆 {i}:")
                print(f"    - ID: {mem_id}")
                print(f"    - 事件: {event}")
                print(f"    - 内容: {memory_text[:100]}..." if len(memory_text) > 100 else f"    - 内容: {memory_text}")
        else:
            print(f"✗ 生成失败: {result.get('message', '未知错误')}")
    else:
        print(f"结果: {result}")


def print_search_result(result: Dict[str, Any]):
    """打印搜索结果"""
    if isinstance(result, dict):
        results = result.get("results", [])
        total = result.get("total", 0)
        query = result.get("query", "")
        
        print(f"✓ 搜索完成")
        print(f"  - 查询: {query}")
        print(f"  - 找到 {total} 条相关记忆")
        
        if results:
            print(f"\n前 {min(5, len(results))} 条记忆:")
            for i, mem in enumerate(results[:5], 1):
                memory_text = mem.get("memory", "")
                score = mem.get("score", 0.0)
                mem_id = mem.get("id", "未知")
                layer = mem.get("layer", "未知")
                
                print(f"\n  记忆 {i} (相似度: {score:.2f}):")
                print(f"    - ID: {mem_id}")
                print(f"    - 层级: {layer}")
                print(f"    - 内容: {memory_text[:150]}..." if len(memory_text) > 150 else f"    - 内容: {memory_text}")
        else:
            print("  ⚠ 没有找到相关记忆")
    else:
        print(f"结果: {result}")


def test_connection():
    """测试连接"""
    print_section("测试连接")
    
    try:
        memory = Memory(
            api_key=API_KEY,
            base_url=BASE_URL,
            default_character_id=CHARACTER_ID
        )
        print(f"✓ 客户端初始化成功")
        print(f"  - Base URL: {BASE_URL}")
        print(f"  - Character ID: {CHARACTER_ID}")
        return memory
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return None


def test_add_memory(memory: Memory):
    """测试添加记忆"""
    print_section("测试添加对话记忆")
    
    # 模拟对话消息
    messages = [
        {"role": "user", "content": "你好，我想了解一下Python编程"},
        {"role": "assistant", "content": "您好！Python是一门非常流行的编程语言，有什么具体问题我可以帮您解答吗？"},
        {"role": "user", "content": "我想学习如何写一个简单的Web应用"},
        {"role": "assistant", "content": "好的，您可以使用Flask或FastAPI框架来创建Web应用。Flask更轻量，FastAPI性能更好且支持异步。"}
    ]
    
    print_step(1, "添加对话记忆")
    print(f"对话内容:")
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        print(f"  {role}: {content[:80]}..." if len(content) > 80 else f"  {role}: {content}")
    
    try:
        result = memory.add(
            messages=messages,
            user_id="demo_user_001",
            character_id=CHARACTER_ID,
            session_id="demo_session_001"
        )
        print_memory_result(result)
        return result
    except TiMEMError as e:
        print(f"✗ 添加记忆失败: {e}")
        return None
    except Exception as e:
        print(f"✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_add_more_memories(memory: Memory):
    """测试添加更多记忆"""
    print_section("测试添加更多对话记忆")
    
    # 第二段对话
    messages2 = [
        {"role": "user", "content": "FastAPI和Flask有什么区别？"},
        {"role": "assistant", "content": "主要区别：1) FastAPI基于异步，性能更好；2) FastAPI自动生成API文档；3) Flask更成熟，生态更丰富；4) FastAPI支持类型提示和验证。"}
    ]
    
    print_step(1, "添加第二段对话")
    try:
        result = memory.add(
            messages=messages2,
            user_id="demo_user_001",
            character_id=CHARACTER_ID,
            session_id="demo_session_002"
        )
        print_memory_result(result)
    except Exception as e:
        print(f"✗ 添加失败: {e}")
    
    # 第三段对话
    messages3 = [
        {"role": "user", "content": "我应该选择哪个框架？"},
        {"role": "assistant", "content": "如果您的项目需要高性能和现代特性（如异步、自动文档），选择FastAPI。如果项目较小或需要更多第三方插件，选择Flask。"}
    ]
    
    print_step(2, "添加第三段对话")
    try:
        result = memory.add(
            messages=messages3,
            user_id="demo_user_001",
            character_id=CHARACTER_ID,
            session_id="demo_session_003"
        )
        print_memory_result(result)
    except Exception as e:
        print(f"✗ 添加失败: {e}")


def test_search_memory(memory: Memory):
    """测试搜索记忆"""
    print_section("测试搜索记忆")
    
    # 测试查询1：关于Python
    print_step(1, "搜索：Python编程")
    try:
        result = memory.search(
            query="Python编程",
            user_id="demo_user_001",
            character_id=CHARACTER_ID,
            limit=5
        )
        print_search_result(result)
    except Exception as e:
        print(f"✗ 搜索失败: {e}")
    
    # 测试查询2：关于Web框架
    print_step(2, "搜索：Web框架选择")
    try:
        result = memory.search(
            query="Web框架选择",
            user_id="demo_user_001",
            character_id=CHARACTER_ID,
            limit=5
        )
        print_search_result(result)
    except Exception as e:
        print(f"✗ 搜索失败: {e}")
    
    # 测试查询3：关于FastAPI
    print_step(3, "搜索：FastAPI特点")
    try:
        result = memory.search(
            query="FastAPI的特点和优势",
            user_id="demo_user_001",
            character_id=CHARACTER_ID,
            limit=5,
            include_context=True  # 包含上下文信息
        )
        print_search_result(result)
    except Exception as e:
        print(f"✗ 搜索失败: {e}")


def test_search_without_character_id(memory: Memory):
    """测试不指定character_id的搜索"""
    print_section("测试全局搜索（不指定角色）")
    
    print_step(1, "全局搜索：编程语言")
    try:
        result = memory.search(
            query="编程语言",
            user_id="demo_user_001",
            limit=5
        )
        print_search_result(result)
    except Exception as e:
        print(f"✗ 搜索失败: {e}")


def main():
    """主函数"""
    print("\n" + "*" * 80)
    print("  TiMem 记忆服务本地测试 Demo")
    print("  测试目标: 本地8000端口的记忆服务")
    print("*" * 80)
    
    print("\n配置信息:")
    print(f"  - Base URL: {BASE_URL}")
    print(f"  - API Key: {API_KEY[:20]}...")
    print(f"  - Character ID: {CHARACTER_ID}")
    
    # 1. 测试连接
    memory = test_connection()
    if not memory:
        print("\n❌ 无法连接到服务，请检查配置和服务状态")
        return
    
    try:
        # 2. 测试添加记忆
        add_result = test_add_memory(memory)
        
        # 3. 添加更多记忆
        test_add_more_memories(memory)
        
        # 4. 测试搜索记忆
        test_search_memory(memory)
        
        # 5. 测试全局搜索
        test_search_without_character_id(memory)
        
        print("\n" + "=" * 80)
        print("  ✅ 所有测试完成！")
        print("=" * 80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断测试")
    except Exception as e:
        print(f"\n\n❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        if memory:
            memory.close()


if __name__ == "__main__":
    main()

