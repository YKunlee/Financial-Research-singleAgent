from __future__ import annotations

"""
listing_tool：上市信息工具（非 LLM）

它在整个流程中的位置：
- analyzer 从用户输入里解析公司名与意图（可能触发 need_listing）
- fetcher 依据 need_listing 决定是否调用本工具
- 本工具只负责“取数 + 结构化 + 写回 state”，不做任何 LLM 推理
- formatter 读取 state.listing_data，组装前端卡片 JSON

数据从哪里来：
- 目前使用本地内置的 mock 数据（LOCAL_LISTING_DATA）
- 后续可替换为真实数据源：交易所/券商 API、数据库、爬虫等（保持输出字段不变即可）

数据要给到哪里去：
- 写入 state.listing_data（字段见 src/state.py: ListingData）
- 同时设置 state.parallel_done.listing=True，供并行汇聚判断
"""

from typing import Dict

from src.state import ListingData, State

# 本地 mock 数据；后续可替换为真实数据源（API/数据库）。
LOCAL_LISTING_DATA: Dict[str, ListingData] = {
    "Apple": {
        "listed_date": "1980-12-12",
        "listing_status": "listed",
        "board": "NASDAQ",
        "source": "local_mock",
    },
    "Microsoft": {
        "listed_date": "1986-03-13",
        "listing_status": "listed",
        "board": "NASDAQ",
        "source": "local_mock",
    },
    "Amazon": {
        "listed_date": "1997-05-15",
        "listing_status": "listed",
        "board": "NASDAQ",
        "source": "local_mock",
    },
}


def listing_tool(state: State) -> dict:
    # 输入：state.company_name
    # 输出：只返回本工具修改的字段（避免并发冲突）
    company = state.get("company_name")
    if not company:
        # 缺少公司名时不抛异常，写入 errors 并标记并行任务完成，避免汇聚节点一直等待。
        return {
            "errors": ["listing_tool: company_name missing"],
            "parallel_done": {"financial": False, "listing": True}
        }

    # 步骤1：取数（当前为本地 mock；未来可替换为 API/DB）
    data = LOCAL_LISTING_DATA.get(
        company,
        {
            "listed_date": "unknown",
            "listing_status": "unknown",
            "board": "unknown",
            "source": "local_mock",
        },
    )
    # 步骤2：解析为统一字段（listed_date/listing_status/board/source）
    # 步骤3：只返回本工具负责的字段，降低耦合

    # 动作：打印上市日期（便于在 CLI / 日志中直接看到结果）
    print(f"{company} listed date: {data['listed_date']}")

    # 步骤4：返回修改的字段（不返回整个 state）
    # 注意：parallel_done 只标记自己的任务完成，另一个字段保持原值
    return {
        "listing_data": dict(data),
        "parallel_done": {"financial": False, "listing": True},
        "trace": ["listing_tool done"]
    }
