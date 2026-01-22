from __future__ import annotations

"""
fetcher 节点：并行任务分发器

它在整个流程中的位置：
- analyzer 完成意图分析，设置好 need_financial 和 need_listing 开关
- fetcher 根据这些开关决定要触发哪些工具节点（可能是一个、两个或零个）
- 不做实际数据获取，只负责分发逻辑和路由决策
- 触发的工具节点会并行执行，完成后汇聚到 formatter

职责说明：
这个节点本身不做任何数据处理，它就像个'交通指挥'，看需求灯是什么颜色，
然后决定让哪些车（工具节点）通行。
"""

from typing import List, Literal

from ..state import State

# 定义可能的下一个节点类型
NextNode = Literal["financial_tool", "listing_tool", "formatter"]


def fetcher_node(state: State) -> State:
    """
    Fetcher 节点：根据并行开关分发任务
    
    职责：
    1. 读取 state 中的并行任务开关（need_financial、need_listing）
    2. 决定需要调用哪些工具节点
    3. 记录路由决策到 trace
    
    输入：state.need_financial, state.need_listing
    输出：更新 state（主要是 trace 记录）
    
    注意：
    - 本节点不直接调用工具，路由逻辑由 graph.py 中的条件边处理
    - 如果两个开关都是 false，会直接跳到 formatter
    """
    need_financial = state.get("need_financial", False)
    need_listing = state.get("need_listing", False)
    
    # 构建路由信息用于日志
    routes: List[str] = []
    
    if need_financial:
        routes.append("financial_tool")
    
    if need_listing:
        routes.append("listing_tool")
    
    # 如果没有任何工具需要调用，直接去 formatter
    if not routes:
        routes.append("formatter (直接)")
        # 既然不需要工具，把 parallel_done 都标记为 true
        state["parallel_done"]["financial"] = True
        state["parallel_done"]["listing"] = True
    
    # 记录分发决策
    state["trace"].append(f"fetcher 分发 -> {', '.join(routes)}")
    
    return state


def should_call_financial(state: State) -> bool:
    """
    条件判断：是否需要调用 financial_tool
    
    供 graph.py 的条件边使用
    """
    return state.get("need_financial", False)


def should_call_listing(state: State) -> bool:
    """
    条件判断：是否需要调用 listing_tool
    
    供 graph.py 的条件边使用
    """
    return state.get("need_listing", False)


def all_parallel_done(state: State) -> bool:
    """
    并行汇聚判断：所有需要的并行任务是否都完成了
    
    供 graph.py 的条件边使用，决定何时可以进入 formatter
    
    逻辑：
    - 如果需要 financial 但还没完成 -> False
    - 如果需要 listing 但还没完成 -> False
    - 其他情况 -> True（可以进入 formatter）
    """
    need_financial = state.get("need_financial", False)
    need_listing = state.get("need_listing", False)
    
    parallel_done = state.get("parallel_done", {"financial": False, "listing": False})
    
    # 如果需要某个工具但它还没完成，返回 False
    if need_financial and not parallel_done.get("financial", False):
        return False
    
    if need_listing and not parallel_done.get("listing", False):
        return False
    
    # 所有需要的都完成了
    return True