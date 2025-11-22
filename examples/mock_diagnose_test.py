"""
AiCV Python SDK - 诊断分析功能模拟测试
使用模拟数据测试诊断分析功能，无需真实API连接
"""

import sys
import os
import json
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from aicv import AiCVClient, AuthenticationError, APIError, ValidationError
except ImportError:
    print("无法导入aicv模块，请确保模块已正确安装")
    sys.exit(1)


class MockAiCVClient(AiCVClient):
    """模拟AiCV客户端，用于测试功能"""
    
    def __init__(self, api_key: str, **kwargs):
        # 不调用父类初始化，避免网络请求
        self.api_key = api_key
        self.base_url = "https://api.aicv.chat"
        self.timeout = 30.0
    
    def _make_request(self, method: str, endpoint: str, data=None, params=None, **kwargs):
        """模拟API请求，返回模拟数据"""
        
        if endpoint == "/api/v1/diagnose":
            return self._mock_diagnose_response(data)
        elif endpoint == "/api/v1/analyze":
            return self._mock_analyze_response(data)
        elif endpoint == "/api/v1/health":
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        elif endpoint == "/api/v1/account":
            return {"account_id": "test-account", "usage": {"requests": 100}}
        else:
            return {"message": "Mock response", "endpoint": endpoint}
    
    def _mock_diagnose_response(self, data):
        """模拟诊断分析响应"""
        cv_text = data.get('cv_text', '')
        target_position = data.get('target_position', '')
        analysis_type = data.get('analysis_type', 'comprehensive')
        include_suggestions = data.get('include_suggestions', True)
        
        # 基于简历内容生成模拟分析结果
        strengths = []
        weaknesses = []
        suggestions = []
        
        # 分析技能
        if 'python' in cv_text.lower():
            strengths.append("具备Python编程技能")
        else:
            weaknesses.append("缺少Python编程技能")
            suggestions.append("建议学习Python编程")
        
        if '机器学习' in cv_text or 'machine learning' in cv_text.lower():
            strengths.append("具备机器学习经验")
        else:
            weaknesses.append("缺少机器学习经验")
            suggestions.append("建议学习机器学习相关技术")
        
        # 分析工作经验
        if '年' in cv_text and any(char.isdigit() for char in cv_text):
            strengths.append("具备工作经验")
        else:
            weaknesses.append("工作经验描述不够清晰")
            suggestions.append("建议详细描述工作经验和项目成果")
        
        # 分析教育背景
        if '学士' in cv_text or '硕士' in cv_text or '博士' in cv_text:
            strengths.append("具备良好的教育背景")
        else:
            weaknesses.append("教育背景信息不完整")
            suggestions.append("建议补充教育背景信息")
        
        # 计算匹配度
        match_score = min(100, len(strengths) * 20 + 40)
        overall_score = min(100, match_score - len(weaknesses) * 5)
        
        response = {
            "analysis_id": f"mock_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "overall_score": overall_score,
            "match_score": match_score,
            "target_position": target_position,
            "analysis_type": analysis_type,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "timestamp": datetime.now().isoformat()
        }
        
        if include_suggestions:
            response["suggestions"] = suggestions
        
        return response
    
    def _mock_analyze_response(self, data):
        """模拟简历分析响应"""
        return {
            "analysis_id": f"mock_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "skills_analysis": {
                "technical_skills": ["Python", "JavaScript"],
                "soft_skills": ["团队合作", "沟通能力"]
            },
            "experience_analysis": {
                "years_experience": 3,
                "key_achievements": ["项目经验丰富"]
            },
            "timestamp": datetime.now().isoformat()
        }


def test_basic_diagnosis():
    """测试基础诊断分析"""
    print("=== 测试基础诊断分析 ===")
    
    client = MockAiCVClient(api_key="test-key")
    
    cv_text = """
    张三
    高级Python开发工程师
    
    工作经验：
    - 5年Python开发经验
    - 3年机器学习项目经验
    - 曾带领5人开发团队
    
    技能：
    - Python, JavaScript, React
    - 机器学习, 深度学习
    - AWS, Docker, Kubernetes
    
    教育背景：
    - 计算机科学学士学位
    """
    
    try:
        result = client.diagnose_resume(
            cv_text=cv_text,
            target_position="高级Python开发工程师",
            company_type="AI/ML公司"
        )
        
        print("✓ 基础诊断分析测试通过")
        print(f"总体评分: {result['overall_score']}")
        print(f"匹配度: {result['match_score']}")
        print(f"优势: {result['strengths']}")
        print(f"不足: {result['weaknesses']}")
        if 'suggestions' in result:
            print(f"建议: {result['suggestions']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 基础诊断分析测试失败: {e}")
        return False


def test_comprehensive_diagnosis():
    """测试综合诊断分析"""
    print("\n=== 测试综合诊断分析 ===")
    
    client = MockAiCVClient(api_key="test-key")
    
    cv_text = """
    李四
    数据科学家
    
    工作经验：
    - 3年数据分析经验
    - 熟悉Python、R语言
    - 有机器学习项目经验
    
    技能：
    - Python, R, SQL
    - 机器学习, 统计分析
    - Tableau, Power BI
    """
    
    try:
        result = client.diagnose_resume(
            cv_text=cv_text,
            target_position="高级数据科学家",
            company_type="互联网科技公司",
            analysis_type="comprehensive"
        )
        
        print("✓ 综合诊断分析测试通过")
        print(f"分析类型: {result['analysis_type']}")
        print(f"总体评分: {result['overall_score']}")
        print(f"优势: {result['strengths']}")
        print(f"不足: {result['weaknesses']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 综合诊断分析测试失败: {e}")
        return False


def test_diagnosis_with_suggestions():
    """测试带建议的诊断分析"""
    print("\n=== 测试带建议的诊断分析 ===")
    
    client = MockAiCVClient(api_key="test-key")
    
    cv_text = """
    王五
    前端开发工程师
    
    技能：
    - HTML, CSS, JavaScript
    - 1年开发经验
    """
    
    try:
        result = client.diagnose_resume(
            cv_text=cv_text,
            target_position="高级前端开发工程师",
            include_suggestions=True
        )
        
        print("✓ 带建议的诊断分析测试通过")
        print(f"总体评分: {result['overall_score']}")
        print(f"优势: {result['strengths']}")
        print(f"不足: {result['weaknesses']}")
        if 'suggestions' in result:
            print(f"改进建议: {result['suggestions']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 带建议的诊断分析测试失败: {e}")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试错误处理 ===")
    
    client = MockAiCVClient(api_key="test-key")
    
    # 测试空简历内容
    try:
        result = client.diagnose_resume(
            cv_text="",
            target_position="测试职位"
        )
        print("✗ 错误处理测试失败：应该抛出验证错误")
        return False
        
    except ValidationError:
        print("✓ 错误处理测试通过：正确拒绝空简历内容")
        return True
        
    except Exception as e:
        print(f"✗ 错误处理测试失败：抛出意外错误: {e}")
        return False


def test_validation():
    """测试参数验证"""
    print("\n=== 测试参数验证 ===")
    
    client = MockAiCVClient(api_key="test-key")
    
    # 测试缺少目标职位
    try:
        result = client.diagnose_resume(
            cv_text="测试简历内容",
            target_position=""
        )
        print("✗ 参数验证测试失败：应该抛出验证错误")
        return False
        
    except ValidationError:
        print("✓ 参数验证测试通过：正确拒绝空目标职位")
        return True
        
    except Exception as e:
        print(f"✗ 参数验证测试失败：抛出意外错误: {e}")
        return False


def main():
    """主函数 - 运行所有模拟测试"""
    print("AiCV Python SDK - 诊断分析功能模拟测试")
    print("=" * 60)
    
    tests = [
        test_basic_diagnosis,
        test_comprehensive_diagnosis,
        test_diagnosis_with_suggestions,
        test_error_handling,
        test_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"测试执行异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"模拟测试完成: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有模拟测试通过！诊断分析功能工作正常。")
    else:
        print(f"⚠️  有 {total - passed} 个测试失败，请检查相关功能。")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
