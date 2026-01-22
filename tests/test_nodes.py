"""
完整节点流程测试脚本

测试从 analyzer -> fetcher -> tools -> formatter 的完整流程
"""

import os
import json
from dotenv import load_dotenv
from src.state import make_initial_state
from src.nodes.analyzer import analyzer_node
from src.nodes.fetcher import fetcher_node
from src.nodes.formatter import formatter_node
from src.tools.financial import financial_tool
from src.tools.listing import listing_tool

# 加载环境变量
load_dotenv()


def print_section(title: str):
    """打印分隔线"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def print_state_info(state, stage: str):
    """打印状态信息"""
    print(f"\n📍 {stage}")
    print(f"   公司: {state.get('company_name', 'N/A')}")
    print(f"   意图: {state.get('intent', 'N/A')}")
    print(f"   need_financial: {state.get('need_financial', False)}")
    print(f"   need_listing: {state.get('need_listing', False)}")
    print(f"   parallel_done: {state.get('parallel_done', {})}")
    if state.get('trace'):
        print(f"   最新 trace: {state['trace'][-1]}")


def test_full_flow(query: str):
    """测试完整流程"""
    print_section(f"测试查询: {query}")
    
    # 步骤1: 创建初始状态
    state = make_initial_state(query)
    print("\n✓ 初始状态创建完成")
    
    # 步骤2: Analyzer 节点
    state = analyzer_node(state)
    print_state_info(state, "Analyzer 完成")
    
    # 步骤3: Fetcher 节点
    state = fetcher_node(state)
    print_state_info(state, "Fetcher 完成")
    
    # 步骤4: 调用工具节点（根据需要）
    if state.get('need_financial'):
        state = financial_tool(state)
        print_state_info(state, "Financial Tool 完成")
    
    if state.get('need_listing'):
        state = listing_tool(state)
        print_state_info(state, "Listing Tool 完成")
    
    # 步骤5: Formatter 节点
    state = formatter_node(state)
    print_state_info(state, "Formatter 完成")
    
    # 输出最终结果
    print("\n" + "─" * 70)
    print("📊 最终输出:")
    print("─" * 70)
    
    if state.get('card_json'):
        print(json.dumps(state['card_json'], ensure_ascii=False, indent=2))
    
    if state.get('errors'):
        print(f"\n⚠️  错误列表: {state['errors']}")
    
    print("\n📝 完整追踪:")
    for trace in state.get('trace', []):
        print(f"   • {trace}")


def main():
    """运行所有测试用例"""
    test_cases = [
        "Apple的市值是多少？",
        "Microsoft什么时候上市的？",
        "Amazon的市值和上市信息",
        "你好，今天天气怎么样？"
    ]
    
    for query in test_cases:
        test_full_flow(query)
    
    print_section("所有测试完成")


if __name__ == "__main__":
    main()
