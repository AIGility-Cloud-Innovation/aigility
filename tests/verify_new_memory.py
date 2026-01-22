import asyncio
import os
import sys
import uuid
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

# Try to import dependencies
try:
    from aigility.memory import Memory, MemoryConfig, MemoryProviderConfig
except ImportError as e:
    print(f"导入模块时出错: {e}")
    print("请确保您在项目根目录下并且已安装依赖项。")
    sys.exit(1)

async def main():
    print("=" * 70)
    print("测试 Memory 类（基于 Provider 架构 + Config 模式）")
    print("=" * 70)

    # Check for API Key
    api_key = os.environ.get("TIMEM_API_KEY")
    if not api_key:
        print("❌ 错误: 环境变量中未找到 TIMEM_API_KEY。")
        print("请在运行前执行 export TIMEM_API_KEY='your_key_here'。")
        return

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 测试场景 1: 使用默认配置（从环境变量读取）")
    print("-" * 70)

    # 方式1: 使用默认配置（从环境变量读取）
    config = 
    memory = Memory()

    if not memory._provider or not memory._provider.enabled:
        print("❌ Memory 初始化失败")
        return
    print("✅ Memory 初始化成功（使用默认配置）")

    # Generate unique IDs for testing
    test_session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    test_user_id = "test_user_config_mode"

    # 2. Test Add Memory
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正在测试添加记忆...")
    print(f"会话ID: {test_session_id}")

    messages = [
        {"role": "user", "content": "My name is Bob and I enjoy playing guitar."},
        {"role": "assistant", "content": "Hi Bob! That's wonderful, guitar is a beautiful instrument."}
    ]

    try:
        result = await memory.add(
            messages=messages,
            session_id=test_session_id,
            user_id=test_user_id,
            character_id="default_character"
        )
        if result.get("success"):
            print("✅ 记忆添加成功。")
            print(f"   记忆数量: {result.get('total', 0)}")
            print(f"   记忆ID: {result.get('memory_id', 'N/A')}")
        else:
            print(f"⚠️ 记忆添加失败: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ 添加记忆时出错: {e}")

    # 3. Test Search Memory
    await asyncio.sleep(2)

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正在测试搜索记忆...")
    query = "What is my name?"
    print(f"查询: {query}")

    try:
        result = await memory.search(
            query=query,
            user_id=test_user_id,
            character_id="default_character",
            limit=3
        )

        if result.get("results"):
            print(f"✅ 找到 {result['total']} 条记忆:")
            for i, mem in enumerate(result["results"], 1):
                memory_text = mem.get("memory", "")
                score = mem.get("score", 0.0)
                print(f"  {i}. {memory_text} (score: {score})")
        else:
            print("⚠️ 未找到记忆。")

    except Exception as e:
        print(f"❌ 搜索记忆时出错: {e}")

    # 4. 测试自定义配置
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 测试场景 2: 使用自定义配置对象")
    print("-" * 70)

    # 方式2: 使用自定义配置对象
    config = MemoryConfig(
        provider=MemoryProviderConfig(
            provider="timem",
            api_key=api_key,
            enabled=True
        )
    )

    memory2 = Memory(config=config)

    if not memory2._provider or not memory2._provider.enabled:
        print("❌ Memory 初始化失败")
    else:
        print("✅ Memory 初始化成功（使用自定义配置）")
        await memory2.close()

    # Clean up
    await memory.close()

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 测试完成。")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())