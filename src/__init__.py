"""
金融研究 Agent 系统核心包

这个包是整个项目的"大脑"，里面装着：
- 状态类型：就像是各个模块之间传递的"信封"，里面装着公司名、意图、查到的数据等
- 工具函数：financial_tool 去查市值盈利，listing_tool 去查上市信息
- 初始化函数：make_initial_state 用来准备一个干净的"信封"

你可以直接 import 这些东西来用，不用关心它们具体在哪个文件里实现的
"""

from src.state import (
    FinancialData,
    IntentType,
    ListingData,
    ParallelDone,
    State,
    make_initial_state,
)
from src.tools.financial import financial_tool
from src.tools.listing import listing_tool

__all__ = [
    # 状态类型
    "State",
    "FinancialData",
    "ListingData",
    "ParallelDone",
    "IntentType",
    # 状态初始化
    "make_initial_state",
    # 工具函数
    "financial_tool",
    "listing_tool",
]
