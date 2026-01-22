"""
节点包 - 流程里的各个"岗位"

把整个查询流程想象成流水线，每个节点就是一个岗位：
- analyzer（还没写）：第一道岗位，看用户说了啥，提取出公司名和想查什么
- fetcher（还没写）：中间岗位，根据需求分配任务，可能同时派活给多个工具
- formatter（还没写）：最后一道岗位，把查到的数据整理成前端需要的格式

这些岗位之间传递的就是那个 State "信封"，上一个岗位填点东西，下一个岗位接着填
"""

# 注意：当前节点尚未实现，仅保留包结构
# from src.nodes.analyzer import analyzer
# from src.nodes.fetcher import fetcher
# from src.nodes.formatter import formatter

__all__ = [
    # "analyzer",
    # "fetcher",
    # "formatter",
]
