# 中文伪代码：定义图结构（包含并行 Fan-out / Fan-in）

# 初始化 StateGraph(State)

# 添加节点:
#   - analyzer
#   - fetcher
#   - financial_tool
#   - listing_tool
#   - formatter

# 设置入口:
#   entry = analyzer

# 连接主流程:
#   analyzer -> 条件路由
#     如果 intent == "chat" : 直接进入 formatter
#     否则 : 进入 fetcher

# fetcher 节点逻辑（仅负责分发，不做实际抓取）:
#   如果 state.need_financial 为 true: 发送到 financial_tool
#   如果 state.need_listing 为 true: 发送到 listing_tool
#   如果两者都为 false: 直接进入 formatter

# 并行 Fan-out:
#   - fetcher 同时触发 financial_tool 与 listing_tool

# 并行 Fan-in（汇聚）:
#   - financial_tool -> formatter
#   - listing_tool -> formatter
#   - formatter 内部判断：若需并行且未完成，则等待

# 构建与返回 graph

# 说明
# - financial_tool 与 listing_tool 只写各自字段
# - formatter 负责合并所有数据并输出 card_json
