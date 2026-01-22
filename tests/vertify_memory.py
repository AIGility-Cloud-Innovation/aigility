import asyncio
import os
import sys
import uuid
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

# Try to import dependencies, handle missing environment gracefully
try:
    from aigility.memory.config import MemoryConfig
    from aigility.memory.providers.timem import TimemMemoryProvider
except ImportError as e:
    print(f"导入模块时出错: {e}")
    print("请确保您在项目根目录下并且已安装依赖项。")
    sys.exit(1)

async def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始 TimemMemoryProvider 验证...")
    
    # 1. Initialize configuration
    config = MemoryConfig()
    
    # Check for API Key
    api_key = config.provider.get_api_key()
    if not api_key:
        print("❌ 错误: 环境变量中未找到 TIMEM_API_KEY。")
        print("请在运行前执行 export TIMEM_API_KEY='your_key_here'。")
        return

    # 2. Initialize Provider
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 正在初始化提供商...")
    provider = TimemMemoryProvider(config.provider)
    
    if not provider.enabled:
        print("❌ 提供商初始化失败 (请检查 timem-ai SDK 是否已安装)。")
        return
    print("✅ 提供商初始化成功。")

    # Generate unique IDs for testing
    test_session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    test_user_id = "test_user_verification"

    # 3. Test Generate Memory
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正在测试添加记忆...")
    print(f"会话ID: {test_session_id}")
    
    messages = [
        {"role": "user", "content": "My favorite color is blue and I love coding in Python."},
        {"role": "assistant", "content": "That's great! Python is a very powerful language."}
    ]
    
    try:
        result = await provider.add_memory(
            messages=messages,
            session_id=test_session_id,
            user_id=test_user_id,
            character_id="default_character"  # Required by Timem API
        )
        if result:
            print("✅ 记忆添加成功。")
            print(f"结果: {result}")
        else:
            print("⚠️ 记忆添加返回空结果 (如果未找到新事实，这是正常情况)。")
    except Exception as e:
        print(f"❌ 添加记忆时出错: {e}")

    # 4. Test Search Memory
    # Wait a moment for indexing if necessary (though usually fast)
    await asyncio.sleep(2)
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 正在测试搜索记忆...")
    query = "What is my favorite color?"
    print(f"查询: {query}")
    
    try:
        memories = await provider.search_memories(
            query_text=query,
            user_id=test_user_id,
            character_id="default_character",
            limit=3
        )
        
        if memories:
            print(f"✅ 找到 {len(memories)} 条记忆:")
            for i, mem in enumerate(memories, 1):
                content = mem.get("memory", mem.get("content", str(mem)))
                print(f"  {i}. {content}")
        else:
            print("⚠️ 未找到记忆。")
            
    except Exception as e:
        print(f"❌ 搜索记忆时出错: {e}")

    # Clean up
    await provider.close()
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 验证完成。")

if __name__ == "__main__":
    asyncio.run(main())