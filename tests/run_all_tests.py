"""
快速运行所有测试

按顺序执行：
1. API 连接测试
2. 独立节点测试
3. 完整流程测试
"""

import subprocess
import sys

def run_test(test_file, description):
    """运行单个测试文件"""
    print("\n" + "=" * 70)
    print(f"  {description}")
    print("=" * 70)
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - 通过")
            return True
        else:
            print(f"❌ {description} - 失败")
            return False
    except Exception as e:
        print(f"❌ {description} - 错误: {e}")
        return False


def main():
    """运行所有测试"""
    tests = [
        ("tests/test_gpt_simple.py", "API 连接测试"),
        ("tests/test_formatter_only.py", "独立节点测试（不依赖 LLM）"),
        ("tests/test_nodes.py", "完整流程集成测试"),
    ]
    
    print("🚀 开始运行测试套件...")
    
    results = []
    for test_file, description in tests:
        success = run_test(test_file, description)
        results.append((description, success))
    
    # 打印总结
    print("\n" + "=" * 70)
    print("  测试总结")
    print("=" * 70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {description}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
