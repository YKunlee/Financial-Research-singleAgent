"""
节点包 - 流程里的各个"岗位"

把整个查询流程想象成流水线，每个节点就是一个岗位：
- analyzer：第一道岗位，看用户说了啥，提取出公司名和想查什么
- fetcher：中间岗位，根据需求分配任务，可能同时派活给多个工具
- formatter：最后一道岗位，把查到的数据整理成前端需要的格式

这些岗位之间传递的就是那个 State "信封"，上一个岗位填点东西，下一个岗位接着填
"""

from .analyzer import analyzer_node
from .fetcher import fetcher_node, should_call_financial, should_call_listing, all_parallel_done
from .formatter import formatter_node

__all__ = [
    "analyzer_node",
    "fetcher_node",
    "formatter_node",
    "should_call_financial",
    "should_call_listing",
    "all_parallel_done",
]
