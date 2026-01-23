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
- 使用 Annotated + operator.add 支持并行节点安全地向列表追加数据。
- 使用自定义 merge_parallel_done 函数支持 parallel_done 的并发更新。
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict, cast

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


def merge_parallel_done(left: ParallelDone, right: ParallelDone) -> ParallelDone:
    """
    并行完成状态合并函数
    
    当两个并行节点同时更新 parallel_done 时，
    LangGraph 会调用此函数合并它们的更新。
    
    策略：两边的字段都保留，True 优先（一旦某个任务完成就标记为 True）
    """
    return {
        "financial": left.get("financial", False) or right.get("financial", False),
        "listing": left.get("listing", False) or right.get("listing", False),
    }


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
    # 会话历史记忆（最近5轮对话的消息列表）
    conversation_history: Annotated[List[Dict[str, str]], operator.add]
    # 控制与诊断（使用 Annotated 支持并发追加）
    errors: Annotated[List[str], operator.add]
    trace: Annotated[List[str], operator.add]
    parallel_done: Annotated[ParallelDone, merge_parallel_done]


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
        "conversation_history": [],  # 空列表,后续由 app.py 填充
        "errors": [],
        "trace": [],
        "parallel_done": {"financial": False, "listing": False},
    }
    return cast(State, state)
