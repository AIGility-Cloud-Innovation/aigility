"""
AiCV Python SDK - 诊断分析功能测试
测试简历诊断分析的各种功能
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


class DiagnoseTester:
    """诊断分析功能测试类"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.test_results = []
    
    def test_basic_diagnosis(self):
        """测试基础诊断分析功能"""
        print("测试基础诊断分析功能...")
        
        cv_text = """
        测试用户
        软件工程师
        
        技能：
        - Python编程
        - 数据库设计
        - 2年开发经验
        
        教育背景：
        - 计算机科学学士
        """
        
        try:
            with AiCVClient(api_key=self.api_key) as client:
                result = client.diagnose_resume(
                    cv_text=cv_text,
                    target_position="高级软件工程师"
                )
                
                self.test_results.append({
                    'test': 'basic_diagnosis',
                    'status': 'success',
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                })
                
                print("✓ 基础诊断分析测试通过")
                return True
                
        except Exception as e:
            self.test_results.append({
                'test': 'basic_diagnosis',
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"✗ 基础诊断分析测试失败: {e}")
            return False
    
    def test_comprehensive_diagnosis(self):
        """测试综合诊断分析功能"""
        print("测试综合诊断分析功能...")
        
        cv_text = """
        高级测试用户
        全栈开发工程师
        
        工作经验：
        - 5年全栈开发经验
        - 熟悉前后端技术栈
        - 有团队管理经验
        
        技能：
        - 前端：React, Vue.js, HTML/CSS
        - 后端：Python, Java, Node.js
        - 数据库：MySQL, MongoDB, Redis
        - 云服务：AWS, Azure
        
        项目经验：
        - 电商平台开发
        - 微服务架构设计
        - 移动应用开发
        """
        
        try:
            with AiCVClient(api_key=self.api_key) as client:
                result = client.diagnose_resume(
                    cv_text=cv_text,
                    target_position="技术总监",
                    company_type="互联网科技公司",
                    analysis_type="comprehensive"
                )
                
                self.test_results.append({
                    'test': 'comprehensive_diagnosis',
                    'status': 'success',
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                })
                
                print("✓ 综合诊断分析测试通过")
                return True
                
        except Exception as e:
            self.test_results.append({
                'test': 'comprehensive_diagnosis',
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"✗ 综合诊断分析测试失败: {e}")
            return False
    
    def test_diagnosis_with_suggestions(self):
        """测试带建议的诊断分析功能"""
        print("测试带建议的诊断分析功能...")
        
        cv_text = """
        初级测试用户
        前端开发工程师
        
        技能：
        - HTML, CSS, JavaScript
        - 1年开发经验
        - 熟悉jQuery
        
        教育背景：
        - 计算机科学学士
        """
        
        try:
            with AiCVClient(api_key=self.api_key) as client:
                result = client.diagnose_resume(
                    cv_text=cv_text,
                    target_position="高级前端开发工程师",
                    include_suggestions=True
                )
                
                # 检查是否包含建议
                has_suggestions = 'suggestions' in result or 'improvements' in result
                
                self.test_results.append({
                    'test': 'diagnosis_with_suggestions',
                    'status': 'success',
                    'result': result,
                    'has_suggestions': has_suggestions,
                    'timestamp': datetime.now().isoformat()
                })
                
                print("✓ 带建议的诊断分析测试通过")
                if has_suggestions:
                    print("  - 包含改进建议")
                else:
                    print("  - 未包含改进建议")
                
                return True
                
        except Exception as e:
            self.test_results.append({
                'test': 'diagnosis_with_suggestions',
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"✗ 带建议的诊断分析测试失败: {e}")
            return False
    
    def test_error_handling(self):
        """测试错误处理"""
        print("测试错误处理...")
        
        try:
            with AiCVClient(api_key="invalid-key") as client:
                result = client.diagnose_resume(
                    cv_text="测试内容",
                    target_position="测试职位"
                )
                
                self.test_results.append({
                    'test': 'error_handling',
                    'status': 'failed',
                    'error': '应该抛出认证错误但没有',
                    'timestamp': datetime.now().isoformat()
                })
                
                print("✗ 错误处理测试失败：应该抛出认证错误")
                return False
                
        except AuthenticationError:
            self.test_results.append({
                'test': 'error_handling',
                'status': 'success',
                'result': '正确抛出认证错误',
                'timestamp': datetime.now().isoformat()
            })
            
            print("✓ 错误处理测试通过：正确抛出认证错误")
            return True
            
        except Exception as e:
            self.test_results.append({
                'test': 'error_handling',
                'status': 'failed',
                'error': f'抛出意外错误: {e}',
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"✗ 错误处理测试失败：抛出意外错误: {e}")
            return False
    
    def test_validation(self):
        """测试参数验证"""
        print("测试参数验证...")
        
        try:
            with AiCVClient(api_key=self.api_key) as client:
                # 测试空简历内容
                result = client.diagnose_resume(
                    cv_text="",
                    target_position="测试职位"
                )
                
                self.test_results.append({
                    'test': 'validation',
                    'status': 'failed',
                    'error': '应该抛出验证错误但没有',
                    'timestamp': datetime.now().isoformat()
                })
                
                print("✗ 参数验证测试失败：应该拒绝空简历内容")
                return False
                
        except ValidationError:
            self.test_results.append({
                'test': 'validation',
                'status': 'success',
                'result': '正确抛出验证错误',
                'timestamp': datetime.now().isoformat()
            })
            
            print("✓ 参数验证测试通过：正确拒绝空简历内容")
            return True
            
        except Exception as e:
            self.test_results.append({
                'test': 'validation',
                'status': 'failed',
                'error': f'抛出意外错误: {e}',
                'timestamp': datetime.now().isoformat()
            })
            
            print(f"✗ 参数验证测试失败：抛出意外错误: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("开始运行诊断分析功能测试...")
        print("=" * 50)
        
        tests = [
            self.test_basic_diagnosis,
            self.test_comprehensive_diagnosis,
            self.test_diagnosis_with_suggestions,
            self.test_error_handling,
            self.test_validation
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"测试执行异常: {e}")
        
        print("\n" + "=" * 50)
        print(f"测试完成: {passed}/{total} 通过")
        
        # 保存测试结果
        self.save_test_results()
        
        return passed, total
    
    def save_test_results(self):
        """保存测试结果到文件"""
        results_file = "diagnose_test_results.json"
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_summary': {
                    'total_tests': len(self.test_results),
                    'passed_tests': len([r for r in self.test_results if r['status'] == 'success']),
                    'failed_tests': len([r for r in self.test_results if r['status'] == 'failed']),
                    'timestamp': datetime.now().isoformat()
                },
                'test_results': self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"测试结果已保存到: {results_file}")


def main():
    """主函数"""
    print("AiCV Python SDK - 诊断分析功能测试")
    print("=" * 50)
    
    # 获取API密钥
    api_key = input("请输入您的API密钥 (或按回车使用测试密钥): ").strip()
    if not api_key:
        api_key = "test-api-key"  # 测试用密钥
        print("使用测试密钥进行测试...")
    
    # 创建测试器并运行测试
    tester = DiagnoseTester(api_key)
    passed, total = tester.run_all_tests()
    
    # 输出最终结果
    if passed == total:
        print("\n🎉 所有测试通过！诊断分析功能工作正常。")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查相关功能。")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
