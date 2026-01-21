from __future__ import annotations

"""
financial_tool：金融数据工具（非 LLM）

它在整个流程中的位置：
- analyzer 从用户输入里解析公司名与意图（可能触发 need_financial）
- fetcher 就会去调用 financial_tool，依据 need_financial 决定是否调用本工具
- 本工具做的事很简单：根据公司名拿到市值等数据（现在是本地 mock），然后把结果写进 state.financial_data
  只负责“取数 + 结构化 + 写回 state”，不做任何 LLM 推理
- formatter 读取 state.financial_data，整理成前端要展示的卡片 JSON

数据从哪里来：
- 目前使用本地内置的 mock 数据（LOCAL_FINANCIAL_DATA），便于先跑通流程
- 后续可替换为真实数据源：外部 API / 数据库 / 文件等（保持输出字段不变即可）

数据要给到哪里去：
- 写入 state.financial_data（字段见 src/state.py: FinancialData）
- 同时设置 state.parallel_done.financial=True，供并行汇聚判断
"""

from typing import Dict

from src.state import FinancialData, State

# 本地 mock 数据；后续可替换为真实数据源（API/数据库）。
LOCAL_FINANCIAL_DATA: Dict[str, FinancialData] = {
    "Apple": {"market_cap": "2.8T", "profit": "96B", "source": "local_mock"},
    "Microsoft": {"market_cap": "3.0T", "profit": "88B", "source": "local_mock"},
    "Amazon": {"market_cap": "1.8T", "profit": "30B", "source": "local_mock"},
}


def financial_tool(state: State) -> State:
    # 输入：state.company_name
    # 输出：state.financial_data + state.parallel_done.financial
    company = state.get("company_name")
    if not company:
        # 缺少公司名时不抛异常，写入 errors 并标记并行任务完成，避免汇聚节点一直等待。
        state["errors"].append("financial_tool: company_name missing")
        state["parallel_done"]["financial"] = True
        return state

    # 步骤1：取数（当前为本地 mock；未来可替换为 API/DB）
    data = LOCAL_FINANCIAL_DATA.get(
        company, {"market_cap": "unknown", "profit": "unknown", "source": "local_mock"}
    )
    # 步骤2：解析为统一字段（market_cap/profit/source）
    # 步骤3：写回 state（只写本工具负责的字段，降低耦合）
    state["financial_data"] = dict(data)

    # 动作：打印市值（便于在 CLI / 日志中直接看到结果）
    print(f"{company} market cap: {data['market_cap']}")

    # 步骤4：标记并行任务完成，供 formatter/fan-in 判断
    state["parallel_done"]["financial"] = True
    state["trace"].append("financial_tool done")
    return state
