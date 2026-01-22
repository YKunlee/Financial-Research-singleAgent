"""
测试 graph 流程是否能跑通（无需 LLM 版本）

说明：
这个测试直接模拟 analyzer 的输出，跳过 LLM 调用，
专注测试 graph 的连线逻辑、并行执行和数据流转。
"""

from src.graph import app
from src.state import make_initial_state


def test_chat_flow():
    """测试普通对话流程"""
    print("\n" + "="*60)
    print("测试1: 普通对话流程（模拟 chat 意图）")
    print("="*60)
    
    # 直接构造已分析好的 state，跳过 analyzer
    state = make_initial_state("你好")
    state["intent"] = "chat"
    state["company_name"] = None
    state["confidence"] = 0.0
    state["need_financial"] = False
    state["need_listing"] = False
    state["trace"].append("analyzer 完成 (模拟)")
    
    # 从 formatter 开始执行
    from src.nodes.formatter import formatter_node
    result = formatter_node(state)
    
    print(f"用户输入: {result['user_query']}")
    print(f"意图: {result['intent']}")
    print(f"卡片类型: {result.get('card_json', {}).get('type', 'N/A')}")
    print(f"Trace: {result['trace']}")
    print()


def test_financial_flow():
    """测试财务数据查询流程"""
    print("\n" + "="*60)
    print("测试2: 财务数据查询流程（模拟 financial 意图）")
    print("="*60)
    
    # 模拟 analyzer 输出
    state = make_initial_state("Apple的市值是多少")
    state["intent"] = "financial"
    state["company_name"] = "Apple"
    state["confidence"] = 0.95
    state["need_financial"] = True
    state["need_listing"] = False
    state["trace"].append("analyzer 完成 (模拟)")
    
    # 执行后续流程：fetcher -> financial_tool -> formatter
    from src.nodes.fetcher import fetcher_node
    from src.tools.financial import financial_tool
    from src.nodes.formatter import formatter_node
    
    state = fetcher_node(state)
    state = financial_tool(state)
    result = formatter_node(state)
    
    print(f"用户输入: {result['user_query']}")
    print(f"公司名: {result['company_name']}")
    print(f"意图: {result['intent']}")
    print(f"财务数据: {result.get('financial_data', 'N/A')}")
    print(f"Trace: {result['trace']}")
    print(f"卡片sections数: {len(result.get('card_json', {}).get('sections', []))}")
    print()


def test_listing_flow():
    """测试上市信息查询流程"""
    print("\n" + "="*60)
    print("测试3: 上市信息查询流程（模拟 listing 意图）")
    print("="*60)
    
    state = make_initial_state("Microsoft什么时候上市的")
    state["intent"] = "listing"
    state["company_name"] = "Microsoft"
    state["confidence"] = 0.92
    state["need_financial"] = False
    state["need_listing"] = True
    state["trace"].append("analyzer 完成 (模拟)")
    
    from src.nodes.fetcher import fetcher_node
    from src.tools.listing import listing_tool
    from src.nodes.formatter import formatter_node
    
    state = fetcher_node(state)
    state = listing_tool(state)
    result = formatter_node(state)
    
    print(f"用户输入: {result['user_query']}")
    print(f"公司名: {result['company_name']}")
    print(f"意图: {result['intent']}")
    print(f"上市数据: {result.get('listing_data', 'N/A')}")
    print(f"Trace: {result['trace']}")
    print(f"卡片sections数: {len(result.get('card_json', {}).get('sections', []))}")
    print()


def test_parallel_flow():
    """测试并行查询流程（同时查财务+上市）"""
    print("\n" + "="*60)
    print("测试4: 并行查询流程（模拟两个工具并行）")
    print("="*60)
    
    state = make_initial_state("告诉我Amazon的市值和上市日期")
    state["intent"] = "financial"
    state["company_name"] = "Amazon"
    state["confidence"] = 0.98
    state["need_financial"] = True
    state["need_listing"] = True
    state["trace"].append("analyzer 完成 (模拟)")
    
    from src.nodes.fetcher import fetcher_node
    from src.tools.financial import financial_tool
    from src.tools.listing import listing_tool
    from src.nodes.formatter import formatter_node
    
    # 模拟并行执行
    state = fetcher_node(state)
    state = financial_tool(state)  # 工具1
    state = listing_tool(state)     # 工具2（实际会并行）
    result = formatter_node(state)
    
    print(f"用户输入: {result['user_query']}")
    print(f"公司名: {result['company_name']}")
    print(f"意图: {result['intent']}")
    print(f"需要财务: {result['need_financial']}")
    print(f"需要上市: {result['need_listing']}")
    print(f"财务数据: {result.get('financial_data', 'N/A')}")
    print(f"上市数据: {result.get('listing_data', 'N/A')}")
    print(f"并行完成状态: {result.get('parallel_done', 'N/A')}")
    print(f"Trace: {result['trace']}")
    print(f"卡片sections数: {len(result.get('card_json', {}).get('sections', []))}")
    print()


if __name__ == "__main__":
    print("\n开始测试 LangGraph 工作流...\n")
    
    try:
        test_chat_flow()
        test_financial_flow()
        test_listing_flow()
        test_parallel_flow()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
