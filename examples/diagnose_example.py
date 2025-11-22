"""
AiCV Python SDK - 简洁简历诊断示例
展示包调用的便捷性
"""

import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aicv import AiCVClient, AuthenticationError, APIError, ValidationError


def simple_diagnose_demo():
    """简洁的简历诊断示例"""
    print("=== AiCV 简历诊断 - 简洁调用示例 ===")
    
    # 1. 一键创建客户端（支持环境变量配置）
    api_key = os.getenv('AICV_API_KEY', 'string')  # 支持环境变量
    verify_ssl = os.getenv('AICV_VERIFY_SSL', 'true').lower() == 'true'
    
    print(f"�� API密钥: {api_key}")
    print(f"🔒 SSL校验: {'启用' if verify_ssl else '禁用'}")
    
    # 2. 示例数据
    resume_data = {
        "resume_text": """
        张三 | 高级Python开发工程师
        
        工作经验：
        • 5年Python开发经验
        • 3年机器学习项目经验  
        • 曾带领5人开发团队
        • 熟悉Django、Flask框架
        
        技能：Python, JavaScript, React, 机器学习, AWS, Docker, Kubernetes
        教育：计算机科学学士学位
        """,
        "job_title": "高级Python开发工程师",
        "job_description": """
        职位要求：
        • 5年以上Python开发经验
        • 熟悉Django、Flask等Web框架
        • 有机器学习项目经验
        • 熟悉AWS云服务
        • 有团队管理经验
        • 熟悉Docker、Kubernetes
        """
    }
    
    try:
        # 3. 一行代码调用API
        print("\n🔄 正在分析简历...")
        with AiCVClient(api_key=api_key, verify=verify_ssl) as client:
            result = client.get_resume_suggestions(**resume_data)
        
        # 4. 简洁的结果展示
        print("✅ 分析完成！")
        print("\n📊 诊断结果:")
        print("=" * 50)
        
        if 'data' in result and 'improvements' in result['data']:
            improvements = result['data']['improvements']
            
            # 按优先级分组显示
            critical = [i for i in improvements if i.get('priority') == 'critical']
            important = [i for i in improvements if i.get('priority') == 'important']
            normal = [i for i in improvements if i.get('priority') == 'normal']
            
            if critical:
                print(f"\n🔴 关键问题 ({len(critical)}个):")
                for i, item in enumerate(critical[:3], 1):  # 只显示前3个
                    print(f"  {i}. {item.get('problem', '')}")
                    print(f"     💡 {item.get('suggestion', '')}")
            
            if important:
                print(f"\n🟡 重要改进 ({len(important)}个):")
                for i, item in enumerate(important[:3], 1):  # 只显示前3个
                    print(f"  {i}. {item.get('problem', '')}")
                    print(f"     💡 {item.get('suggestion', '')}")
            
            if normal:
                print(f"\n🟢 优化建议 ({len(normal)}个):")
                for i, item in enumerate(normal[:2], 1):  # 只显示前2个
                    print(f"  {i}. {item.get('problem', '')}")
            
            print(f"\n📈 总计发现 {len(improvements)} 个改进点")
            
        else:
            print("📄 完整结果:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        
        return True
        
    except AuthenticationError as e:
        print(f"❌ 认证失败: {e}")
        return False
    except APIError as e:
        print(f"❌ API错误: {e}")
        return False
    except ValidationError as e:
        print(f"❌ 参数错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 调用失败: {e}")
        if "SSL" in str(e):
            print("💡 提示: 设置环境变量 AICV_VERIFY_SSL=false 可禁用SSL校验")
        return False


def advanced_demo():
    """高级用法示例"""
    print("\n" + "=" * 60)
    print("=== 高级用法示例 ===")
    
    # 环境变量配置示例
    print("🔧 环境变量配置:")
    print("export AICV_API_KEY='your-api-key'")
    print("export AICV_VERIFY_SSL='true'")
    
    # 批量处理示例
    print("\n📦 批量处理示例:")
    print("""
# 批量分析多个简历
resumes = [
    {"resume_text": "简历1", "job_title": "职位1", "job_description": "描述1"},
    {"resume_text": "简历2", "job_title": "职位2", "job_description": "描述2"}
]

with AiCVClient(api_key=api_key) as client:
    results = []
    for resume in resumes:
        result = client.get_resume_suggestions(**resume)
        results.append(result)
    """)
    
    # 异步处理示例
    print("\n⚡ 异步处理示例:")
    print("""
# 使用异步客户端（需要安装 httpx[asyncio]）
import asyncio
from aicv import AsyncAiCVClient

async def analyze_resume():
    async with AsyncAiCVClient(api_key=api_key) as client:
        result = await client.get_resume_suggestions(**resume_data)
        return result
    """)


def main():
    """主函数"""
    print("AiCV Python SDK - 简历诊断工具")
    print("=" * 60)
    print("✨ 简洁调用，强大功能")
    print("🔧 支持环境变量配置")
    print("⚡ 600秒超时，适合复杂分析")
    print("🔒 默认SSL校验，安全可靠")
    
    try:
        # 运行简洁示例
        success = simple_diagnose_demo()
        
        if success:
            print("\n🎉 示例运行成功!")
            advanced_demo()
        else:
            print("\n❌ 示例运行失败")
            
    except Exception as e:
        print(f"运行示例时发生错误: {e}")
    
    print("\n" + "=" * 60)
    print("📚 使用说明:")
    print("1. 安装: pip install aicv-python")
    print("2. 配置: export AICV_API_KEY='your-key'")
    print("3. 调用: from aicv import AiCVClient")
    print("4. 分析: client.get_resume_suggestions(...)")
    print("\n🚀 开始使用AiCV，让简历更出色！")


if __name__ == "__main__":
    main()
