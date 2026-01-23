"""
测试会话上下文记忆功能

测试场景：
1. 正常指代：腾讯的市值 → 它的市盈率 → 应识别为腾讯
2. 无历史指代：它的市值 → 应降级为 chat（没有公司上下文）
3. 多轮切换：腾讯的市值 → 阿里的利润 → 它的市盈率 → 应识别为阿里
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.state import make_initial_state
from src.nodes.analyzer import analyzer_node


def test_normal_reference():
    """
    测试场景1：正常指代关系
    用户先问"腾讯的市值"，再问"它的市盈率"
    预期：第二次应该识别出公司是"腾讯"
    """
    print("\n" + "=" * 80)
    print("【测试1】正常指代关系")
    print("=" * 80)
    
    # 第一轮：建立上下文
    print("\n第一轮：用户问 '腾讯的市值'")
    state1 = make_initial_state("腾讯的市值")
    result1 = analyzer_node(state1)
    
    print(f"识别公司: {result1['company_name']}")
    print(f"意图: {result1['intent']}")
    print(f"置信度: {result1['confidence']}")
    
    assert result1["company_name"] == "腾讯", f"第一轮应该识别为腾讯，实际为: {result1['company_name']}"
    assert result1["intent"] == "financial", f"第一轮意图应该是financial，实际为: {result1['intent']}"
    
    # 第二轮：使用指代词，传入历史
    print("\n第二轮：用户问 '它的市盈率呢'（使用指代词）")
    state2 = make_initial_state("它的市盈率呢")
    state2["conversation_history"] = [
        {"role": "user", "content": "腾讯的市值"},
        {"role": "assistant", "content": "腾讯的市值是 xxx"}
    ]
    result2 = analyzer_node(state2)
    
    print(f"识别公司: {result2['company_name']}")
    print(f"意图: {result2['intent']}")
    print(f"置信度: {result2['confidence']}")
    
    assert result2["company_name"] == "腾讯", f"第二轮应该从历史推断为腾讯，实际为: {result2['company_name']}"
    assert result2["intent"] == "financial", f"第二轮意图应该是financial，实际为: {result2['intent']}"
    
    print("\n✅ 测试1通过：能够正确理解指代关系")


def test_no_history_reference():
    """
    测试场景2：无历史上下文的指代
    用户直接问"它的市值"（没有历史）
    预期：应该降级为 chat（缺少上下文信息）
    """
    print("\n" + "=" * 80)
    print("【测试2】无历史上下文的指代")
    print("=" * 80)
    
    print("\n用户直接问 '它的市值'（没有历史）")
    state = make_initial_state("它的市值")
    result = analyzer_node(state)
    
    print(f"识别公司: {result['company_name']}")
    print(f"意图: {result['intent']}")
    print(f"置信度: {result['confidence']}")
    
    # 因为没有历史上下文，LLM 应该无法推断公司名
    # 根据业务规则，无公司名时应该降级为 chat
    assert result["intent"] == "chat", f"无历史时使用指代词应该降级为chat，实际为: {result['intent']}"
    
    print("\n✅ 测试2通过：能够识别缺少上下文的情况")


def test_multiple_companies_reference():
    """
    测试场景3：多轮切换公司
    用户先问"腾讯的市值"，再问"阿里的利润"，最后问"它的市盈率"
    预期：最后应该识别为"阿里"（最近提到的公司）
    """
    print("\n" + "=" * 80)
    print("【测试3】多轮切换公司的指代")
    print("=" * 80)
    
    # 第一轮：腾讯
    print("\n第一轮：用户问 '腾讯的市值'")
    state1 = make_initial_state("腾讯的市值")
    result1 = analyzer_node(state1)
    print(f"识别公司: {result1['company_name']}")
    
    # 第二轮：切换到阿里
    print("\n第二轮：用户问 '阿里的利润'")
    state2 = make_initial_state("阿里的利润")
    state2["conversation_history"] = [
        {"role": "user", "content": "腾讯的市值"},
        {"role": "assistant", "content": "腾讯的市值是 xxx"}
    ]
    result2 = analyzer_node(state2)
    print(f"识别公司: {result2['company_name']}")
    assert "阿里" in result2["company_name"], f"第二轮应该识别为阿里，实际为: {result2['company_name']}"
    
    # 第三轮：使用指代词，应该指向最近的"阿里"
    print("\n第三轮：用户问 '它的市盈率呢'（使用指代词）")
    state3 = make_initial_state("它的市盈率呢")
    state3["conversation_history"] = [
        {"role": "user", "content": "腾讯的市值"},
        {"role": "assistant", "content": "腾讯的市值是 xxx"},
        {"role": "user", "content": "阿里的利润"},
        {"role": "assistant", "content": "阿里的利润是 yyy"}
    ]
    result3 = analyzer_node(state3)
    
    print(f"识别公司: {result3['company_name']}")
    print(f"意图: {result3['intent']}")
    
    assert "阿里" in result3["company_name"], f"第三轮应该识别为阿里（最近提到的），实际为: {result3['company_name']}"
    assert result3["intent"] == "financial", f"第三轮意图应该是financial，实际为: {result3['intent']}"
    
    print("\n✅ 测试3通过：能够正确追踪最近提到的公司")


def test_comprehensive_reference():
    """
    测试场景4：综合测试 - 模拟真实对话流程
    """
    print("\n" + "=" * 80)
    print("【测试4】综合对话流程测试")
    print("=" * 80)
    
    conversation_history = []
    
    # 第一轮：普通对话
    print("\n第1轮：'你好'")
    state = make_initial_state("你好")
    state["conversation_history"] = conversation_history
    result = analyzer_node(state)
    print(f"→ 意图: {result['intent']}")
    assert result["intent"] == "chat"
    
    conversation_history.append({"role": "user", "content": "你好"})
    conversation_history.append({"role": "assistant", "content": "你好！"})
    
    # 第二轮：查询腾讯
    print("\n第2轮：'腾讯的市值是多少'")
    state = make_initial_state("腾讯的市值是多少")
    state["conversation_history"] = conversation_history
    result = analyzer_node(state)
    print(f"→ 公司: {result['company_name']}, 意图: {result['intent']}")
    assert result["company_name"] == "腾讯"
    
    conversation_history.append({"role": "user", "content": "腾讯的市值是多少"})
    conversation_history.append({"role": "assistant", "content": "腾讯的市值是..."})
    
    # 第三轮：继续查询腾讯（使用指代词）
    print("\n第3轮：'那它的利润呢'")
    state = make_initial_state("那它的利润呢")
    state["conversation_history"] = conversation_history
    result = analyzer_node(state)
    print(f"→ 公司: {result['company_name']}, 意图: {result['intent']}")
    assert result["company_name"] == "腾讯"
    
    conversation_history.append({"role": "user", "content": "那它的利润呢"})
    conversation_history.append({"role": "assistant", "content": "腾讯的利润是..."})
    
    # 第四轮：继续查询（省略公司名）
    print("\n第4轮：'上市时间呢'")
    state = make_initial_state("上市时间呢")
    state["conversation_history"] = conversation_history
    result = analyzer_node(state)
    print(f"→ 公司: {result['company_name']}, 意图: {result['intent']}")
    assert result["company_name"] == "腾讯"
    assert result["intent"] == "listing"
    
    print("\n✅ 测试4通过：综合对话流程正常")


if __name__ == "__main__":
    try:
        test_normal_reference()
        test_no_history_reference()
        test_multiple_companies_reference()
        test_comprehensive_reference()
        
        print("\n" + "=" * 80)
        print("🎉 所有测试通过！会话上下文记忆功能正常工作")
        print("=" * 80)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
