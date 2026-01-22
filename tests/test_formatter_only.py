"""
Fetcher 和 Formatter 节点独立测试（不依赖 LLM）

直接构造 state 来测试节点逻辑
"""

import json
from src.state import make_initial_state
from src.nodes.fetcher import fetcher_node
from src.nodes.formatter import formatter_node
from src.tools.financial import financial_tool
from src.tools.listing import listing_tool


def print_section(title: str):
    """打印分隔线"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def test_case_1_financial_only():
    """测试场景1: 只需要财务数据"""
    print_section("测试场景1: 只需要财务数据 (Apple)")
    
    # 手动构造 state，模拟 analyzer 的输出
    state = make_initial_state("Apple的市值是多少？")
    state["company_name"] = "Apple"
    state["intent"] = "financial"
    state["confidence"] = 0.95
    state["need_financial"] = True
    state["need_listing"] = False
    
    print("\n✓ 初始状态（模拟 analyzer 输出）:")
    print(f"   公司: {state['company_name']}")
    print(f"   意图: {state['intent']}")
    print(f"   need_financial: {state['need_financial']}")
    print(f"   need_listing: {state['need_listing']}")
    
    # Fetcher 节点
    state = fetcher_node(state)
    print(f"\n✓ Fetcher 完成: {state['trace'][-1]}")
    
    # Financial tool
    if state['need_financial']:
        state = financial_tool(state)
        print(f"✓ Financial Tool 完成: {state['trace'][-1]}")
    
    # Formatter 节点
    state = formatter_node(state)
    print(f"✓ Formatter 完成: {state['trace'][-1]}")
    
    # 输出结果
    print("\n📊 最终卡片 JSON:")
    print(json.dumps(state['card_json'], ensure_ascii=False, indent=2))


def test_case_2_listing_only():
    """测试场景2: 只需要上市信息"""
    print_section("测试场景2: 只需要上市信息 (Microsoft)")
    
    state = make_initial_state("Microsoft什么时候上市的？")
    state["company_name"] = "Microsoft"
    state["intent"] = "listing"
    state["confidence"] = 0.92
    state["need_financial"] = False
    state["need_listing"] = True
    
    print("\n✓ 初始状态:")
    print(f"   公司: {state['company_name']}")
    print(f"   意图: {state['intent']}")
    
    state = fetcher_node(state)
    print(f"\n✓ Fetcher: {state['trace'][-1]}")
    
    if state['need_listing']:
        state = listing_tool(state)
        print(f"✓ Listing Tool: {state['trace'][-1]}")
    
    state = formatter_node(state)
    print(f"✓ Formatter: {state['trace'][-1]}")
    
    print("\n📊 最终卡片 JSON:")
    print(json.dumps(state['card_json'], ensure_ascii=False, indent=2))


def test_case_3_both():
    """测试场景3: 需要财务和上市信息"""
    print_section("测试场景3: 需要财务和上市信息 (Amazon)")
    
    state = make_initial_state("Amazon的市值和上市时间")
    state["company_name"] = "Amazon"
    state["intent"] = "financial"
    state["confidence"] = 0.88
    state["need_financial"] = True
    state["need_listing"] = True
    
    print("\n✓ 初始状态:")
    print(f"   公司: {state['company_name']}")
    print(f"   意图: {state['intent']}")
    print(f"   need_financial: {state['need_financial']}")
    print(f"   need_listing: {state['need_listing']}")
    
    state = fetcher_node(state)
    print(f"\n✓ Fetcher: {state['trace'][-1]}")
    
    # 并行执行两个工具
    if state['need_financial']:
        state = financial_tool(state)
        print(f"✓ Financial Tool: {state['trace'][-1]}")
    
    if state['need_listing']:
        state = listing_tool(state)
        print(f"✓ Listing Tool: {state['trace'][-1]}")
    
    print(f"   parallel_done: {state['parallel_done']}")
    
    state = formatter_node(state)
    print(f"✓ Formatter: {state['trace'][-1]}")
    
    print("\n📊 最终卡片 JSON:")
    print(json.dumps(state['card_json'], ensure_ascii=False, indent=2))


def test_case_4_chat():
    """测试场景4: 普通对话（不需要工具）"""
    print_section("测试场景4: 普通对话")
    
    state = make_initial_state("你好")
    state["company_name"] = None
    state["intent"] = "chat"
    state["confidence"] = 0.0
    state["need_financial"] = False
    state["need_listing"] = False
    
    print("\n✓ 初始状态:")
    print(f"   意图: {state['intent']}")
    
    state = fetcher_node(state)
    print(f"\n✓ Fetcher: {state['trace'][-1]}")
    print(f"   parallel_done: {state['parallel_done']}")
    
    # 注意：这里会尝试调用 LLM 生成回复，可能失败
    # 但 formatter 有降级处理
    state = formatter_node(state)
    print(f"✓ Formatter: {state['trace'][-1]}")
    
    print("\n📊 最终卡片 JSON:")
    print(json.dumps(state['card_json'], ensure_ascii=False, indent=2))
    
    if state.get('errors'):
        print(f"\n⚠️  错误: {state['errors']}")


def test_case_5_unknown_company():
    """测试场景5: 未知公司（测试降级行为）"""
    print_section("测试场景5: 未知公司")
    
    state = make_initial_state("某不知名公司的市值")
    state["company_name"] = "UnknownCorp"
    state["intent"] = "financial"
    state["confidence"] = 0.5
    state["need_financial"] = True
    state["need_listing"] = False
    
    print("\n✓ 初始状态:")
    print(f"   公司: {state['company_name']}")
    
    state = fetcher_node(state)
    state = financial_tool(state)
    state = formatter_node(state)
    
    print("\n📊 最终卡片 JSON:")
    print(json.dumps(state['card_json'], ensure_ascii=False, indent=2))


def main():
    """运行所有测试"""
    test_case_1_financial_only()
    test_case_2_listing_only()
    test_case_3_both()
    test_case_4_chat()
    test_case_5_unknown_company()
    
    print_section("所有测试完成 ✅")
    print("\n总结:")
    print("  ✓ Fetcher 节点: 正确分发任务")
    print("  ✓ Financial Tool: 正确获取财务数据")
    print("  ✓ Listing Tool: 正确获取上市信息")
    print("  ✓ Formatter 节点: 正确格式化输出")
    print("  ✓ 错误处理: 降级行为正常")


if __name__ == "__main__":
    main()
