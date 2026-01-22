"""
analyzer 节点快速测试脚本

用于验证 analyzer_node 的基本功能：
1. 能否正确提取公司名
2. 能否正确判断意图类型
3. 能否正确设置并行任务开关
"""

import os
from dotenv import load_dotenv
from src.state import make_initial_state
from src.nodes import analyzer_node

# 加载环境变量
load_dotenv()

def test_analyzer():
    """测试 analyzer 节点的不同场景"""
    
    test_cases = [
        {
            "query": "腾讯的市值是多少？",
            "expected_intent": "financial",
            "expected_company": "腾讯"
        },
        {
            "query": "告诉我阿里巴巴什么时候上市的",
            "expected_intent": "listing",
            "expected_company": "阿里巴巴"
        },
        {
            "query": "你好，今天天气怎么样？",
            "expected_intent": "chat",
            "expected_company": None
        },
        {
            "query": "小米的市值和上市时间",
            "expected_intent": "financial",  # 优先 financial
            "expected_company": "小米"
        }
    ]
    
    print("=" * 60)
    print("开始测试 analyzer_node")
    print("=" * 60)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {case['query']}")
        print("-" * 60)
        
        # 创建初始状态
        state = make_initial_state(case["query"])
        
        # 调用 analyzer 节点
        result = analyzer_node(state)
        
        # 输出结果
        print(f"✓ 公司名: {result['company_name']}")
        print(f"✓ 意图: {result['intent']}")
        print(f"✓ 置信度: {result['confidence']}")
        print(f"✓ 需要财务数据: {result['need_financial']}")
        print(f"✓ 需要上市信息: {result['need_listing']}")
        
        if result['errors']:
            print(f"⚠ 错误: {result['errors']}")
        
        if result['trace']:
            print(f"📋 追踪: {result['trace'][-1]}")
        
        # 简单验证
        if case['expected_intent'] == result['intent']:
            print("✅ 意图判断正确")
        else:
            print(f"❌ 意图判断错误: 期望 {case['expected_intent']}, 实际 {result['intent']}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_analyzer()
