"""
简化版上下文记忆测试 - 快速验证核心功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.state import make_initial_state
from src.nodes.analyzer import analyzer_node


def main():
    """运行核心测试场景"""
    print("\n" + "=" * 80)
    print("【快速测试】会话上下文记忆功能")
    print("=" * 80)
    
    # 测试1：正常指代
    print("\n测试1: 腾讯的市值 → 它的市盈率")
    state1 = make_initial_state("腾讯的市值")
    result1 = analyzer_node(state1)
    print(f"  第1轮 - 公司: {result1['company_name']}, 意图: {result1['intent']}")
    
    state2 = make_initial_state("它的市盈率呢")
    state2["conversation_history"] = [
        {"role": "user", "content": "腾讯的市值"},
        {"role": "assistant", "content": "腾讯的市值是 xxx"}
    ]
    result2 = analyzer_node(state2)
    print(f"  第2轮 - 公司: {result2['company_name']}, 意图: {result2['intent']}")
    
    success1 = result2["company_name"] == "腾讯"
    print(f"  结果: {'✅ 通过' if success1 else '❌ 失败'}")
    
    # 测试2：无历史
    print("\n测试2: 它的市值（无历史）")
    state3 = make_initial_state("它的市值")
    result3 = analyzer_node(state3)
    print(f"  公司: {result3['company_name']}, 意图: {result3['intent']}")
    
    success2 = result3["intent"] == "chat"
    print(f"  结果: {'✅ 通过' if success2 else '❌ 失败'}")
    
    # 总结
    print("\n" + "=" * 80)
    if success1 and success2:
        print("🎉 所有核心测试通过!")
        print("=" * 80)
        return 0
    else:
        print("❌ 部分测试失败")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
