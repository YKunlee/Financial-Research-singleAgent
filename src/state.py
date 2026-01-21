"""
LangGraph 状态契约与字段定义。

页面逻辑：
1) analyzer 解析用户输入并写入公司名、意图、置信度与并行开关。
2) fetcher 只做分发，依据 need_* 触发工具节点。
3) financial_tool 与 listing_tool 只写各自结果并更新 parallel_done。
4) formatter 汇总所有字段，输出 card_json 或 chat_reply。

补充说明：
- State 是跨节点共享的唯一数据载体，字段必须全量初始化，避免隐式兜底。
- 各节点只读写与自己相关的字段，降低耦合与竞态风险。
- parallel_done 用于并行汇聚判断，确保 formatter 只在必要数据齐备时产出。
- errors 与 trace 用于错误显性暴露与执行追踪，便于排障与审计。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TypedDict, cast

IntentType = Literal["financial", "listing", "chat"]


class FinancialData(TypedDict):
    market_cap: str
    profit: str
    source: str


class ListingData(TypedDict):
    listed_date: str
    listing_status: str
    board: str
    source: str


class ParallelDone(TypedDict):
    financial: bool
    listing: bool


class State(TypedDict):
    # 用户输入
    user_query: str
    # LLM 解析结果
    company_name: Optional[str]
    intent: Optional[IntentType]
    confidence: Optional[float]
    # 并行任务开关
    need_financial: bool
    need_listing: bool
    # 任务执行结果（由工具节点写入）
    financial_data: Optional[FinancialData]
    listing_data: Optional[ListingData]
    # 日常对话回复（当 intent=chat）
    chat_reply: Optional[str]
    # 前端卡片输出
    card_json: Optional[Dict[str, Any]]
    # 控制与诊断
    errors: List[str]
    trace: List[str]
    parallel_done: ParallelDone


def make_initial_state(user_query: str) -> State:
    # 入参校验
    if not isinstance(user_query, str):
        raise TypeError("user_query 必须是 str。")
    if not user_query.strip():
        raise ValueError("user_query 不能为空。")
    # 把所有字段都初始化到一个 dict 里
    state: Dict[str, Any] = {
        "user_query": user_query,
        "company_name": None,
        "intent": None,
        "confidence": None,
        "need_financial": False,
        "need_listing": False,
        "financial_data": None,
        "listing_data": None,
        "chat_reply": None,
        "card_json": None,
        "errors": [],
        "trace": [],
        "parallel_done": {"financial": False, "listing": False},
    }
    return cast(State, state)
