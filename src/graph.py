"""
graph.py - LangGraph 工作流编排

作用：
这是整个 Agent 的"交通枢纽"，定义了各个节点如何连接、数据如何流转。
就像搭积木一样，把 retriever、analyzer、fetcher、工具节点、formatter 串成一条流水线，
支持并行执行多个任务（Fan-out），然后在 formatter 汇总结果（Fan-in）。

流程图：
                 retrieve_node (RAG检索)
                       |
                    analyzer
                       |
                    (意图判断)
                    /       \\
               intent=chat   intent=financial/listing
                  |              |
                  |           fetcher (分发器)
                  |           /     \\
                  |     (并行触发)   (并行触发)
                  |      /              \\
                  |  financial_tool   listing_tool
                  |      \\              /
                  |       \\            /
                  |        (汇聚点)
                  |           |
                  +---> formatter ---> END
"""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, StateGraph

from .nodes.analyzer import analyzer_node
from .nodes.fetcher import fetcher_node
from .nodes.formatter import formatter_node
from .nodes.retriever import retrieve_node
from .state import State
from .tools.financial import financial_tool
from .tools.listing import listing_tool


def route_after_analyzer(state: State) -> Literal["fetcher", "formatter"]:
    """
    路由函数：analyzer 之后的分支决策
    
    决策逻辑：
    - 如果是普通对话（intent=chat），直接跳到 formatter 生成回复
    - 如果需要查询数据（financial/listing），进入 fetcher 分发到工具节点
    """
    intent = state.get("intent", "chat")
    
    if intent == "chat":
        # 对话模式：直接生成回复，不需要数据工具
        return "formatter"
    else:
        # 数据查询模式：需要 fetcher 来决定调用哪些工具
        return "fetcher"


def route_after_fetcher(state: State) -> list[Literal["financial_tool", "listing_tool", "formatter"]]:
    """
    路由函数：fetcher 之后的并行分发
    
    决策逻辑：
    - 根据 need_financial 和 need_listing 开关决定触发哪些工具
    - 可能触发 0 个、1 个或 2 个工具（并行执行）
    - 如果都不需要，直接进入 formatter
    
    返回值：包含下一步节点名称的列表（支持并行）
    """
    need_financial = state.get("need_financial", False)
    need_listing = state.get("need_listing", False)
    
    next_nodes = []
    
    if need_financial:
        next_nodes.append("financial_tool")
    
    if need_listing:
        next_nodes.append("listing_tool")
    
    # 如果没有任何工具需要调用，直接去 formatter
    if not next_nodes:
        next_nodes.append("formatter")
    
    return next_nodes


def build_graph() -> StateGraph:
    """
    构建 LangGraph 工作流
    
    步骤说明：
    1. 创建 StateGraph 实例，指定状态类型
    2. 添加所有节点（retriever、analyzer、fetcher、工具节点、formatter）
    3. 设置入口节点（从 retriever 开始，先检索相关文档）
    4. 连接各节点的边（包括条件边、并行边）
    5. 编译并返回可执行的 graph
    """
    # 步骤1：初始化 StateGraph
    graph = StateGraph(State)
    
    # 步骤2：添加所有节点
    graph.add_node("retrieve_node", retrieve_node)  # RAG 检索节点
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("fetcher", fetcher_node)
    graph.add_node("financial_tool", financial_tool)
    graph.add_node("listing_tool", listing_tool)
    graph.add_node("formatter", formatter_node)
    
    # 步骤3：设置入口节点（从 retrieve_node 开始，先进行 RAG 检索）
    graph.set_entry_point("retrieve_node")
    
    # 步骤4：连接主流程边
    
    # retrieve_node -> analyzer（检索完成后进入意图分析）
    graph.add_edge("retrieve_node", "analyzer")
    
    # analyzer -> 条件路由（chat 直达 formatter，其他走 fetcher）
    graph.add_conditional_edges(
        "analyzer",
        route_after_analyzer,
        {
            "fetcher": "fetcher",
            "formatter": "formatter"
        }
    )
    
    # fetcher -> 并行分发（Fan-out）
    # 根据 need_* 开关，可能触发 financial_tool、listing_tool 或直接到 formatter
    graph.add_conditional_edges(
        "fetcher",
        route_after_fetcher,
        # 这里不需要显式的映射，LangGraph 会根据返回的列表自动处理并行
    )
    
    # 并行汇聚（Fan-in）：工具节点完成后都汇入 formatter
    graph.add_edge("financial_tool", "formatter")
    graph.add_edge("listing_tool", "formatter")
    
    # formatter 是最后一个节点，完成后结束流程
    graph.add_edge("formatter", END)
    
    # 步骤5：编译图
    return graph.compile()


# 导出编译好的 graph 实例，供 main.py 使用
app = build_graph()
