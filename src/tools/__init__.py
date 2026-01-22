"""
工具箱 - 专门负责"干活"的函数

这里面有两个小帮手：
- financial_tool：问它"这家公司市值多少、赚了多少钱"，它就去查
- listing_tool：问它"这家公司啥时候上市的、在哪个板块"，它就去查

现在还没接真实数据源，用的是本地写死的测试数据
等后面接上真实 API 或数据库，把数据源换掉就行，其他地方不用动
"""

from src.tools.financial import financial_tool
from src.tools.listing import listing_tool

__all__ = [
    "financial_tool",
    "listing_tool",
]
