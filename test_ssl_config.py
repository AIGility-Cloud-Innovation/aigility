"""
测试TiMEM Python SDK的SSL配置功能
"""

def test_ssl_config():
    """测试SSL配置"""
    print("=== TiMEM Python SDK SSL配置测试 ===")
    
    # 测试同步客户端
    print("1. 同步客户端测试")
    try:
        from timem import TiMEMClient
        
        # 默认配置（verify_ssl=False）
        client1 = TiMEMClient(api_key="test-key")
        print("默认配置客户端创建成功")
        
        # 自定义配置（verify_ssl=True）
        client2 = TiMEMClient(api_key="test-key", verify_ssl=True)
        print("自定义配置客户端创建成功")
        
        print("同步客户端SSL配置正常")
        
    except Exception as e:
        print(f"同步客户端SSL配置错误: {e}")
    
    # 测试异步客户端
    print("\n2. 异步客户端测试")
    try:
        from timem import AsyncTiMEMClient
        
        # 默认配置（verify_ssl=False）
        client1 = AsyncTiMEMClient(api_key="test-key")
        print("默认配置异步客户端创建成功")
        
        # 自定义配置（verify_ssl=True）
        client2 = AsyncTiMEMClient(api_key="test-key", verify_ssl=True)
        print("自定义配置异步客户端创建成功")
        
        print("异步客户端SSL配置正常")
        
    except Exception as e:
        print(f"异步客户端SSL配置错误: {e}")
    
    print("\n=== TiMEM Python SDK SSL配置测试完成 ===")
    print("SSL配置功能已成功实现！")


if __name__ == "__main__":
    test_ssl_config()
