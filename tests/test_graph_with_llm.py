"""
完整测试：使用 LLM 进行端到端测试

说明：
这个测试会调用真实的 LLM（GPT-4o-mini），
验证从用户输入 -> analyzer -> fetcher -> tools -> formatter 的完整流程。

前置条件：
1. 需要在 .env 中配置 GPT_4O_MINI_API_KEY
2. 需要安装 python-dotenv（pip install python-dotenv）
"""

from src.graph import app
from src.state import make_initial_state
import json


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "="*70)
    print(f"{title}")
    print("="*70)


def print_result(result: dict):
    """格式化打印结果"""
    print(f"📝 用户输入: {result['user_query']}")
    print(f"🏢 公司名: {result.get('company_name', 'N/A')}")
    print(f"🎯 意图: {result.get('intent', 'N/A')}")
    print(f"📊 置信度: {result.get('confidence', 'N/A')}")
    print(f"💰 需要财务数据: {result.get('need_financial', False)}")
    print(f"📈 需要上市数据: {result.get('need_listing', False)}")
    
    if result.get('financial_data'):
        print(f"💵 财务数据: {result['financial_data']}")
    
    if result.get('listing_data'):
        print(f"📅 上市数据: {result['listing_data']}")
    
    if result.get('chat_reply'):
        print(f"💬 对话回复: {result['chat_reply']}")
    
    if result.get('errors'):
        print(f"⚠️  错误信息: {result['errors']}")
    
    print(f"🔍 执行追踪:")
    for trace in result.get('trace', []):
        print(f"   - {trace}")
    
    if result.get('card_json'):
        card = result['card_json']
        print(f"🎴 卡片类型: {card.get('type', 'N/A')}")
        if card.get('sections'):
            print(f"📦 数据区块数: {len(card['sections'])}")
    print()


def test_chat():
    """测试1: 普通对话"""
    print_section("测试1: 普通对话（应该触发 chat 模式）")
    
    state = make_initial_state("你好")
    result = app.invoke(state)
    print_result(result)


def test_financial():
    """测试2: 财务查询"""
    print_section("测试2: 财务查询（应该触发 financial_tool）")
    
    state = make_initial_state("Apple的市值是多少")
    result = app.invoke(state)
    print_result(result)


def test_listing():
    """测试3: 上市信息查询"""
    print_section("测试3: 上市信息查询（应该触发 listing_tool）")
    
    state = make_initial_state("Microsoft什么时候上市的")
    result = app.invoke(state)
    print_result(result)


def test_parallel():
    """测试4: 并行查询"""
    print_section("测试4: 并行查询（应该同时触发两个工具）")
    
    state = make_initial_state("告诉我Amazon的市值和上市日期")
    result = app.invoke(state)
    print_result(result)


def test_unknown_company():
    """测试5: 未知公司"""
    print_section("测试5: 未知公司（应该返回未知数据）")
    
    state = make_initial_state("Tesla的市值是多少")
    result = app.invoke(state)
    print_result(result)


def main():
    """主测试流程"""
    print("\n" + "🚀"*35)
    print("   LangGraph 完整流程测试（使用 GPT-4o-mini）")
    print("🚀"*35)
    
    try:
        test_chat()
        test_financial()
        test_listing()
        test_parallel()
        test_unknown_company()
        
        print_section("✅ 所有测试完成！")
        print("\n🎉 恭喜！LangGraph 工作流已完全打通，包括：")
        print("   ✓ LLM 意图分析")
        print("   ✓ 条件路由")
        print("   ✓ 并行执行")
        print("   ✓ 数据汇聚")
        print("   ✓ 结果格式化")
        print()
        
    except Exception as e:
        print_section("❌ 测试失败")
        print(f"错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n💡 提示:")
        print("   1. 检查 .env 文件是否存在")
        print("   2. 确认 GPT_4O_MINI_API_KEY 是否正确配置")
        print("   3. 确保安装了 python-dotenv: pip install python-dotenv")
        print()


if __name__ == "__main__":
    main()
